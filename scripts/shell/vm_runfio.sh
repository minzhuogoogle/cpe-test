#!/bin/bash
nfs_server_ip=10.99.0.2
nfs_data_container='ZMDATA'
ping_retry=30
sudo apt-get update
sudo apt-get iputils-ping
sudo apt install fio -y
sudo apt install nfs-common -y
sudo mkdir -p /mnt/elastifile


export nfs_server_reachable=`ping $nfs_server_ip -c 5 | grep "0% packet loss"`
check_result=${#nfs_server_reachable}

count=1
while [[ "$check_result" -lt 5 ] && [ $count -lt $ping_retry ]]
do
   sleep 1
   export nfs_server_reachable=`ping $nfs_server_ip -c 5 | grep "0% packet loss"`
   check_result=${#nfs_server_reachable}
   count=`expr $count+1`
done    

if [ $count -eq $ping_retry ]
then
    echo "Fail to connect to NFS server."    
elif   
    echo "Start fio on Elastifile datacontainer."
    sudo mount -o nolock $nsf_server_ip:/$nfs_data_container/root /mnt/elastifile
    cd /mnt/elastifile
    sudo git clone git@github.com:minzhuogoogle/cpe-test.git
    cd cpe-test/fio/elastifile
    declare -a iotype=('readbw', 'readiops', 'writebw', 'writeiops', 'randrwbw', 'randrwiops')

    for i in "${arr[@]}"
    do
      sudo curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/fio/elastifile/fio.$i
      NOW=`date +%m.%d.%Y.%H.%M.%S`
      HOSTNAME=$(hostname)
      sudo fio fio.$i  --refill_buffers --norandommap --time_based --output-format=json --output elastifile.fio.$i.$NOW.log
      gsutil cp elastifile.fio.$i.$NOW.log gs://elastifile_test/test_result/elastifile.fio.$i.$NOW.log
      sudo rm *.*.*
    done
fi    
