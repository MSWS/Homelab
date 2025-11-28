#!/bin/bash

source /home/iboaz/.restic.sh

exec > >(logger -t backup) 2>&1

/usr/bin/docker image prune --filter "until=168h" --force
/usr/bin/docker network prune -f
/usr/bin/docker volume prune -f
/usr/bin/docker builder prune -f

#/usr/bin/restic unlock
#/usr/bin/restic backup -o s3.storage-class=INTELLIGENT_TIERING --exclude-file=/home/iboaz/excludes.txt --one-file-system --verbose /
/usr/bin/restic -r /mnt/usb/backups/ unlock
/usr/bin/restic -r /mnt/usb/backups/ backup --exclude-file=/home/iboaz/excludes.txt --one-file-system --verbose --json / | python3 /home/iboaz/backup_log.py "USB"
/usr/bin/restic -r b2:debian-homelab-backups:/  unlock
/usr/bin/restic -r b2:debian-homelab-backups:/  backup --exclude-file=/home/iboaz/excludes.txt --one-file-system --verbose --json / | python3 /home/iboaz/backup_log.py "Backblaze"
/usr/bin/restic forget --keep-last 1 --keep-daily 3 --keep-weekly 4 --keep-monthly 3 --keep-yearly 3 --prune
/usr/bin/restic -r /mnt/usb/backups/ forget --keep-last 1 --keep-daily 7 --keep-weekly 8 --keep-monthly 3 --keep-yearly 3 --prune
/usr/bin/restic -r b2:debian-homelab-backups:/ forget --keep-last 1 --keep-daily 3 --keep-weekly 4 --keep-monthly 3 --keep-yearly 3 --prune
