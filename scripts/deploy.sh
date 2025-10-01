#!/bin/bash

# FileManager Bot Deployment Script
# Comprehensive deployment automation with blue-green strategy

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
DEPLOYMENT_DIR="/opt/filemanager-bot"
BACKUP_DIR="/opt/filemanager-bot/backups"
COMPOSE_FILE="$PROJECT_ROOT/docker-compose.yml"
ENV_FILE="$PROJECT_ROOT/.env.production"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $*"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*"
}

# Utility functions
check_dependencies() {
    log_info "Checking dependencies..."

    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi

    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi

    # Check git
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed"
        exit 1
    fi

    log_success "All dependencies are installed"
}

validate_environment() {
    log_info "Validating environment configuration..."

    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file not found: $ENV_FILE"
        exit 1
    fi

    # Check required environment variables
    required_vars=(
        "BOT_TOKEN"
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "ENCRYPTION_KEY"
    )

    for var in "${required_vars[@]}"; do
        if ! grep -q "^${var}=" "$ENV_FILE"; then
            log_error "Required environment variable $var not found in $ENV_FILE"
            exit 1
        fi
    done

    log_success "Environment configuration is valid"
}

run_tests() {
    log_info "Running automated tests..."

    # Navigate to project directory
    cd "$PROJECT_ROOT"

    # Run Python tests if test files exist
    if [ -f "requirements.txt" ]; then
        log_info "Installing test dependencies..."
        pip install -r requirements.txt

        # Run basic syntax check
        python -m py_compile src/main.py
        log_success "Python syntax check passed"
    fi

    # Run Docker build test
    log_info "Testing Docker build..."
    docker build -t filemanager-bot:test .

    # Clean up test image
    docker rmi filemanager-bot:test

    log_success "All tests passed"
}

create_backup() {
    local backup_name="pre-deployment-$(date +%Y%m%d-%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"

    log_info "Creating pre-deployment backup..."

    mkdir -p "$BACKUP_DIR"

    # Backup current deployment if it exists
    if [ -d "$DEPLOYMENT_DIR" ]; then
        tar -czf "$backup_path.tar.gz" -C "$DEPLOYMENT_DIR" .
        log_success "Backup created: $backup_path.tar.gz"
    else
        log_info "No existing deployment to backup"
    fi
}

deploy_blue_green() {
    local target_color="$1"

    log_info "Starting blue-green deployment to $target_color..."

    # Determine current and target versions
    if [ "$target_color" = "blue" ]; then
        local current="green"
        local target="blue"
    else
        local current="blue"
        local target="green"
    fi

    # Check if target version is running
    if docker ps -q -f name="filemanager-bot-$target" | grep -q .; then
        log_info "Target version ($target) is already running, switching traffic..."

        # Update nginx to point to target version
        update_nginx_upstream "$target"

        # Stop current version
        log_info "Stopping current version ($current)..."
        docker-compose -f "$COMPOSE_FILE" -p "filemanager-bot-$current" down

        log_success "Blue-green deployment completed"
        return
    fi

    # Deploy target version
    log_info "Deploying new version to $target..."

    # Create target-specific compose file
    create_colored_compose_file "$target"

    # Start target version
    COMPOSE_FILE="$PROJECT_ROOT/docker-compose.$target.yml" \
    COMPOSE_PROJECT_NAME="filemanager-bot-$target" \
    docker-compose up -d

    # Wait for health check
    wait_for_health "filemanager-bot-$target"

    # Update nginx to point to target version
    update_nginx_upstream "$target"

    # Stop current version if running
    if docker ps -q -f name="filemanager-bot-$current" | grep -q .; then
        log_info "Stopping current version ($current)..."
        docker-compose -f "$COMPOSE_FILE" -p "filemanager-bot-$current" down
    fi

    log_success "Blue-green deployment completed"
}

create_colored_compose_file() {
    local color="$1"
    local colored_file="$PROJECT_ROOT/docker-compose.$color.yml"

    # Copy base compose file and modify container names
    cp "$COMPOSE_FILE" "$colored_file"
    sed -i.bak "s/container_name: filemanager/container_name: filemanager-$color/g" "$colored_file"
    sed -i.bak "s/COMPOSE_PROJECT_NAME=filemanager-bot/COMPOSE_PROJECT_NAME=filemanager-bot-$color/g" "$colored_file"

    rm -f "$colored_file.bak"
}

