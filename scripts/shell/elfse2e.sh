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


provision_elastifile() {
    terraform init
    retval=$?
    if [ $retval -ne 0 ]; then
       exit -1
    fi
    echo "run terraform apply to start elfs instance"
    if  [ "$pstest" == "1" ]; then
        sed -i 's/elfs/pselfs/' terraform.tfvars
    fi
   
    cat terraform.tfvars
    
    terraform apply --auto-approve | tee -a output.txt &

    maxcount=30
    count=0
    ret=1
    
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

    if [ $retval -eq -1 ] || [ "$status" = "Failed." ] ; then
       NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
       
       cat terraform.tfvars >> output.txt
       if  [ -f "create_vheads.log" ]; then
          cat create_vheads.log >> output.txt 
       fi   
       logfile=$testname.terraform.provision.$(hostname).$NOW.$disktype.txt
       gsutil cp output.txt gs://cpe-performance-storage/test_result/$logfile
       echo $logfile
       name=$disktype-elfs
       return -1
    fi
    
    if  [ -f "create_vheads.log" ]; then
       NOW=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
       
       cat terraform.tfvars >> output.txt
       cat create_vheads.log >> output.txt 
       logfile=$testname.terraform.provision.$(hostname).$NOW.$disktype.txt
       gsutil cp output.txt gs://cpe-performance-storage/test_result/$logfile
       echo $logfile
    else
       return -1
    fi
    
}


start_vm() {
     nfs_server=$1
     fio_start=$2
     test_duration=$3
     test_name=$4
     echo "vmname = $vmname"
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-4'
     vminstance="$disktype-$(hostname)-$vmseq"
     echo $vminstance

     gcloud compute --project=$project instances create $vminstance  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype\ $nfs_server\ $fio_start\ $test_duration\ $test_name
    # retval=$?
    # if [ $retval -ne 0 ]; then
    #    cleanup 
    #    return -1
    # fi
     vmseq=$((vmseq+1))
}


inject_failure_into_cluster() {
    failure_node_name="$disktype-elfs-elfs"
    failure_node=`gcloud compute instances list --project $project --filter=$failure_node_name | grep -v NAME | cut -d ' ' -f1 | head -n 1`
    echo "vm to be deleted: $failure_node, $project, $zone"
    gcloud compute instances delete $failure_node --project $project --zone $zone -q
}


logfiles_uploaded() {
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio | wc -l`
   export filelists=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio`
   return $number_logfiles
}

delete_vm() {
    name=$1
    for i in `gcloud compute instances list --project $project --filter=$name | grep -v NAME | cut -d ' ' -f1`; 
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
    vmaffix=$1
    if [ "$vmaffix" == '' ]; then
        vmaffix='elfs'
    fi
    checklen=${#vmaffix}
    echo $checklen
    if [ $checklen -eq 0 ]; then
       return
    fi  
    delete_vm $vmaffix
    #delete_traffic_node()
    #delete_routers()
    #delete_firewalls()
    #delete_subnetworks()
}


# --------------
# Start here
# ./elfse2e.sh phdd 0 1 300 elfs-daily-e2e-phdd'
# --------------
clients=1
project=''
newelfs=''
zone=''
region=''
edisk=''
fio_done=0
vmseq=1
ha=0
disktype=$1
mfio=$2
deletion=$3
testduration=$4
testname=$5
clients=1
skipprovision=0
pstest=0

echo  $disktype $mfio $deletion $testduration $testname

case "$testname" in
    *-daily-* ) echo "prepare daily e2e test";;
    *-perf-* ) echo "preppare perf test";skipprovision=1;;
    *-scalability-* ) echo "prepare scability test";clients=256;skipprovision=1;;
    *-ha-* ) echo "prepare ha test";ha=1;;
    *-io-* ) echo "prepare io only test";skipprovision=1;;
    *-ps-* ) echo "prepare postsubmit sanity test"; newelfs="pselfs-$disktype"; pstest=1;;
    * ) echo "Error...";;
esac


if [ "$deletion" -eq "1" ] ; then
  if [[ $testname = *-io-* ]]; then
      echo "Skip cleanup elastfile nodes"
      cleanup $(hostname)
  else
      cleanup $disktype
  fi
fi


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

if [ "$skipprovision"  -eq "0" ]; then
    provision_elastifile
fi
retval=$?
if [ $retval -ne 0 ]; then
    #cleanup
    exit -1
fi

if [ "$pstest" -eq "1" ]; then
   export nfs_server_ips=`gcloud compute instances list --project=cpe-performance-storage --filter="$disktype-pselfs-elfs-"  --format="value(networkInterfaces[0].networkIP)"`
else
   export nfs_server_ips=`gcloud compute instances list --project=cpe-performance-storage --filter="$disktype-elfs-elfs-"  --format="value(networkInterfaces[0].networkIP)"`
fi
export snodes=`gcloud compute instances list --project=cpe-performance-storage --filter="$disktype-elfs-elfs-"  | wc -l`
snodes=3
echo $nfs_server_ips $snodes

delaytime=$(($snodes*$clients))
export now=` date +"%s"`
echo $now $delaytimer
export timer=`date -d "+ $delaytime minutes" +"%s"`
running_clients=0
while [ $running_clients -lt $clients ]
do
    for nfs_server in $nfs_server_ips
    do
        export now=` date`
        echo $now
        start_vm $nfs_server $timer $testduration $testname
        retval=$?
        if [ $retval -ne 0 ]; then
         #   cleanup
            exit -1
        fi
        running_clients=$((running_clients+1))
    done
done
export now=` date `
if [ "$ha" -eq '1' ]; then
    inject_failure_into_cluster 
fi 
echo $now

sleep $(($testduration*6+300)) 

logfiles_uploaded
no_of_logfiles=$?
echo $no_of_logfiles
if [ "$mfio" -eq "0" ]; then
    expected_logfile=$((clients*6))
else
    expected_logfile=$((nodes*clients*6))
fi    

if [ $no_of_logfiles -ge $expected_logfile ]; then
        fio_done=1
fi    
count=0
while [[ "$fio_done" -eq "0"  &&  $count -lt 60 ]] 
do
   sleep 60
   logfiles_uploaded
   no_of_logfiles=$?
   echo $no_of_logfiles
   if [ $no_of_logfiles -ge $expected_logfile ]; then
        fio_done=1
   fi      
   count=$((count+1))
done

sleep 600
export now=` date `
echo $now

#if [ "$deletion" -eq '1' ]; then
#   if [ "$pstest" -eq "1" ]; then
#        cleanup "$disktype-pselfs"
#   fi
#   cleanup "$disktype-elfs"  
#fi



if [ "$test_done" -eq "-1" ]; then
    echo "io testing might have problem."
    exit -1
fi  
