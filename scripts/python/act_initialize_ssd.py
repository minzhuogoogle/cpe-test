#!/usr/bin/python
####
# Act config creator to help configuration for tests
####

import cmd
import os
import sys
import argparse
import subprocess
from subprocess import call
import re
import time


#act_cfg_gen(args.no_ssd, args.actwriteload, args.actreadload,  no_queue, no_thread_per_queue, args.runtime, args.actfile)
NVME='nvme0n'
FACTOR=1000

def get_device_name(no_of_devices=0):
    cmd = "lsblk"
    device_list = []
    print "cmd:", cmd
    try:
        templist = subprocess.check_output(cmd.split(";")).splitlines()
    except Exception, i:
        print '\nException: ', i
        return  NULL
    nvmelist = []
    print templist
    for _temp in templist:
        print _temp
        if NVME in _temp:
           nvmelist.append(_temp)
    print nvmelist
    if not nvmelist:
       return NULL
    if no_of_devices == 0 :
       no_of_devices = len(nvmelist)
    if no_of_devices > len(nvmelist) or no_of_devices < 1:
       print "No enough nvme devices."
       return NULL
    else:
      for device in range(no_of_devices):
          device_list.append( '/dev/' + nvmelist[device].split()[0])
    print device_list
    return device_list

def kill_all_actprep():
    cmd = "sudo killall actprep"
    print "cmd:", cmd
    try:
        subprocess.check_output(cmd.split()).splitlines()
        return True
    except Exception, i:
        print '\nException: ', i
        return False

def stop_all_act_process():
    cmd = "sudo killall act"
    print "cmd:", cmd
    try:
        subprocess.check_output(cmd.split()).splitlines()
        return True
    except Exception, i:
        print '\nException: ', i
        return False


def act_initialize_ssd(device_list):
#    cmd = "cd act"
#    print "cmd:", cmd
#    try:
#        subprocess.call(cmd.split())
#        return True
#    except Exception, i:
#        print '\nException: ', i
#        return False
    print "ssd device list:", device_list
    for _ssd in device_list:
        cmd = "sudo ./actprep {} ".format(_ssd)
        print "cmd:", cmd
        try: 
            subprocess.Popen(cmd.split())
            return True
        except Exception, i:
            print '\nException: ', i
            return False



parser = argparse.ArgumentParser()
parser.add_argument('-device_type', '--device_type', dest='device_type', type=str, default='nvme')
parser.add_argument('-device_list', '--device_list', dest='device_list', type=str)

args = parser.parse_args()

if args.device_type == "nvme":
    ssd_device_list = get_device_name(0)
else:
    ssd_device_list = args.device_list.split()

kill_all_actprep()
stop_all_act_process()

if not act_initialize_ssd(ssd_device_list):
    print "Fails to initialize device."
