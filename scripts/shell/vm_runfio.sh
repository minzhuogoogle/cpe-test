#!/bin/bash
sudo apt-get update
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile
sudo mount -o nolock 10.99.0.2:/DC01/root /mnt/elastifile
cd /mnt/elastifile
curl -OL https://raw.githubusercontent.com/minzhuogoogle/storage-performance/master/fio.perf.profile
NOW=$(date +"%m.%d.%Y")
HOSTNAME=$(hostname)
fio fio.perf.profile --output-format=json --output elastifile.$HOSTNAME.$NOW.json
gsutil cp elastifile.$HOSTNAME.$NOW.json gs://cpe-performance-storage/test_result/elastifile.$HOSTNAME.$NOW.json
