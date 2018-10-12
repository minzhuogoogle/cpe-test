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
import numpy as np
from math import sqrt

SSD_CFG_SUFFIX = " --local-ssd interface=nvme "
VM_CREATE_SUFFIX = "gcloud compute instances create "
verbose = True
#ssd_pattern = '(nvme0n\d+)\s+\d+:\d\s*\s+\d+\s+(\d+.G)\s+\d+\s+disk'
ssd_pattern = '(nvme0n\d+)\s+\d+:\d.*disk'

FIO_INSTALL_CLI='sudo apt-get install git; cd /opt; sudo git clone https://github.com/axboe/fio; cd fio; sudo apt-get install  gcc -y ;sudo ./configure; sudo apt install make;  sudo make; sudo make install; sudo apt install nfs-common -y'
FIO_INSTALL_CLI='sudo apt-get update;  sudo apt install fio -y; sudo apt install nfs-common -y'

NFS_CLIENT_MOUNT='sudo mkdir -p /mnt/ssd; sudo mount -o nolock 10.99.0.2:/DATA/root /mnt/ssd'

ACT_INSTALL_CLI = 'git clone https://github.com/aerospike/act.git; sudo apt-get install make gcc libc6-dev libssl-dev zlib1g-dev python -y; cd act; make; make -f Makesalt'
ACT_CFG_CLI = 'cd; cd act; gsutil cp gs://testing-log/aerospike/act.package.tar act.package.tar; tar xvf act.package.tar; sudo chmod 777 *.*'
GIT_CLONE_CLI='git clone https://github.com/minzhuogoogle/storage-performance.git; cp storage-performance/*.py .; sudo chmod +x *.py'
fio_cli = "sudo fio --name=fio.data --iodepth=64 --rw=randrw --rwmixwrite=70 --rwmixread=30 --refill_buffers --norandommap --randrepeat=0 --ioengine=libaio --bs=16k --direct=1 --size=1024M --numjobs=8 --group_reporting  --time_based --runtime=86400 &"
fio_cli = "sudo fio --filename=performance.fio --direct=1 --rw=write --refill_buffers --norandommap --randrepeat=0 --ioengine=libaio --bs=128k --size=1G --iodepth=8 --numjobs=8 --runtime=86400 --group_reporting --name=performance --time_based --output=fio.write.8k.1g.8.8.log  &"
fio_cli = 'sudo killall fio'
ACT_RUN_OUPUT_LENGTH = 200
ACT_RUN_HOUR = 196
PAUSE = 10
RETRY = 3
RAMP_TIME = 13
INCREASE_CHECK = 6


#mzhuo@nfs-client-1:/mnt/ssd/tmp$ ps -eaf|grep fio
#root     16226     1  0 06:17 ?        00:00:00 sudo fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16227 16226  1 06:17 ?        00:08:30 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16233 16227  1 06:17 ?        00:12:31 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16234 16227  1 06:17 ?        00:12:17 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16235 16227  1 06:17 ?        00:12:32 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16236 16227  1 06:17 ?        00:12:14 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16237 16227  2 06:17 ?        00:15:04 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16238 16227  1 06:17 ?        00:12:03 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16239 16227  1 06:17 ?        00:12:20 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16240 16227  1 06:17 ?        00:12:05 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16241 16227  1 06:17 ?        00:12:20 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16242 16227  1 06:17 ?        00:12:01 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16243 16227  1 06:17 ?        00:12:14 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400

#root     16244 16227  1 06:17 ?        00:11:56 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16245 16227  1 06:17 ?        00:12:01 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16246 16227  2 06:17 ?        00:15:06 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16247 16227  1 06:17 ?        00:12:37 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16248 16227  1 06:17 ?        00:12:01 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16249 16227  1 06:17 ?        00:12:34 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16250 16227  2 06:17 ?        00:13:43 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16251 16227  1 06:17 ?        00:12:18 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16252 16227  1 06:17 ?        00:12:15 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16253 16227  1 06:17 ?        00:12:37 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16254 16227  2 06:17 ?        00:15:03 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16255 16227  1 06:17 ?        00:12:34 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16256 16227  2 06:17 ?        00:13:42 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16257 16227  1 06:17 ?        00:12:39 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16258 16227  2 06:17 ?        00:15:03 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16259 16227  2 06:17 ?        00:13:45 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16260 16227  1 06:17 ?        00:11:57 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16261 16227  1 06:17 ?        00:12:00 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16262 16227  1 06:17 ?        00:12:15 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16263 16227  1 06:17 ?        00:12:15 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400
#root     16264 16227  1 06:17 ?        00:12:02 fio --name=read.data.small --iodepth=128 --rw=randread --bs=1500 --direct=1 --size=512M --numjobs=32 --group_reporting --rate_iops=22000 --time_based --runtime=86400

