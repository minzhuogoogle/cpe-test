#!/bin/bash
nfs_server_ip=10.142.0.6
nfs_data_container='ZMDATA'
ping_retry=30
repeat=10
interval=60
sudo apt-get update
sudo apt-get git
sudo apt-get iputils-ping
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile

gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json

start_fio() 
{
      iotype=$1	
      echo $iotype
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.$iotype
      NOW=`date +%m.%d.%Y.%H.%M.%S`
      HOSTNAME=$(hostname)
      logfile=elfs.fio.$iotype.$HOSTNAME.$NOW.hdd.txt
      echo $logfile
      sudo fio fio.$iotype  --refill_buffers --norandommap --time_based --output-format=json --output $logfile
      gsutil cp $logfile gs://cpe-performance-storage/test_result/$logfile
      sudo rm *.*.*
}


export nfs_server_reachable=`ping $nfs_server_ip -c 5 | grep "0% packet loss"`
check_result=${#nfs_server_reachable}
echo $check_result

count=0
while [ "$check_result" -lt 5 ] && [ $count -lt $ping_retry ] 
do
   sleep 1
   export nfs_server_reachable=`ping $nfs_server_ip -c 5 | grep "0% packet loss"`
   check_result=${#nfs_server_reachable}
   count=$((count+1))
done    

echo "ping succeeds"
echo $count
if [ $count -lt $ping_retry ]
then
    echo "Start fio on Elastifile datacontainer."
    sudo mount -o nolock $nfs_server_ip:/$nfs_data_container/root /mnt/elastifile
    cd /mnt/elastifile
    declare -a iotype=('readbw' 'readiops' 'writebw' 'writeiops' 'randrwbw' 'randrwiops')
#    declare -a iotype=('writebw' 'randrwbw')
    number=0
    while [ $number -lt $repeat ] 
    do 
      for i in "${iotype[@]}"
      do 
	 echo $i     
         start_fio $i
      done
      echo $number

      number=$((number+1))
      sleep $interval
      echo $number
    done
else
   echo "Can not reach NFS server."
fi