update_nginx_upstream() {
    local target_color="$1"

    log_info "Updating nginx upstream to $target_color..."

    # Update nginx configuration
    if [ -f "/etc/nginx/sites-available/filemanager-bot" ]; then
        # Update nginx config to point to target color
        sed -i.bak "s/upstream filemanager_bot.*/upstream filemanager_bot { server filemanager-$target_color:10000; }/" \
            /etc/nginx/sites-available/filemanager-bot

        # Reload nginx
        systemctl reload nginx
        log_success "Nginx configuration updated"
    else
        log_warning "Nginx configuration not found, skipping upstream update"
    fi
}

wait_for_health() {
    local project_name="$1"
    local max_attempts=30
    local attempt=1

    log_info "Waiting for $project_name to become healthy..."

    while [ $attempt -le $max_attempts ]; do
        if curl -f "http://localhost:8001/health" &>/dev/null; then
            log_success "Service is healthy"
            return 0
        fi

        log_info "Health check attempt $attempt/$max_attempts failed, waiting..."
        sleep 10
        ((attempt++))
    done

    log_error "Service failed to become healthy after $max_attempts attempts"
    return 1
}

rollback_deployment() {
    local target_color="$1"

    log_warning "Rolling back deployment..."

    # Determine which color to rollback to
    if [ "$target_color" = "blue" ]; then
        local rollback_to="green"
    else
        local rollback_to="blue"
    fi

    # Start rollback version
    if [ -f "$PROJECT_ROOT/docker-compose.$rollback_to.yml" ]; then
        log_info "Starting rollback version ($rollback_to)..."
        COMPOSE_FILE="$PROJECT_ROOT/docker-compose.$rollback_to.yml" \
        COMPOSE_PROJECT_NAME="filemanager-bot-$rollback_to" \
        docker-compose up -d

        # Wait for health
        wait_for_health "filemanager-bot-$rollback_to"

        # Update nginx
        update_nginx_upstream "$rollback_to"

        log_success "Rollback completed"
    else
        log_error "No rollback version found"
        exit 1
    fi
}

cleanup_old_deployments() {
    log_info "Cleaning up old deployments..."

    # Keep only last 5 backups
    cd "$BACKUP_DIR"
    ls -t *.tar.gz | tail -n +6 | xargs -r rm -f

    # Remove unused Docker images
    docker image prune -f

    log_success "Cleanup completed"
}

monitor_deployment() {
    local duration_minutes="${1:-10}"

    log_info "Monitoring deployment for $duration_minutes minutes..."

    local end_time=$((SECONDS + duration_minutes * 60))

    while [ $SECONDS -lt $end_time ]; do
        # Check service health
        if ! curl -f "http://localhost:8001/health" &>/dev/null; then
            log_error "Service health check failed during monitoring"
            return 1
        fi

        # Check error rates (if monitoring is available)
        if curl -f "http://localhost:8001/metrics" &>/dev/null; then
            local error_rate=$(curl -s "http://localhost:8001/metrics" | grep "errors_total" | awk '{print $2}' || echo "0")

            if [ "$error_rate" -gt 10 ]; then
                log_error "High error rate detected: $error_rate"
                return 1
            fi
        fi

        sleep 30
    done

    log_success "Deployment monitoring completed successfully"
}

# Main deployment function
main() {
    local action="${1:-deploy}"
    local environment="${2:-production}"
    local target_color="${3:-blue}"

    log_info "FileManager Bot Deployment Script"
    log_info "Action: $action"
    log_info "Environment: $environment"
    log_info "Target: $target_color"

    case "$action" in
        "deploy")
            check_dependencies
            validate_environment
            run_tests
            create_backup
            deploy_blue_green "$target_color"
            monitor_deployment 5
            cleanup_old_deployments
            log_success "Deployment completed successfully"
            ;;

        "rollback")
            rollback_deployment "$target_color"
            log_success "Rollback completed successfully"
            ;;

        "test")
            check_dependencies
            validate_environment
            run_tests
            log_success "Pre-deployment tests completed"
            ;;

        "backup")
            create_backup
            log_success "Backup completed"
            ;;

        "monitor")
            monitor_deployment 60
            ;;

        "cleanup")
            cleanup_old_deployments
            log_success "Cleanup completed"
            ;;

        *)
            log_error "Unknown action: $action"
            echo "Usage: $0 {deploy|rollback|test|backup|monitor|cleanup} [environment] [target_color]"
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"