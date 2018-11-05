#!/bin/bash

SCALE_VM=16
PERF_VM=4
declare -a ELFSNAME=( 'test-elfs' 'ha-lssd-elfs' 'ha-pssd-elfs' 'ha-phdd-elfs' 'test-lssd-elfs' 'test-pssd-elfs' 'test-phdd-elfs' 'ha-elfs' 'test-elfs')

delete_vm() {
    name=$1
    echo $name
    for i in `gcloud compute instances list --project $project --filter="zone:$zone name:$name"  | grep -v NAME |  cut -d ' ' -f1`;
    do
        echo "vm to be deleted: $i, $project, $zone"
        gcloud compute instances delete $i --project $project --zone $zone -q;
        #retval=$?
        #if [ $retval -ne 0 ]; then
        #    return -1
        #fi
    done
    return 0
}

delete_address() {
    name=$1
    region=$2
    echo "delete_address $name $region"
    #echo "cmd: gcloud compute addresses list --project $project --filter=$region | grep $name |  cut -d ' ' -f1"
    for i in `gcloud compute addresses list --filter=$region | grep $name |  cut -d ' ' -f1`;
    do
         echo "addess to be deleted: $i, $project, $region"
         gcloud compute addresses delete $i --project $project --region $region -q;
         retval=$?
         if [ $retval -ne 0 ]; then
             return -1
         fi
    done
}

delete_subnet() {
     name=$1
     region=$2
     echo "delete_subnet $name $region"
     #echo "cmd: gcloud compute  networks subnets  list --project $project   --filter=$region | grep $name  | cut -d ' ' -f1"
     for i in `gcloud compute  networks subnets  list  --filter=$region | grep $name  | cut -d ' ' -f1`;
     do
         echo "subnet to be deleted: $i, $project, $region"
         gcloud compute  networks subnets delete $i --project $project --region $region -q;
         retval=$?
         if [ $retval -ne 0 ]; then
             return -1
         fi
     done
}

delete_route() {
    name=$1
    region=$2
    echo "delete_route $name $region"
    #echo "cmd: gcloud compute routes list --project $project  --filter=$region | grep $name  | cut -d ' ' -f1"
    for i in `gcloud compute routes list   --filter=$region | grep $name  | cut -d ' ' -f1`;
    do
        echo "route to be deleted: $i, $project, $region"
        gcloud compute  routes delete $i --project $project -q;
        retval=$?
        if [ $retval -ne 0 ]; then
            return -1
        fi
     done
}

delete_network() {
    name=$1
    region=$2
    echo "delete_network $name $region"
    #echo "cmd: gcloud compute  networks subnets  list --project $project   --filter=$region | grep $name  | cut -d ' ' -f1"
    for i in `gcloud compute networks list --project $project  --filter=$region | grep $name | cut -d ' ' -f1`;
    do
        echo "network to be deleted: $i, $project, $region"
        gcloud compute networks  delete $i --project $project -q;
        retval=$?
        if [ $retval -ne 0 ]; then
            return -1
        fi
     done
}

delete_firewall() {
    name=$1
    region=$2
    echo "delete_firewall $name $region"
    #echo "cmd: gcloud compute firewall-rules list --project $project  --filter="NAME:$name"  --format="table(NAME)" | grep -v NAME |  cut -d ' ' -f1"
    for i in `gcloud compute firewall-rules list  --filter="NAME:$name"  --format="table(NAME)" | grep -v NAME |  cut -d ' ' -f1`;
    do
        echo "firewall to be deleted: $i, $project, $region"
        gcloud compute firewall-rules delete $i --project $project -q;
        retval=$?
        if [ $retval -ne 0 ]; then
            return -1
        fi
     done
}

cleanup_test() {
    name=$1
    delete_vm $name
    for i in `gcloud compute regions list  | cut -d ' ' -f1`
    do
        echo $i
        if [[ $zone =~ $i ]]; then
           echo "zone $zone in region $i "
           delete_address $name $i
           delete_subnet $name $i
           delete_route $name $i
           delete_network $name $i
	   continue
	fi   
    done
    delete_firewall $name
}

