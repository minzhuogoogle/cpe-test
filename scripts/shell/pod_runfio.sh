#!/bin/bash
cd /mnt/elastifile
curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.profile
NOW=$(date +"%m.%d.%Y")
HOSTNAME=$(hostname)
fio fio.profile  --refill_buffers --norandommap --time_based --output-format=json --output elastifile.$HOSTNAME.$NOW.json
gsutil cp elastifile.$HOSTNAME.$NOW.json gs://cpe-performance-storage/test_result/elastifile.$HOSTNAME.$NOW.json

