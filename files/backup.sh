#!/bin/bash
echo "-*- Start backup -*-"
# sudo mount /dev/sda1 /mnt/
sudo docker stop immich_server immich_postgres joplin_db joplin vaultwarden
sudo rsync -avh --delete /home/ebenezer /mnt/backup/ebenezer
sudo docker start immich_server immich_postgres joplin_db joplin vaultwarden
# sudo umount /mnt/
echo "-*- End backup -*-"
