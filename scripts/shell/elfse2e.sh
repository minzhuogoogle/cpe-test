#!/bin/bash

delete_vm() {
    name=$1
    echo $name
    for i in `gcloud compute instances list --project $project --filter=$name  | grep -v NAME |  cut -d ' ' -f1`;
    do
       echo "vm to be deleted: $i, $project, $zone"
       gcloud compute instances delete $i --project $project --zone $zone -q;
       retval=$?
       if [ $retval -ne 0 ]; then
          return -1
       fi
    done
    return 0
}

delete_address() {
    name=$1
    region=$2
    for i in `gcloud compute addresses list --project $project --filter=$region | grep $name |  cut -d ' ' -f1`
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
    for i in `gcloud compute  networks subnets  list --project $project   --filter=$region | grep $name  | cut -d ' ' -f1`;
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

    for i in `gcloud compute routes list --project $project  --filter=$region | grep $name  | cut -d ' ' -f1`;
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
    for i in `gcloud compute firewall-rules list --project $project  --filter="NAME:$name"  --format="table(NAME)" | grep -v NAME |  cut -d ' ' -f1`;
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
       if [[ $i =~ "NAME" ]]; then
           echo "skip"
           continue
       fi
       delete_address $name $i
       delete_subnet $name $i
       delete_route $name $i
       delete_network $name $i
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
    nodefailure=0
    diskfailure=0
    project=cpe-performance-storage
    zone=us-east1-b
    region=us-east1
    cluster=test-$disktype-elfs
    elfsimage=elastifile-storage-2-7-5-12-ems
    
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

    
    emsname="test-$disktype-elfs"
    enodename="test-$disktype-elfs-elfs"
    testvmname="test-elfs-$disktype"
    echo $emsname, $enodename, $testvmname

    echo "disktype = $disktype"
    echo "project = $project"
    echo "zone = $zone"
    echo "disktype = $disktype"
 
    case "$testname" in
        *-daily-e2e* ) 
            echo "prepare daily e2e test";
            mfio=0;
            skipprovision=0;
            deletion=1
        ;;
        *-perf-* ) 
            echo "preppare perf test";
            skipprovision=1;
            iotest=1;
            mfio=1
        ;; 
        *-scalability-* ) 
            echo "prepare scability test";
            clients=1;
            iotest=1;
            mfio=1
        ;;
        *elfs-ha-*-node* ) 
            echo "prepare ha test";
            hatest=1;
            mfio=0;
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
        *elfs-ha-*-disk* ) 
            echo "prepare ha test";
            hatest=1;
            mfio=0;
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
        *-io-* ) 
            echo "prepare io only test";
            iotest=1;
            mfio=1
        ;;
        *-ps-* ) 
            echo "prepare postsubmit sanity test"; 
            pstest=1;
            mfio=0;
            skipprovision=0;
            deletion=1;
            emsname="ps-$disktype-elfs";
            enodename="ps-$disktype-elfs-elfs"; 
            testvmname="ps-elfs-$disktype";
            cluster=ps-$disktype-elfs
        ;;
        *-cleanup-* ) 
            echo "prepare to cleanup all resources used by testing"; 
            cleanup=1
        ;;
        *-demo-*-single* ) 
            echo "prepare to run io on demo lssd instance";
            iotest=1;
            emsname="demo-$disktype-vm";
            enodename="demo-$disktype-vm-elfs"; 
            testvmname="demo-vm-$disktype";
            iotest=1;
            clients=4;
            demotest=1;
            mfio=1
        ;;
        *-demo-*-scale* ) 
            echo "prepare to run io on demo lssd instance";
            iotest=1;
            emsname="demo-$disktype-vm";
            enodename="demo-$disktype-vm-elfs"; 
            testvmname="demo-vm-$disktype";
            iotest=1;
            clients=16;
            demotest=1;
            mfio=1
        ;;
        * ) echo "Error..."
        ;;
    esac

    cd gcp-automation/
    gsutil cp gs://cpe-performance-storage/cpe-performance-storage-b13c1a7348ad.json elastifile.json
    gcloud auth activate-service-account --key-file elastifile.json
    echo `pwd`
    disktype_check $disktype
    retval=$?
    if [ $retval -ne 0 ]; then
        echo "Disktype $disktype provided is not supported, please select one of: lssd, pssd or phdd."
        return -1
    fi
}   
 
