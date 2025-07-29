#!/bin/bash

# Docker Development Environment Management Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if .env file exists
check_env() {
    if [[ ! -f .env ]]; then
        print_warning ".env file not found. Please create one based on .env.example"
        print_status "Example: cp .env.example .env"
        exit 1
    fi
}

# Function to start development environment
start_dev() {
    print_status "Starting Callie development environment..."
    check_env
    
    print_status "Building and starting services..."
    docker-compose -f docker-compose.dev.yml up --build -d
    
    print_success "Development environment started!"
    print_status "Services:"
    print_status "  🔧 API: http://localhost:8000"
    print_status "  📱 UI: http://localhost:3000"
    print_status "  📖 API Docs: http://localhost:8000/docs"
    
    print_status "To view logs: ./scripts/docker-dev.sh logs"
    print_status "To stop: ./scripts/docker-dev.sh stop"
}

# Function to start production environment
start_prod() {
    print_status "Starting Callie production environment..."
    check_env
    
    print_status "Building and starting services..."
    docker-compose up --build -d
    
    print_success "Production environment started!"
    print_status "Services:"
    print_status "  🔧 API: http://localhost:8000"
    print_status "  📱 UI: http://localhost:3000"
}

# Function to stop services
stop() {
    print_status "Stopping all Callie services..."
    docker-compose -f docker-compose.dev.yml down 2>/dev/null || true
    docker-compose down 2>/dev/null || true
    print_success "All services stopped"
}

# Function to show logs
logs() {
    if [[ $# -eq 0 ]]; then
        print_status "Showing logs for all services..."
        docker-compose -f docker-compose.dev.yml logs -f
    else
        print_status "Showing logs for service: $1"
        docker-compose -f docker-compose.dev.yml logs -f "$1"
    fi
}

# Function to restart services
restart() {
    print_status "Restarting Callie services..."
    stop
    sleep 2
    start_dev
}

# Function to show status
status() {
    print_status "Callie service status:"
    docker-compose -f docker-compose.dev.yml ps
}

# Function to clean up
clean() {
    print_status "Cleaning up Docker resources..."
    stop
    
    print_status "Removing unused containers and images..."
    docker system prune -f
    
    print_status "Removing Callie images..."
    docker images | grep callie | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
    
    print_success "Cleanup complete"
}

# Function to show help
help() {
    echo "Callie Docker Development Environment"
    echo ""
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  dev          Start development environment (with hot reloading)"
    echo "  prod         Start production environment"
    echo "  stop         Stop all services"
    echo "  restart      Restart development environment"
    echo "  logs [svc]   Show logs (optionally for specific service)"
    echo "  status       Show service status"
    echo "  clean        Clean up Docker resources"
    echo "  help         Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 dev                    # Start development environment"
    echo "  $0 logs                   # Show all logs"
    echo "  $0 logs callie-api        # Show API logs only"
    echo "  $0 logs callie-ui-dev     # Show UI logs only"
}

# Main script logic
case "${1:-help}" in
    dev)
        start_dev
        ;;
    prod)
        start_prod
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    logs)
        logs "${2:-}"
        ;;
    status)
        status
        ;;
    clean)
        clean
        ;;
    help|*)
        help
        ;;
esac 