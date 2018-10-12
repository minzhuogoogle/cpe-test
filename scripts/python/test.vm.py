#!/usr/bin/env python
import sys
import pexpect
import time
import os
import datetime
import time
import commands
import re
import argparse
import random
import subprocess
from subprocess import call

from random import randint

###### global variables ##################
vm_name=[]
vm_zone=[]

zone_list= ['us-east1-b','us-east4-b','us-central1-b','us-west1-b','us-west2-b']
machine_type_list = ['n1-highcpu-4', 'n1-highmem-4']
localssd_number_list = [8]
act_load = [1, 2, 3, 4, 6, 8]
p = {}
################ get the list of zones #########
def get_list_zones():
# gcloud compute zone list
    cmd = "gcloud;compute;zones;list"
    print "cmd:", cmd
    include_zone=['us-']
    templine = subprocess.check_output(cmd.split(";")).splitlines()[1:]
    for  _line in templine:
         print _line
         for _zone in include_zone:
             if _zone in _line:
                zone_list.append(_line.split()[0])
    print zone_list

def get_list_machine_type():
    return
# gcloud compute zone list
    cmd = "gcloud;compute;machine-types;list"
    print "cmd:", cmd
    exclude_type = ['micro', 'standard','small', 'mega', 'ultra'  ]
    include_type = ['n1-highcpu-4']
    templine = subprocess.check_output(cmd.split(";")).splitlines()[1:]
    for  _line in templine:
       print _line
       flag = True
       fflag = False
       for _type in exclude_type:
           if _type in _line:
               flag = False
               continue
       if flag:      
          for _type in include_type:  
            for _type in include_type: 
                if _type in _line:
                    fflag = True
                    continue
       if fflag:           
          machine_type_list.append(_line.split()[0])
    print machine_type_list

def create_vm(machine_type, ssdnumber, zone, sequence):
 #   return 
    ssdstring0 = "--local-ssd interface=nvme "
    ssdstring = ''
    for i in range(0, ssdnumber):
        ssdstring += ssdstring0
    cmd2createvm = "gcloud compute instances create testvm-{}-{}-{}-{} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(machine_type, ssdnumber, zone, sequence, machine_type, zone, ssdstring )
    print  cmd2createvm 
    vm_name.append('testvm-{}-{}-{}-{}'.format(machine_type, ssdnumber, zone, sequence))
    vm_zone.append(zone)
    try:
       output = subprocess.check_call(cmd2createvm.split())
       if "RUNNING" in output:
           print "vm created"
           return 1
       else:
           print "vm creation fails"
           return 0  
    except Exception as e:
       print "error in creating vm"
       return 0

def create_vms():
 #   return
    running_vm = []
    running_vm_in_zone = []
    for _ssd in localssd_number_list:
      for _machine_type in machine_type_list:
        for  _zone in zone_list:
             for j in [1]:
          #       print "going to create cm", _ssd, _machine_type, _zone, j
                 if not create_vm(_machine_type, _ssd, _zone, j) == 0:
                    running_vm.append('testvm-{}-{}-{}-{}'.format(_machine_type, _ssd, _zone, j))
                    running_vm_in_zone.append(_zone) 
    
    return running_vm, running_vm_in_zone
########## common libraries #############
def mylist_mean(mylist):
    mysum = 0
#    print mylist
    for _num in mylist:
	mysum = mysum + float(_num)
    average = float(mysum)/float(len(mylist))
    return average

def mylist_max(mylist):
    mymax = mylist[0] 
    for _num in mylist:
        if float(_num) > mymax:
		mymax = float(_num)
    return mymax

def mylist_min(mylist):
    mymax = mylist[0]
    for _num in mylist:
        if float(_num) < mymax:
                mymax = float(_num)
    return mymax
 
def remove_duplicates(x):
    a = []
    for i in x:
        if i not in a:
            a.append(i)
    return a

def sendcmd2vm(sshh, cmd):
    sshh.flush()
    sshh.sendline(cmd)
    sshh.expect("mzhuo>")


def get_args():
    '''This function parses and return arguments passed in'''
    # Assign description to the help doc
    parser = argparse.ArgumentParser(
        description='Script retrieves schedules from a given server')
    # Add arguments
    parser.add_argument(
        '-t', '--ttype', type=str, help='Testing Type', required=True, default="1,2,3,4,5")
    parser.add_argument(
        '-ep', '--expected_converge_time', type=int, help='Expected converge time for P2MP tunnel', required=False, default=60)
    parser.add_argument(
        '-et', '--expected_traffic_time', type=int, help='Expected converge time for Traffic', required=False, default=240)
    parser.add_argument(
        '-p', '--pause', type=int, help='pause between loops', required=False, default=120)
    parser.add_argument(
        '-l', '--loop', type=int, help='Testing loop', required=False, default=1000)
    parser.add_argument(
        '-m', '--cmplsp2mp', type=int, help='on/off for mpls p2mp state check', required=False, default=1)
    parser.add_argument(
        '-f', '--cmctraffic', type=int, help='multicast traffic check', required=False, default=1)
  # Array for all arguments passed to script
    args = parser.parse_args()
    # Assign args to variables
    loop = args.loop
    ttype = args.ttype
    ectp2mp = args.expected_converge_time
    ectt = args.expected_traffic_time
    pause = args.pause
    print args.ttype
    ttype = args.ttype.split(",")
    print ttype
    cmplsp2mp  = args.cmplsp2mp
    cmctraffic = args.cmctraffic 
    # Return all variable values
    return loop, ttype,ectp2mp, ectt, pause, cmplsp2mp, cmctraffic


def pollall():
    print "Prepare to poll all state\n"
    for _sw in sw_list:
        collectAllLog(p[_sw])


