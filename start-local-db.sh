#!/bin/bash

# Script to start local development environment with system services

echo "Starting local development environment..."

# Check if PostgreSQL is installed
if ! command -v psql &> /dev/null; then
    echo "ERROR: PostgreSQL is not installed."
    echo "Please install PostgreSQL and try again."
    exit 1
fi

# Check if Redis is installed
if ! command -v redis-cli &> /dev/null; then
    echo "ERROR: Redis is not installed."
    echo "Please install Redis and try again."
    exit 1
fi

echo "Starting PostgreSQL service..."
sudo systemctl start postgresql

echo "Starting Redis service..."
sudo systemctl start redis

# Wait for services to start
echo "Waiting for services to start..."
sleep 5

# Check if services are running
echo "Checking PostgreSQL..."
sudo -u postgres pg_isready -d taiger_db

echo "Checking Redis..."
redis-cli ping

echo "Services started successfully!"
echo "PostgreSQL: localhost:5432"
echo "Redis: localhost:6379"
echo ""
echo "To stop services, run:"
echo "sudo systemctl stop postgresql redis"