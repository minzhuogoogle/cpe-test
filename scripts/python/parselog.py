#!/usr/bin/env python

import sys
import pexpect
import os
import argparse
import subprocess
from subprocess import call
import re
import time
import fnmatch
import os


verbose = True
BOARD = ['fizz', 'gaudo', 'Teemo', 'Guado','Panther','Buddy', 'Zako', 'Tricky', 'Rikku']

def process_cmd(cli, lastoutput, mgmt_ip, logdir):
    if "#" in cli:
       return True, "#"
    if "CONTINUTE_ON_CONDITION" in cli:
       ctype = re.findall("^CONTINUTE_ON_CONDITION:OUTPUT_([A-Z]*):.*$", cli)
       cvalue = re.findall("^CONTINUTE_ON_CONDITION:OUTPUT_[A-Z]*:(.*)$", cli)
       if not ctype or not cvalue:
           return True, '#'
       ctype = ctype[0]
       cvalue = cvalue[0]
       if ctype == 'LEN':
           if len(lastoutput) < int(cvalue):
               return False, None
           else:
               print "Found something interesting, continue....."
               return True, '#'
       if ctype == 'VALUE':
           if cvalue in lastoutput:
               return False, None
           else:
               print "Found something interesting, continue....."
               return True, '#'
    if 'TIMESTAMP' in cli:
        timestamp = getreboottimestamp(mgmt_ip)
        cli = cli.replace("TIMESTAMP", timestamp)
    if 'scp' in cli or "getlog" in cli or 'debug' in cli:
        ctype = cli.split(':')[-1]
        ctype = re.findall("^scp:([a-zA-Z]*).*$", cli)
        ctype = ctype[0]
        print ctype
        debug_log = generate_debug_log(mgmt_ip)
        cli = 'scp root@{}:/tmp/{} {}.{}.{}'.format(mgmt_ip, debug_log, mgmt_ip, ctype, debug_log)
    print cli,
    print '\n'
    return True, cli

def getreboottimestamp(mgmt_ip):
    ssh_oper = ssh2cfm(mgmt_ip)
    if not ssh_oper:
        return None
    uptime = send_cmd_host(ssh_oper, 'uptime -s')
    timestamp = re.findall("\\d{4}[-]?\\d{1,2}[-]?\\d{1,2} \\d{1,2}:\\d{1,2}", uptime)
    timestamp = 'T'.join(timestamp[0].split())
    logoutfromcfm(ssh_oper)
    return timestamp

def generate_debug_log(mgmt_ip):
    ssh_oper = ssh2cfm(mgmt_ip)
    if not ssh_oper:
        return None
    debug_log = send_cmd_host(ssh_oper, 'generate_logs')
    debug_log = re.findall('Logs saved to /tmp/(.*.tgz)', debug_log)
    logoutfromcfm(ssh_oper)
    return debug_log[0]


def ssh2cfm(ipv4):
    try:
        ssh_oper = pexpect.spawn('ssh %s@%s' % ('root', ipv4))
        if verbose:
            ssh_oper.logfile = sys.stdout
            ssh_oper.timeout = 1000
            ssh_oper.maxread=1000
            ssh_oper.expect('#')
    except pexpect.TIMEOUT:
        print "Couldn't log on to CfM."
        return None
    return ssh_oper

def send_cmd_host(sshh, cmdline):
    sshh.sendline(cmdline)
    sshh.expect("localhost")
    output = sshh.before
    return output

def logoutfromcfm(ssh_oper):
    ssh_oper.sendline('exit')
    return

def run_cmd_on_cfm(cfm, cmd, logdir):
    print "=====IP: ", cfm
    ssh_oper = ssh2cfm(cfm)
    if not ssh_oper:
      return
    output = []
    next_cli, cli = process_cmd(cmd, output, cfm, logdir)
    if cfm in cli:
        call(cli.split(" "))
        return
    if ssh_oper:
        output = send_cmd_host(ssh_oper, cli)
        logoutfromcfm(ssh_oper)
    return

def run_cmds_on_cfm(mgmt_ip, cmdfile, logdir):
    output = None
    cmdlines = open(cmdfile).readlines()
    print "=====IP: ", mgmt_ip
    for cmdtemp in cmdlines:
        next_cli, cli = process_cmd(cmdtemp, output, mgmt_ip, logdir)
        if not next_cli:
            break
        if next_cli:
            if '#' in cli:
                continue
            if mgmt_ip in cli:
                call(cli.split(" "))
                continue
            ssh_oper = ssh2cfm(mgmt_ip)
            if not ssh_oper:
                continue
            output = send_cmd_host(ssh_oper, cli)
            logoutfromcfm(ssh_oper)
    return


