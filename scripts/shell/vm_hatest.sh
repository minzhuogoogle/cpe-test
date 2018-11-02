#!/bin/bash
#gcloud compute --project=$project instances create $vminstance  --zone=$zone --machine-type=$machine_type
#--scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=
#sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ 
#sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\
#$disktype\ $nfs_server\ $fio_start\ $test_duration\ $test_name
   
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
sudo mkdir -p /mnt/elastifile
#gsutil cp gs://cpe-performance-storage-data/elastifile.json elastifile.json
gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
gcloud auth activate-service-account --key-file  elastifile.json

start_fio() 
{
    
      disktype=$1
      nfsserver=$2
      testduration=$3
      testname=$4
      fiofile=$iotype.$nfsserver
      #cd /mnt/elastifile
      echo  $disktype $nfsserver
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.data.verify
      
      cat fio.data.verify
      NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
      HOSTNAME=$(hostname)
      logfile=$testname.fio.ha.$HOSTNAME.$NOW.$disktype.txt
      echo $logfile
      sudo fio fio.data.verify --refill_buffers --norandommap --time_based --output-format=json --output $logfile
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
         
	       
             start_fio  $testtype $nfs_server $testduration $testname
	     export current=`date +"%s"`
	     echo $current, $fio_start
	     delta=$((current-fio_start))
	     testgap=$(($testduration+30))
	     expected_gap=$(($testgap*testno))
	     while [ $delta -lt $expected_gap ]
	     do 
	        sleep 1
		export current=`date +"%s"`
		delta=$((current-fio_start))
		echo $current, $fio_start,  "<===>" $delta, $expected_gap
             done
	     testno=$((testno+1))
        
         echo $number
         number=$((number+1))
         sleep $interval
         echo $number
      done
else
      echo "Can not reach NFS server."
fi