#mzhuo    16277     1  2 06:18 ?        00:16:07 fio --name=write.data --iodepth=128 --rw=randwrite --bs=128k --direct=1 --buffered=0 --size=375M --numjobs=1 --group_reporting --rate_iops=150 --time_based --runtime=86400
#mzhuo    16284     1  4 06:18 ?        00:28:32 fio --name=read.data --iodepth=128 --rw=randread --bs=128k --direct=1 --buffered=0 --size=375M --numjobs=1 --group_reporting --rate_iops=150 --time_based --runtime=86400


###### global variables ##################

vm_access_handler = {}

def strictly_increasing(L):
#    print "check whether it is increased\n"
#    print L
#    time.sleep(1)
    return all(x<y for x, y in zip(L, L[1:]))

def strictly_decreasing(L):
    return all(x>y for x, y in zip(L, L[1:]))

def non_increasing(L):
    return all(x>=y for x, y in zip(L, L[1:]))

def non_decreasing(L):
    return all(x<=y for x, y in zip(L, L[1:]))

def data_variation(data):
    return pvariance(data)

def monotonic(x):
    dx = np.diff(x)
    return np.all(dx <= 0) or np.all(dx >= 0)

def monotonicincrease(x):
    dx = np.diff(x)
    return  np.all(dx >= 0)

def monotonicdecrease(x):
    dx = np.diff(x)
    return  np.all(dx <= 0)



def mean(L):
    return sum(L) / len(L)


def data_process(L):
    average =round(mean([float(_each[8]) for _each in L]), 2)
    deviation = round(np.std([float(_each[8]) for _each in L]), 2)
    maximum = round(max([float(_each[8]) for _each in L]), 2)
    return average, deviation, maximum


def reset_vm_instance(vm_name, vm_zone):
    cmd =  'gcloud compute instances reset {} --zone={} '.format(vm_name, vm_zone)
    try:
        templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    except Exception as e:
        print "Fail to reset vm {} in {}".format(vm_name, vm_zone)
        return False
    if 'Updated' in templist:
        return True
    else:
        return False


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


def send_cmd_and_get_output(vm_name, vm_zone, cmd):
    key='{};{}'.format(vm_name, vm_zone)
    vmprompt = '.*@{}.*'.format(vm_name)
    if not key in vm_access_handler.keys():
        ssh_to_vm(vm_name, vm_zone)
    try:
       vm_access_handler[key].flush()
       vm_access_handler[key].sendline(cmd)
       vm_access_handler[key].expect(vmprompt)
       temp = vm_access_handler[key].before
       return vm_access_handler[key].after
    except pexpect.TIMEOUT:
       raise OurException("Couldn't run cmd {} on the vm {} in zone {}".format(cmd, vm_name, vm_zone))
 


def get_full_list_zones():
    cmd = "gcloud compute zones list"
    try:
        templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    except Exception as e:
        print "Fail to get the list of zone"
        return None
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None

def get_full_list_machine_type():
    cmd = "gcloud compute machine-types list "
    try:
        templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    except Exception as e:
        print "Fail to get the list of machine type"
        return None
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def get_full_list_vm():
    full_list_vm = []
    cmd = "gcloud compute instances list "
    try:
        templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    except Exception as e:
        print "Fail to get the list of vm."
        return None
    if len(templist) > 0:
       return [[_temp.split()[0], _temp.split()[1], _temp.split()[2], _temp.split()[3] , _temp.split()[4]] for _temp in templist]
    else:
        return None


