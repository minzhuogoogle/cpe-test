#!/bin/bash

disktype_check()
{
    disktype=$1
    valid=(lssd pssd phdd)
    retVal=-1
    for x in "${valid[@]}"
    do
         if [ "$disktype" == "$x" ]; then
             retVal=0
         fi
    done
    return $retVal
}


initialization()
{
   cd gcp-automation/
   echo `pwd`
   echo $disktype
   curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.$disktype
   
   gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
   #gsutil cp gs://cpe-performance-storage-data/elastifile.json elastifile.json
   gcloud auth activate-service-account --key-file elastifile.json
   cp terraform.tfvars.$disktype terraform.tfvars
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
    #cd gcp-automation/
    echo "iotest ?"  $iotest
    if [ $iotest -eq 1 ]; then
        return 0
    fi    
    terraform init
    retval=$?
    if [ $retval -ne 0 ]; then
       return -1
    fi
    echo "run terraform apply to start elfs instance"
    sed -i 's/ssd/persistent/' terraform.tfvar
    if  [ "$pstest" == "1" ]; then
        sed -i 's/elfs/pselfs/' terraform.tfvars
    fi
    echo "==== new terraform.tfvars====="
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
       return 0
    else
       return -1
    fi
    
}


start_vm() {
     nfs_server=$1
     fio_start=$2
     test_duration=$3
     test_name=$4
     echo "project = $project"
     echo "zone = $zone"
     zone="us-east1-b"
     machine_type='n1-standard-1'
     if [ $pstest -eq 1 ]; then
          vminstance="psvm-$disktype-$(hostname)-$vmseq"
     else
          vminstance="vm-$disktype-$(hostname)-$vmseq"
     fi
     echo $vminstance

     gcloud compute --project=$project instances create $vminstance  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype\ $nfs_server\ $fio_start\ $test_duration\ $test_name
     retval=$?
     if [ $retval -ne 0 ]; then
           return -1
     fi
     vmseq=$((vmseq+1))
     return 0
}


inject_failure_into_cluster() {
    failure_node_name="$disktype-elfs-elfs"
    failure_node=`gcloud compute instances list --project $project --filter=$failure_node_name | grep -v NAME | cut -d ' ' -f1 | head -n 1`
    echo "vm to be deleted: $failure_node, $project, $zone"
    gcloud compute instances delete $failure_node --project $project --zone $zone -q
    retval=$?
    if [ $retval -ne 0 ]; then
           return -1
    fi
    return 0
}


logfiles_uploaded() {
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio | wc -l`
   export filelists=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio`
   return $number_logfiles
}

delete_vm() {
    #protected_nodes=(gke-prow-default-pool-acf595a2-bldl gke-prow-default-pool-acf595a2-hv8b)
    name=$1
    
    for i in `gcloud compute instances list --project $project --filter=$name | grep -v NAME | cut -d ' ' -f1`; 
    do 
       echo "vm to be deleted: $i, $project, $zone"
       ##for x in "${protected_nodes[@]}"
       #do
       #    if [ "$i" == "$x" ]; then
       #        return 0
       #    fi
       #done
       gcloud compute instances delete $i --project $project --zone $zone -q; 
    done
    retval=$?
    if [ $retval -ne 0 ]; then
           return -1
    fi
    return 0
}


delete_routers() {

    for i in `gcloud compute network list --project $project --filter=$vm_name | grep -v NAME | cut -d ' ' -f1`;
    do
       gcloud compute instances delete $i --project $project --zone $zone -q;
    done
}


cleanup() {
    vmaffix=$1
    echo "all vm with $vmaffix will be deleted"
    if [ "$vmaffix" == '' ]; then
        vmaffix='elfs'
    fi
    checklen=${#vmaffix}
    echo $checklen
    if [ $checklen -eq 0 ]; then
       return
    fi  
    delete_vm $vmaffix
    retval=$?
    if [ $retval -ne 0 ]; then
           return -1
    fi
    return 0
    #delete_traffic_node()
    #delete_routers()
    #delete_firewalls()
    #delete_subnetworks()
}


# --------------
# Start here
# ./elfse2e.sh phdd 0 1 300 elfs-daily-e2e-phdd'
# --------------
disktype=$1
testduration=$2
testname=$3
echo  $disktype $testduration $testname

project=''
newelfs=''
zone=''
region=''
edisk=''

clients=1
fio_done=0
vmseq=1
ha=0
skipprovision=1
deletion=0
pstest=0
iotest=0
cleanup=0

case "$testname" in
    *-daily-e2e* ) echo "prepare daily e2e test";mfio=0;skipprovision=0;deletion=1;;
    *-perf-* ) echo "preppare perf test";skipprovision=1;iotest=1;mfio=1;;
    *-scalability-* ) echo "prepare scability test";clients=9;iotest=1;mfio=1;;
    *elfs-ha-* ) echo "prepare ha test";ha=1;iotest=1;mfio=1;;
    *-io-* ) echo "prepare io only test";iotest=1;mfio=1;;
    *-ps-* ) echo "prepare postsubmit sanity test"; pstest=1;mfio=0;skipprovision=0;deletion=1;;
    *-cleanup-* ) echo "prepare to cleanup all resources used by testing"; cleanup=1;;
    * ) echo "Error...";;
