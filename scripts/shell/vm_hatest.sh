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
      echo $disktype $nfsserver
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.data.verify
      cat fio.data.verify
      NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
      HOSTNAME=$(hostname)
      logfile=$testname.fio.$testname.$HOSTNAME.$NOW.$disktype.txt
      echo $logfile
      sudo fio fio.data.verify --refill_buffers --norandommap --output-format=json --output $logfile
      gsutil cp $logfile gs://cpe-performance-storage/test_result/$logfile
      sudo rm -rf /mnt/elastifile/$testname.fio*.*
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
      sudo rm -rf /mnt/elastifile/*.*
      sync
      number=0
      export now=` date +"%s"`
      while [ "$fio_start" != "$now" ]; do  
	  sleep 1;      
          export now=` date +"%s"`
	  echo $now "=?" $fio_start
      done
      while [ $number -lt $repeat ] 
      do 
          start_fio $testtype $nfs_server $testduration $testname
          number=$((number+1))
          sleep $interval
          echo $number
      done
else
      echo "Can not reach NFS server."
fi
