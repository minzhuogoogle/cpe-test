#!/bin/bash

disktype_check() 
{
    disktype=$1
    valid=(lssd pssd phdd)
    ok=-1
    for x in "${valid[@]}" ; do 
         if [ "$disktype" = "$x" ]; then
             ok=0 ; 
         fi ; 
    done 
    return $ok
}

initialization() 
{
   cd gcp-automation/ 
   gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
   gcloud auth activate-service-account --key-file elastifile.json
   cp terraform.tfvars.$disktype terraform.tfvars
   cat terraform.tfvars
   # temporarily disable load-balancing
   sed 's/true/false/' terraform.tfvars
   
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

provision_elastifile() {
    postsubmit=$1
    terraform init
    retval=$?
    if [ $retval -ne 0 ]; then
       exit -1
    fi
    echo "run terraform apply to start elfs instance"
    if [ "$postsubmit" = "1" ]; then
       sed 's/elfs/elfs-post/' terraform.tfvars
    fi
    terraform apply --auto-approve &  
    
    maxcount=15
    count=0
    ret=1
    sleep 300
    while [ $count -lt $maxcount ] && [ $ret -eq 1 ]; do
        num_terraform_proc=$(ps -ef | grep "terraform apply"  | grep -v workspace | grep -v grep | wc -l)
        echo "processs is $num_terrform_proc"
        if [ $num_terraform_proc -gt 0 ]; then
            echo "still running"
            ret=1
            sleep 30
        else
            echo "stopped"
            ret=0
        fi
        let count=count+1
        echo "count = $count"
    done

    if [ $count -eq $maxcount ] && [ $ret -eq 1 ]; then
        echo -ne " failed to stop!! "
        retval=-1
    else
        echo "finished"
        retval=0
    fi
    
    echo "retval=$retval"
    echo $(tail -5 create_vheads.log )
    process=$( grep Failed create_vheads.log | cut -d ' ' -f1 )
    status=$( grep Failed create_vheads.log | cut -d ' ' -f2 )
    echo "process = $process, status=$status"
    
    if [ $retval -eq -1 ] || [ "$status" = "Failed." ]; then
       NOW=`date +%m.%d.%Y.%H.%M.%S`
       cat terraform.tfvars >> create_vheads.log
       logfile=elfs.terraform.provision.$(hostname).$NOW.$disktype.txt
       gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/$logfile
       echo $logfile
       name=$disktype-elfs
       cleanup $project $zone $name
       exit -1
    fi
    NOW=`date +%m.%d.%Y.%H.%M.%S`
    testname=$(hostname)
    cat terraform.tfvars >> create_vheads.log
    logfile=elfs.terraform.provision.$(hostname).$NOW.$disktype.txt
    gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/$logfile
    echo $logfile
    
}

start_vm() {
     echo "vmname = $vmname"
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-4'
     gcloud compute --project=$project instances create $vmname  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype  
     retval=$?
     if [ $retval -ne 0 ]; then
        cleanup $project $zone $disktype
        exit -1
     fi
}

is_test_done() {
   expected_files=$1
   export number_logfiles_1=`gsutil ls gs://cpe-performance-storage/test_result/ | grep $(hostname) | grep elfs | grep fio | wc -l`
   export number_logfiles_2=`gsutil ls gs://cpe-performance-storage/test_result/backup | grep $(hostname) | grep elfs | grep fio | wc -l`
   let number_logfiles=number_logfiles_1+number_logfiles_2
   #echo "Found $number_logfiles io logfile uploaded."
   if [ $number_logfiles -lt $expected_files ]; 
   then
       echo "-1"
   fi
   echo "1"
}

delete_vm() {
  
    for i in `gcloud compute instances list --project $project --filter=$vmname | grep -v NAME | cut -d ' ' -f1`; 
    do 
       echo "vm to be deleted: $i, $project, $zone"
       gcloud compute instances delete $i --project $project --zone $zone -q; 
    done
}



delete_routers() {

    for i in `gcloud compute network list --project $project --filter=$vm_name | grep -v NAME | cut -d ' ' -f1`; 
    do 
       gcloud compute instances delete $i --project $project --zone $zone -q; 
    done
}

cleanup() {
    delete_vm $project $zone $disktype
    #delete_traffic_node()
    #delete_routers()
    #delete_firewalls()
    #delete_subnetworks()
}


# --------------
# Start here
# --------------
project=''
zone=''
region=''
edisk=''
disktype=$1
postsubmit=$2
if [ "$postsubmit" = "1" ]; then
   vmname=post-$disktype-$(hostname)
else
   vmname=$disktype-$(hostname)
fi   

disktype_check $disktype
retval=$?
if [ $retval -ne 0 ]; then
    echo "Disktype $disktype provided is not supported, please select one of: lssd, pssd or phdd."
    exit -1
fi

initialization
echo "disktype = $disktype,  storage_in_terraform = $edisk"

echo "project = $project"
echo "zone = $zone"
echo "disktype = $disktype"
echo "terraform type = $edisk"
cleanup $project $zone $disktype

provision_elastifile $postsubmit
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

start_vm $project $zone $disktype
if [ $retval -ne 0 ]; then
    exit -1
fi

sleep 1800
is_test_done 6
test_done=$?
echo "test_done is $test_done"
count=0
while [[ "$test_done" -eq "-1"  &&  $count -lt 10 ]] 
do
   sleep 1
   is_test_done 6
   test_done=$?
   echo "test_done is $test_done"
   count=$((count+1))
done

elfsname=$disktype-elfs
#cleanup $project $zone $elfsname
vmname=$disktype-$(hostname)
#cleanup $project $zone $vmname

if [ "$test_done" -eq "-1" ]; then
    echo "io testing might have problem"
    exit -1
fi   
