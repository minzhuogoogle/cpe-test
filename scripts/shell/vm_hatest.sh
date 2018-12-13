#!/bin/bash

testtype=$1
nfs_server=$2
fio_start=$3
testduration=$4
testname=$5
nfs_data_container='DC01'
ping_retry=30
interval=60
sudo apt-get update
sudo apt-get git
sudo apt-get iputils-ping
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile
gsutil cp gs://cpe-test/elastifile.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json

start_fio() 
{
      disktype=$1
      nfsserver=$2
      testduration=$3
      testname=$4
      
      HOSTNAME=$(hostname)
      fiofile=$iotype.$nfsserver.$HOSTNAME
      echo  $disktype $nfsserver
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.data.verify
      
      cat fio.data.verify
      NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`

      logfile=$testname.fio.failover.$HOSTNAME.$NOW.$disktype.txt
      echo $logfile
      sudo fio fio.data.verify --refill_buffers --norandommap --time_based --output-format=json --output $logfile
      gsutil cp $logfile gs://cpe-performance-storage/test_result/$logfile
      sudo rm -rf /mnt/elastifile/*.*
}
      
export nfs_server_reachable=`ping $nfs_server -c 5 | grep "0% packet loss"`
check_result=${#nfs_server_reachable}
echo $check_result
      
count=0
while [ "$check_result" -lt 5 ] && [ $count -lt $ping_retry ] 
do
        sleep 1
        export nfs_server_reachable=`ping $nfs_server -c 5 | grep "0% packet loss"`
        check_result=${#nfs_server_reachable}
        count=$((count+1))
done    

echo "ping succeeds"
echo $count      

if [ $count -lt $ping_retry ]
then
      echo "Start fio on Elastifile datacontainer."
      sudo mount -o nolock $nfs_server:/$nfs_data_container/root /mnt/elastifile
      export now=` date +"%s"`
     
      while [ $fio_start -gt $now ]; do  
          export now=` date +"%s"`
	  echo $now "=?" $fio_start
	  sleep 1; 
      done
      
      start_fio  $testtype $nfs_server $testduration $testname 
else
      echo "Can not reach NFS server."
fi
