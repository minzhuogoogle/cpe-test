#!/bin/bash
#sudo apt-get update
#sudo apt install fio -y
#sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile
sudo mount -o nolock 10.99.0.2:/DC01/root /mnt/elastifile
cd /mnt/elastifile
gsutil cp gs://elastifile_test/nelastifile.json elastifile.json 
#gcloud auth activate-service-account --key-file elastifile.json
sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.profile
NOW=$(date +"%Y.%m.%d")
HOSTNAME=$(hostname)
sudo fio fio.profile  --refill_buffers --norandommap --time_based --output-format=json --output elastifile.$HOSTNAME.$NOW.log
gsutil cp elastifile.$HOSTNAME.$NOW.log gs://elastifile_test/test_result/elastifile.$HOSTNAME.$NOW.log
sudo rm *.*