cleanup_test () {
    echo "start cleanup resource"
    cleanup $emsname 
    cleanup $testvmname
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
    if [ "$io_date_done" == "1" ]; then
        delete_vm $testvmname 
    fi	
    if [ "$pstest" == "1" ]; then
        delete_vm $emsname
    fi
    if [ "$io_integrity_done" == "1" ]; then
        delete_vm $emsname
    fi
}	

prepare_io_test () {
    if [ $mfio -eq 0 ] ; then
        export nfs_server_ips=`gcloud compute instances list --project=$project --filter=$enodename  --format="value(networkInterfaces[0].networkIP)" | head -n 1`
    else
        export nfs_server_ips=`gcloud compute instances list --project=$project --filter=$enodename  --format="value(networkInterfaces[0].networkIP)" `
    fi
    echo "nfs servers:" $nfs_server_ip

    vhead_count=0
    for i in nfs_server_ips
    do
        vhead_count=$((vhead_count+1))
    done

    if [ $vhead_count -eq 0 ]; then
        echo "no enode available"
        return -1 
    fi

    clients=$((clients*vhead_count))

    return 0
}


provision_elastifile() {
    #cd gcp-automation/
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

    echo "terraform.tfvars used in this test"
    cat terraform.tfvars

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
    if  [ $pstest -eq 1 ]; then
        echo "set number of node"
        sed -i "s/test-${disktype}/ps-${disktype}/g" terraform.tfvars
    fi
    if  [ $hatest -eq 1 ]; then
        echo "set number of node"
        sed -i "s/test-${disktype}/ha-${disktype}/g" terraform.tfvars
        sed -i "s/us-east1-b/us-central1-f/g" terraform.tfvars
        zone='us-central1-f'
    fi
    echo "==== new terraform.tfvars====="
    cat terraform.tfvars

    terraform apply --auto-approve | tee -a output.txt &

    maxcount=20
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
    echo "provision done" $enodename $mfio $disktype
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


run_test() {
    prepare_io_test
    retval=$?
    if [ $retval -ne 0 ]; then
	echo "Failure in retrieve Elastifile enode"    
        return -1
    fi
    delaytime=$(($clients+2))
    export now=`date +"%s"`
    export timer=`date -d "+ $delaytime minutes" +"%s"`
    echo $now "wait for this minutes to start traffic on testing vm" $delaytime $timer
    running_clients=0
    while [ $running_clients -lt $clients ]
    do
        for nfs_server in $nfs_server_ips
        do
            export now=`date +"%s"`
            newtimer=`date -d "+ 1minutes" +"%s"`
            echo "Now: ", $now, $newtimer
            echo "Wait until:" $timer
            if [ $timer > $newtimer ]; then
                start_vm $nfs_server $timer $ioruntime $testname
            else
                start_vm $nfs_server $newtimer $ioruntime $testname
            fi
 		    
            retval=$?
            if [ $retval -ne 0 ]; then
                echo "Fail to create test vm."
                delete_vm $testvmname
                exit -1 
            fi 
           
            export now=`date +"%s"`
            echo "Now:", $now
            running_clients=$((running_clients+1))
        done
    done
    if [ $hatest -eq 1 ]; then
        inject_failure_into_cluster
        retval=$?
        if [ $retval -ne 0 ]; then
            echo "Fail to create test vm."
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
     #zone="us-east1-b"
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
# gcloud compute instances describe test-lssd-elfs-elfs-1d391f3b  --format="text(disks[0].deviceName)"
# gcloud compute instances detach-disk   test-pssd-elfs-elfs-08e6beef    --disk=test-pssd-elfs-elfs-08e6beef-external-ssd-01
    enode=$1
    gcloud compute instances stop $enode  --project=$project  --zone=$zone
    retval=$?
    if [ $retval -ne 0 ]; then
         return -1
    fi
}


inject_storage_failure_to_vm() {
# gcloud compute instances describe test-lssd-elfs-elfs-1d391f3b  --format="text(disks[0].deviceName)"
# gcloud compute instances detach-disk   test-pssd-elfs-elfs-08e6beef	 --disk=test-pssd-elfs-elfs-08e6beef-external-ssd-01
    echo "detaching disk" 
    enode=$1
    export diskindex=`gcloud compute instances describe $enode --project=$project  --zone=$zone --format="text(disks[].index)"   |  tail -n 1 |  cut -d ' ' -f2`
    diskindex=$((diskindex-1))
    export diskname=`gcloud compute instances describe $enode  --project=$project  --zone=$zone  --format="text(disks[$diskindex].deviceName)" | grep $disktype-elfs-elfs | cut -d ' ' -f2 `
    echo $diskname
    echo "this is disk to be detached from $enode: $diskname"
    echo "cmd: gcloud compute instances detach-disk  $enode  --disk=$diskname   --zone=$zone  -q"
    gcloud compute instances detach-disk  $enode  --disk=$diskname   --zone=$zone  -q
    retval=$?
    if [ $retval -ne 0 ]; then
         return -1
    fi
}

inject_failure_into_cluster() {
    echo "info:" $project $enodename
    echo "cmd==gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | tail -n 1"
    echo "cmd==gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | head -n 1"
    export failure_node=`gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | tail -n 1`
    #export traffic_node=`gcloud compute instances list --project $project --filter=$enodename | grep -v NAME | cut -d ' ' -f1 | tail -n 1`
    echo "ha nodes:" $failure_node $traffic_node
    delaytime=0
    export now=`date +"%s"`
    echo $now  "......wait for this minutes:" $delaytime
    export timer=`date -d "+ $delaytime minutes" +"%s"`
    echo `date -d "+ $delaytime minutes" +"%s"`
    if [ $nodefailure -eq 1 ]; then
        echo "prepare to inject failure in enode";
        echo "vm to inject failre: $failure_node, $project, $zone"
        #start_vm $traffic_node $delaytime $testname
        inject_node_failure_to_clustervm $failure_node
        retval=$?
        if [ $retval -ne 0 ]; then
            return -1
        fi
    fi
    if [ $diskfailure -eq 1 ]; then
         echo "preppare to inject failure in storage on enode";
         echo "vm to inject failure $failure_node, $project, $zone"
         #start_vm $traffic_node $delaytime $testname
         inject_storage_failure_to_vm $failure_node
                 #gcloud compute instances delete $failure_node --project $project --zone $zone -q
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
   return $number_logfiles
}


test_result() {
    count=0
    no_of_logfile=0
    logfiles_uploaded
    no_of_logfiles=$?
    echo $no_of_logfiles
    if [ $hatest -eq 1 ]; then
        expected_logfile=1
    else
        expect_logfile=$((clients*6))
    fi	
    if [ $no_of_logfiles -ge $expected_logfile ]; then
       io_data_done=1
    fi
    count=0
    while [[ "$io_date_done" == "0"  &&  $count -lt 60 ]]
    do
      sleep 60
      logfiles_uploaded
      no_of_logfiles=$?
      echo $no_of_logfiles
      if [ $no_of_logfiles -ge $expected_logfile ]; then
          io_date_done=1
      fi 
      count=$((count+1))
    done

    if [ "$io_data_done" == "0" ]; then
        echo "io testing might have problem."
        return -1
    fi 

    return 0
}

# ----------------------------------------------------
# Start here
# example: ./elfse2e.sh phdd  300 elfs-daily-e2e-phdd
#          phdd --- persistent hdd
#          300  --- io test run time
#          elfs-daily-e2e-phdd -- testname
# ----------------------------------------------------
disktype=$1
ioruntime=$2
testname=$3
echo "disktype is $disktype"  
echo "io run time is $ioruntime"
echo "testname is $testname"

initialization

echo "cleanup ? $cleanup"
echo "skip provision ? $skipprovision"


if [ $cleanup -eq 1 ]; then
    cleanup_test "d-elfs"
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
