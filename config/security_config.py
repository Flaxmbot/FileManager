"""
Production Security Configuration for Telegram Bot

This module provides comprehensive security configurations for production deployment.
"""

import json
import secrets
from pathlib import Path
from typing import Dict


def create_production_security_config() -> Dict:
    """Create production security configuration"""

    config = {
        "ssl": {
            "enabled": True,
            "cert_path": "/etc/ssl/certs/bot.crt",
            "key_path": "/etc/ssl/private/bot.key",
            "ciphers": "ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS",
            "protocols": ["TLSv1.2", "TLSv1.3"]
        },

        "webhook": {
            "secret_token": secrets.token_urlsafe(32),
            "validate_ip": True,
            "allowed_ips": [
                "149.154.160.0/20",
                "91.108.4.0/22",
                "91.108.56.0/22",
                "91.108.8.0/22",
                "95.161.64.0/20"
            ]
        },

        "rate_limiting": {
            "enabled": True,
            "requests_per_minute": 1000,
            "burst_limit": 50
        },

        "monitoring": {
            "enabled": True,
            "log_security_events": True,
            "alert_on_suspicious_activity": True
        }
    }

    return config


def main():
    """Generate security configuration files"""

    project_root = Path(__file__).parent.parent
    config_dir = project_root / "config"
    config_dir.mkdir(exist_ok=True)

    # Create security config
    config = create_production_security_config()

    config_file = config_dir / "security.json"
    with open(config_file, "w") as f:
        json.dump(config, f, indent=2)

    print(f"✅ Created security configuration: {config_file}")


if __name__ == "__main__":
    main()