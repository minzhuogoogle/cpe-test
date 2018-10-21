#!/bin/bash

disktype_check() {
    disktype=$1
    valid=(lssd, pssd, phdd)
    ok=-1
    for x in "${valid[@]}" ; do 
         if [ "$disktype" = "$x" ]; then
             ok=0 ; 
         fi ; 
    done 
    return $ok
}

initializtion() {
   cd gcp-automation/ 
   gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
   gcloud auth activate-service-account --key-file elastifile.json
   cp terraform.tfvars.$disktype terraform.tfvars
   cat terraform.tfvars
   sed 's/true/false/' terraform.tfvars
   export zone=`grep ZONE terraform.tfvars | awk -v N=3 '{print $N}'`
   zone=${zone:1:-1}
   export project=`grep PROJECT terraform.tfvars | awk -v N=3 '{print $N}'`
   project=${project:1:-1}
   export cluster_name=`grep CLUSTER_NAME terraform.tfvars | awk -v N=3 '{print $N}'`
   cluster_name=${cluster_name:1:-1}
   export disk=`grep DISK_TYPE terraform.tfvars | awk -v N=3 '{print $N}'`
   disk=${disk:1:-1}
   echo "$project,$zone,$cluster_name,$disk"
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
       exit -1
    fi
    HNOW=$(date +"%Y%m%d")
    NOW=`date +%m.%d.%Y.%H.%M.%S`
    HOSTNAME=$(hostname)
    gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$HOSTNAME.$NOW.txt
}

start_vm() {
     project=$1
     hostname=$(hostname)
     zone=$2
     disktype=$3
     vm_name=$disktype-$hostname
     machine_type='n1-standard-4'
     gcloud compute --project=$project instances create $instance_name  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype  
     retval=$?
     if [ $retval -ne 0 ]; then
        exit -1
     fi
}

test_done(){
   expected_files=$1
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/ | grep $hostname | grep -v create_vheads | wc -l`
   if [ $number_logfiles -lt $expected_files ]; 
   then
       return -1
   fi
   return 1
}

cleanup() {
    delete_elfs_nodes()
    delete_traffic_node()
    delete_routers()
    delete_firewalls()
    delete_subnetworks()
}

disktype=$1
disktype_check $disktype
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

results=`initializtion`
project=`get_rtrn $results 1`
zone=`get_rtrn $results 2`
cluster=`get_rtrn $results 3`
ttype=`get_rtrn $results 4`
    
echo "project = $project"
echo "zone = $zone"
echo "terraform type = $ttype"
provision_elastifile $disktype
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

start_vm $project $zone $disktype

if [ $retval -ne 0 ]; then
    exit -1
fi

test_done=`is_test_done`
while [ test_done ] && [ $count < 200 ]
count=1
do
    sleep 10
    count=`expr $count+1`
done