def get_vm_ssd_info(vm_name, vm_zone):
    ssd_list = []
    cmd = "lsblk"
    output = send_cmd_and_get_output(vm_name, vm_zone, cmd).splitlines()
    if len(output) > 0:
        matchssd = re.compile(ssd_pattern)
        for _line in output:
            if matchssd.match(_line):
                 ssd_list.append(matchssd.match(_line).group(1))
        return ssd_list
    else:
        return  None

def prepare_act_cfg_on_vm(vm_name, vm_zone, write_load, read_load, runtime):
    ssd_list = get_vm_ssd_info(vm_name, vm_zone)
    act_cfg_generate_cli = 'python act_config_generator.py --numberofssd {} --actwriteload {} --actreadload {} --runtime  {}'.format(len(ssd_list), write_load, read_load, runtime)
    send_cmd_and_get_output(vm_name, vm_zone, act_cfg_generate_cli)
    return ssd_list


def install_act_on_vm(vm_name, vm_zone):
    send_cmd_and_get_output(vm_name, vm_zone, ACT_INSTALL_CLI)

def install_fio_on_vm(vm_name, vm_zone):
    send_cmd_and_get_output(vm_name, vm_zone, FIO_INSTALL_CLI)
    send_cmd_and_get_output(vm_name, vm_zone, NFS_CLIENT_MOUNT)
    return 

def download_script_to_vm(vm_name, vm_zone):
    send_cmd_and_get_output(vm_name, vm_zone, GIT_CLONE_CLI)

def kill_act(vm_list, zone_list):
    for _vm, _zone in zip(vm_list, zone_list):
        kill_act_process(_vm, _zone)


def kill_act_process(vm_name, vm_zone):
    i = 0
    while is_process_running(vm_name, vm_zone, 'act') and i < RETRY:
        cli = 'sudo killall act'
        send_cmd_and_get_output(vm_name, vm_zone, cli)
        time.sleep(PAUSE)
        i += 1
    return
#[mzhuo@elastifile-client-3 ~]$ sudo showmount -e 10.99.0.2
#Export list for 10.99.0.2:
#/ssd-container-2/root *
#/ssd-container-1/root *
#[mzhuo@elastifile-client-3 ~]$ sudo mount 10.99.0.2:/ssd-container-1/root /mnt/ssd1
#[mzhuo@elastifile-client-3 ~]$ sudo mount 10.99.0.2:/ssd-container-2/root /mnt/ssd2
# fio --name first --verify_dump=1 --verify=meta --readwrite=randrw --size=1G --continue_on_error=verify

def run_fio_on_vm(vm_name, vm_zone):
    return
 #   send_cmd_and_get_output(vm_name, vm_zone, 'sudo reboot')
 #   return
#    cli="mkdir -p /mnt/ssd/{}; cd /mnt/ssd/{}".format(vm_name,vm_name)
#    send_cmd_and_get_output(vm_name, vm_zone, cli)
    cli="sudo mkdir -p /mnt/ssd/{}; cd /mnt/ssd/{}".format(vm_name,vm_name)
    send_cmd_and_get_output(vm_name, vm_zone, cli)
    send_cmd_and_get_output(vm_name, vm_zone, fio_cli)

def act_run(vm_name, vm_zone, force):
    ssd_list = get_vm_ssd_info(vm_name, vm_zone)
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

    prepare_act_cfg_on_vm(vm_name, vm_zone, write_load, read_load, ACT_RUN_HOUR)
    act_cfg_file = 'actcfg_ssd_{}_write_{}_read_{}.txt'.format(len(ssd_list), write_load, read_load)
    outputfile = "{}_{}_{}".format(vm_name, vm_zone, act_cfg_file)
    cli = "cd act"
    send_cmd_and_get_output(vm_name, vm_zone, cli)
    cli = "sudo ./act {} > {} & ".format(act_cfg_file, outputfile)
    output=send_cmd_and_get_output(vm_name, vm_zone, cli)



