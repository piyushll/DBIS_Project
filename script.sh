#!/bin/bash
set -e  # Exit immediately if a command fails

# PostgreSQL connection parameters
DB_NAME="dblp15"
DB_USER="postgres"  # Default PostgreSQL user
DB_PASSWORD="Piyush@123"  # Replace with your actual password
DB_HOST="localhost"
DB_PORT="5432"

# DDL file path
DDL_FILE="data.ddl"  # Path to your DDL file

# Check if the DDL file exists
if [ ! -f "$DDL_FILE" ]; then
    echo "Error: DDL file '$DDL_FILE' not found."
    exit 1
fi

# Test connection to PostgreSQL
echo "Testing connection to PostgreSQL..."
if ! PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "SELECT 1" >/dev/null 2>&1; then
    echo "Error: Failed to connect to PostgreSQL. Please check your connection parameters."
    exit 1
fi

# Drop database if it exists
echo "Dropping database $DB_NAME if it exists..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "DROP DATABASE IF EXISTS $DB_NAME;"

# Create database
echo "Creating database $DB_NAME..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -c "CREATE DATABASE $DB_NAME;"

# Execute DDL file
echo "Executing DDL file to create schema..."
PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$DDL_FILE"

echo "Database setup completed successfully!"