disktype_check() {
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


initialization() {
    clients=1
    vmseq=1
    skipprovision=1
    mfio=0
    deletion=0
    cleanup=0
    pstest=0
    iotest=0
    hatest=0
    demotest=0
    scaletest=0
    nodefailure=0
    diskfailure=0
    
    project=cpe-performance-storage
    zone=us-east1-b
    region=us-east1
    cluster=test-$disktype-elfs
    elfsimage=elastifile-storage-2-7-5-12-ems
    
    emsname="test-$disktype-elfs"
    enodename="test-$disktype-elfs-elfs"
    testvmname="test-elfs-$disktype"
    
    
    case "$testname" in
        elfs-daily-e2e* ) 
            echo "prepare daily e2e test";
            skipprovision=0;
            deletion=1
        ;;
        elfs-perf-* ) 
            echo "prepare perf test";
            iotest=1;
            mfio=1;
	    clients=$PERF_VM;
        ;; 
        elfs-scalability-* ) 
            echo "prepare scability test";
            clients=$SCALE_VM;
            iotest=1;
	    scaletest=1;
            mfio=1;
	;;
        elfs-ha-*-node* ) 
            echo "prepare ha test for node failure";
            hatest=1;
            nodefailure=1;
            emsname="ha-$disktype-elfs";
            enodename="ha-$disktype-elfs-elfs"; 
            testvmname="ha-elfs-$disktype";
            skipprovision=0
            deletion=1
            zone=us-central1-f;
	    region=us-central1;
            cluster=ha-$disktype-elfs
        ;;
        elfs-ha-*-disk* ) 
            echo "prepare ha test for disk failure";
            hatest=1;
            diskfailure=1;
            emsname="ha-$disktype-elfs";
            enodename="ha-$disktype-elfs-elfs"; 
            testvmname="ha-elfs-$disktype";
            skipprovision=0
            deletion=1
            zone=us-central1-f;
	    region=us-central1;
            cluster=ha-$disktype-elfs
        ;;
        elfs-daily-io-* ) 
            echo "prepare io only test";
            iotest=1;
            mfio=1
        ;;
        elfs-ps-* ) 
            echo "prepare postsubmit sanity test"; 
	    mfio=1;
            pstest=1;
            skipprovision=0;
            deletion=1;
            emsname="ps-$disktype-elfs";
            enodename="ps-$disktype-elfs-elfs"; 
            testvmname="ps-elfs-$disktype";
            cluster=ps-$disktype-elfs
        ;;
        elfs-demo-*-single* ) 
            echo "prepare to run io on demo lssd instance";
            iotest=1;
            emsname="demo-$disktype-vm";
            enodename="demo-$disktype-vm-elfs"; 
            testvmname="demo-vm-$disktype";
            iotest=1;
            clients=1;
            demotest=1;
        ;;
        elfs-demo-*-scalability* ) 
            echo "prepare to run io on demo lssd instance";
            iotest=1;
            emsname="demo-$disktype-vm";
            enodename="demo-$disktype-vm-elfs"; 
            testvmname="demo-vm-$disktype";
            iotest=1;
            clients=$PERF_VM;
            demotest=1;
	    scaletest=1;
            mfio=1
        ;;
	elfs-cleanup ) 
            echo "prepare to cleanup all resources used by testing"; 
            cleanup=1;
	    return 0
        ;;
        * ) echo "Error..."
        ;;
    esac
    
    disktype_check $disktype
    retval=$?
    if [ $retval -ne 0 ]; then
        echo "Disktype $disktype provided is not supported, please select one of: lssd, pssd or phdd."
        return -1
    fi
   
    case "$disktype" in 
        lssd )
	    elfstemplate=custom
	    ;;
	pssd )
	    elfstemplate=medium
	    ;;
	phdd )
	    elfstemplate=small
	    ;;
	* ) echo "Error..."
        ;;
    esac
    
    io_data_done=0
    io_integrity_done=0

    echo "disktype = $disktype"
    echo "project = $project"
    echo "region = $region"
    echo "zone = $zone"
    echo "testname = $testname"
    echo "ioruntime = $ioruntime"
 
    echo "Elastifile Cluster name = $emsname"
    echo "Elastifile node name = $enodename"
    echo "Elastifile test vm name = $testvmname"
    
    cd gcp-automation/
    gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
    gcloud auth activate-service-account --key-file elastifile.json
}   
 