def upload_log_from_vm(vm_name, vm_zone, vm_machine_type, actverboselog):
    cli = "cd act"
    send_cmd_and_get_output(vm_name, vm_zone, cli)
    cli = "ls -latr | grep {}".format('txt')
    outputlist=send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()
    actverboselog.write('=======================================================================\n')
    actverboselog.write('\n\nACT result for VM {} in Zone {}.\n'.format(vm_name, vm_zone))
    actverboselog.write('=======================================================================\n')

    for _line in  outputlist:
        if 'txt' in _line and not 'grep' in _line:
            newlist0 = str(_line).split()[-1].split('.')
            tempact = '.'.join(newlist0[:-1])

            if int(str(_line).split()[4]) < 50000:
               continue
            actfile = '{}.txt'.format(tempact)
            actverboselog.write(actfile)
            actverboselog.write('\n')
            cli = "latency_calc/act_latency.py -l {}".format(actfile)
            actverboselog.write(cli)
            actverboselog.write('\n')

            actlist = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()[2:-2]
            if len(actlist) > 0:
                for _lline in actlist:
                    actverboselog.write(_lline)
                    actverboselog.write('\n')
#            actverboselog.write('Done with file {} on  {} in zone.'.format(actfile, vm_name, vm_zone))
                actverboselog.write('\n')

            errorlog = 'ERROR: large block writes'
            cli = 'grep  {} {} -A 10 -B 5 '.format(errorlog, actlist)
            erroroutput =  send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()[2:-2]
            print erroroutput
            if len(erroroutput) > 400:
                actverboselog.write('\n'.join(erroroutput.splitlines()[2:]))
                actverboselog.write('\n')


    actverboselog.write('=======================================================================\n')
    return


def is_process_running(vm_name, vm_zone, process_name):
    cli = "ps aux"
    output = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()
    process_running = False
    for _temp in output:
        for __temp in _temp:
            if process_name in __temp:
                process_running = True
                break
    return process_running


def is_act_running(vm_name, vm_zone):
    cli = "ps aux"
    output = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()
    act_running = False
    for _temp in output:
        if "act" in _temp:
            act_running = True
            break
    return act_running


def is_init_running(vm_name, vm_zone):
    cli = "ps aux"
    output = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()
    init_running = False
    for _temp in output:
        for __temp in _temp:
            if "actprep" in __temp:
                act_running = True
                break
    return act_running


def convert_2_list(actoutput):
    actoutput = actoutput[5:-3]
#  data is act version 4.0
#        trans                                              device
#        %>(ms)                                             %>(ms)
#slice        1      2      4      8     16     32     64        1      2      4      8     16     32     64
#-----   ------ ------ ------ ------ ------ ------ ------   ------ ------ ------ ------ ------ ------ ------
#    1     0.24   0.10   0.00   0.00   0.00   0.00   0.00     0.24   0.10   0.00   0.00   0.00   0.00   0.00
#    2     0.64   0.26   0.01   0.00   0.00   0.00   0.00     0.63   0.26   0.01   0.00   0.00   0.00   0.00
#    3     0.99   0.41   0.01   0.00   0.00   0.00   0.00     0.97   0.40   0.01   0.00   0.00   0.00   0.00
#    4     1.29   0.54   0.01   0.00   0.00   0.00   0.00     1.27   0.53   0.01   0.00   0.00   0.00   0.00
#    5     1.55   0.65   0.01   0.00   0.00   0.00   0.00     1.53   0.64   0.01   0.00   0.00   0.00   0.00
#    6     1.77   0.74   0.02   0.00   0.00   0.00   0.00     1.75   0.73   0.01   0.00   0.00   0.00   0.00
    sequence = 1
    alldata = []
    for _temp in actoutput:
        slicedata = _temp.split()
    #    print slicedata
 #       if int(slicedata[0]) == sequence and len(slicedata) == 15:
        if len(slicedata) == 15 and not '-' in slicedata:
            alldata.append(slicedata)
            sequence += 1
    return alldata

def is_strictly_increase(testdata):
    if len(testdata) <=  RAMP_TIME:
        return False, 0, 0
    is_strictly_increase = strictly_increasing([float(temp[8]) for  temp in  testdata[RAMP_TIME:]])
    if is_strictly_increase:
        return True, RAMP_TIME, len(testdata)
    else:
        max_increase=0
        for i in range(len(testdata)):
            for j in range(len(testdata)):
                if j < i or  i < RAMP_TIME:
                     continue
                if strictly_increasing([float(temp[8]) for  temp in  testdata[i:j]]):
                    if max_increase  <  j-i:
                        max_increase = j-i
                        first = i
                        last=j
        if max_increase > 1:
            return True, first, last
        else:
            return False, 0, 0
    return False, 0, 0


