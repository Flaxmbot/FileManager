"""
Real-time file synchronization service for Android devices
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Set

from sqlalchemy.orm import Session
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent

from ..database.session import get_db
from ..models.device import Device
from .websocket_service import get_websocket_service


class FileSyncService:
    """Service for real-time file synchronization"""

    def __init__(self):
        self.websocket_service = get_websocket_service()
        self.logger = logging.getLogger(__name__)

        # File watchers for different devices
        self.watchers: Dict[str, Observer] = {}
        self.watched_paths: Dict[str, Set[str]] = {}

        # File hash cache for change detection
        self.file_hashes: Dict[str, Dict[str, str]] = {}

        # Sync configuration
        self.sync_extensions = {'.txt', '.jpg', '.png', '.pdf', '.doc', '.docx', '.mp4', '.mp3'}
        self.max_file_size = 100 * 1024 * 1024  # 100MB
        self.sync_delay = 2  # seconds

        # Pending sync operations
        self.pending_operations: Dict[str, List[Dict]] = {}

    def start_device_sync(self, device_id: str, paths: List[str]) -> bool:
        """Start file synchronization for a device"""
        try:
            self.logger.info(f"Starting file sync for device {device_id} on paths: {paths}")

            # Stop existing watcher if any
            self.stop_device_sync(device_id)

            # Create file watcher
            event_handler = DeviceFileEventHandler(device_id, self)
            observer = Observer()
            self.watchers[device_id] = observer

            # Start watching paths
            for path in paths:
                if os.path.exists(path):
                    observer.schedule(event_handler, path, recursive=True)
                    if device_id not in self.watched_paths:
                        self.watched_paths[device_id] = set()
                    self.watched_paths[device_id].add(path)
                    self.logger.info(f"Watching path: {path}")

            observer.start()
            self.logger.info(f"File sync started for device {device_id}")

            return True

        except Exception as e:
            self.logger.error(f"Error starting file sync for device {device_id}: {e}")
            return False

    def stop_device_sync(self, device_id: str) -> bool:
        """Stop file synchronization for a device"""
        try:
            if device_id in self.watchers:
                self.watchers[device_id].stop()
                self.watchers[device_id].join()
                del self.watchers[device_id]

            if device_id in self.watched_paths:
                del self.watched_paths[device_id]

            if device_id in self.file_hashes:
                del self.file_hashes[device_id]

            if device_id in self.pending_operations:
                del self.pending_operations[device_id]

            self.logger.info(f"File sync stopped for device {device_id}")
            return True

        except Exception as e:
            self.logger.error(f"Error stopping file sync for device {device_id}: {e}")
            return False

    def sync_file_to_device(self, device_id: str, file_path: str, target_path: str) -> bool:
        """Sync a file to a device"""
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Source file does not exist: {file_path}")
                return False

            file_size = os.path.getsize(file_path)
            if file_size > self.max_file_size:
                self.logger.error(f"File too large: {file_size} > {self.max_file_size}")
                return False

            # Check if file should be synced based on extension
            if not self._should_sync_file(file_path):
                self.logger.info(f"Skipping file due to extension filter: {file_path}")
                return False

            # Read file content
            with open(file_path, 'rb') as f:
                file_content = f.read()

            # Calculate file hash
            file_hash = hashlib.sha256(file_content).hexdigest()

            # Create sync operation
            sync_operation = {
                "type": "file_sync",
                "operation": "upload",
                "source_path": file_path,
                "target_path": target_path,
                "file_hash": file_hash,
                "file_size": file_size,
                "timestamp": datetime.now().isoformat()
            }

            # Send to device via WebSocket
            message = {
                "type": "file_operation",
                "data": sync_operation
            }

            return self.websocket_service.send_message_to_device(device_id, message)

        except Exception as e:
            self.logger.error(f"Error syncing file to device {device_id}: {e}")
            return False

    def request_file_from_device(self, device_id: str, file_path: str, local_path: str) -> bool:
        """Request a file from a device"""
        try:
            # Create file request operation
            request_operation = {
                "type": "file_request",
                "file_path": file_path,
                "local_path": local_path,
                "timestamp": datetime.now().isoformat()
            }

            # Send to device via WebSocket
            message = {
                "type": "file_operation",
                "data": request_operation
            }

            return self.websocket_service.send_message_to_device(device_id, message)

        except Exception as e:
            self.logger.error(f"Error requesting file from device {device_id}: {e}")
            return False

    def _should_sync_file(self, file_path: str) -> bool:
        """Check if file should be synchronized based on filters"""
        _, ext = os.path.splitext(file_path.lower())
        return ext in self.sync_extensions

    def _get_file_hash(self, file_path: str) -> Optional[str]:
        """Get file hash for change detection"""
        try:
            if not os.path.exists(file_path):
                return None

            # Check if hash is cached
            file_mtime = os.path.getmtime(file_path)
            cache_key = f"{file_path}:{file_mtime}"

            # Simple hash caching (in production, use a more sophisticated cache)
            if cache_key in self.file_hashes.get(file_path, {}):
                return self.file_hashes[file_path][cache_key]

            # Calculate hash
            with open(file_path, 'rb') as f:
                content = f.read()
                file_hash = hashlib.sha256(content).hexdigest()

            # Cache hash
            if file_path not in self.file_hashes:
                self.file_hashes[file_path] = {}
            self.file_hashes[file_path][cache_key] = file_hash

            return file_hash

        except Exception as e:
            self.logger.error(f"Error getting file hash for {file_path}: {e}")
            return None

    def handle_device_file_operation(self, device_id: str, operation: Dict) -> bool:
        """Handle file operation from device"""
        try:
            operation_type = operation.get("operation")

            if operation_type == "file_change":
                return self._handle_file_change(device_id, operation)
            elif operation_type == "file_delete":
                return self._handle_file_delete(device_id, operation)
            elif operation_type == "file_upload":
                return self._handle_file_upload(device_id, operation)
            else:
                self.logger.warning(f"Unknown file operation type: {operation_type}")
                return False

        except Exception as e:
            self.logger.error(f"Error handling device file operation: {e}")
            return False

    def _handle_file_change(self, device_id: str, operation: Dict) -> bool:
        """Handle file change from device"""
        try:
            file_path = operation.get("file_path")
            file_hash = operation.get("file_hash")

            if not file_path or not file_hash:
                self.logger.error("Missing file_path or file_hash in file_change operation")
                return False

            self.logger.info(f"File changed on device {device_id}: {file_path}")

            # TODO: Implement file change handling
            # This could trigger a sync operation or notification

            return True

        except Exception as e:
            self.logger.error(f"Error handling file change: {e}")
            return False

    def _handle_file_delete(self, device_id: str, operation: Dict) -> bool:
        """Handle file deletion from device"""
        try:
            file_path = operation.get("file_path")

            if not file_path:
                self.logger.error("Missing file_path in file_delete operation")
                return False

            self.logger.info(f"File deleted on device {device_id}: {file_path}")

            # TODO: Implement file deletion handling

            return True

        except Exception as e:
            self.logger.error(f"Error handling file delete: {e}")
            return False

    def _handle_file_upload(self, device_id: str, operation: Dict) -> bool:
        """Handle file upload from device"""
        try:
            file_path = operation.get("file_path")
            file_content = operation.get("file_content")
            file_hash = operation.get("file_hash")

            if not file_path or not file_content or not file_hash:
                self.logger.error("Missing required fields in file_upload operation")
                return False

            self.logger.info(f"File upload from device {device_id}: {file_path}")

            # TODO: Implement file upload handling
            # This would save the file to the appropriate location

            return True

        except Exception as e:
            self.logger.error(f"Error handling file upload: {e}")
            return False

    def get_sync_status(self, device_id: str) -> Dict:
        """Get synchronization status for a device"""
        return {
            "device_id": device_id,
            "is_watching": device_id in self.watchers,
            "watched_paths": list(self.watched_paths.get(device_id, set())),
            "pending_operations": len(self.pending_operations.get(device_id, [])),
            "last_activity": self.device_heartbeat.get(device_id, {}).isoformat() if device_id in self.device_heartbeat else None
        }


class DeviceFileEventHandler(FileSystemEventHandler):
    """File system event handler for device synchronization"""

    def __init__(self, device_id: str, sync_service: FileSyncService):
        self.device_id = device_id
        self.sync_service = sync_service
        self.logger = logging.getLogger(__name__)

        # Debounce timer for rapid file changes
        self.debounce_timer: Optional[asyncio.Task] = None
        self.pending_events: List[FileSystemEvent] = []

    def on_modified(self, event):
        """Handle file modification"""
        if not event.is_directory:
            self._debounce_event(event, "modified")

    def on_created(self, event):
        """Handle file creation"""
        if not event.is_directory:
            self._debounce_event(event, "created")

    def on_deleted(self, event):
        """Handle file deletion"""
        if not event.is_directory:
            self._debounce_event(event, "deleted")

    def on_moved(self, event):
        """Handle file move/rename"""
        if not event.is_directory:
            self._debounce_event(event, "moved")

    def _debounce_event(self, event: FileSystemEvent, event_type: str):
        """Debounce rapid file events"""
        # Cancel existing timer
        if self.debounce_timer:
            self.debounce_timer.cancel()

        # Add event to pending list
        self.pending_events.append(event)

        # Create new debounce timer
        self.debounce_timer = asyncio.create_task(self._process_debounced_events())

    async def _process_debounced_events(self):
        """Process debounced file events"""
        try:
            # Wait for debounce delay
            await asyncio.sleep(self.sync_service.sync_delay)

            # Process all pending events
            for event in self.pending_events:
                await self._process_file_event(event)

            # Clear pending events
            self.pending_events.clear()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.logger.error(f"Error processing debounced events: {e}")
        finally:
            self.debounce_timer = None

    async def _process_file_event(self, event: FileSystemEvent):
        """Process a single file event"""
        try:
            # Check if file should be synced
            if not self.sync_service._should_sync_file(event.src_path):
                return

            # Get file hash for change detection
            file_hash = self.sync_service._get_file_hash(event.src_path)
            if not file_hash:
                return

            # Create sync operation
            operation = {
                "type": "file_change",
                "event_type": event.event_type,
                "src_path": event.src_path,
                "dest_path": getattr(event, 'dest_path', None),
                "file_hash": file_hash,
                "file_size": os.path.getsize(event.src_path) if os.path.exists(event.src_path) else 0,
                "timestamp": datetime.now().isoformat()
            }

            # Send to device via WebSocket
            message = {
                "type": "file_operation",
                "data": operation
            }

            success = self.sync_service.websocket_service.send_message_to_device(
                self.device_id,
                message
            )

            if success:
                self.logger.info(f"Sent file event to device {self.device_id}: {event.src_path}")
            else:
                self.logger.error(f"Failed to send file event to device {self.device_id}")

        except Exception as e:
            self.logger.error(f"Error processing file event: {e}")


# Global file sync service instance
file_sync_service = FileSyncService()


def get_file_sync_service() -> FileSyncService:
    """Get file sync service instance"""
    return file_sync_service