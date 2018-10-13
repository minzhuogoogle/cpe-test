#!/bin/bash
sudo apt-get update
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile
sudo mount -o nolock 10.99.0.2:/DC01/root /mnt/elastifile
cd /mnt/elastifile
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.profile
NOW=$(date +"%m.%d.%Y")
HOSTNAME=$(hostname)
fio fio.profile  --refill_buffers --norandommap --time_based --output-format=json --output elastifile.$HOSTNAME.$NOW.json
gsutil cp elastifile.$HOSTNAME.$NOW.json gs://cpe-performance-storage/test_result/elastifile.$HOSTNAME.$NOW.json

project='cpe-performance-storage'
zone='us-east1-b'

for i in `gcloud compute instances list --project $project --filter='test-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone; done
