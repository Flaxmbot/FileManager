"""
WebSocket service for real-time communication with Android devices
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional
from datetime import datetime, timedelta
import secrets

import websockets
from websockets.server import WebSocketServerProtocol
from sqlalchemy.orm import Session

from ..models.device import Device
from ..models.user import User
from ..database.session import get_db


class WebSocketService:
    """WebSocket service for real-time device communication"""

    def __init__(self):
        self.connected_devices: Dict[str, WebSocketServerProtocol] = {}
        self.device_auth_tokens: Dict[str, str] = {}
        self.device_heartbeat: Dict[str, datetime] = {}
        self.logger = logging.getLogger(__name__)

        # Configuration
        self.heartbeat_timeout = 60  # seconds
        self.cleanup_interval = 30   # seconds

        # Start cleanup task
        self.cleanup_task = None

    async def start_server(self, host: str = "0.0.0.0", port: int = 8765):
        """Start WebSocket server"""
        self.logger.info(f"Starting WebSocket server on {host}:{port}")

        # Start cleanup task
        self.cleanup_task = asyncio.create_task(self._cleanup_stale_connections())

        try:
            async with websockets.serve(
                self._handle_connection,
                host,
                port,
                ping_interval=25,
                ping_timeout=10,
                close_timeout=5
            ):
                await asyncio.Future()  # Run forever
        except Exception as e:
            self.logger.error(f"WebSocket server error: {e}")
        finally:
            if self.cleanup_task:
                self.cleanup_task.cancel()

    async def _handle_connection(self, websocket: WebSocketServerProtocol, path: str):
        """Handle new WebSocket connection"""
        try:
            # Parse path to extract device ID
            device_id = self._extract_device_id(path)
            if not device_id:
                await websocket.close(1008, "Invalid device ID in path")
                return

            self.logger.info(f"New connection attempt for device: {device_id}")

            # Authenticate device
            auth_success = await self._authenticate_device(websocket, device_id)
            if not auth_success:
                await websocket.close(1008, "Authentication failed")
                return

            # Register device connection
            self.connected_devices[device_id] = websocket
            self.device_heartbeat[device_id] = datetime.now()

            self.logger.info(f"Device {device_id} connected successfully")

            try:
                # Handle messages from device
                async for message in websocket:
                    await self._handle_message(device_id, message)

            except websockets.exceptions.ConnectionClosed:
                self.logger.info(f"Device {device_id} connection closed")
            except Exception as e:
                self.logger.error(f"Error handling device {device_id}: {e}")
            finally:
                # Cleanup device connection
                await self._cleanup_device(device_id)

        except Exception as e:
            self.logger.error(f"Connection handler error: {e}")

    def _extract_device_id(self, path: str) -> Optional[str]:
        """Extract device ID from WebSocket path"""
        try:
            # Expected path format: /ws/device/{device_id}
            parts = path.strip('/').split('/')
            if len(parts) >= 3 and parts[0] == 'ws' and parts[1] == 'device':
                return parts[2]
            return None
        except Exception:
            return None

    async def _authenticate_device(self, websocket: WebSocketServerProtocol, device_id: str) -> bool:
        """Authenticate device connection"""
        try:
            # Wait for authentication message
            try:
                auth_message = await asyncio.wait_for(
                    websocket.recv(),
                    timeout=10.0
                )
            except asyncio.TimeoutError:
                self.logger.warning(f"Authentication timeout for device {device_id}")
                return False

            # Parse authentication message
            try:
                auth_data = json.loads(auth_message)
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid authentication JSON for device {device_id}")
                return False

            # Validate authentication data
            if not self._validate_auth_data(auth_data, device_id):
                return False

            # Generate and store auth token
            auth_token = secrets.token_urlsafe(32)
            self.device_auth_tokens[device_id] = auth_token

            # Send authentication success response
            response = {
                "type": "auth_success",
                "token": auth_token,
                "timestamp": datetime.now().isoformat()
            }
            await websocket.send(json.dumps(response))

            return True

        except Exception as e:
            self.logger.error(f"Authentication error for device {device_id}: {e}")
            return False

    def _validate_auth_data(self, auth_data: dict, device_id: str) -> bool:
        """Validate device authentication data"""
        try:
            # Check required fields
            required_fields = ["device_id", "app_version", "timestamp"]
            for field in required_fields:
                if field not in auth_data:
                    self.logger.warning(f"Missing field '{field}' in auth data")
                    return False

            # Validate device ID matches
            if auth_data["device_id"] != device_id:
                self.logger.warning(f"Device ID mismatch: {auth_data['device_id']} != {device_id}")
                return False

            # Validate timestamp is recent (within 5 minutes)
            try:
                auth_time = datetime.fromisoformat(auth_data["timestamp"])
                if datetime.now() - auth_time > timedelta(minutes=5):
                    self.logger.warning("Authentication timestamp too old")
                    return False
            except (ValueError, TypeError):
                self.logger.warning("Invalid timestamp format")
                return False

            return True

        except Exception as e:
            self.logger.error(f"Auth validation error: {e}")
            return False

    async def _handle_message(self, device_id: str, message: str):
        """Handle message from device"""
        try:
            # Update heartbeat
            self.device_heartbeat[device_id] = datetime.now()

            # Parse message
            try:
                data = json.loads(message)
            except json.JSONDecodeError:
                self.logger.warning(f"Invalid JSON from device {device_id}: {message}")
                return

            # Handle different message types
            message_type = data.get("type")

            if message_type == "heartbeat":
                await self._handle_heartbeat(device_id, data)
            elif message_type == "device_info":
                await self._handle_device_info(device_id, data)
            elif message_type == "file_operation":
                await self._handle_file_operation(device_id, data)
            elif message_type == "status_update":
                await self._handle_status_update(device_id, data)
            else:
                self.logger.warning(f"Unknown message type from device {device_id}: {message_type}")

        except Exception as e:
            self.logger.error(f"Error handling message from device {device_id}: {e}")

    async def _handle_heartbeat(self, device_id: str, data: dict):
        """Handle heartbeat message"""
        # Update heartbeat timestamp
        self.device_heartbeat[device_id] = datetime.now()

        # Send heartbeat acknowledgment
        response = {
            "type": "heartbeat_ack",
            "timestamp": datetime.now().isoformat(),
            "server_time": datetime.now().isoformat()
        }

        if device_id in self.connected_devices:
            await self.connected_devices[device_id].send(json.dumps(response))

    async def _handle_device_info(self, device_id: str, data: dict):
        """Handle device info update"""
        self.logger.info(f"Device info update from {device_id}: {data}")

        # Store device info in database
        try:
            with get_db() as db:
                device = db.query(Device).filter(Device.device_id == device_id).first()
                if device:
                    device.last_seen = datetime.now()
                    device.device_info = json.dumps(data.get("data", {}))
                    db.commit()
        except Exception as e:
            self.logger.error(f"Error updating device info in database: {e}")

    async def _handle_file_operation(self, device_id: str, data: dict):
        """Handle file operation from device"""
        self.logger.info(f"File operation from device {device_id}: {data}")

        # TODO: Implement file operation handling
        # This would integrate with the existing file handlers

    async def _handle_status_update(self, device_id: str, data: dict):
        """Handle status update from device"""
        self.logger.info(f"Status update from device {device_id}: {data}")

        # TODO: Implement status update handling

    async def _cleanup_stale_connections(self):
        """Clean up stale connections"""
        while True:
            try:
                current_time = datetime.now()
                stale_devices = []

                for device_id, last_heartbeat in self.device_heartbeat.items():
                    if current_time - last_heartbeat > timedelta(seconds=self.heartbeat_timeout):
                        stale_devices.append(device_id)

                for device_id in stale_devices:
                    self.logger.info(f"Cleaning up stale connection for device {device_id}")
                    await self._cleanup_device(device_id)

                await asyncio.sleep(self.cleanup_interval)

            except Exception as e:
                self.logger.error(f"Error in cleanup task: {e}")
                await asyncio.sleep(self.cleanup_interval)

    async def _cleanup_device(self, device_id: str):
        """Clean up device connection"""
        if device_id in self.connected_devices:
            try:
                websocket = self.connected_devices[device_id]
                await websocket.close(1000, "Connection timeout")
            except Exception:
                pass

            del self.connected_devices[device_id]

        if device_id in self.device_heartbeat:
            del self.device_heartbeat[device_id]

        if device_id in self.device_auth_tokens:
            del self.device_auth_tokens[device_id]

    def send_message_to_device(self, device_id: str, message: dict) -> bool:
        """Send message to specific device"""
        if device_id not in self.connected_devices:
            self.logger.warning(f"Device {device_id} not connected")
            return False

        try:
            websocket = self.connected_devices[device_id]
            asyncio.create_task(websocket.send(json.dumps(message)))
            return True
        except Exception as e:
            self.logger.error(f"Error sending message to device {device_id}: {e}")
            return False

    def broadcast_message(self, message: dict, exclude_devices: Set[str] = None):
        """Broadcast message to all connected devices"""
        if exclude_devices is None:
            exclude_devices = set()

        for device_id, websocket in self.connected_devices.items():
            if device_id not in exclude_devices:
                try:
                    asyncio.create_task(websocket.send(json.dumps(message)))
                except Exception as e:
                    self.logger.error(f"Error broadcasting to device {device_id}: {e}")

    def get_connected_devices(self) -> Dict[str, datetime]:
        """Get list of connected devices with their last heartbeat"""
        return {
            device_id: heartbeat_time
            for device_id, heartbeat_time in self.device_heartbeat.items()
        }


# Global WebSocket service instance
websocket_service = WebSocketService()


def get_websocket_service() -> WebSocketService:
    """Get WebSocket service instance"""
    return websocket_service