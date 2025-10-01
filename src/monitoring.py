"""
Health monitoring and metrics collection for the FileManager bot
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from fastapi import FastAPI, HTTPException
import uvicorn
from sqlalchemy import text
from sqlalchemy.orm import Session

from .config.settings import settings
from .database.session import get_db, engine
from .services.websocket_service import get_websocket_service
from .services.file_sync_service import get_file_sync_service
from .services.command_integration_service import get_command_integration_service
from .services.notification_service import get_notification_service


# Global metrics storage
metrics_data = {
    "start_time": time.time(),
    "requests_total": 0,
    "errors_total": 0,
    "response_time_seconds": [],
    "active_connections": 0,
    "database_connections": 0,
    "last_health_check": None
}

# Health check results
health_status = {
    "status": "healthy",
    "timestamp": None,
    "checks": {}
}


def update_metrics(metric_name: str, value: float, metric_type: str = "counter"):
    """Update metrics data"""
    if metric_type == "counter":
        if metric_name not in metrics_data:
            metrics_data[metric_name] = 0
        metrics_data[metric_name] += value
    elif metric_type == "gauge":
        metrics_data[metric_name] = value
    elif metric_type == "histogram":
        if metric_name not in metrics_data:
            metrics_data[metric_name] = []
        metrics_data[metric_name].append(value)
        # Keep only last 1000 values
        if len(metrics_data[metric_name]) > 1000:
            metrics_data[metric_name] = metrics_data[metric_name][-1000:]


async def run_health_server(host: str = "0.0.0.0", port: int = 8001):
    """Run the health monitoring server"""
    app = FastAPI(title="FileManager Bot Health API", version="1.0.0")

    @app.get("/health")
    async def health_check():
        """Basic health check endpoint"""
        return await perform_health_checks()

    @app.get("/health/detailed")
    async def detailed_health_check():
        """Detailed health check with component status"""
        return await perform_detailed_health_checks()

    @app.get("/metrics")
    async def get_metrics():
        """Prometheus-style metrics endpoint"""
        return await generate_metrics_response()

    @app.get("/status")
    async def get_status():
        """Get current system status"""
        return {
            "status": "running",
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": time.time() - metrics_data["start_time"],
            "version": "1.0.0",
            "environment": settings.ENVIRONMENT
        }

    @app.post("/health/trigger")
    async def trigger_health_check():
        """Manually trigger health checks"""
        return await perform_health_checks(force=True)

    logger = logging.getLogger(__name__)
    logger.info(f"Starting health server on {host}:{port}")

    config = uvicorn.Config(app, host=host, port=port, access_log=False)
    server = uvicorn.Server(config)
    await server.serve()


async def perform_health_checks(force: bool = False) -> Dict[str, Any]:
    """Perform comprehensive health checks"""
    global health_status

    # Skip if recently checked (unless forced)
    if not force and health_status["timestamp"]:
        last_check = datetime.fromisoformat(health_status["timestamp"])
        if datetime.now() - last_check < timedelta(seconds=30):
            return health_status

    start_time = time.time()
    checks = {}
    overall_status = "healthy"
    errors = []

    # Database health check
    db_status, db_error = await check_database_health()
    checks["database"] = {"status": db_status, "error": db_error}
    if db_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"Database: {db_error}")

    # Redis health check
    redis_status, redis_error = await check_redis_health()
    checks["redis"] = {"status": redis_status, "error": redis_error}
    if redis_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"Redis: {redis_error}")

    # WebSocket service health check
    ws_status, ws_error = await check_websocket_service_health()
    checks["websocket_service"] = {"status": ws_status, "error": ws_error}
    if ws_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"WebSocket Service: {ws_error}")

    # File sync service health check
    fs_status, fs_error = await check_file_sync_service_health()
    checks["file_sync_service"] = {"status": fs_status, "error": fs_error}
    if fs_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"File Sync Service: {fs_error}")

    # Command integration service health check
    ci_status, ci_error = await check_command_integration_service_health()
    checks["command_integration_service"] = {"status": ci_status, "error": ci_error}
    if ci_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"Command Integration Service: {ci_error}")

    # Notification service health check
    ns_status, ns_error = await check_notification_service_health()
    checks["notification_service"] = {"status": ns_status, "error": ns_error}
    if ns_status != "healthy":
        overall_status = "unhealthy"
        errors.append(f"Notification Service: {ns_error}")

    # Update global health status
    health_status = {
        "status": overall_status,
        "timestamp": datetime.now().isoformat(),
        "response_time_seconds": time.time() - start_time,
        "checks": checks,
        "errors": errors
    }

    # Update metrics
    update_metrics("health_check_total", 1, "counter")
    update_metrics("health_check_response_time_seconds", time.time() - start_time, "histogram")

    return health_status


async def perform_detailed_health_checks() -> Dict[str, Any]:
    """Perform detailed health checks with additional metrics"""
    basic_health = await perform_health_checks()

    # Add service-specific metrics
    detailed_info = {
        **basic_health,
        "services": {
            "websocket": get_websocket_service().get_connected_devices(),
            "file_sync": get_file_sync_service().get_sync_status(None),
            "command_integration": get_command_integration_service().get_service_stats(),
            "notification": get_notification_service().get_notification_stats()
        },
        "system": {
            "memory_usage": await get_memory_usage(),
            "disk_usage": await get_disk_usage(),
            "cpu_usage": await get_cpu_usage()
        }
    }

    return detailed_info


async def check_database_health() -> tuple[str, Optional[str]]:
    """Check database connectivity and performance"""
    try:
        start_time = time.time()

        # Test database connection
        with get_db() as db:
            # Simple query to test connection
            result = db.execute(text("SELECT 1")).fetchone()

            # Check database performance
            perf_start = time.time()
            db.execute(text("SELECT COUNT(*) FROM devices")).fetchone()
            perf_time = time.time() - perf_time

            response_time = time.time() - start_time

            # Update metrics
            update_metrics("database_response_time_seconds", response_time, "histogram")
            update_metrics("database_query_time_seconds", perf_time, "histogram")

            if response_time > 1.0:  # Slower than 1 second
                return "degraded", f"Slow response time: {response_time:.3f}s"
            elif perf_time > 0.5:  # Query slower than 500ms
                return "degraded", f"Slow query time: {perf_time:.3f}s"

            return "healthy", None

    except Exception as e:
        update_metrics("database_errors_total", 1, "counter")
        return "unhealthy", str(e)


async def check_redis_health() -> tuple[str, Optional[str]]:
    """Check Redis connectivity and performance"""
    try:
        import redis

        start_time = time.time()

        # Test Redis connection
        redis_url = settings.REDIS_URL
        client = redis.from_url(redis_url)

        # Simple ping test
        response = client.ping()
        if not response:
            return "unhealthy", "Redis ping failed"

        response_time = time.time() - start_time

        # Update metrics
        update_metrics("redis_response_time_seconds", response_time, "histogram")

        if response_time > 0.5:  # Slower than 500ms
            return "degraded", f"Slow response time: {response_time:.3f}s"

        return "healthy", None

    except Exception as e:
        update_metrics("redis_errors_total", 1, "counter")
        return "unhealthy", str(e)


async def check_websocket_service_health() -> tuple[str, Optional[str]]:
    """Check WebSocket service health"""
    try:
        ws_service = get_websocket_service()
        connected_devices = ws_service.get_connected_devices()

        # Check if service is responsive
        if len(connected_devices) == 0:
            return "degraded", "No connected devices"

        return "healthy", None

    except Exception as e:
        return "unhealthy", str(e)


async def check_file_sync_service_health() -> tuple[str, Optional[str]]:
    """Check file sync service health"""
    try:
        fs_service = get_file_sync_service()
        # Add health check logic for file sync service
        return "healthy", None

    except Exception as e:
        return "unhealthy", str(e)


async def check_command_integration_service_health() -> tuple[str, Optional[str]]:
    """Check command integration service health"""
    try:
        ci_service = get_command_integration_service()
        stats = ci_service.get_service_stats()

        if stats["running_commands"] > 10:  # Too many running commands
            return "degraded", f"High command load: {stats['running_commands']}"

        return "healthy", None

    except Exception as e:
        return "unhealthy", str(e)


async def check_notification_service_health() -> tuple[str, Optional[str]]:
    """Check notification service health"""
    try:
        ns_service = get_notification_service()
        stats = ns_service.get_notification_stats()

        # Check for notification backlog
        # This would need to be implemented in the notification service

        return "healthy", None

    except Exception as e:
        return "unhealthy", str(e)


async def generate_metrics_response() -> str:
    """Generate Prometheus-style metrics response"""
    lines = []

    # Basic metrics
    uptime = time.time() - metrics_data["start_time"]
    lines.append(f"filemanager_bot_uptime_seconds {uptime}")
    lines.append(f"filemanager_bot_requests_total {metrics_data['requests_total']}")
    lines.append(f"filemanager_bot_errors_total {metrics_data['errors_total']}")

    # Response time histogram
    if metrics_data["response_time_seconds"]:
        response_times = metrics_data["response_time_seconds"]
        lines.append(f"filemanager_bot_response_time_seconds_count {len(response_times)}")
        lines.append(f"filemanager_bot_response_time_seconds_sum {sum(response_times)}")
        if response_times:
            lines.append(f"filemanager_bot_response_time_seconds_avg {sum(response_times)/len(response_times)}")

    # Health check metrics
    if health_status["timestamp"]:
        last_check = datetime.fromisoformat(health_status["timestamp"])
        last_check_seconds = (datetime.now() - last_check).total_seconds()
        lines.append(f"filemanager_bot_last_health_check_seconds {last_check_seconds}")

    # Service-specific metrics
    try:
        ws_devices = get_websocket_service().get_connected_devices()
        lines.append(f"filemanager_bot_websocket_connected_devices {len(ws_devices)}")

        ci_stats = get_command_integration_service().get_service_stats()
        lines.append(f"filemanager_bot_active_commands {ci_stats['active_commands']}")

        ns_stats = get_notification_service().get_notification_stats()
        lines.append(f"filemanager_bot_notifications_total {ns_stats['total_notifications']}")

    except Exception as e:
        logging.error(f"Error generating service metrics: {e}")

    return "\n".join(lines) + "\n"


async def get_memory_usage() -> Dict[str, float]:
    """Get memory usage information"""
    try:
        import psutil
        process = psutil.Process()
        memory_info = process.memory_info()

        return {
            "rss_mb": memory_info.rss / 1024 / 1024,
            "vms_mb": memory_info.vms / 1024 / 1024,
            "percent": process.memory_percent()
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}


async def get_disk_usage() -> Dict[str, float]:
    """Get disk usage information"""
    try:
        import psutil
        disk_usage = psutil.disk_usage('/')

        return {
            "total_gb": disk_usage.total / 1024 / 1024 / 1024,
            "used_gb": disk_usage.used / 1024 / 1024 / 1024,
            "free_gb": disk_usage.free / 1024 / 1024 / 1024,
            "percent_used": disk_usage.percent
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}


async def get_cpu_usage() -> Dict[str, float]:
    """Get CPU usage information"""
    try:
        import psutil
        cpu_percent = psutil.cpu_percent(interval=1)

        return {
            "percent": cpu_percent,
            "count": psutil.cpu_count(),
            "count_logical": psutil.cpu_count(logical=True)
        }
    except ImportError:
        return {"error": "psutil not available"}
    except Exception as e:
        return {"error": str(e)}


# Background task for periodic health checks
async def start_periodic_health_checks():
    """Start periodic health check task"""
    while True:
        try:
            await perform_health_checks()
            await asyncio.sleep(30)  # Check every 30 seconds
        except Exception as e:
            logging.error(f"Error in periodic health check: {e}")
            await asyncio.sleep(60)  # Wait longer on error


# Integration with main application
def setup_health_monitoring():
    """Setup health monitoring for the application"""
    # Start periodic health checks
    asyncio.create_task(start_periodic_health_checks())

    # Setup metrics collection middleware (if using a web framework)
    # This would be integrated with your FastAPI or other web framework

    logging.info("Health monitoring setup completed")