def run_cmds_on_cfms(cfmfile, cmdfile, logdir):
    output = None
    cfmfiles = open(cfmfile).readlines()
    cmdlines = open(cmdfile).readlines()
    for temp in cfmfiles:
        if not len(temp.split()) == 2:
            print "can not find mgmt ipv4 for this CFM.", temp
            continue
        mgmt_ip = temp.split()[0]
        board = temp.split()[1]
        print "=====IP: ", mgmt_ip, "=====Board:", board
        if not board in BOARD:
            print "Skip this CfM"
            continue
        for cmdtemp in cmdlines:
            next_cli, cli = process_cmd(cmdtemp, output, mgmt_ip, logdir)

            if not next_cli:
               break
            if next_cli:
                if '#' in cli:
                    continue
                if mgmt_ip in cli:
                   call(cli.split(" "))
                   continue
                ssh_oper = ssh2cfm(mgmt_ip)
                if not ssh_oper:
                    continue
                output = send_cmd_host(ssh_oper, cli)
                print output
                logoutfromcfm(ssh_oper)
    return


def run_cmd_on_cfms(cfmfile, cmd, logdir):
    output = None
    cfmfiles = open(cfmfile).readlines()
    for temp in cfmfiles:
        if not len(temp.split()) == 2:
            print "can not find mgmt ipv4 for this CFM.", temp
            continue
        mgmt_ip = temp.split()[0]
        board = temp.split()[1]
        print "=====IP: ", mgmt_ip, "=====Board:", board
        if not board in BOARD:
            print "Skip this CfM"
            continue
        next_cli, cli = process_cmd(cmd, output, mgmt_ip, logdir)
        if mgmt_ip in cli:
            call(cli.split(" "))
            continue
        ssh_oper = ssh2cfm(mgmt_ip)
        if not ssh_oper:
            continue
        output = send_cmd_host(ssh_oper, cli)
        logoutfromcfm(ssh_oper)
    return

def populatedata(iotype,readObj,writeObj, logfile):
    if iotype == 1:
      print writeObj.group(1), writeObj.group(2),  writeObj.group(3) ; writeObj.group(4);writeObj(5) 
    if iotype == 2:
       print readObj.group()
    if iotype == 3:
      print writeObj.group(); writeObj.group(1), writeObj.group(2),  writeObj.group(3) ; writeObj.group(4);
      print readObj.group()

def extractdata(logfile, matchfile):
    datalist=[]
    writematch='write:'
    readtempline=None
    writetempline=None
    readObj=None
    writeObj=None
    filedir='/usr/local/google/home/mzhuo/partner/testlog/mnt/vol31'
    cmd = "egrep;{};{}/{};-A;1".format(writematch, filedir, matchfile)
    writebw, writeiops, writelatency = 0, 0,0
    readbw, readiops, readlatency = 0, 0,0

    print "cmd:", cmd
    try:
        templine = subprocess.check_output(cmd.split(";"))
        writetempline='END'.join(templine.split('\n'))
    except Exception as e:
        templine = None

    readmatch='read:'

    filedir='/usr/local/google/home/mzhuo/partner/testlog/mnt/vol31'
    cmd = "egrep;{};{}/{};-A;1".format(readmatch, filedir, matchfile)

    print "cmd:", cmd
    try:
        templine = subprocess.check_output(cmd.split(";"))
        readtempline='END'.join(templine.split('\n'))
    except Exception as e:
        templine = None
    
    print "this is line\n",writetempline, readtempline ,"====end of line\n\n"
    if writetempline:
       writeObj=re.search(r'write:\sIOPS=(\d*.*\d*k*),\sBW=(\d*.\d*)([M|K])iB.*END.*clat.*avg=(\d*.\d*).*END', writetempline)
    if readtempline:
       readObj=re.search(r'read:\sIOPS=(\d*.*\d*k*),\sBW=(\d*.\d*)([M|K])iB.*END.*clat.*avg=(\d*.\d*).*END', readtempline)
      # re.search(r'read:\sIOPS=(\d*.*\d*)(k*),\sBW=(\d*.\d*)([M|K])iB.*END.*clat.*avg=(\d*.\d*).*END', readtempline)
    if not writeObj and not readObj:
       print "error in extracting data"
       time.sleep(90)
    if writeObj and not readObj:
      print "start:",  writeObj.group() ,"****end"
      print "this is data\n"
      print writeObj.group(1), writeObj.group(2), writeObj.group(3), writeObj.group(4)
    #  time.sleep(10)
      writeiops=writeObj.group(1)
      writebw=writeObj.group(2)
      writebwunit=writeObj.group(3)
      writelatency=writeObj.group(4)
      print "value:",  writeiops,  "value:", writebw, "unit:", writebwunit, writelatency
      if 'k' in writeiops:
        writeiops=float(writeiops[0:-1])*1000
      if writebwunit is 'M':
         writebw=float(writebw)*1000
      print "value:",  writeiops,  "value:", writebw, "unit:", writebwunit, writelatency
       
    if readObj and not writeObj:
      print "start:",  readObj.group() ,"****end"

      print "this is data\n"
      print readObj.group(1), readObj.group(2),  readObj.group(3) , readObj.group(4)
      readiops=readObj.group(1)
      readbw=readObj.group(2)
      readbwunit=readObj.group(3)
      readlatency=readObj.group(4)
      if 'k' in readiops:
        readiops=float(readiops[0:-1])*1000
      if readbwunit is 'M':
         readbw=float(readbw)*1000
      print "%s %s %s %s".format(readiops, readbw, readbwunit, readlatency) 
    #  time.sleep(10)
    if readObj and writeObj:
       print "write start:",  writeObj.group() ,"****end"
       print "read start:",  readObj.group() ,"****end"

       print "this is data\n"

       writeiops=writeObj.group(1)
       writebw=writeObj.group(2)
       writebwunit=writeObj.group(3)
       writelatency=writeObj.group(4)
       print "value:",  writeiops,  "value:", writebw, "unit:", writebwunit, writelatency
       if 'k' in writeiops:
        writeiops=float(writeiops[0:-1])*1000
       if writebwunit is 'M':
         writebw=float(writebw)*1000
       print "value:",  writeiops,  "value:", writebw, "unit:", writebwunit, writelatency
       
 
       readiops=readObj.group(1)
       readbw=readObj.group(2)
       readbwunit=readObj.group(3)
       readlatency=readObj.group(4)
       if 'k' in readiops:
        readiops=float(readiops[0:-1])*1000
       if readbwunit is 'M':
         readbw=float(readbw)*1000
       print "%s %s %s %s".format(readiops, readbw, readbwunit, readlatency) 

    return str(writebw), str(writeiops), str(writelatency) , str(readbw), str(readiops),str( readlatency) 

