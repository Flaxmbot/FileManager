# FileManager Telegram Bot

A comprehensive Python Telegram bot for remote Android device control and file management, built with aiogram 3.x and featuring RSA-4096 encryption for secure communication.

## Features

### 🔐 Security & Authentication
- **RSA-4096 encryption** for all device communications
- **Secure token-based authentication** with automatic key rotation
- **Multi-user support** with role-based permissions
- **End-to-end encrypted** file transfers

### 📁 File Operations
- **Browse directories** and list files with metadata
- **Download files** from device to Telegram
- **Upload files** from Telegram to device
- **Delete files/folders** with confirmation prompts
- **Search files** on device with real-time results

### 📱 Device Control
- **Screenshot capture** and sharing
- **Screen streaming** for real-time viewing
- **Device information** retrieval (battery, storage, etc.)
- **Connection status** monitoring

### 🛠️ Advanced Features
- **PostgreSQL database** for user management and operation logging
- **Redis support** for session storage and caching
- **Docker containerization** for easy deployment
- **Comprehensive logging** with structured output
- **Rate limiting** and abuse prevention

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL database
- Telegram Bot Token (from @BotFather)
- Android device with FileManager app

### Installation

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd telegram-bot
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\\Scripts\\activate
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Initialize database:**
   ```bash
   # Database will be created automatically on first run
   # Or use docker-compose for full stack:
   docker-compose up -d
   ```

4. **Run the bot:**
   ```bash
   python -m src.main
   ```

## Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | ✅ |
| `DATABASE_URL` | PostgreSQL connection string | ✅ |
| `REDIS_URL` | Redis connection (optional) | ❌ |
| `SECRET_KEY` | Application secret key | ✅ |
| `ENCRYPTION_KEY` | Data encryption key | ✅ |

### Docker Deployment (Render)

1. **Connect to Render:**
   - Fork this repository
   - Connect to Render dashboard
   - Create new Web Service

2. **Configure environment:**
   ```yaml
   # render.yaml handles most configuration
   # Add secrets in Render dashboard:
   # - bot-token
   # - database-url
   # - redis-url (optional)
   # - postgres-password
   ```

3. **Deploy:**
   ```bash
   # Manual deploy via Render dashboard
   # or use CLI if configured
   ```

## Usage

### Basic Commands

1. **Start the bot:**
   ```
   /start
   ```

2. **Authenticate device:**
   ```
   /auth <your-device-token>
   ```
   Get token from Android app: Settings > Telegram Bot > Generate Token

3. **Browse files:**
   ```
   /list /sdcard/Documents
   ```

4. **Download file:**
   ```
   /download /sdcard/photo.jpg
   ```

5. **Upload file:**
   ```
   /upload <reply-to-file>
   ```

6. **Screenshot:**
   ```
   /screenshot
   ```

7. **Device info:**
   ```
   /info
   ```

### File Operations

- **List directory:** `/list <path>`
- **Download file:** `/download <file-path>`
- **Upload file:** Send file + `/upload` command
- **Delete file:** `/delete <file-path>` (with confirmation)
- **Search files:** `/search <query>`

### Media Operations

- **Screenshot:** `/screenshot` - Capture current screen
- **Screen view:** `/screenview` - Stream screen (10 captures max)

## Architecture

### Project Structure
```
telegram-bot/
├── src/
│   ├── main.py                 # Application entry point
│   ├── config/
│   │   └── settings.py         # Configuration management
│   ├── database/
│   │   └── session.py          # Database connections
│   ├── models/
│   │   ├── base.py            # Base model
│   │   ├── user.py            # User model
│   │   └── device.py          # Device model
│   ├── security/
│   │   └── encryption.py      # RSA-4096 encryption
│   ├── services/
│   │   ├── user_service.py    # User management
│   │   ├── device_service.py  # Device operations
│   │   └── device_manager.py  # Real-time communication
│   ├── handlers/
│   │   ├── start.py           # Welcome & help
│   │   ├── auth.py            # Authentication
│   │   ├── files.py           # File operations
│   │   ├── media.py           # Screenshot & screenview
│   │   ├── device.py          # Device management
│   │   └── common.py          # Error handling
│   └── utils/
│       └── logger.py          # Structured logging
├── requirements.txt            # Python dependencies
├── Dockerfile                 # Container configuration
├── docker-compose.yml         # Local development stack
├── render.yaml               # Render deployment config
└── README.md                 # This file
```

### Security Architecture

1. **RSA-4096 Encryption:**
   - Public key encryption for device communication
   - Private key decryption on bot side
   - Perfect forward secrecy for session keys

2. **Authentication Flow:**
   - Device generates unique token in Android app
   - User sends token via `/auth` command
   - Bot validates token and establishes secure connection

3. **Permission System:**
   - Role-based access control (Admin/User/Guest)
   - Granular permissions for different operations
   - Operation logging for audit trails

## Development

### Local Development

```bash
# Start all services
docker-compose up -d

# Run bot locally
python -m src.main

# View logs
docker-compose logs -f bot
```

### Database Migrations

The bot uses Alembic for database migrations:

```bash
# Initialize migrations (if needed)
alembic init alembic

# Generate migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head
```

### Testing

```bash
# Run tests (when implemented)
pytest

# Run with coverage
pytest --cov=src
```

## Deployment

### Render (Recommended)

1. **Setup Render account**
2. **Connect repository**
3. **Configure environment secrets:**
   - `BOT_TOKEN` - Your Telegram bot token
   - `DATABASE_URL` - Render PostgreSQL URL
   - `REDIS_URL` - Render Redis URL (optional)
   - `POSTGRES_PASSWORD` - Database password

4. **Deploy automatically** on git push

### Manual Deployment

```bash
# Build and run with Docker
docker build -t filemanager-bot .
docker run -d --name filemanager-bot \
  -e BOT_TOKEN=your_token \
  -e DATABASE_URL=your_db_url \
  filemanager-bot
```

## Troubleshooting

### Common Issues

1. **Bot not responding:**
   - Check `BOT_TOKEN` is correct
   - Verify bot is not already running
   - Check network connectivity

2. **Database connection errors:**
   - Verify `DATABASE_URL` format
   - Check database is running and accessible
   - Ensure database user has proper permissions

3. **Device connection issues:**
   - Ensure Android app is running
   - Check device token is valid and not expired
   - Verify device has network connectivity

4. **File operation failures:**
   - Check file paths start with `/sdcard/` or similar
   - Verify file exists and is accessible
   - Check user has required permissions

### Logs

```bash
# View application logs
docker-compose logs -f bot

# View specific service logs
docker-compose logs postgres
docker-compose logs redis
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
python -m src.main
```

## API Reference

### Bot Commands

| Command | Description | Permission |
|---------|-------------|------------|
| `/start` | Initialize bot and show help | All |
| `/auth <token>` | Authenticate device | All |
| `/list <path>` | List directory contents | read_files |
| `/download <path>` | Download file | read_files |
| `/upload` | Upload file (reply to file) | write_files |
| `/delete <path>` | Delete file/folder | delete_files |
| `/search <query>` | Search files | read_files |
| `/screenshot` | Capture screenshot | screenshot |
| `/screenview` | Stream screen | screenview |
| `/info` | Device information | device_info |

### Permissions

- **Admin:** All permissions
- **User:** read_files, write_files, delete_files, screenshot, screenview, device_info
- **Guest:** read_files, device_info

## Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the repository
- Check existing documentation
- Review logs for error details

---

**Built with ❤️ using aiogram 3.x, PostgreSQL, and RSA-4096 encryption**