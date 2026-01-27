#!/usr/bin/env python3
"""
Database Backup Script for GN Manager
Automates SQLite database backups with retention policy

Usage:
    python scripts/backup_db.py
    
Schedule with cron:
    0 2 * * * cd /path/to/gnmanager && python scripts/backup_db.py
"""
import os
import shutil
import gzip
from datetime import datetime, timedelta
import logging

# Configuration
DB_PATH = '../../gnmanager.db'  # Relative to scripts/ dir
BACKUP_DIR = '../../backups'
RETENTION_DAYS = 7
RETENTION_WEEKLY = 4  # Keep 4 weekly backups (28 days)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def create_backup():
    """Create a compressed backup of the database"""
    try:
        # Get absolute paths
        script_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.abspath(os.path.join(script_dir, DB_PATH))
        backup_dir = os.path.abspath(os.path.join(script_dir, BACKUP_DIR))
        
        # Create backup directory if it doesn't exist
        os.makedirs(backup_dir, exist_ok=True)
        
        # Check if database exists
        if not os.path.exists(db_path):
            logger.error(f'Database not found: {db_path}')
            return False
        
        # Generate backup filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'gnmanager_backup_{timestamp}.db.gz'
        backup_path = os.path.join(backup_dir, backup_filename)
        
        # Create compressed backup
        logger.info(f'Creating backup: {backup_filename}')
        with open(db_path, 'rb') as f_in:
            with gzip.open(backup_path, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        # Verify backup
        backup_size = os.path.getsize(backup_path)
        db_size = os.path.getsize(db_path)
        logger.info(f'Backup created: {backup_size} bytes (original: {db_size} bytes)')
        
        if backup_size == 0:
            logger.error('Backup file is empty!')
            return False
        
        return True
        
    except Exception as e:
        logger.error(f'Backup failed: {str(e)}', exc_info=True)
        return False


def cleanup_old_backups():
    """Remove old backups according to retention policy"""
    try:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        backup_dir = os.path.abspath(os.path.join(script_dir, BACKUP_DIR))
        
        if not os.path.exists(backup_dir):
            return
        
        now = datetime.now()
        backups = []
        
        # List all backup files
        for filename in os.listdir(backup_dir):
            if filename.startswith('gnmanager_backup_') and filename.endswith('.db.gz'):
                filepath = os.path.join(backup_dir, filename)
                mtime = os.path.getmtime(filepath)
                backups.append((filepath, datetime.fromtimestamp(mtime)))
        
        # Sort by date (newest first)
        backups.sort(key=lambda x: x[1], reverse=True)
        
        logger.info(f'Found {len(backups)} backup files')
        
        # Keep last 7 daily backups
        daily_backups = backups[:RETENTION_DAYS]
        
        # Keep 4 weekly backups (older than 7 days, one per week)
        weekly_backups = []
        week_numbers = set()
        for backup_path, backup_date in backups[RETENTION_DAYS:]:
            week_num = backup_date.isocalendar()[1]  # ISO week number
            if week_num not in week_numbers and len(weekly_backups) < RETENTION_WEEKLY:
                weekly_backups.append((backup_path, backup_date))
                week_numbers.add(week_num)
        
        # Combine backups to keep
        keep_backups = set([b[0] for b in daily_backups + weekly_backups])
        
        # Delete old backups
        deleted_count = 0
        for backup_path, backup_date in backups:
            if backup_path not in keep_backups:
                logger.info(f'Deleting old backup: {os.path.basename(backup_path)} ({backup_date.date()})')
                os.remove(backup_path)
                deleted_count += 1
        
        logger.info(f'Cleanup complete: kept {len(keep_backups)} backups, deleted {deleted_count}')
        
    except Exception as e:
        logger.error(f'Cleanup failed: {str(e)}', exc_info=True)


def main():
    """Main backup routine"""
    logger.info('=== Database Backup Started ===')
    
    if create_backup():
        cleanup_old_backups()
        logger.info('=== Database Backup Completed Successfully ===')
        return 0
    else:
        logger.error('=== Database Backup Failed ===')
        return 1


if __name__ == '__main__':
    exit(main())
