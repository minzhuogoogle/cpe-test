#!/bin/bash

# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Run one cli to upgrade image on multiple CfMs defined in cfmfile.
# If # is added in front of mgmt_ip in cfmfile, this cfm will be skipped.

if [ $# -ne 2 ]; then
echo "Usage: fiobatch.sh fiobatchtest.log fiobatch.cfg"
echo "cfgfile defines the list of CfM with mgmt ipv4, and platform"
echo "Example:  ./upgradecfm.sh  hosts.bst.txt  R64-10176.0.0"
echo "Output of cfgfile:
100.123.170.8 guado
100.123.174.2 guado
#100.107.146.4 guado # this cfm will be skipped
100.107.146.22 guado
100.107.146.16 guado
100.107.146.3 guado
100.107.146.21 guado
100.107.146.27 guado
"
exit $ERR
fi



cd /usr/local/google/home/mzhuo/partner/testlog 
for pattern in read write rw 
do for iodepth in  16  
   do for blocksize in  8k 
      do for filesize in 512k  
         do for numjobs in 6 
            do NOW=$(date +"%m.%d.%Y")
            HOSTNAME=$(hostname)
            rbwvalue=0
            riopsvalue=0
            rlatvalue=0
            wbwvalue=0
            wiopsvalue=0
            wlatvalue=0

            fio --name=$pattern.data --iodepth=$iodepth --rw=$pattern --bs=$blocksize  \
                        --direct=1 --buffered=0 --size=$filesize --numjobs=$numjobs  --fsync=1 \
                        --fsync_on_close=1 --group_reporting \
                        --output=fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log
            echo "=================================="
            infoline=$(printf "pattern=%s iodepth=%s blocksize=%s filesize=%s numjobs=%s time=%s Hostname=%s" "$pattern $iodepth $blocksize $filsize $numjobs $NOW $HOSTNAME")
            echo $infoline
            templine=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log)
            echo $templine
            echo "================="
            readorwrite=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log |  awk -v N=1 '{print $N}')
            echo $readorwrite
            if [ "$readorwrite" = "read" ]; then 
               echo "this is only read"
               rbwvalue=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | awk -v N=4 '{print $N}')
               riopsvalue=$(grep  "runt" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log |  awk -v N=5 '{print $N}')
               rlatvalue=$(grep "clat" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep -v percentiles | awk -v N=5 '{print $N}')
            elif [ "$readorwrite" = "write:" ]; then 
               echo "this is only write"
               wbwvalue=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | awk -v N=3 '{print $N}')
               wiopsvalue=$(grep  "runt" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log |  awk -v N=4 '{print $N}')
               wlatvalue=$(grep "clat" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep -v percentiles | awk -v N=5 '{print $N}')
            else   
               echo "this is write/read"
               rbwvalue=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep read | awk -v N=4 '{print $N}')
               wbwvalue=$(grep 'runt' fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep write | awk -v N=3 '{print $N}')
               riopsvalue=$(grep  "runt" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep read |  awk -v N=5 '{print $N}')
               wiopsvalue=$(grep  "runt" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log | grep write | awk -v N=4 '{print $N}')
               rlatvalue=$(grep "read : io" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log -A 4 | grep clat | grep -v percentiles | awk -v N=5 '{print $N}')
               wlatvalue=$(grep "write: io" fio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log -A 4 | grep clat | grep -v percentiles | awk -v N=5 '{print $N}')
            fi
            echo "bw:" $rbwvalue, $wbwvalue
            echo "iops:" $riopsvalue, $wiopsvalue
            echo "latency:" $rlatvalue, $wlatvalue
            rbwvalue=${rbwvalue:3}
            riopsvalue=${riopsvalue:5}
            rlatvalue=${rlatvalue:4}
            wbwvalue=${wbwvalue:3}
            wiopsvalue=${wiopsvalue:5}
            wlatvalue=${wlatvalue:4}
            echo pattern $iodepth $blocksize $filsize $numjobs $NOW $HOSTNAME >> fio.log
            echo $rbwvalue $riopsvalue $rlatvalue $wbwvalue $wiopsvalue $wlatvalue >> fio.log
            
            rm -rf *.data
            done
         done
       done   
   done
done
