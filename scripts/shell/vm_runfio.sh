#!/bin/bash
testtype=$1
nfs_server=$2
fio_start=$3
nfs_data_container='DC01'
ping_retry=30
repeat=1
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
      disktype=$2
      nfsserver=$3
      fiofile=fio.$nfsserver
      #cd /mnt/elastifile
      echo $iotype $disktype $nfsserver
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.$iotype
      sudo sed -i "s/300/600/" fio.$iotype
      sudo sed -i "s/${iotype}/${fiofile}/" fio.$iotype
      cat fio.$iotype
      NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
      HOSTNAME=$(hostname)
      logfile=elfs.fio.$iotype.$HOSTNAME.$NOW.$disktype.txt
      echo $logfile
      sudo fio fio.$iotype --refill_buffers --norandommap --time_based --output-format=json --output $logfile
      gsutil cp $logfile gs://cpe-performance-storage/test_result/$logfile
      sudo rm -rf /mnt/elastifile/fio.*
}

disktypes=('lssd-elfs' 'pssd-elfs' 'phdd-elfs')
      
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
      #cd /mnt/elastifile
      declare -a iotype=('readbw' 'readiops' 'writebw' 'writeiops' 'randrwbw' 'randrwiops')
      number=0
      export now=` date +"%s"`
      while [ "$fio_start" != "$now" ]; do  
          export now=` date +"%s"`
	  echo $now "=?" $fio_start
	  sleep 1; 
      done
      testno=1
      while [ $number -lt $repeat ] 
      do 
         for j in "${iotype[@]}"
         do 
	     echo $j     
             start_fio $j $testtype $nfs_server
	     export current=`date +"%s"`
	     delta=$((current-fio_start))
	     expected_gap=$((660*testno))
	     while [ $delta -lt $expected_gap ]
	     do 
	        sleep 1
		export current=`date +"%s"`
             done
	     testno=$((testno+1))
         done
         echo $number
         number=$((number+1))
         sleep $interval
         echo $number
      done
else
      echo "Can not reach NFS server."
fi
