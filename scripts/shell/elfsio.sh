#!/bin/bash

disktype_check() 
{
    disktype=$1
    valid=(lssd pssd phdd)
    ok=-1
    for x in "${valid[@]}"
    do 
         if [ "$disktype" = "$x" ]; then
             ok=0 
         fi 
    done 
    return $ok
}


initialization() 
{
   cd gcp-automation/ 
   gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
   gcloud auth activate-service-account --key-file elastifile.json
   cp terraform.tfvars.$disktype terraform.tfvars
   #if [ "$postsubmit" -eq "1" ]; then
   #    sed -i 's/elfs/elfs/' terraform.tfvars
   #fi
   cat terraform.tfvars
   # temporarily disable load-balancing
   sed -i 's/true/false/' terraform.tfvars
   
   export zone=`grep ZONE terraform.tfvars | awk -v N=3 '{print $N}'`
   zone=${zone:1:-1}
   export project=`grep PROJECT terraform.tfvars | awk -v N=3 '{print $N}'`
   project=${project:1:-1}
   export cluster_name=`grep CLUSTER_NAME terraform.tfvars | awk -v N=3 '{print $N}'`
   cluster_name=${cluster_name:1:-1}
   export disk=`grep DISK_TYPE terraform.tfvars | awk -v N=3 '{print $N}'`
   edisk=${disk:1:-1}
   echo $project,$zone,$cluster_name,$edisk
}
   

start_vm() {
     nfs_server=$1
     fio_start=$2
     echo "vmname = $vmname"
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-4'
     vminstance="$disktype-$(hostname)-$vmseq"
     echo $vminstance
     gcloud compute --project=$project instances create $vminstance  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype\ $nfs_server\ $fio_start
     retval=$?
     if [ $retval -ne 0 ]; then
        cleanup 
        exit -1
     fi
     vmseq=$((vmseq+1))
}


is_test_done() {
   expected_files=$1
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep elfs | grep fio | wc -l`
   export filelists=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep elfs | grep fio`
   
   #echo "Found $number_logfiles io logfile uploaded."
   #if [ $number_logfiles -lt $expected_files ]; 
   #then
   #    echo "-1"
   #fi
   #echo "1"
   echo "$filelists"
}






# --------------
# Start here
# --------------
project=''
zone=''
region=''
edisk=''
fio_done=0
vmseq=1
disktype=$1
mfio=$2
postsubmit=1


if [ "$postsubmit" -eq "1" ]; then
    vmname=post-$disktype-$(hostname)
else
    vmname=$disktype-$(hostname)
fi   
echo $vmname



disktype_check $disktype
retval=$?
if [ $retval -ne 0 ]; then
    echo "Disktype $disktype provided is not supported, please select one of: lssd, pssd or phdd."
    exit -1
fi

initialization
echo "disktype = $disktype, storage_in_terraform = $edisk"

echo "project = $project"
echo "zone = $zone"
echo "disktype = $disktype"
echo "terraform type = $edisk"




export nfs_server_ips=`gcloud compute instances list --project=cpe-performance-storage --filter="$disktype-elfs-elfs-"  --format="value(networkInterfaces[0].networkIP)"`
echo $nfs_server_ips
export now=` date +"%s"`
export timer=`date -d "+ 5 minutes" +"%s"`
for nfs_server in $nfs_server_ips
do
    export now=` date`
    echo $now
    start_vm $nfs_server $timer
    retval=$?
    if [ $retval -ne 0 ]; then
        cleanup 
     exit -1
     fi
done
export now=` date `
echo $now
sleep 1200
#is_test_done 18
#test_done=$?
#filenums=${#testdone}
#echo "test_done is $test_done"
#if [ $filenums -gt 18]; then
#        fio_done=1
#fi    
#count=0
#while [[ "$fio_done" -eq "0"  &&  $count -lt 60 ]] 
#do
#   sleep 60
#   is_test_done 6
#   test_done=$?
#   echo "test_done is $test_done"
#   filenums=${#testdone}
#   if [ $filenums -gt 6]; then
#        fio_done=1
#   fi     
#   count=$((count+1))
#done

#sleep 600
export now=` date `
echo $now
#if [ "$debug" -eq '0']; then
#cleanup 
#fi    


#if [ "$test_done" -eq "-1" ]; then
#    echo "io testing might have problem."
#    exit -1
#fi   
