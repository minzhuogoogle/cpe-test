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
    terraform apply --auto-approve &
    PROC_ID=$!
    count=0
    
    notdone=1
    
    MAX=15
    COUNT=0

    until [ $COUNT -gt $MAX ] ; do
        echo -ne "."
        PROCESS_NUM=$(ps -ef | grep "terraform" | grep -v `basename $0` | grep -v "grep" | wc -l)
        if [ $PROCESS_NUM -gt 0 ]; then
            #runs
            RET=1
        else
            #stopped
            RET=0
        fi

        if [ $RET -eq $START_OR_STOP ]; then
            sleep 60 #wait...
        else
            if [ $START_OR_STOP -eq 1 ]; then
                    echo -ne " stopped"
            else
                    echo -ne " started"
            fi
            echo
            exit 0
        fi
        let COUNT=COUNT+1
    done

    if [ $START_OR_STOP -eq 1 ]; then
        echo -ne " failed to stop!! "
    else
        echo -ne " failed to start!!"
    fi

    
    #while [ kill -0 "$PROC_ID" >/dev/null 2>&1 ] && [ count -lt 60 ]; do
    #while [ $notdone -eq 1 ] && [ count -lt 60 ]; do
    #     echo "PROCESS IS RUNNING"
    #     count=$((count+1))
 
    #     sleep 60
    #done
    
    #if [ kill -0 "$PROC_ID" >/dev/null 2>&1 ] && [ count -eq 60 ]; then
    #     echo "It takes too long to finish ELFS provisioning, kill it."
    #     kill -9 "$PROC_ID"
    #fi

    retval=$?
    if [ $retval -ne 0 ]; then
       NOW=`date +%m.%d.%Y.%H.%M.%S`
       testname=$(hostname)
       gsutil cp terraform.tfvars gs://cpe-performance-storage/test_result/terraform.tfvars.$disktype.$testname.$NOW.txt
       gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$testname.$NOW.txt
       name=$disktype-elfs
       cleanup $project $zone $name
       exit -1
    fi
    NOW=`date +%m.%d.%Y.%H.%M.%S`
   
    gsutil cp terraform.tfvars gs://cpe-performance-storage/test_result/terraform.tfvars.$disktype.$testname.$NOW.txt
    gsutil cp create_vheads.log gs://cpe-performance-storage/test_result/create_vheads.$disktype.$testname.$NOW.txt
}

start_vm() {
     project=$1
     zone=$2
     disktype=$3
     vmname=$disktype-$(hostname)
     echo "vmname = $vmname"
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-4'
     gcloud compute --project=$project instances create $vmname  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype  
     retval=$?
     if [ $retval -ne 0 ]; then
        elfsname=$disktype-elfs
        cleanup $project $zone $elfsname
        vmname=$disktype-$(hostname)
        cleanup $project $zone $vmname
        exit -1
     fi
}

is_test_done() {
   expected_files=$1
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/ | grep $(hostname) | grep elfs | grep fio | wc -l`
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
elfsname=''
vmname=''
testnam=''
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
test_done=`is_test_done 6`
echo "test_done is $test_done"
count=0
while [ $test_done -eq -1 ] && [ $count -lt 10 ] 
do
   sleep 60
   test_done=`is_test_done 6`
   echo "test_done is $test_done"
   count=$((count+1))
done

elfsname=$disktype-elfs
cleanup $project $zone $elfsname
vmname=$disktype-$(hostname)
cleanup $project $zone $vmname

if [ $test_done -eq -1 ]; then
    echo "io testing might have problem"
    exit -1
fi   