pre_cleanup() {
    echo "delete traffic VMs........"
    delete_vm $testvmname

    if [ $deletion -eq 1 ]; then
        echo "delete elfs nodes........"
        delete_vm $emsname
    fi
}

post_cleanup() {
    if [ $io_data_done -eq 1 ]; then
        delete_vm $testvmname 
	if [[ $hatest -eq 1 || $pstest -eq 1 ]]; then
	    delete_vm $emsname
	fi
    fi	
}	

prepare_io_test () {
    if [ $mfio -eq 0 ] ; then
        export nfs_server_ips=`gcloud compute instances list --project=$project --filter=$enodename  --format="value(networkInterfaces[0].networkIP)" | head -n 1`
    else
        export nfs_server_ips=`gcloud compute instances list --project=$project --filter=$enodename  --format="value(networkInterfaces[0].networkIP)" `
    fi
    echo "nfs servers: $nfs_server_ips"
    
    for i in $nfs_server_ips
    do
        enodecount=$((enodecount+1))
    done
   
    if [ $enodecount -eq 0 ]; then
        echo "No enode available."
        return -1 
    fi
    
    clients=$((clients*enodecount))
    echo "Total clients: $clients for $enodecount enodes."
    return 0
}


provision_elastifile() {
    curl -OL https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/elastifile/terraform.tfvars.$disktype
    cp terraform.tfvars.$disktype terraform.tfvars
    cat terraform.tfvars
    # temporarily disable load-balancing
    sed -i 's/true/false/' terraform.tfvars

    sed -i "s/testimage/${elfsimage}/g" terraform.tfvars
    sed -i "s/testtemplate/${elfstemplate}/g" terraform.tfvars
    sed -i "s/testzone/${zone}/g" terraform.tfvars
    sed -i "s/testproject/${project}/g" terraform.tfvars
    sed -i "s/testcluster/${cluster}/g" terraform.tfvars

    echo "==== new terraform.tfvars====="
    cat terraform.tfvars

    if [[ $iotest -eq 1 || $demotest -eq 1 ]]; then
        return 0
    fi
    
    terraform init
    retval=$?
    if [ $retval -ne 0 ]; then
       return -1
    fi

    terraform apply --auto-approve | tee -a output.txt &

    maxcount=15
    count=0
    ret=1

    while [ $count -lt $maxcount ] && [ $ret -eq 1 ]; do
        num_terraform_proc=$(ps -ef | grep "terraform apply"  | grep -v workspace | grep -v grep | wc -l)
        echo "terraform processs is $num_terrform_proc . counter=$count"
        if [ $num_terraform_proc -gt 0 ]; then
            echo "terraform still running"
            ret=1
            sleep 60
        else
            echo "terraform stopped"
            ret=0
        fi
        count=$((count+1))
    done

    if [ $count -eq $maxcount ] && [ $ret -eq 1 ]; then
        echo "Terraform failed to stop!! "
        retval=-1
    else
        echo "Terraform finished"
        retval=0
    fi

    process=$( grep Failed create_vheads.log | cut -d ' ' -f1 )
    status=$( grep Failed create_vheads.log | cut -d ' ' -f2 )
    echo "process=$process, status=$status"
    if [ $retval -eq -1 ] || [ "$status" = "Failed." ] ; then
        currenttime=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
	echo $currenttime >> output.txt
        cat terraform.tfvars >> output.txt
        if [ -f "create_vheads.log" ]; then
            cat create_vheads.log >> output.txt
        fi
        logfile=$testname.terraform.provision.$(hostname).$currenttime.$disktype.txt
        gsutil cp output.txt gs://cpe-performance-storage/test_result/$logfile
        echo "$logfile is uploaded to gcs bucket."
        return -1
    fi

    if [ -f "create_vheads.log" ]; then
        currenttime=`TZ=UTC+7 date +%m.%d.%Y.%H.%M.%S`
	echo $currenttime >> output.txt
        cat terraform.tfvars >> output.txt
        cat create_vheads.log >> output.txt
        logfile=$testname.terraform.provision.$(hostname).$currenttime.$disktype.txt
        gsutil cp output.txt gs://cpe-performance-storage/test_result/$logfile
        echo "$logfile is uploaded to gcs bucket."
        return 0
    else
        return -1
    fi

}

