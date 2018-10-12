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
verbose = True
#ssd_pattern = '(nvme0n\d+)\s+\d+:\d\s*\s+\d+\s+(\d+.G)\s+\d+\s+disk'
ssd_pattern = '(nvme0n\d+)\s+\d+:\d.*disk'

ACT_INSTALL_CLI = 'git clone https://github.com/aerospike/act.git; sudo apt-get install make gcc libc6-dev libssl-dev zlib1g-dev python -y; cd act;/ make; make -f Makesalt'
ACT_CFG_CLI = 'cd ; cd act; gsutil cp gs://testing-log/aerospike/act.package.tar act.package.tar; tar xvf act.package.tar; sudo chmod 777 *.*'



###### global variables ##################
#zone_list= ['us-east1-b','us-east4-b','us-central1-b','us-west1-b','us-west2-b']
#machine_type_list = ['n1-highcpu-4', 'n1-highmem-4']
localssd_number_list = [8]
zone_list=[]
machine_type_list = []
vm_list = []

vm_access_handler = {}


def check_running_act_instance(vm_name, vm_zone):
    cmd =  'gcloud compute instances reset {} --zone={}'.format(vm_name, vm_zone)
    print "cmd:", cmd
    templist = subprocess.check_output(cmd.split('')).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def reset_vm_instance(vm_name, vm_zone):
    cmd =  'gcloud compute instances reset {} --zone={} '.format(vm_name, vm_zone)
    print "cmd:", cmd
    templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def ssh_to_vm(vm_name, vm_zone):
    vmprompt = '.*@{}.*'.format(vm_name)
    key='{};{}'.format(vm_name, vm_zone)
    try:
        vm_access_handler[key] = pexpect.spawn('gcloud compute ssh %s --zone=%s' % (vm_name,vm_zone))
        vm_access_handler[key].expect(vmprompt)
        if verbose:
            vm_access_handler[key].logfile = sys.stdout
            vm_access_handler[key].timeout = 1000
            vm_access_handler[key].maxread=1000
    except pexpect.TIMEOUT:
        raise OurException("Couldn't ssh to the vm {} in zone {}".format(vm_name, vm_zone))
    print  vm_access_handler.keys() 

################ get the list of zones #########
def send_cmd_and_get_output(vm_name, vm_zone, cmd):
    key='{};{}'.format(vm_name, vm_zone)
    vmprompt = '.*@{}.*'.format(vm_name)
    if not key in vm_access_handler.keys():
        print "ssh to vm"
        ssh_to_vm(vm_name, vm_zone)
    else:
        print "ssh access existing"
    vm_access_handler[key].flush()
    vm_access_handler[key].sendline(cmd)
    vm_access_handler[key].expect(vmprompt)
    temp = vm_access_handler[key].before
    return vm_access_handler[key].after


def get_full_list_zones():
    cmd = "gcloud compute zones list"
    print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None

def get_full_list_machine_type():
    cmd = "gcloud compute machine-types list "
    print "cmd:", cmd
    templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def get_full_list_vm():
  #cloud compute instances list | awk  '{print $5}'
    full_list_vm = []
    cmd = "gcloud compute instances list "
    print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
       return [[_temp.split()[0], _temp.split()[1], _temp.split()[2], _temp.split()[3] , _temp.split()[4]] for _temp in templist]
    else:
        return None


def get_vm_ssd_info(vm_name, vm_zone):
    ssd_list = []
    cmd = "lsblk"
    output = send_cmd_and_get_output(vm_name, vm_zone, cmd).splitlines()
    print '*******',output,"***", len(output)
#    time.sleep(5)
    if len(output) > 0:
        matchssd = re.compile(ssd_pattern)
        for _line in output:
            print "new line : ", _line
            if matchssd.match(_line):
                 ssd_list.append(matchssd.match(_line).group(1))
        print "ssd list : " ,ssd_list         
        return ssd_list
        
    else:
        return  None

def prepare_act_cfg_on_vm(vm_name, vm_zone, write_load, read_load, runtime):
    ssd_list = get_vm_ssd_info(vm_name, vm_zone)
    act_cfg_generate_cli = 'cd act; python act_config_generator.py --numberofssd {} --actwriteload {} --actreadload {} --runtime  {}'.format(len(ssd_list), write_load, read_load, runtime)
    send_cmd_and_get_output(vm_name, vm_zone, act_cfg_generate_cli)
    return ssd_list

def act_run(vm_name, vm_zone):
#    send_cmd_and_get_output(vm_name, vm_zone, ACT_INSTALL_CLI)
#    time.sleep(10) 
    send_cmd_and_get_output(vm_name, vm_zone, ACT_CFG_CLI)
#    time.sleep(10)
    ssd_list = get_vm_ssd_info(vm_name, vm_zone)

    print ssd_list
 #   time.sleep(10)
    if len(ssd_list) == 0:
       return None
    if len(ssd_list) <= 4:
       no_ssd = len(ssd_list)
       write_load = 6
       read_load = 6
    elif len(ssd_list) <= 6:
       no_ssd = len(ssd_list)
       write_load = 4
       read_load = 4
    else:
       no_ssd = 6
       write_load = 3
       read_load = 3



    prepare_act_cfg_on_vm(vm_name, vm_zone, write_load, read_load, 196)
    act_cfg_file = 'actcfg_ssd_{}_write_{}_read_{}.txt'.format(len(ssd_list), write_load, read_load)
    outputfile = "{}_{}_{}".format(vm_name,vm_zone, act_cfg_file)
    print "generate cfg file"
    print "run act"
    cli = "cd act"
    send_cmd_and_get_output(vm_name, vm_zone, cli)
    cli = "sudo ./act {} > {} & ".format(act_cfg_file, outputfile)
    output=send_cmd_and_get_output(vm_name, vm_zone, cli)

#    ; cd act; ./act {} > {}".format(act_cfg_file, outputfile)
#    output=send_cmd_and_get_output(vm_name, vm_zone, change_path)
#    send_cmd_and_get_output(vm_name, vm_zone, 'pwd')
#    act_run_cli = './act {} > {}'.format(act_cfg_file, outputfile)
#    act_run_cli = 'sudo ./home/mzhuo/act {} > ~/act/{} '.format(act_cfg_file, outputfile)
#    print act_run_cli
#    output=send_cmd_and_get_output(vm_name, vm_zone, act_run_cli)
    print "output for act running****************", output
    print "****"

#    time.sleep(10)


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
#all_zones = get_full_list_zones()
#print all_zones;

#all_machine_types = get_full_list_machine_type()
#print all_machine_types;

all_vms =  get_full_list_vm()
print all_vms

#for eachvm in all_vms:
#    print eachvm
#    reset_vm_instance(eachvm[0], eachvm[1])
#    break
    
time.sleep(60)  

for eachvm in all_vms:
    print eachvm
#    ssd_list = get_vm_ssd_info(eachvm[0], eachvm[1])
#    print ssd_list
    act_run(eachvm[0], eachvm[1])
#    break

######## populate data for machine type ####

######## create list of VMs #########
real_vm_name = []
real_vm_zone = []
real_vm_name, real_vm_zone = create_vms()
