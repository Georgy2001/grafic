#!/bin/bash

# Development helper script
set -e

echo "🚀 График Смен - Development Setup"

# Function to show help
show_help() {
    echo "Usage: ./dev.sh [command]"
    echo ""
    echo "Commands:"
    echo "  start     - Start development environment"
    echo "  stop      - Stop all containers"
    echo "  logs      - Show logs"
    echo "  rebuild   - Rebuild and restart"
    echo "  clean     - Clean up containers and volumes"
    echo "  test      - Run tests"
    echo "  help      - Show this help"
}

# Start development environment
start_dev() {
    echo "🔨 Starting development environment..."
    docker-compose up -d
    echo "✅ Development environment started!"
    echo ""
    echo "🌐 Available services:"
    echo "   Frontend: http://localhost:3000"
    echo "   Backend:  http://localhost:8001"
    echo "   API Docs: http://localhost:8001/docs"
    echo "   MongoDB:  mongodb://localhost:27017"
    echo ""
    echo "📊 To view logs: ./dev.sh logs"
}

# Stop containers
stop_dev() {
    echo "🛑 Stopping development environment..."
    docker-compose down
    echo "✅ Development environment stopped!"
}

# Show logs
show_logs() {
    echo "📊 Showing logs (Press Ctrl+C to exit)..."
    docker-compose logs -f
}

# Rebuild and restart
rebuild_dev() {
    echo "🔨 Rebuilding development environment..."
    docker-compose down
    docker-compose build --no-cache
    docker-compose up -d
    echo "✅ Development environment rebuilt and started!"
}

# Clean up
clean_dev() {
    echo "🧹 Cleaning up containers and volumes..."
    docker-compose down -v
    docker system prune -f
    echo "✅ Cleanup completed!"
}

# Run tests
run_tests() {
    echo "🧪 Running tests..."
    echo "Backend tests:"
    docker-compose exec backend python -m pytest
    echo "✅ Tests completed!"
}

# Check if docker is running
check_docker() {
    if ! docker info > /dev/null 2>&1; then
        echo "❌ Docker is not running. Please start Docker first."
        exit 1
    fi
}

# Main script logic
case "${1:-help}" in
    start)
        check_docker
        start_dev
        ;;
    stop)
        stop_dev
        ;;
    logs)
        show_logs
        ;;
    rebuild)
        check_docker
        rebuild_dev
        ;;
    clean)
        clean_dev
        ;;
    test)
        check_docker
        run_tests
        ;;
    help|*)
        show_help
        ;;
esac