run_test() {
    prepare_io_test
    retval=$?
    if [ $retval -ne 0 ]; then
	echo "Failure in retrieve Elastifile enode."    
        return -1
    fi
    if [ $mfio -eq 0 ]; then
        delaytime=2
    else
        delaytime=$((clients+2))
        if [ $scaletest -eq 1 ]; then
            delaytime=$((enodecount*8))
	    ioruntime=$((clients*60+120))
        fi
    fi
    
    echo "delaytime=$delaytime minutes, ioruntime=$ioruntime seconds".
    export now=`date +"%s"`
    export timer=`date -d "+ $delaytime minutes" +"%s"`
    echo "current timestamp: $now; traffic starting timestamp:$timer"
    running_clients=0
    if [ $hatest -eq 0 ]; then
        while [ $running_clients -lt $clients ]
        do
            for nfs_server in $nfs_server_ips
            do
                newtimer=`date -d "+ 3minutes" +"%s"`
                if [ $timer -gt $newtimer ]; then
                    start_vm $nfs_server $timer $ioruntime $testname
                else
                    start_vm $nfs_server $newtimer $ioruntime $testname
                fi
 		retval=$?
                if [ $retval -ne 0 ]; then
                   echo "Fail to create test vm."
                   delete_vm $testvmname
                   return -1 
                fi 
                export now=`date`
                echo "Now:" $now
                running_clients=$((running_clients+1))
            done
        done
    else	
        inject_failure_into_cluster
	retval=$?
        if [ $retval -ne 0 ]; then
            echo "Fail to inject failure into cluster."
	    return -1 
        fi 
    fi
    return 0
}	

start_vm() {
     nfs_server=$1
     fio_start=$2
     test_duration=$3
     test_name=$4
     echo "project = $project"
     echo "zone = $zone"
     machine_type='n1-standard-1'

     echo $testvmname
     if [ $hatest -eq 1 ]; then
         gcloud compute --project=$project instances create $testvmname-ha-$(hostname)-$vmseq  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_hatest.sh\;\ sudo\ chmod\ 777\ vm_hatest.sh\;\ sudo\ ./vm_hatest.sh\ $disktype\ $nfs_server\ $fio_start\ $test_duration\ $test_name
     else
         gcloud compute --project=$project instances create $testvmname-$(hostname)-$vmseq  --zone=$zone --machine-type=$machine_type --scopes=https://www.googleapis.com/auth/devstorage.read_write --metadata=startup-script=sudo\ curl\ -OL\ https://raw.githubusercontent.com/minzhuogoogle/cpe-test/master/scripts/shell/vm_runfio.sh\;\ sudo\ chmod\ 777\ vm_runfio.sh\;\ sudo\ ./vm_runfio.sh\ $disktype\ $nfs_server\ $fio_start\ $test_duration\ $test_name

     fi
     retval=$?
     if [ $retval -ne 0 ]; then
           return -1
     fi
     vmseq=$((vmseq+1))
     return 0
}


inject_node_failure_to_clustervm() {
    enode=$1
    gcloud compute instances delete $enode  --project=$project  --zone=$zone -q
    retval=$?
    if [ $retval -ne 0 ]; then
         return -1
    fi
}


inject_storage_failure_to_vm() {
    enode=$1
    echo "Detaching disk from Enode $enode." 
    export diskindex=`gcloud compute instances describe $enode --project=$project  --zone=$zone --format="text(disks[].index)"   |  tail -n 1 |  cut -d ' ' -f2`
    diskindex=$((diskindex-1))
    export diskname=`gcloud compute instances describe $enode  --project=$project  --zone=$zone  --format="text(disks[$diskindex].deviceName)" | grep $disktype-elfs-elfs | cut -d ' ' -f2 `
    echo "This is disk $diskname to be detached from $enode."
    echo "cmd: gcloud compute instances detach-disk  $enode  --disk=$diskname   --zone=$zone  -q"
    gcloud compute instances detach-disk  $enode  --disk=$diskname   --zone=$zone  -q
    retval=$?
    if [ $retval -ne 0 ]; then
         return -1
    fi
}

