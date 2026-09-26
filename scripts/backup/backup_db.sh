#!/bin/bash
# Script to backup PostgreSQL database in Docker

BACKUP_DIR="./backups"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
CONTAINER_NAME="banking_postgres"
DB_NAME="banking_data_platform"
DB_USER="admin"

mkdir -p "$BACKUP_DIR"

echo "Starting backup of database '$DB_NAME' from container '$CONTAINER_NAME'..."
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" -F c > "$BACKUP_DIR/db_backup_$TIMESTAMP.dump"

if [ $? -eq 0 ]; then
  echo "Backup successful: $BACKUP_DIR/db_backup_$TIMESTAMP.dump"
else
  echo "Backup failed!"
  exit 1
fi