def check_act_run(vm_name, vm_zone, vm_machine_type, actlogfile, actsummaryfile, acterrorlog):
    slices = []
    check_done = True
    logfile = None
    timestamp = None
    owner = 'mzhuo'
    cli = "ps -eaf|grep act |grep sudo"
    output=send_cmd_and_get_output(vm_name, vm_zone, cli)
    # print "output :\n"
    # print output
    print "***len", len(output), '\n'
    if len(output) < ACT_RUN_OUPUT_LENGTH:
        temp = 'No act is running on {} in zone.'.format(vm_name, vm_zone)
        print temp
        print '\n'
        acterrorlog.write(temp)
        acterrorlog.write('\n')
        check_done = False
    else:
       cli = "cd act"
       send_cmd_and_get_output(vm_name, vm_zone, cli)
       cli = "ls -latr | grep actcfg | grep {}_{} ".format(vm_name, vm_zone)
       output=' '.join(send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines())
       # print "output :\n"
       # print output
       # print "***\n", len(output)
       act_log_file = '.*{}\s{}\s+(\d+).*({}_{}.*.txt).*'.format(owner, owner, vm_name, vm_zone)
       match_act_log_file = re.compile(act_log_file)
       # print "patter: ", act_log_file
       if match_act_log_file.match(output):
           logfilesize = match_act_log_file.match(output).group(1)
           logfilename = match_act_log_file.match(output).group(2)
           # print "log file is  " , logfilename, logfilesize
           time.sleep(2)
           cli = "ls -latr | grep actcfg | grep {}_{} ".format(vm_name, vm_zone)
           output=' '.join(send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines())
           # print "output :\n"
           # print output
           # print "***\n", len(output)
           if match_act_log_file.match(output):
               actlogfile.write('\n\nACT result for VM {} in Zone {}.\n'.format(vm_name, vm_zone))
               actlogfile.write('===============================================================================================================================================================================================\n')
               newlogfilesize = match_act_log_file.match(output).group(1)
               newlogfilename = match_act_log_file.match(output).group(2)
               if newlogfilename == logfilename:
                   if logfilesize < newlogfilesize:
                       cli = "latency_calc/act_latency.py -l {}".format(newlogfilename)
                      # actlogfile.write('cli: {} \n'.format(cli))
                       outputpattern = ".*actcfg_ssd_(\d+)_write_(\d+)_read_(\d+).txt".format(vm_name, vm_zone)
                       test_pattern = re.compile(outputpattern)
                       if test_pattern.match(newlogfilename):
                           no_ssd = test_pattern.match(newlogfilename).group(1)
                           write_load =  test_pattern.match(newlogfilename).group(2)
                           read_load = test_pattern.match(newlogfilename).group(3)
                           actlogfile.write('no_of_ssd: {}, write load:{},  read load: {}\n'.format(no_ssd, write_load, read_load))
                       actlist = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()[3:-1] 
                       slices = convert_2_list(actlist)
                       is_increase, first, last =  is_strictly_increase(slices)
                       average, maximum, deviation = data_process(slices)
                       actlogfile.write('\n'.join(actlist))
                       number_pattern='([-+]?\d*\.\d+)\s+'
                       number_findall = re.compile(number_pattern)
                       linebreak = False
                       total_write = int(no_ssd) * int(write_load)
                       total_read = int(no_ssd) * int(read_load)
                       for _line in actlist:
                           # print "line : ", _line
                           allnumbers = number_findall.findall(_line)
                           # print allnumbers
                           for _number in allnumbers:
                               if float(_number) >= 5:
                                  status = 'FAIL'
                                  linebreak = True
                                  break
                           if linebreak:
                               # print "no need to chech more lines"
                               break
                           # print "need to ccheck more"  
                       if not  linebreak:      
                           status = "PASS"

                       if is_increase and (last-first) > INCREASE_CHECK:
                           increase_flag =  True 
                       else:
                           increase_flag = False
                       fillspace = 13 - len(vm_machine_type)
                       for i in range(fillspace):
                           temp_vm_type= vm_machine_type+' '
                       if increase_flag:    
                         temp = '{:>3}  {:>6}  {:>6}  {:^70}  {:^18}  {:>13}  {:>6}  {:>6}  {:>6}  {:>6}  {:>6}  {:>4}  {:>4}  {:>4}'.format(no_ssd, total_write, total_read, vm_name, vm_zone, vm_machine_type, status, 'FAIL', average, deviation, maximum, len(slices), first, last)
                       else:
                         temp = '{:>3}  {:>6}  {:>6}  {:^70}  {:^18}  {:>13}  {:>6}  {:>6}  {:>6}  {:>6}  {:6}  {:>4}'.format(no_ssd, total_write, total_read, vm_name, vm_zone, vm_machine_type, status,  'PASS', average, deviation, maximum, len(slices))
                       if increase_flag:    
                         temp = '{:>3},  {:>6},  {:>6},  {:^70},  {:^18},  {:>13},  {:>6},  {:>6},  {:>6},  {:>6},  {:>6},  {:>4},  {:>4},  {:>4}'.format(no_ssd, total_write, total_read, vm_name, vm_zone, vm_machine_type, status, 'FAIL', average, deviation, maximum, len(slices), first, last)
                       else:
                         temp = '{:>3},  {:>6},  {:>6},  {:^70},  {:^18},  {:>13},  {:>6},  {:>6},  {:>6},  {:>6},  {:6},  {:>4}'.format(no_ssd, total_write, total_read, vm_name, vm_zone, vm_machine_type, status,  'PASS', average, deviation, maximum, len(slices))

                       actsummaryfile.write(temp) 
                       actsummaryfile.write('\n')
                       actlogfile.write('\n')
                       actlogfile.write(temp)
                       actlogfile.write('\n===============================================================================================================================================================================================\n')
                   else:
                       errorlog = 'ERROR: large block writes can\'t keep up'
                       try:
                          actrunningfile = open(logfilename, 'r')
                           
                          if errorlog in actrunningfile.read():
                             temp = 'Error {} on vm {} in zone {}: type::{}, write:{}, read:{}, ssd:{}.'.format(errorlog, vm_name, vm_zone, vm_machine_type, total_write, total_read, no_ssd)
                             acterrorfile.write(temp)
                             acterrorfile.write('\n')
                          else:
                             temp = 'Test done {} on vm {} in zone {}: type::{}, write:{}, read:{}, ssd:{}.'.format(errorlog, vm_name, vm_zone, vm_machine_type, total_write, total_read, no_ssd)  
                             acterrorfile.write(temp)
                             acterrorfile.write('\n')
                       except Exception as e:
                            temp = 'can not find log file {} on  vm {} in zone {}.'.format(logfilename,  vm_name, vm_zone)
                            acterrorfile.write(temp)
                            acterrorfile.write('\n')

       else:
            check_done=False
            print "fail to match file"
            temp = 'No  act log file found on {} in zone.'.format(vm_name, vm_zone)
            acterrorlog.write(temp)
            acterrorlog.write('\n')

    if not check_done:
    #    install_act_on_vm(vm_name, vm_zone)
    #    download_script_to_vm(vm_name, vm_zone)
    #    act_run(vm_name, vm_zone, False)
        print "make act run"
