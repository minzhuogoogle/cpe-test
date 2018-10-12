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
verbose = True
#ssd_pattern = '(nvme0n\d+)\s+\d+:\d\s*\s+\d+\s+(\d+.G)\s+\d+\s+disk'
ssd_pattern = '(nvme0n\d+)\s+\d+:\d.*disk'

ACT_INSTALL_CLI = 'git clone https://github.com/aerospike/act.git; sudo apt-get install make gcc libc6-dev libssl-dev zlib1g-dev python -y; cd act; make; make -f Makesalt'
ACT_CFG_CLI = 'cd ; cd act; gsutil cp gs://testing-log/aerospike/act.package.tar act.package.tar; tar xvf act.package.tar; sudo chmod 777 *.*'
ACT_RUN_OUPUT_LENGTH = 200
ACT_RUN_HOUR = 196
PAUSE = 10
RETRY = 3

###### global variables ##################
localssd_number_list = [8]
zone_list=[]
machine_type_list = []
vm_list = []

vm_access_handler = {}


def check_running_act_instance(vm_name, vm_zone):
    cmd =  'gcloud compute instances reset {} --zone={}'.format(vm_name, vm_zone)
    # print "cmd:", cmd
    templist = subprocess.check_output(cmd.split('')).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def reset_vm_instance(vm_name, vm_zone):
    cmd =  'gcloud compute instances reset {} --zone={} '.format(vm_name, vm_zone)
    # print "cmd:", cmd
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
    # print  vm_access_handler.keys() 

################ get the list of zones #########
def send_cmd_and_get_output(vm_name, vm_zone, cmd):
    key='{};{}'.format(vm_name, vm_zone)
    vmprompt = '.*@{}.*'.format(vm_name)
    if not key in vm_access_handler.keys():
        # print "ssh to vm"
        ssh_to_vm(vm_name, vm_zone)
    else:
         print "ssh access existing"
    print " 2222 : cmd: " , cmd     
    print "\n\n"
    vm_access_handler[key].flush()
    vm_access_handler[key].sendline(cmd)
    vm_access_handler[key].expect(vmprompt)
    temp = vm_access_handler[key].before
    return vm_access_handler[key].after


def get_full_list_zones():
    cmd = "gcloud compute zones list"
    # print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None

def get_full_list_machine_type():
    cmd = "gcloud compute machine-types list "
    # print "cmd:", cmd
    templist = subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
        return [_temp.split()[0] for _temp in templist]
    else:
        return None


def get_full_list_vm():
  #cloud compute instances list | awk  '{# print $5}'
    full_list_vm = []
    cmd = "gcloud compute instances list "
    # print "cmd:", cmd
    templist =  subprocess.check_output(cmd.split()).splitlines()[1:]
    if len(templist) > 0:
       return [[_temp.split()[0], _temp.split()[1], _temp.split()[2], _temp.split()[3] , _temp.split()[4]] for _temp in templist]
    else:
        return None


def get_vm_ssd_info(vm_name, vm_zone):
    ssd_list = []
    cmd = "lsblk"
    output = send_cmd_and_get_output(vm_name, vm_zone, cmd).splitlines()
    # print '*******',output,"***", len(output)
#    time.sleep(5)
    if len(output) > 0:
        matchssd = re.compile(ssd_pattern)
        for _line in output:
            # print "new line : ", _line
            if matchssd.match(_line):
                 ssd_list.append(matchssd.match(_line).group(1))
        # print "ssd list : " ,ssd_list
        return ssd_list
    else:
        return  None

def prepare_act_cfg_on_vm(vm_name, vm_zone, write_load, read_load, runtime):
    ssd_list = get_vm_ssd_info(vm_name, vm_zone)
    act_cfg_generate_cli = 'cd act; python act_config_generator.py --numberofssd {} --actwriteload {} --actreadload {} --runtime  {}'.format(len(ssd_list), write_load, read_load, runtime)
    send_cmd_and_get_output(vm_name, vm_zone, act_cfg_generate_cli)
    return ssd_list


def install_act_on_vm(vm_name, vm_zone):
    send_cmd_and_get_output(vm_name, vm_zone, ACT_INSTALL_CLI)

def install_fio_on_vm(vm_name, vm_zone):
    return 

def download_script_to_vm(vm_name, vm_zone):
    send_cmd_and_get_output(vm_name, vm_zone, ACT_CFG_CLI)