#options={
#           0 : createvm,
#           1 : deletevm,
#           2 : act,
#           3 : fio,
#           4 : mountfs,
#}

###### test starts here


####### populate data for zone ####
#get_list_zones()
######## populate data for machine type ####
#get_list_machine_type()

######## create list of VMs #########
real_vm_name = []
real_vm_zone = []
real_vm_name, real_vm_zone = create_vms()
######## Prepare VMs for testing #####

####### Start testing #########
vminstance='testvm-n1-highcpu-64-8-us-central1-b-1  us-central1-b  n1-highcpu-64               10.128.0.6   35.188.80.199    RUNNING  \
testvm-n1-highmem-64-8-us-central1-b-1  us-central1-b  n1-highmem-64               10.128.0.7   35.202.227.242   RUNNING \
testvm-n1-highcpu-64-8-us-east1-b-1     us-east1-b     n1-highcpu-64               10.142.0.5   35.231.246.200   RUNNING \
testvm-n1-highcpu-64-8-us-east4-b-1     us-east4-b     n1-highcpu-64               10.150.0.7   35.199.62.195    RUNNING\
testvm-n1-highmem-64-8-us-west1-b-1     us-west1-b     n1-highmem-64               10.138.0.8   104.199.112.101  RUNNING \
testvm-n1-highcpu-64-8-us-west2-b-1     us-west2-b     n1-highcpu-64               10.168.0.6   35.236.102.104   RUNNING'
cmd = "gcloud;compute;instances;list"
print "cmd:", cmd
vmlines = subprocess.check_output(cmd.split(";")).splitlines()
#vmlines = vminstance.splitlines()
for _vmline in vmlines:
    print _vmline
#    z=re.match("(^testvm-n1.*-1)\s*(us.*-b)\s*.*", _vmline)
#    if z:
#      vmname =z.group(1)
#      vmzone=z.group(2)
    if "testvm" in  _vmline.split()[0] and ( "highcpu-4" in _vmline.split()[0] or "highmeme-4" in _vmline.split()[0]):   
       real_vm_name.append(_vmline.split()[0])
       real_vm_zone.append(_vmline.split()[1])

print real_vm_name
print real_vm_zone
time.sleep(10)

#######initialize test #########
#1. get ssh to all vm
vm_index = 0
verbose=1
print real_vm_name
print real_vm_zone
for _vm in real_vm_name:
    vmprompt = 'mzhuo@{}.*'.format(_vm)
    sshcli = 'gcloud compute ssh %s --zone=%s' % (_vm, real_vm_zone[vm_index])
    print "now let's ssh to new switch %s", _vm
    try:
        p[_vm] = pexpect.spawn('gcloud compute ssh %s --zone=%s' % (_vm, real_vm_zone[vm_index]))
        p[_vm].expect(vmprompt)
        if verbose:
            p[_vm].logfile = sys.stdout
            p[_vm].timeout = 1000
            p[_vm].maxread=1000
#        p[_vm].sendline('git clone https://github.com/aerospike/act.git;sudo apt-get install make gcc libc6-dev libssl-dev zlib1g-dev python -y;cd act; make; make -f Makesalt' )
 #       p[_vm].expect('mzhuo')
        p[_vm].sendline("sudo killall actprep")
        p[_vm].expect(vmprompt)

        p[_vm].sendline("lsblk | awk -v N=1 '{print $N}'")
        p[_vm].expect(vmprompt)
        output = p[_vm].before
        print "\nthis is output from cli:\n"
        print output
        print "-end of output\n"
        nvmeline = output.splitlines()
        nvmelist = []
        for _nvme in nvmeline:
            if "nvme0n" in _nvme:
              nvmelist.append(_nvme)
        print "\n\n"
        print ','.join(nvmelist)
        nvmessd = ""
        print "\n\n"
        nvmessd = "device-names: "
        print "end end"
        for _nvme in nvmelist:
             print _nvme
             p[_vm].flush()
             cmdline='cd act; sudo ./actprep /dev/{}  &'.format(_nvme)
             print '>>>>cmdline : {}'.format(cmdline)
             p[_vm].sendline(cmdline)
             p[_vm].expect(vmprompt)
             nvmessd += '/dev/{}, '.format(_nvme) 
        print nvmessd    
        print "*nvme cmd :{}*".format(nvmessd)
        time.sleep(5)
#        p[_vm].sendline('gsutil cp gs://testing-log/aerospike/actconfig_8x_6d.txt ~/act/actconfig_8x_6d.txt')
#        p[_vm].expect(vmprompt)
#        p[_vm].sendline('echo \'{}\'  >>  ~/act/actconfig_8x_6d.txt'.format(nvmessd))
#        p[_vm].expect(vmprompt)
        p[_vm].sendline('gsutil cp  gs://testing-log/aerospike/act_config_generator.py act_config_generator.py') #gsutil cp gs://testing-log/aerospike/actconfig_8x_6d.txt ~/act/actconfig_8x_6d.txt')
        cmd = "sudo chmod 777 act_config_generator.py"
        p[_vm].sendline("cmd")
        p[_vm].expect(vmprompt)


 

    except pexpect.TIMEOUT:
         print "fails to ssh to vm", _vm, real_vm_zone[vm_index]     
    vm_index += 1


for _vm in real_vm_name:
    break
    actprep = True
    while actprep:
        print "polling whether actprep is done"
        p[_vm].sendline('ps -af|grep actprep')
        p[_vm].expect(vmprompt)
        output = p[_vm].before
        print output
        if not "nvme0n" in output:
           actprep = False
    p[_vm].sendline('cd ~/act; sudo ./act  actconfig_8x_6d.txt  > {}.8x_1d.txt &'.format(_vm))
    p[_vm].expect(vmprompt)