#        time.sleep(100)

def create_vm(project, machine_type, ssdnumber, zone, sequence):
    return True
    ssd_cfg_string = SSD_CFG_SUFFIX*int(ssdnumber)
    vm_name = "{}-cpu-{}-ssd-{}-zone-{}-no-{}".format('perf', machine_type, ssdnumber, zone, sequence)

    vm_name = "{}-zone-{}-no-{}".format('perf',  zone, sequence)
    print vm_name
    cmd2createvm = "{} {} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(VM_CREATE_SUFFIX, vm_name, machine_type, zone, ssd_cfg_string)
    print cmd2createvm
#    cmd2checkvm = "gcloud compute  instances  reset  {} --zone {}".format(vm_name, zone)
#    print cmd2checkvm
#    output = subprocess.check_output(cmd2checkvm.split())
#    return
#    cmd2createvm = "{} {} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(VM_CREATE_SUFFIX, vm_name, machine_type, zone, ssd_cfg_string)
    try:
       output = subprocess.check_output(cmd2createvm.split())
       print output
       if "RUNNING" in output:
           print "vm created"
           return True
       else:
           print "vm creation fails"
           return False
    except Exception as e:
       print "error in creating vm"
       return False

def create_vms(project, localssd_number_list, machine_type_list, zone_list, vmperzone):
    running_vm = []
    running_vm_zone = []
    running_vm_machine = []
    running_vm_ssd = []
    vm_index = 0
    for _ssd in localssd_number_list:
        for _machine_type in machine_type_list:
           for _zone in zone_list:
               for j in range(vmperzone):
                   print "going to create vm", _ssd, _machine_type, _zone, j
                   if create_vm(project, _machine_type, _ssd, _zone, j):