def kill_act_process(vm_name, vm_zone):
    i = 0
    while is_act_running(vm_name, vm_zone) and i < RETRY:
        cli = 'sudo killall act'
        send_cmd_and_get_output(vm_name, vm_zone, cli)
        time.sleep(PAUSE)
        i += 1
    return


def act_run(vm_name, vm_zone, force):
#    if is_act_running(vm_name, vm_zone):
#        if not force:
#            print "Act is already running on {} in {}.\n".format(vm_name, vm_zone)
#            return
#        else:
#            kill_act_process(vm_name, vm_zone)

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


def is_act_running(vm_name, vm_zone):
    cli = "ps -eaf|grep act |grep sudo"
    output=send_cmd_and_get_output(vm_name, vm_zone, cli)
    print "***len\n", len(output)
    return len(output) > 200


def check_act_run(vm_name, vm_zone, vm_machine_type, actlogfile, actsummaryfile, acterrorlog):
    check_done = True;
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
               actlogfile.write('=======================================================================\n')
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
                       actlist = send_cmd_and_get_output(vm_name, vm_zone, cli).splitlines()[2:-2]    
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
                       fillspace = 13 - len(vm_machine_type)
                       for i in range(fillspace):
                           temp_vm_type= vm_machine_type+' '
                       temp = '{:>3}  {:>16}  {:>15}  {:^40} {:^18} {:>10}   {:>4}'.format(no_ssd, total_write, total_read, vm_name, vm_zone, vm_machine_type, status)
                       actsummaryfile.write(temp) 
                       actsummaryfile.write('\n')
                       actlogfile.write('\n')
                       actlogfile.write(temp)
                       actlogfile.write('\n=====================================================================\n')
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
    ssd_cfg_string = SSD_CFG_SUFFIX*ssdnumber
    vm_name = "{}-cpu-{}-ssd-{}-zone-{}-no-{}".format(project, machine_type, ssdnumber, zone, sequence)
    cmd2createvm = "{} {} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(VM_CREATE_SUFFIX, vm_name, machine_type, zone, ssd_cfg_string)
    print cmd2createvm
    cmd2checkvm = "gcloud compute  instances describe  {} --zone {}".format(vm_name, zone)

#    cmd2createvm = "{} {} --machine-type {} --zone {} --image-family=ubuntu-1804-lts --image-project=ubuntu-os-cloud  {}".format(VM_CREATE_SUFFIX, vm_name, machine_type, zone, ssd_cfg_string)
    try:
       output = subprocess.check_call(cmd2checkvm.split())
       if "RUNNING" in output:
           # print "vm created"
           return 1
       else:
           # print "vm creation fails"
           return 0
    except Exception as e:
       # print "error in creating vm"
       return 0

def create_vms(project, localssd_number_list, machine_type_list, zone_list):
    running_vm = []
    running_vm_zone = []
    running_vm_machine = []
    running_vm_ssd = []
    for _ssd in localssd_number_list:
      for _machine_type in machine_type_list:
        for  _zone in zone_list:
             for j in [1]:
          #       # print "going to create cm", _ssd, _machine_type, _zone, j
       #          if create_vm(project, _machine_type, _ssd, _zone, j) == 1:
                    vm_name = "{}-cpu-{}-ssd-{}-zone-{}-no-{}".format(project,_machine_type, _ssd, _zone, j)
                    running_vm.append(vm_name)
                    running_vm_zone.append(_zone)
                    running_vm_machine.append(_machine_type)
                    running_vm_ssd.append(_ssd) 


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

def check_act_result_on_all_vm(actlogfile, actsummaryfile, acterrorlog):
    for eachvm in all_vms:
        check_act_run(eachvm[0], eachvm[1], eachvm[2],  actlogfile, actsummaryfile, acterrorlog)

def upload_log_form_all_vm(actverboselog):
    for eachvm in all_vms:
        upload_log_from_vm(eachvm[0], eachvm[1], eachvm[2], actverboselog)


def init_ssd(vm_name, vm_zone):
 #   act_init_ssd_cli = 'cd act; python act_initialize_ssd.py'
    act_check = "cd act; ls -latr; ps -eaf|grep act" 
    send_cmd_and_get_output(vm_name, vm_zone, act_check)
    return

