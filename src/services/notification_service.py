"""
Advanced notification system for real-time alerts and messaging
"""

import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Any
from enum import Enum
import uuid

from sqlalchemy.orm import Session

from ..database.session import get_db
from ..models.device import Device
from .websocket_service import get_websocket_service


class NotificationPriority(Enum):
    """Notification priority levels"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Notification types"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SECURITY = "security"
    SYSTEM = "system"
    FILE_OPERATION = "file_operation"
    DEVICE_STATUS = "device_status"


class NotificationChannel(Enum):
    """Notification channels"""
    WEBSOCKET = "websocket"
    TELEGRAM = "telegram"
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationRule:
    """Notification rule for automated alerts"""

    def __init__(
        self,
        rule_id: str,
        name: str,
        condition: Dict[str, Any],
        actions: List[Dict[str, Any]],
        enabled: bool = True
    ):
        self.rule_id = rule_id
        self.name = name
        self.condition = condition
        self.actions = actions
        self.enabled = enabled
        self.created_at = datetime.now()

    def matches_condition(self, event: Dict[str, Any]) -> bool:
        """Check if event matches rule condition"""
        try:
            condition = self.condition

            # Check event type
            if "event_type" in condition and event.get("type") != condition["event_type"]:
                return False

            # Check priority
            if "priority" in condition:
                event_priority = event.get("priority", NotificationPriority.NORMAL.value)
                if event_priority != condition["priority"]:
                    return False

            # Check device_id
            if "device_id" in condition and event.get("device_id") != condition["device_id"]:
                return False

            # Check custom conditions
            if "custom_conditions" in condition:
                for key, expected_value in condition["custom_conditions"].items():
                    if event.get(key) != expected_value:
                        return False

            return True

        except Exception as e:
            logging.error(f"Error checking notification rule condition: {e}")
            return False


class NotificationService:
    """Advanced notification service"""

    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.logger = logging.getLogger(__name__)

        # Notification queues for different channels
        self.notification_queues: Dict[NotificationChannel, asyncio.Queue] = {
            channel: asyncio.Queue() for channel in NotificationChannel
        }

        # Active notification rules
        self.notification_rules: Dict[str, NotificationRule] = {}

        # Notification history
        self.notification_history: List[Dict] = []

        # Maximum history size
        self.max_history_size = 1000

        # Worker tasks
        self.worker_tasks: List[asyncio.Task] = []

        # Default notification rules
        self._setup_default_rules()

    def _setup_default_rules(self):
        """Setup default notification rules"""
        # Critical system errors
        self.add_notification_rule(
            "critical_errors",
            "Critical System Errors",
            {
                "event_type": "system_error",
                "priority": NotificationPriority.CRITICAL.value
            },
            [
                {
                    "channel": NotificationChannel.TELEGRAM.value,
                    "template": "🚨 CRITICAL: {message}"
                }
            ]
        )

        # Security alerts
        self.add_notification_rule(
            "security_alerts",
            "Security Alerts",
            {
                "event_type": "security_event",
                "priority": NotificationPriority.HIGH.value
            },
            [
                {
                    "channel": NotificationChannel.TELEGRAM.value,
                    "template": "🔒 SECURITY: {message}"
                }
            ]
        )

        # File operations
        self.add_notification_rule(
            "file_operations",
            "File Operations",
            {
                "event_type": "file_operation",
                "priority": NotificationPriority.NORMAL.value
            },
            [
                {
                    "channel": NotificationChannel.WEBSOCKET.value,
                    "template": "📁 File: {operation} - {file_path}"
                }
            ]
        )

        # Device status changes
        self.add_notification_rule(
            "device_status",
            "Device Status Changes",
            {
                "event_type": "device_status",
                "priority": NotificationPriority.NORMAL.value
            },
            [
                {
                    "channel": NotificationChannel.TELEGRAM.value,
                    "template": "📱 Device {device_id}: {status}"
                }
            ]
        )

    async def start_service(self):
        """Start the notification service"""
        # Start worker tasks for each channel
        for channel in NotificationChannel:
            task = asyncio.create_task(self._process_notification_queue(channel))
            self.worker_tasks.append(task)

        self.logger.info("Notification service started")

    async def stop_service(self):
        """Stop the notification service"""
        # Cancel all worker tasks
        for task in self.worker_tasks:
            task.cancel()

        self.worker_tasks.clear()
        self.logger.info("Notification service stopped")

    def add_notification_rule(
        self,
        rule_id: str,
        name: str,
        condition: Dict[str, Any],
        actions: List[Dict[str, Any]],
        enabled: bool = True
    ) -> bool:
        """Add a notification rule"""
        try:
            rule = NotificationRule(rule_id, name, condition, actions, enabled)
            self.notification_rules[rule_id] = rule
            self.logger.info(f"Added notification rule: {rule_id}")
            return True
        except Exception as e:
            self.logger.error(f"Error adding notification rule {rule_id}: {e}")
            return False

    def remove_notification_rule(self, rule_id: str) -> bool:
        """Remove a notification rule"""
        if rule_id in self.notification_rules:
            del self.notification_rules[rule_id]
            self.logger.info(f"Removed notification rule: {rule_id}")
            return True
        return False

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a notification rule"""
        if rule_id in self.notification_rules:
            self.notification_rules[rule_id].enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a notification rule"""
        if rule_id in self.notification_rules:
            self.notification_rules[rule_id].enabled = False
            return True
        return False

    async def send_notification(
        self,
        notification_type: NotificationType,
        priority: NotificationPriority,
        title: str,
        message: str,
        channels: List[NotificationChannel] = None,
        data: Dict[str, Any] = None,
        device_id: str = None,
        user_id: str = None
    ) -> str:
        """Send a notification"""
        try:
            # Generate notification ID
            notification_id = str(uuid.uuid4())

            # Create notification object
            notification = {
                "notification_id": notification_id,
                "type": notification_type.value,
                "priority": priority.value,
                "title": title,
                "message": message,
                "timestamp": datetime.now().isoformat(),
                "channels": [channel.value for channel in (channels or [NotificationChannel.WEBSOCKET])],
                "data": data or {},
                "device_id": device_id,
                "user_id": user_id,
                "status": "pending"
            }

            # Add to history
            self.notification_history.append(notification)

            # Keep history size in check
            if len(self.notification_history) > self.max_history_size:
                self.notification_history = self.notification_history[-self.max_history_size:]

            # Queue for processing
            default_channels = channels or [NotificationChannel.WEBSOCKET]
            for channel in default_channels:
                await self.notification_queues[channel].put(notification)

            # Check notification rules
            await self._process_notification_rules(notification)

            self.logger.info(f"Notification sent: {notification_id}")
            return notification_id

        except Exception as e:
            self.logger.error(f"Error sending notification: {e}")
            return None

    async def _process_notification_rules(self, notification: Dict):
        """Process notification against rules"""
        try:
            for rule in self.notification_rules.values():
                if not rule.enabled:
                    continue

                if rule.matches_condition(notification):
                    # Execute rule actions
                    for action in rule.actions:
                        await self._execute_rule_action(rule, notification, action)

        except Exception as e:
            self.logger.error(f"Error processing notification rules: {e}")

    async def _execute_rule_action(self, rule: NotificationRule, notification: Dict, action: Dict):
        """Execute a notification rule action"""
        try:
            channel_name = action.get("channel")
            template = action.get("template", "{message}")

            # Format message with template
            formatted_message = template.format(**notification)

            # Send to specified channel
            channel = NotificationChannel(channel_name)
            await self._send_to_channel(channel, {
                "title": notification.get("title", "Notification"),
                "message": formatted_message,
                "priority": notification.get("priority"),
                "data": notification.get("data", {})
            })

        except Exception as e:
            self.logger.error(f"Error executing rule action for rule {rule.rule_id}: {e}")

    async def _send_to_channel(self, channel: NotificationChannel, message: Dict):
        """Send notification to specific channel"""
        try:
            if channel == NotificationChannel.WEBSOCKET:
                # Broadcast to all connected devices
                self.websocket_service.broadcast_message({
                    "type": "notification",
                    "data": message
                })
            elif channel == NotificationChannel.TELEGRAM:
                # Send via Telegram (implement based on your bot structure)
                await self._send_telegram_notification(message)
            # Add other channels as needed

        except Exception as e:
            self.logger.error(f"Error sending to channel {channel.value}: {e}")

    async def _send_telegram_notification(self, message: Dict):
        """Send notification via Telegram"""
        # TODO: Implement Telegram notification sending
        # This would integrate with your existing Telegram bot handlers
        pass

    async def _process_notification_queue(self, channel: NotificationChannel):
        """Process notification queue for a channel"""
        queue = self.notification_queues[channel]

        while True:
            try:
                notification = await queue.get()

                # Update status
                notification["status"] = "processing"

                # Send to channel
                await self._send_to_channel(channel, notification)

                # Update status
                notification["status"] = "sent"

                queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error processing notification queue for {channel.value}: {e}")
                await asyncio.sleep(1)

    def get_notification_history(
        self,
        limit: int = 50,
        notification_type: NotificationType = None,
        priority: NotificationPriority = None,
        device_id: str = None
    ) -> List[Dict]:
        """Get notification history with filters"""
        filtered_history = self.notification_history

        if notification_type:
            filtered_history = [
                n for n in filtered_history
                if n.get("type") == notification_type.value
            ]

        if priority:
            filtered_history = [
                n for n in filtered_history
                if n.get("priority") == priority.value
            ]

        if device_id:
            filtered_history = [
                n for n in filtered_history
                if n.get("device_id") == device_id
            ]

        return filtered_history[-limit:]

    def get_notification_stats(self) -> Dict:
        """Get notification statistics"""
        total_notifications = len(self.notification_history)
        last_24h = datetime.now() - timedelta(hours=24)

        recent_notifications = [
            n for n in self.notification_history
            if datetime.fromisoformat(n["timestamp"]) > last_24h
        ]

        # Count by type
        type_counts = {}
        for notification in self.notification_history:
            notif_type = notification.get("type", "unknown")
            type_counts[notif_type] = type_counts.get(notif_type, 0) + 1

        # Count by priority
        priority_counts = {}
        for notification in self.notification_history:
            priority = notification.get("priority", "normal")
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

        return {
            "total_notifications": total_notifications,
            "recent_notifications": len(recent_notifications),
            "active_rules": len([r for r in self.notification_rules.values() if r.enabled]),
            "total_rules": len(self.notification_rules),
            "notifications_by_type": type_counts,
            "notifications_by_priority": priority_counts
        }


# Global notification service instance
notification_service = NotificationService()


def get_notification_service() -> NotificationService:
    """Get notification service instance"""
    return notification_service


# Convenience functions for common notifications

async def send_system_notification(
    message: str,
    priority: NotificationPriority = NotificationPriority.NORMAL,
    device_id: str = None
):
    """Send a system notification"""
    return await notification_service.send_notification(
        NotificationType.SYSTEM,
        priority,
        "System Notification",
        message,
        device_id=device_id
    )


async def send_security_alert(
    message: str,
    security_event: str,
    device_id: str = None
):
    """Send a security alert"""
    return await notification_service.send_notification(
        NotificationType.SECURITY,
        NotificationPriority.HIGH,
        "Security Alert",
        message,
        data={"security_event": security_event},
        device_id=device_id
    )


async def send_file_operation_notification(
    operation: str,
    file_path: str,
    device_id: str = None
):
    """Send a file operation notification"""
    return await notification_service.send_notification(
        NotificationType.FILE_OPERATION,
        NotificationPriority.NORMAL,
        "File Operation",
        f"{operation}: {file_path}",
        data={"operation": operation, "file_path": file_path},
        device_id=device_id
    )


async def send_device_status_notification(
    status: str,
    device_id: str
):
    """Send a device status notification"""
    priority = NotificationPriority.HIGH if status == "offline" else NotificationPriority.NORMAL

    return await notification_service.send_notification(
        NotificationType.DEVICE_STATUS,
        priority,
        "Device Status",
        f"Device {device_id}: {status}",
        data={"status": status},
        device_id=device_id
    )