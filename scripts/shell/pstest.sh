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
    disktype=$1
    terraform init
    retval=$?
    if [ $retval -ne 0 ]; then
       exit -1
    fi
    terraform apply --auto-approve
    retval=$?
    if [ $retval -ne 0 ]; then
       NOW=`date +%m.%d.%Y.%H.%M.%S`
       hostname=$(hostname)
       gsutil cp terraform.tfvars gs://cpe-performance-storage/test_result/terraform.tfvars.$disktype.$hostname.$NOW.txt
       gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$hostname.$NOW.txt
       name=$disktype-elfs
       cleanup $project $zone $name
       exit -1
    fi
    NOW=`date +%m.%d.%Y.%H.%M.%S`
   
    gsutil cp terraform.tfvars gs://cpe-performance-storage/test_result/terraform.tfvars.$disktype.$hostname.$NOW.txt
    gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$hostname.$NOW.txt
}

start_vm() {
     project=$1
     zone=$2
     disktype=$3
     vmname=$disktype-$hostname
     echo "vm_name = $vm_name"
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-4'
     gcloud compute --project=$project instances create $vmname  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype  
     retval=$?
     if [ $retval -ne 0 ]; then
        name=$disktype-elfs
        cleanup $project $zone $name
        name=$disktype-$hostname
        cleanup $project $zone $name
        exit -1
     fi
}

test_done() {
   expected_files=$1
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/ | grep $hostname | grep elfs | grep fio | wc -l`
   echo "Found $number_logfiles io logfile uploaded."
   if [ $number_logfiles -lt $expected_files ]; 
   then
       return -1
   fi
   return 1
}

delete_vm() {
    project=$1
    zone=$2
    vmname=$3
    for i in `gcloud compute instances list --project $project --filter=$vmname | grep -v NAME | cut -d ' ' -f1`; 
    do 
       echo "vm to be deleted: $i, $project, $zone"
       gcloud compute instances delete $i --project $project --zone $zone -q; 
    done
}



delete_routers() {
    project=$1
    zone=$2
    vm_name=$3

    for i in `gcloud compute network list --project $project --filter=$vm_name | grep -v NAME | cut -d ' ' -f1`; 
    do 
       gcloud compute instances delete $i --project $project --zone $zone -q; 
    done
}

cleanup() {
    echo "start cleanup....."
    project=$1
    zone=$2
    vmname=$3
    delete_vm $project $zone $vmname
    #delete_traffic_node()
    #delete_routers()
    #delete_firewalls()
    #delete_subnetworks()
}

# Start here

project=''
zone=''
edisk=''
hostname=''
disktype=$1
disktype_check $disktype
retval=$?
if [ $retval -ne 0 ]; then
    echo "Disktype $disktype provided is not supported, please select one of: lssd, pssd or phdd."
    exit -1
fi

initialization

    
echo "project = $project"
echo "zone = $zone"
echo "disktype = $disktype"
echo "terraform type = $edisk"
provision_elastifile $disktype
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

start_vm $project $zone $disktype
if [ $retval -ne 0 ]; then
    exit -1
fi

sleep 1850
test_done=`test_done 6`
count=0
while [ $test_done -eq -1 ] && [ $count -lt 10 ] 
do
   sleep 60
   test_done=`is_test_done 6`
   count=$((count+1))
done

name=$disktype-elfs
cleanup $project $zone $name
name=$disktype-$hostname
cleanup $project  $zone $name

if [ $test_done -eq -1 ]; then
    echo "io testing might have problem"
    exit -1
fi   