inject_failure_into_cluster() {
    echo "cmd==gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | tail -n 1"
    echo "cmd==gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | head -n 1"
    export failure_node=`gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | tail -n 1`
    export traffic_node=`gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | head -n 1`
    echo "failured to be injected: $failure_node, traffic node: $traffic_node"
    delaytime=2
    export now=`date +"%s"`
    export timer=`date -d "+ $delaytime minutes" +"%s"`
    echo "Wait for this minutes: $delaytime, $timer since $now"
    if [ $nodefailure -eq 1 ]; then
        echo "prepare to inject failure in enode";
        for nfs_server in $nfs_server_ips
	do
            start_vm $nfs_server $timer $ioruntime $testname
	done     
        inject_node_failure_to_clustervm $failure_node
        retval=$?
        if [ $retval -ne 0 ]; then
            return -1
        fi
    fi
    if [ $diskfailure -eq 1 ]; then
         echo "preppare to inject failure in storage on enode";
         for nfs_server in $nfs_server_ips
	 do
             start_vm $nfs_server $timer $ioruntime $testname
	 done
         inject_storage_failure_to_vm $failure_node
         retval=$?
         if [ $retval -ne 0 ]; then
              return -1
         fi
    fi    
    return 0
}


logfiles_uploaded() {
   export number_logfiles=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio | wc -l`
   export filelists=`gsutil ls gs://cpe-performance-storage/test_result/** | grep $(hostname) | grep $testname | grep fio`
   echo $filelists
   return $number_logfiles
}


test_result() {
    count=0
    if [ $hatest -eq 1 ]; then
        maxcount=15
	waittime=$((ioruntime+delaytime*60))
    elif [ $scaletest -eq 1 ]; then
        maxcount=30
	waittime=$((ioruntime*2+delaytime*60))
    else
        maxcount=30
        waittime=$((ioruntime*6+delaytime*60))
    fi 	
    export now=`date`
    echo "clock :  $now"
    echo "wait for $waittime seconds"
    sleep $waittime	
    export now=`date`
    echo "clock :  $now"
    no_of_logfiles=0
    logfiles_uploaded
    no_of_logfiles=$?
    echo $no_of_logfiles
    
    if [ $hatest -eq 1 ]; then
        expected_logfile=1
    elif [ $scaletest -eq 1 ]; then
        expected_logfile=$((clients*2))
    else
        expected_logfile=$((clients*6))
    fi	
    
    echo "expected_logfile:" $expected_logfile
   
    if (($no_of_logfiles < $expected_logfile )); then
       io_data_done=0
    else
       io_data_done=1
    fi
    count=0
    while [[ $io_data_done -eq 0  &&  $count -lt $maxcount ]]
    do
        echo "sleep to check logfile done?  $io_date_done count=  $count "
        sleep 60
        logfiles_uploaded
        no_of_logfiles=$?
        echo "no of logfiles:  $no_of_logfiles; expected logfile:  $expected_logfile"
        if [ $no_of_logfiles -ge $expected_logfile ]; then
            echo "set test done"
            io_data_done=1
        else
            echo "set test not done"
            io_data_done=0
        fi
      
        count=$((count+1))
    done

    if [ $io_data_done -eq 0 ]; then
        echo "io testing might have problem."
        return -1
    fi 

    return 0
}

# ----------------------------------------------------
# Start here
# example: ./elfse2e.sh phdd  300 elfs-daily-e2e-phdd
#          elfs-daily-e2e-phdd -- testname
#          phdd --- persistent hdd
#          300  --- io test run time
# ----------------------------------------------------
testname=$1
disktype=$2
ioruntime=$3

clients=1
delaytime=0
enodecount=0

initialization
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

if [ $cleanup -eq 1 ]; then
    for j in "${ELFSNAME[@]}"
    do
        case "$j" in 
        ha* )
	    zone="us-central1-f"
	    ;;
	demo* )
	    zone="us-east1-b"
	    ;;
	* )
	    zone="us-east1-b"
            ;;
        esac
        echo "Cleaning up all resources with name $j in zone $zone"
        cleanup_test $j
    done
    exit 0
fi    

pre_cleanup
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

if [ $skipprovision -eq 0 ]; then
    provision_elastifile
    retval=$?
    if [ $retval -ne 0 ]; then
        exit -1
    fi
fi

run_test
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

test_result
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

post_cleanup
retval=$?
if [ $retval -ne 0 ]; then
    exit -1
fi

exit 0
