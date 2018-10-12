#!/bin/bash

# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#


for pattern in read randrw
do for iodepth in  128
   do for blocksize in  16k
      do for filesize in 512M
         do for numjobs in  16
            do NOW=$(date +"%m.%d.%Y")
            HOSTNAME=$(hostname)
            fio --name=$pattern.data --iodepth=$iodepth --rw=$pattern --bs=$blocksize  \
                        --direct=1 --size=$filesize --numjobs=$numjobs  --fsync=1 --do_verify=1 --verify_fatal=1 \
                        --rwmixread=70 --rwmixwrite=30 --group_reporting  \
                        --output=qfio.$pattern.$iodepth.$blocksize.$filesize.$numjobs.$NOW.$HOSTNAME.log
            rm -rf $pattern.data.*
            done
         done
       done
   done
done
