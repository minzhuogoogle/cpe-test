#!/usr/bin/env python

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

NVME='nvme0n'
FACTOR=1000
ssd_pattern = '(nvme0n\d+)\s+\d+:\d.*disk'

def get_device_name(no_of_devices):
    cmd = "lsblk"
    print "cmd:", cmd
    try:
        templist = subprocess.check_output(cmd.split(";")).splitlines()
    except Exception, i:
        print '\nException: ', i
        return  None
    print templist
    nvmelist = []
    for _temp in templist:
       print "new:", _temp
       matchssd = re.compile(ssd_pattern)
       if matchssd.match(_temp):
           nvmelist.append(_temp)
    if not nvmelist:
       print "did not find ssd"
       return None
    if no_of_devices > len(nvmelist) or no_of_devices < 1:
       print "No enough nvme devices."
       return None
    else:
      device_list = ''
      for device in range(no_of_devices):
          device_list += '/dev/' + nvmelist[device].split()[0]
          if device != no_of_devices:
              device_list += ','
    return device_list


def make_file_executable(actfile):
    cmd = "sudo chmod 700  {}".format(actfile)
    print "cmd:", cmd
    try:
        subprocess.check_output(cmd.split()).splitlines()
        return True
    except Exception, i:
        print '\nException: ', i
        return False



def act_cfg_gen(no_of_devices, writeload, readload, num_queues, threads_per_queue, runtime, actfile):
    device_names = ''
    report_interval_sec = 1
    record_bytes = 1536
    large_block_op_kbytes = 128
    microsecond_histograms = 'no'
    scheduler_mode = 'noop'
    use_standard = True

    device_list = ''
    device_names = device_list

    test_duration_sec = runtime * 3600

    write_reqs_per_sec = int(writeload) * no_of_devices * FACTOR
    read_reqs_per_sec =  int(readload) * no_of_devices * FACTOR
    device_names = get_device_name(no_of_devices)
    if not device_names:
        return None
       
    print "device_name = ", device_names
    try:
        act_file_fd = open(actfile, "wb")
        act_file_fd.write('##########\n')
        act_file_fd.write('act config file for testing ' + str(no_of_devices) + ' device(s). \n')
        act_file_fd.write(' writing load: ' +  str(writeload) + '\n')
        act_file_fd.write(' read load: ' +  str(readload) + '\n')

        act_file_fd.write('##########\n\n')
        act_file_fd.write('# comma-separated list:\n')
        act_file_fd.write('device-names: %s\n\n' % str(device_names))
        act_file_fd.write('# mandatory non-zero:\n')
        act_file_fd.write('num-queues: %s\n' % str(num_queues))
        act_file_fd.write('threads-per-queue: %s\n' % str(threads_per_queue))
        act_file_fd.write('test-duration-sec: %s\n' % str(test_duration_sec))
        act_file_fd.write('report-interval-sec: %s\n' % str(report_interval_sec))
        act_file_fd.write('large-block-op-kbytes: %s\n\n' % str(large_block_op_kbytes))
        act_file_fd.write('record-bytes: %s\n' % str(record_bytes))
        act_file_fd.write('read-reqs-per-sec: %s\n\n' % str(read_reqs_per_sec))
        act_file_fd.write('# usually non-zero:\n')
        act_file_fd.write('write-reqs-per-sec: %s\n' % str(write_reqs_per_sec))
        act_file_fd.write('# yes|no - default is no:\n')
        act_file_fd.write('microsecond-histograms: %s\n\n' % str(microsecond_histograms))
        act_file_fd.write('# noop|cfq - default is noop:\n')
        act_file_fd.write('scheduler-mode: %s\n' % str(scheduler_mode))
        act_file_fd.close()
        print 'Config file ' + str(actfile) + ' successfully created.'
        return True
    except Exception, i:
        print '\nException: ', i
        return False


parser = argparse.ArgumentParser()
parser.add_argument('-actcfgfile', '--cfgfile_for_act', dest='actfile', type=str, default='actcfg')
parser.add_argument('-numberofssd', '--numberofssd', dest='no_ssd', type=int, default=4)
parser.add_argument('-actwriteload', '--actwriteload', dest='actwriteload', type=int, default=12)
parser.add_argument('-actreadload', '--actreadload', dest='actreadload', type=int, default=6)
parser.add_argument('-runtime', '--runtime', dest='runtime', type=int, default=168)
parser.add_argument('-no_queue', '--no_queue', dest='no_queue', type=int, default=8)
parser.add_argument('-no_thread_per_queue', '--no_thread_per_queue', dest='no_thread_per_queue', type=int, default=8)


args = parser.parse_args()

actcfg_file = '{}_ssd_{}_write_{}_read_{}.txt'.format(args.actfile, args.no_ssd, args.actwriteload, args.actreadload)
print actcfg_file

if not act_cfg_gen(args.no_ssd,  args.actwriteload, args.actreadload,  args.no_queue, args.no_thread_per_queue, args.runtime, actcfg_file):
    print "Fails to create ACT configuration file."

