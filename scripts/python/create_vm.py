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


SSD_CFG_SUFFIX = " --local-ssd interface=nvme "
VM_CREATE_SUFFIX = "gcloud compute instances create "
VM_APPENDIX = "cpe-test-vm"

###### global variables ##################
#zone_list= ['us-east1-b','us-east4-b','us-central1-b','us-west1-b','us-west2-b']
#machine_type_list = ['n1-highcpu-4', 'n1-highmem-4']
localssd_number_list = [8]
zone_list=[]
machine_type_list = []
vm_list = []
################ get the list of zones #########
def get_full_list_zones():
    cmd = "gcloud compute zones list"
    print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 1:
        return [_temp.split()[0] for _temp in templist]
    else:
        return NULL

def get_full_list_machine_type():
    cmd = "gcloud compute machine-types list "
    print "cmd:", cmd
    templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 1:
        return [_temp.split()[0] for _temp in templist]
    else:
        return NULL


def get_full_list_vm():
  #cloud compute instances list | awk  '{print $5}'
    full_list_vm = []
    cmd = "gcloud compute instances list "
    print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 1:
       return [[_temp.split()[0], _temp.split()[1], _temp.split()[2], _temp.split()[3] , _temp.split()[4]] for _temp in templist]
    else:
        return NULL




def create_vm(machine_type, ssdnumber, zone, sequence):
    ssd_cfg_string = SSD_CFG_SUFFIX*ssdnumber
    vm_name = "{}-cpu-{}-ssd-{}-zone-{}-no{}".format(VM_APPENDIX, machine_type, ssdnumber, zone, sequence)
    cmd2createvm = "{} {} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(VM_CREATE_SUFFIX, vm_name, machine_type, zone, ssdstring)
    print cmd2createvm
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


def sendcmd2vm(sshh, cmd):
    sshh.flush()
    sshh.sendline(cmd)
    sshh.expect("mzhuo>")


###### test starts here

####### populate data for zone ####
all_zones = get_full_list_zones()
print all_zones; 

all_machine_types = get_full_list_machine_type()
print all_machine_types;

all_vms =  get_full_list_vm()
print all_vms
######## populate data for machine type ####

time.sleep(60)
######## create list of VMs #########
real_vm_name = []
real_vm_zone = []
real_vm_name, real_vm_zone = create_vms()
