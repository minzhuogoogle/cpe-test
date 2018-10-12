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


parser = argparse.ArgumentParser()
parser.add_argument('-device_type', '--device_type', dest='device_type', type=str, default='nvme')
parser.add_argument('-device_list', '--device_list', dest='device_list', type=str)
parser.add_argument('-actcfgfile', '--cfgfile_for_act', dest='actfile', type=str, default='actcfg')
parser.add_argument('-numberofssd', '--numberofssd', dest='no_ssd', type=int, default=4)
parser.add_argument('-actwriteload', '--actwriteload', dest='actwriteload', type=int, default=12)
parser.add_argument('-actreadload', '--actreadload', dest='actreadload', type=int, default=6)
parser.add_argument('-runtime', '--runtime', dest='runtime', type=int, default=168)
parser.add_argument('-no_queue', '--no_queue', dest='no_queue', type=int, default=8)
parser.add_argument('-no_thread_per_queue', '--no_thread_per_queue', dest='no_thread_per_queue', type=int, default=8)

args = parser.parse_args()

hostname = subprocess.check_output('hostname')
print hostname

kill_all_actprep()
stop_all_act_process()

#generate act run config file
cfgname = '{}_ssd_{}_write_{}_read_{}.txt'.format(args.actfile, args.no_ssd, args.actwriteload, args.actreadload)
outputname = '{}_{}.log'.format(hostname.splitlines()[0], cfgname)
cmd='./act_config_generator.py -numberofssd {} -actwriteload {} -actreadload {} -runtime {}'.format(args.no_ssd, args.actwriteload, args.actreadload, args.runtime)
print cmd
subprocess.call(cmd.split())
print "cfg file done"

cmd = './run_act.sh {} {}'.format(cfgname, outputname)
subprocess.check_output(cmd.split())
