#!/bin/bash

# Copyright (c) 2011 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Run one cli to upgrade image on multiple CfMs defined in cfmfile.
# If # is added in front of mgmt_ip in cfmfile, this cfm will be skipped.

if [ $# -ne 1 ]; then
echo "Usage: upgradecfm.sh <cfgfile>  <version>"
fi

declare -a cmdlists
#set cfg file and image version
cfgfile=$1
ver=$2
echo $cfgfile, $ver

#populate list of CfMs along with board type
declare -a vmname
while read -r vmname; do
      echo $vmname
      vmname+=($vmname)
done < $cfgfile

n=${#vmname[@]}

#start upgrade image to CFMs one by one
for ((i=0;i<8;i++)); do
  vmname=${vmname[$i]}
  echo $vmname is $vmname
  cmd="gcloud compute ssh $vmname"
  echo $cmd
  eval $cmd
done

