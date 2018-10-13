#!/bin/bash
sudo apt-get update
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile
sudo mount -o nolock 10.99.0.2:/DC01/root /mnt/elastifile
cd /mnt/elastifile
sudo gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json 
gcloud auth activate-service-account --key-file elastifile.json
sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.profile
NOW=$(date +"%Y.%m.%d")
HOSTNAME=$(hostname)
sudo fio fio.profile  --refill_buffers --norandommap --time_based  --group_reporting  --output elastifile.$HOSTNAME.$NOW.log
gsutil cp elastifile.$HOSTNAME.$NOW.log gs://cpe-performance-storage/test_result/elastifile.$HOSTNAME.$NOW.log
sudo rm *.*
project='cpe-performance-storage'
zone='us-east1-b'

#for i in `gcloud compute instances list --project $project --filter='test-elastifile-storage' | grep -v NAME | cut -d ' ' -f1`; do gcloud compute instances delete $i --project $project --zone $zone -q; done
