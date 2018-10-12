#!/bin/bash
# found in the LICENSE file.
#

cfgfile=$1
outputfile=$2
cmd='sudo ./act '$cfgfile
$cmd > $outputfile &