def parsedate(iopattern, iodepth, ioblocksize, iofilesize, ionumjobs, logfile):
    filelist = os.listdir('/usr/local/google/home/mzhuo/partner/testlog/mnt/vol31')
    print filelist
    datadict = {}
    myfile = open(logfile, "a")
    for _pattern in iopattern:
      for _iodepth in  iodepth:
          for _blocksize in  ioblocksize:
             for _filesize in  iofilesize:
                 for _numjobs in  ionumjobs:
                     filename =  "fio.{}.{}.{}.{}.{}.*".format(_pattern, _iodepth, _blocksize, _filesize, _numjobs)
                     print filename
                     for _file in filelist:
                         if fnmatch.fnmatch(_file, filename):
                            matchfile = _file
                            print matchfile
                            dataresult=extractdata(logfile, matchfile)
                            print "dataresult", dataresult
                            print  ','.join(dataresult) 
                            totalbw=float(dataresult[0])+float(dataresult[3])
                            totaliops=float(dataresult[1])+float(dataresult[4])
                            if float(dataresult[2]) < 10:
                                  avelatency=float(dataresult[5])
                            elif float(dataresult[5]) < 10:
                                  avelatency=float(dataresult[2])
                            else:
                                  avelatency=(float(dataresult[2])+float(dataresult[5]))/2


                            msg2file="{}, {}, {}, {}, {}, {}, {}, {}, {}\n".format(_pattern,_iodepth, _blocksize, _filesize, _numjobs, ','.join(dataresult), totalbw, totaliops, avelatency)
                            datadict[(_pattern,_iodepth, _blocksize, _filesize, _numjobs)]=dataresult
                            print msg2file
                            myfile.write(msg2file)
                            continue
                       #  else:
                       #     time.sleep(10)
                       #     print "no file found"
                       #     exit
    for _value in datadict.keys():
                                print _value, datadict[_value]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-iopattern', '--file_for_CfM', default='write read randwrite randread readwrite randrw', dest='pattern')
    parser.add_argument('-iodepth', '--file_for_cmds', default='16 64 128 256 512', dest='iodepth')
    parser.add_argument('-blocksize', '--cfm_ipv4', default='4k 8k 16k 32k 64k', dest='blocksize')
    parser.add_argument('-filesize', '--command_line', default='1024M', dest='filesize')
    parser.add_argument('-numfiles', '--numoffiles', default='48', dest='numfiles')
    parser.add_argument('-logfile', '--log_file_dir', default='fio.test.log.txt', dest='logfile')
    args = parser.parse_args()
    pattern = args.pattern.split()
    iodepth = args.iodepth.split()
    blocksize = args.blocksize.split()
    filesize = args.filesize.split()
    numfiles = args.numfiles.split()
    logfile = args.logfile
    print pattern
    print iodepth
    print blocksize
    print filesize
    print numfiles
    print logfile
    parsedate(pattern, iodepth, blocksize, filesize, numfiles, logfile)

if __name__=='__main__':
    main()