#                       vm_name = "{}-cpu-{}-ssd-{}-zone-{}-no-{}".format(project,_machine_type, _ssd, _zone, j)
                       vm_name = "{}-zone-{}-no-{}".format('perf', _zone, j)
                       running_vm.append(vm_name)
                       running_vm_zone.append(_zone)
                       running_vm_machine.append(_machine_type)
                       running_vm_ssd.append(_ssd)
                       vm_index = vm_index + 1
    print running_vm
    return running_vm, running_vm_zone, running_vm_machine, running_vm_ssd


###### test starts here

####### populate data for zone ####
#all_zones = get_full_list_zones()
## print all_zones;

#all_machine_types = get_full_list_machine_type()
## print all_machine_types;

all_vms =  get_full_list_vm()
# print all_vms


def reset_all_vms():
    for eachvm in all_vms:
        # print eachvm
        reset_vm_instance(eachvm[0], eachvm[1])

def run_act_on_all_vm():
    for eachvm in all_vms:
        # print eachvm
        act_run(eachvm[0], eachvm[1])

def check_act_result_on_vms(vm_list, zone_list, machine_list, actlogfile, actsummaryfile, acterrorlog):
    vm_index = 0
    for eachvm in vm_list:
        check_act_run(eachvm, zone_list[vm_index], machine_list[vm_index], actlogfile, actsummaryfile, acterrorlog)
        vm_index += 1

def upload_log_form_all_vm(actverboselog):
    for eachvm in all_vms:
        upload_log_from_vm(eachvm[0], eachvm[1], eachvm[2], actverboselog)


def init_ssd(vm_name, vm_zone):
    act_init_ssd_cli = 'cd act; python act_initialize_ssd.py'
    send_cmd_and_get_output(vm_name, vm_zone, act_init_ssd_cli)
    return

######## populate data for machine type ####
parser = argparse.ArgumentParser()
parser.add_argument('-project', '--project', dest='project', type=str, default='cpe-performance-storage')
parser.add_argument('-createvm', '--createvm', dest='createvm', type=bool, default=False)
parser.add_argument('-defaultssd', '--defaultssd', dest='defaultssd', type=str, default='0')
parser.add_argument('-defaultvmtype', '--defaultvmtype', dest='defaultvmtype', type=str, default='n1-standard-1')
parser.add_argument('-defaultzone', '--defaultzone', dest='defaultzone', type=str, default='us-central1-f')
parser.add_argument('-defaultvmperzone', '--defaultvmperzone', dest='defaultvmperzone', type=int, default=512)


parser.add_argument('-getscript', '--getscript', dest='getscript', type=bool, default=False)
parser.add_argument('-installact', '--installact', dest='installact', type=bool, default=False)
parser.add_argument('-installfio', '--installfio', dest='installfio', type=bool, default=False)

parser.add_argument('-resetvm', '--resetvm', dest='resetvm', type=bool, default=False)
parser.add_argument('-deletevm', '--deletevm', dest='deletevm', type=bool, default=False)

parser.add_argument('-initssd', '--initssd', dest='initssd', type=bool, default=False)
parser.add_argument('-runact', '--runact', dest='runact', type=bool, default=False)
parser.add_argument('-ssdact', '--ssdact', dest='ssdact', type=int, default=1)
parser.add_argument('-loadact', '--loadact', dest='loadact', type=int, default=12)
parser.add_argument('-actlog', '--actlog', dest='actlog', type=str, default='act')
parser.add_argument('-actresult', '--actresult', dest='actresult', type=bool, default=False)

