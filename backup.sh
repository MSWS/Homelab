#!/bin/bash

source /home/iboaz/.restic.sh

exec > >(logger -t backup) 2>&1

/usr/bin/restic backup -o s3.storage-class=INTELLIGENT_TIERING --exclude-file=/home/iboaz/excludes.txt --one-file-system --verbose /
/usr/bin/restic -r /mnt/usb/backups/ backup --exclude-file=/home/iboaz/excludes.txt --one-file-system --verbose /
/usr/bin/restic forget --keep-last 1 --keep-daily 3 --keep-weekly 4 --keep-monthly 3 --keep-yearly 3 --prune
/usr/bin/restic -r /mnt/usb/backups/ forget --keep-last 1 --keep-daily 7 --keep-weekly 8 --keep-monthly 3 --keep-yearly 3 --prune
