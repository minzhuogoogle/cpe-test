#!/bin/bash
testtype=$1
nfs_server=$2
fio_start=$3
testduration=$4
testname=$5
nfs_data_container='DC01'
ping_retry=30
repeat=1
interval=60
sudo apt-get update
sudo apt-get git
sudo apt-get iputils-ping
sudo apt install fio -y
sudo apt install nfs-common -y
sudo apt-get install make gcc libc6-dev libssl-dev zlib1g-dev python -y
sudo git clone https://github.com/aerospike/act.git
cd act; make; make -f Makesalt
gsutil cp gs://cpe-performance-storage/aerospike.computer.json aerospike.json
gcloud auth activate-service-account --key-file  aerospike.json

sleep 10000