parser.add_argument('-actwriteload', '--actwriteload', dest='actwriteload', type=int, default=12)
parser.add_argument('-actreadload', '--actreadload', dest='actreadload', type=int, default=12)
parser.add_argument('-runtime', '--runtime', dest='runtime', type=int, default=168)
parser.add_argument('-no_queue', '--no_queue', dest='no_queue', type=int, default=8)
parser.add_argument('-no_thread_per_queue', '--no_thread_per_queue', dest='no_thread_per_queue', type=int, default=8)

parser.add_argument('-uploadactlog', '--uploadactlog', dest='uploadactlog', type=bool, default=False)
parser.add_argument('-uploadbucket', '--uploadbucket', dest='uploadbucket', type=str)
parser.add_argument('-killact', '--killact', dest='killact', type=bool, default=False)

currentDT = datetime.datetime.now()
timestamp = '{}-{}-{}-{}-{}'.format(currentDT.month, currentDT.day, currentDT.year, currentDT.hour, currentDT.minute)

args = parser.parse_args()
actreportlog = '{}.{}.detail.{}.log'.format(args.project, args.actlog, timestamp)
actsummarylog = '{}.{}.summary.{}.log'.format(args.project, args.actlog, timestamp)
acterrorlog = '{}.{}.error.{}.log'.format(args.project, args.actlog, timestamp)
actverboselog = '{}.{}.verbose.{}.log'.format(args.project, args.actlog, timestamp)

vm_list = []

if "ALL" in args.defaultzone:
    zones = get_full_list_zones()
else:
    zones = args.defaultzone.split(';')

if args.createvm:
    vm_list, zone_list, machine_list, ssd_list = create_vms(args.project, args.defaultssd.split(','), args.defaultvmtype.split(','), zones, args.defaultvmperzone)
    
    indexvm = 0
    for _vm in vm_list:
        install_fio_on_vm(_vm, zone_list[indexvm])
        run_fio_on_vm(_vm, zone_list[indexvm])
#       install_act_on_vm(_vm, zone_list[indexvm])
#       download_script_to_vm(_vm, zone_list[indexvm])
#       prepare_act_cfg_on_vm(_vm, zone_list[indexvm], args.actwriteload, args.actreadload, args.runtime)
        indexvm += 1
#       time.sleep(120)
     
    time.sleep(9999999999999)

    indexvm = 234
    for _vm in vm_list:
        init_ssd(_vm, zone_list[indexvm])
        indexvm += 1
    indexvm = 0
    for _vm in vm_list:
        if not is_process_running(_vm, zone_list[indexvm], 'actprep'):
            act_run(_vm, zone_list[indexvm], True)
        indexvm += 1

if args.uploadactlog:
   actverbosefile = open(actverboselog, 'w')
   upload_log_form_all_vm(actverbosefile)
   actverbosefile.close()

if args.actresult:
    actlogfile = open(actreportlog, 'w')
    actsummaryfile = open(actsummarylog, 'w')
    acterrorfile = open(acterrorlog, 'w')
    header = 'SSD  W_Load  R_Load                                VM_NAME                                          ZONE        MACHINE_TYPE   5%_check  6h_inc   Avg     Max    StDev  Total From   To' 
    actsummaryfile.write(header)
    actsummaryfile.write('===============================================================================================================================================================================================\n')
    if not vm_list:
        vm_full_list = get_full_list_vm()
        vm_list = [ _temp[0] for _temp in vm_full_list ]
        zone_list = [ _temp[1] for _temp in vm_full_list ]
        machine_list = [ _temp[2] for _temp in vm_full_list ]

    check_act_result_on_vms(vm_list, zone_list, machine_list, actlogfile, actsummaryfile, acterrorfile)
    actsummaryfile.write('================================================================================================================================================================================================\n')
    actlogfile.close()
    actsummaryfile.close()
    acterrorfile.close()

if args.killact:
     if not vm_list:
        vm_full_list = get_full_list_vm()
        vm_list = [ _temp[0] for _temp in vm_full_list ]
        zone_list = [ _temp[1] for _temp in vm_full_list ]

     kill_act(vm_list, zone_list)

