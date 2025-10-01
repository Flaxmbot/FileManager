"""
Custom command integration service for bot automation
"""

import asyncio
import json
import logging
import os
import subprocess
import shlex
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from enum import Enum
import uuid

from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.device import Device
from .websocket_service import get_websocket_service


class CommandStatus(Enum):
    """Command execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class CommandIntegrationService:
    """Service for custom command integrations"""

    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.logger = logging.getLogger(__name__)

        # Active command executions
        self.active_commands: Dict[str, Dict] = {}

        # Command history
        self.command_history: List[Dict] = []

        # Maximum concurrent commands per device
        self.max_concurrent_commands = 3

        # Command timeout (seconds)
        self.command_timeout = 300  # 5 minutes

        # Cleanup task
        self.cleanup_task = None

    async def start_service(self):
        """Start the command integration service"""
        self.cleanup_task = asyncio.create_task(self._cleanup_expired_commands())
        self.logger.info("Command integration service started")

    async def stop_service(self):
        """Stop the command integration service"""
        if self.cleanup_task:
            self.cleanup_task.cancel()

        # Cancel all active commands
        for command_id in list(self.active_commands.keys()):
            await self.cancel_command(command_id)

        self.logger.info("Command integration service stopped")

    async def execute_command(
        self,
        device_id: str,
        command: str,
        parameters: Dict[str, Any] = None,
        async_execution: bool = False
    ) -> str:
        """Execute a command on a device"""
        try:
            # Check if device can accept more commands
            device_commands = [
                cmd for cmd in self.active_commands.values()
                if cmd["device_id"] == device_id and cmd["status"] in [CommandStatus.RUNNING, CommandStatus.PENDING]
            ]

            if len(device_commands) >= self.max_concurrent_commands:
                raise Exception(f"Device {device_id} has reached maximum concurrent commands limit")

            # Generate command ID
            command_id = str(uuid.uuid4())

            # Create command execution record
            command_record = {
                "command_id": command_id,
                "device_id": device_id,
                "command": command,
                "parameters": parameters or {},
                "status": CommandStatus.PENDING,
                "start_time": datetime.now(),
                "end_time": None,
                "result": None,
                "error": None,
                "async_execution": async_execution
            }

            self.active_commands[command_id] = command_record
            self.command_history.append(command_record.copy())

            # Send command to device
            command_message = {
                "type": "execute_command",
                "command_id": command_id,
                "command": command,
                "parameters": parameters or {},
                "timestamp": datetime.now().isoformat()
            }

            success = self.websocket_service.send_message_to_device(device_id, command_message)

            if not success:
                # Remove from active commands if send failed
                if command_id in self.active_commands:
                    del self.active_commands[command_id]

                command_record["status"] = CommandStatus.FAILED
                command_record["error"] = "Failed to send command to device"
                command_record["end_time"] = datetime.now()

                raise Exception("Failed to send command to device")

            # Update status to running
            command_record["status"] = CommandStatus.RUNNING

            # If not async, wait for completion
            if not async_execution:
                return await self._wait_for_command_completion(command_id)
            else:
                return command_id

        except Exception as e:
            self.logger.error(f"Error executing command on device {device_id}: {e}")
            raise

    async def _wait_for_command_completion(self, command_id: str, timeout: int = None) -> str:
        """Wait for command completion"""
        timeout = timeout or self.command_timeout
        start_time = datetime.now()

        while datetime.now() - start_time < timedelta(seconds=timeout):
            if command_id not in self.active_commands:
                # Command completed or was removed
                break

            command_record = self.active_commands[command_id]
            if command_record["status"] in [CommandStatus.COMPLETED, CommandStatus.FAILED, CommandStatus.CANCELLED]:
                break

            await asyncio.sleep(1)

        # Get final result
        if command_id in self.active_commands:
            command_record = self.active_commands[command_id]

            if command_record["status"] == CommandStatus.RUNNING:
                # Command timed out
                command_record["status"] = CommandStatus.TIMEOUT
                command_record["error"] = "Command execution timed out"
                command_record["end_time"] = datetime.now()

                # Remove from active commands
                del self.active_commands[command_id]

                raise Exception("Command execution timed out")

            # Remove from active commands
            del self.active_commands[command_id]

            if command_record["status"] == CommandStatus.FAILED:
                raise Exception(command_record["error"] or "Command execution failed")

            return command_record["result"]
        else:
            raise Exception("Command not found or already completed")

    async def cancel_command(self, command_id: str) -> bool:
        """Cancel a running command"""
        try:
            if command_id not in self.active_commands:
                return False

            command_record = self.active_commands[command_id]

            # Send cancellation to device
            cancel_message = {
                "type": "cancel_command",
                "command_id": command_id,
                "timestamp": datetime.now().isoformat()
            }

            device_id = command_record["device_id"]
            self.websocket_service.send_message_to_device(device_id, cancel_message)

            # Update command status
            command_record["status"] = CommandStatus.CANCELLED
            command_record["end_time"] = datetime.now()

            # Remove from active commands
            del self.active_commands[command_id]

            self.logger.info(f"Command {command_id} cancelled")
            return True

        except Exception as e:
            self.logger.error(f"Error cancelling command {command_id}: {e}")
            return False

    def handle_command_result(self, device_id: str, result_data: Dict) -> bool:
        """Handle command result from device"""
        try:
            command_id = result_data.get("command_id")
            if not command_id or command_id not in self.active_commands:
                self.logger.warning(f"Received result for unknown command: {command_id}")
                return False

            command_record = self.active_commands[command_id]

            # Update command record
            command_record["status"] = CommandStatus.COMPLETED
            command_record["result"] = result_data.get("result")
            command_record["end_time"] = datetime.now()

            self.logger.info(f"Command {command_id} completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Error handling command result: {e}")
            return False

    def handle_command_error(self, device_id: str, error_data: Dict) -> bool:
        """Handle command error from device"""
        try:
            command_id = error_data.get("command_id")
            if not command_id or command_id not in self.active_commands:
                self.logger.warning(f"Received error for unknown command: {command_id}")
                return False

            command_record = self.active_commands[command_id]

            # Update command record
            command_record["status"] = CommandStatus.FAILED
            command_record["error"] = error_data.get("error", "Unknown error")
            command_record["end_time"] = datetime.now()

            self.logger.error(f"Command {command_id} failed: {command_record['error']}")
            return True

        except Exception as e:
            self.logger.error(f"Error handling command error: {e}")
            return False

    async def _cleanup_expired_commands(self):
        """Clean up expired commands"""
        while True:
            try:
                current_time = datetime.now()
                expired_commands = []

                for command_id, command_record in self.active_commands.items():
                    if command_record["status"] == CommandStatus.RUNNING:
                        start_time = command_record["start_time"]
                        if current_time - start_time > timedelta(seconds=self.command_timeout):
                            expired_commands.append(command_id)

                for command_id in expired_commands:
                    self.logger.warning(f"Command {command_id} timed out, cancelling")
                    await self.cancel_command(command_id)

                await asyncio.sleep(30)  # Check every 30 seconds

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(30)

    def get_command_status(self, command_id: str) -> Optional[Dict]:
        """Get command execution status"""
        if command_id in self.active_commands:
            return self.active_commands[command_id].copy()

        # Check history
        for record in reversed(self.command_history):
            if record["command_id"] == command_id:
                return record.copy()

        return None

    def get_device_commands(self, device_id: str) -> List[Dict]:
        """Get all commands for a device"""
        device_commands = []

        # Active commands
        for command_record in self.active_commands.values():
            if command_record["device_id"] == device_id:
                device_commands.append(command_record.copy())

        # Recent history (last 50 commands)
        for record in reversed(self.command_history[-50:]):
            if record["device_id"] == device_id:
                device_commands.append(record.copy())

        return device_commands

    def get_service_stats(self) -> Dict:
        """Get service statistics"""
        active_count = len(self.active_commands)
        running_commands = [
            cmd for cmd in self.active_commands.values()
            if cmd["status"] == CommandStatus.RUNNING
        ]

        return {
            "active_commands": active_count,
            "running_commands": len(running_commands),
            "total_history": len(self.command_history),
            "max_concurrent_commands": self.max_concurrent_commands,
            "command_timeout": self.command_timeout
        }


# Predefined command templates
COMMAND_TEMPLATES = {
    "screenshot": {
        "description": "Take device screenshot",
        "parameters": {},
        "category": "system"
    },
    "get_device_info": {
        "description": "Get detailed device information",
        "parameters": {},
        "category": "system"
    },
    "list_apps": {
        "description": "List installed applications",
        "parameters": {
            "system_apps": {"type": "boolean", "default": False, "description": "Include system apps"}
        },
        "category": "apps"
    },
    "backup_contacts": {
        "description": "Backup device contacts",
        "parameters": {
            "format": {"type": "string", "default": "vcf", "description": "Backup format (vcf/json)"}
        },
        "category": "backup"
    },
    "get_location": {
        "description": "Get current device location",
        "parameters": {
            "accuracy": {"type": "string", "default": "high", "description": "Location accuracy"}
        },
        "category": "location"
    },
    "scan_network": {
        "description": "Scan network for devices",
        "parameters": {},
        "category": "network"
    },
    "get_battery_info": {
        "description": "Get battery information",
        "parameters": {},
        "category": "system"
    },
    "clear_cache": {
        "description": "Clear application cache",
        "parameters": {
            "package_name": {"type": "string", "description": "Specific package to clear (optional)"}
        },
        "category": "maintenance"
    }
}


class CommandTemplateManager:
    """Manager for command templates"""

    def __init__(self):
        self.templates = COMMAND_TEMPLATES.copy()

    def register_template(self, name: str, template: Dict):
        """Register a new command template"""
        self.templates[name] = template

    def get_template(self, name: str) -> Optional[Dict]:
        """Get command template by name"""
        return self.templates.get(name)

    def get_templates_by_category(self, category: str) -> Dict:
        """Get all templates in a category"""
        return {
            name: template for name, template in self.templates.items()
            if template.get("category") == category
        }

    def get_all_templates(self) -> Dict:
        """Get all command templates"""
        return self.templates.copy()

    def validate_command(self, command: str, parameters: Dict = None) -> bool:
        """Validate command and parameters against template"""
        template = self.get_template(command)
        if not template:
            return False

        # TODO: Implement parameter validation based on template schema
        return True


# Global instances
command_integration_service = CommandIntegrationService()
command_template_manager = CommandTemplateManager()


def get_command_integration_service() -> CommandIntegrationService:
    """Get command integration service instance"""
    return command_integration_service


def get_command_template_manager() -> CommandTemplateManager:
    """Get command template manager instance"""
    return command_template_manager