esac

echo "skip?" $skipprovision "pstest?" $pstest "iotest?" $iotest "ha?" $ha "cleanup?" $cleanup
if [ $cleanup -eq 1 ]; then
   echo "start cleanup resource"
   cleanup "elfs"
   return 0
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

echo "delete traffic VMs........"
if [ $pstest -eq 0 ]; then
    export vmlists=`gcloud compute instances list --project $project --filter="vm-$disktype" | grep -v NAME | cut -d ' ' -f1`
else
    export vmlists=`gcloud compute instances list --project $project --filter="psvm-$disktype" | grep -v NAME | cut -d ' ' -f1`
fi    
for i in $vmlists
do 
    echo "vm to be deleted: $i, $project, $zone"
    gcloud compute instances delete $i --project $project --zone $zone -q; 
done

echo "delete elfs nodes........"
if [ "$deletion" == "1" ]; then
    if [ "$pstest" == "1" ]; then
         echo "delete elfs nodes created during postsubmit test........" 
         cleanup "$disktype-pselfs"
    else
         echo "delete elfs nodes created during test........" 
         cleanup "$disktype-elsf"
    fi   
fi

if [ "$skipprovision" == "0" ]; then
    provision_elastifile
fi

retval=$?
if [ $retval -ne 0 ]; then
    if [ "$deletion" == "1" ] && [ "$iotest" == "0" ]; then
         if [ "$pstest" -eq "1" ]; then
             cleanup "$disktype-pselfs"
         else
             cleanup "$disktype-elfs"
         fi   
    fi
    exit -1
fi

if [ "$pstest" == "1" ]; then
   snodename="$disktype-pselfs-elfs-" 
else
   snodename="$disktype-elfs-elfs-" 
fi   
echo $snodename $mfio $disktype
if [ "$mfio" == "0" ] ; then
     echo $snodename $mfio $disktype
     export nfs_server_ips=`gcloud compute instances list --project=cpe-performance-storage --filter=$snodename  --format="value(networkInterfaces[0].networkIP)" | head -n 1`
else
     echo $snodename $mfio $disktype
     export nfs_server_ips=`gcloud compute instances list --project=cpe-performance-storage --filter=$snodename  --format="value(networkInterfaces[0].networkIP)" `
fi     

echo "nfs servers:" $nfs_server_ip

# TODO: get number of enodes from nfs_server_ips
if [ "$mfio" == "0" ] ; then
     snodes=1
else
     snodes=4
fi 

echo $nfs_server_ips $snodes
delaytime=$(($clients+2))
export now=`date +"%s"`
echo $now  "wait for this minutes:" $delaytime
export timer=`date -d "+ $delaytime minutes" +"%s"`
echo `date -d "+ $delaytime minutes" +"%s"`
running_clients=0
while [ $running_clients -lt $clients ]
do
    for nfs_server in $nfs_server_ips
    do
        export now=`date +"%s"`
        newtimer=`date -d "+ 2 minutes" +"%s"`
        echo "this is now: ", $now, $newtimer
        echo "wait until:" $timer
        if [ $timer > $newtimer ]; then
           start_vm $nfs_server $timer $testduration $testname
        else
           start_vm $nfs_server $newtimer $testduration $testname
        fi
        export now=`date +"%s"`
        echo "this is now again", $now
        retval=$?
        if [ $retval -ne 0 ]; then
         #   cleanup
            exit -1
        fi  
        running_clients=$((running_clients+1))
    done
done
export now=`date`
if [ "$ha" == "1" ]; then
    inject_failure_into_cluster 
fi 
echo $now

sleep $(($testduration*6+30)) 

logfiles_uploaded
no_of_logfiles=$?
echo $no_of_logfiles
if [ "$mfio" == "0" ]; then
    expected_logfile=$((clients*6))
else
    expected_logfile=$((snodes*clients*6))
fi    

if [ $no_of_logfiles -ge $expected_logfile ]; then
    fio_done=1
fi    


count=0
while [[ "$fio_done" == "0"  &&  $count -lt 60 ]] 
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


if [ "$pstest" == "1" ]; then
    cleanup "$disktype-pselfs"
    cleanup "ps-$disktype-"
fi

if [ "$fio_done" == "0" ]; then
    echo "io testing might have problem."
    exit 0
fi  
