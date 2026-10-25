#!/bin/sh
# Nightly SQLite backup. Uses sqlite3's .backup, which is safe on a live WAL database
# (a plain file copy is not). Keeps KEEP_DAYS days of gzipped copies.
set -eu

DB_PATH="${DB_PATH:-/data/guild.db}"
BACKUP_DIR="${BACKUP_DIR:-/backups}"
KEEP_DAYS="${KEEP_DAYS:-14}"
BACKUP_HOUR="${BACKUP_HOUR:-9}"   # UTC

backup() {
  if [ ! -f "$DB_PATH" ]; then echo "no database at $DB_PATH yet, skipping"; return 0; fi
  ts=$(date -u +%Y%m%d-%H%M%S)
  out="$BACKUP_DIR/guild-$ts.db"
  sqlite3 "$DB_PATH" ".backup '$out'" && gzip "$out" && echo "backed up to $out.gz"
  find "$BACKUP_DIR" -name 'guild-*.db.gz' -mtime +"$KEEP_DAYS" -delete
}

mkdir -p "$BACKUP_DIR"
[ "${1:-}" = "--once" ] && { backup; exit 0; }

while true; do
  now=$(( $(date -u +%H | sed 's/^0//') * 3600 + $(date -u +%M | sed 's/^0//') * 60 + $(date -u +%S | sed 's/^0//') ))
  wait=$(( BACKUP_HOUR * 3600 - now ))
  [ "$wait" -le 0 ] && wait=$(( wait + 86400 ))
  echo "next backup in ${wait}s"
  sleep "$wait"
  backup || echo "backup failed"
done