######## populate data for machine type ####
parser = argparse.ArgumentParser()
parser.add_argument('-project', '--project', dest='project', type=str, default='aerospike-211521')
parser.add_argument('-resetvm', '--resetvm', dest='resetvm', type=bool, default=False)
parser.add_argument('-initssd', '--initssd', dest='initssd', type=bool, default=False)
parser.add_argument('-installact', '--installact', dest='installact', type=bool, default=False)
parser.add_argument('-installfio', '--installfio', dest='installfio', type=bool, default=False)
parser.add_argument('-downloadscript', '--downloadscript', dest='downloadscript', type=bool, default=False)

parser.add_argument('-runact', '--runact', dest='runact', type=bool, default=False)
parser.add_argument('-checkact', '--checkact', dest='checkact', type=bool, default=False)
parser.add_argument('-actwriteload', '--actwriteload', dest='actwriteload', type=int, default=12)
parser.add_argument('-actreadload', '--actreadload', dest='actreadload', type=int, default=6)
parser.add_argument('-runtime', '--runtime', dest='runtime', type=int, default=168)
parser.add_argument('-no_queue', '--no_queue', dest='no_queue', type=int, default=8)
parser.add_argument('-no_thread_per_queue', '--no_thread_per_queue', dest='no_thread_per_queue', type=int, default=8)

parser.add_argument('-createvm', '--createvm', dest='createvm', type=bool, default=False)
parser.add_argument('-appendixvm', '--appendixvm', dest='appendixvm', type=str, default='testvm')
parser.add_argument('-actlog', '--actlog', dest='actlog', type=str, default='act')
parser.add_argument('-uploadactlog', '--uploadactlog', dest='uploadactlog', type=bool, default=False)
parser.add_argument('-onevm', '--onevm', dest='onevm', type=str, default=None)
parser.add_argument('-onezone', '--onezone', dest='onezone', type=str, default=None)

currentDT = datetime.datetime.now()
timestamp = '{}-{}-{}-{}-{}'.format(currentDT.month, currentDT.day, currentDT.year, currentDT.hour, currentDT.minute)

args = parser.parse_args()
actreportlog = '{}.{}.detail.{}.log'.format(args.project, args.actlog, timestamp)
actsummarylog = '{}.{}.summary.{}.log'.format(args.project, args.actlog, timestamp)
acterrorlog = '{}.{}.error.{}.log'.format(args.project, args.actlog, timestamp)
actverboselog = '{}.{}.verbose.{}.log'.format(args.project, args.actlog, timestamp)


localssd_number_list=[1]
machine_type_list=['n1-highcpu-2']
zone_list = get_full_list_zones()
if args.createvm:
   vm_list, zone_list, machine_list, ssd_list = create_vms(args.project, localssd_number_list, machine_type_list, zone_list)
   indexvm = 0
   for _vm in vm_list:
       prepare_act_cfg_on_vm(_vm, zone_list[indexvm], 1, 1, 192)
       act_run(_vm, zone_list[indexvm], True)

#     install_act_on_vm(_vm, zone_list[indexvm])
#     download_script_to_vm(_vm, zone_list[indexvm])
       init_ssd(_vm, zone_list[indexvm])
       indexvm += 1

if args.uploadactlog:
   actverbosefile = open(actverboselog, 'w')
   upload_log_form_all_vm(actverbosefile)
   actverbosefile.close()

if args.checkact:
    actlogfile = open(actreportlog, 'w')
    actsummaryfile = open(actsummarylog, 'w')
    acterrorfile = open(acterrorlog, 'w')
    header = 'SSD  Total_Write_Load  Total_Read_Load                 VM_NAME                          ZONE        MACHINE_TYPE    STATUS\n'
    actsummaryfile.write(header)
    actsummaryfile.write('================================================================================================================================\n')
    check_act_result_on_all_vm(actlogfile, actsummaryfile, acterrorfile)
    actsummaryfile.write('================================================================================================================================\n')
    actlogfile.close()
    actsummaryfile.close()
    acterrorfile.close()


if args.runact:
    print "Run act....."
    if args.onevm:
       vm_name = args.onevm
       vm_zone = args.onezone
       print vm_name, vm_zone
       act_run(vm_name, vm_zone)
    else:
       full_list_vm = get_full_list_vm()
       for _vm in full_list_vm:
           act_run(_vm[0], _vm[1])
