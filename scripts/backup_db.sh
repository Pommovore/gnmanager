#!/bin/bash
# Database Backup Script Wrapper for Cron
# Ensures the script runs from the correct directory

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

# Change to project directory
cd "$PROJECT_DIR"

# Run the Python backup script
python3 "$SCRIPT_DIR/backup_db.py" >> "$SCRIPT_DIR/backup.log" 2>&1

# Exit with the Python script's exit code
exit $?
