#!/usr/bin/env python

import sys
import pexpect
import os
import argparse
import subprocess
from subprocess import call
import re
import time

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

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('-cfmfile', '--file_for_CfM', dest='cfmfile')
    parser.add_argument('-cmdfile', '--file_for_cmds', dest='cmdfile')
    parser.add_argument('-cfm', '--cfm_ipv4', dest='cfm')
    parser.add_argument('-cmd', '--command_line', dest='cmd')
    parser.add_argument('-logfile', '--log_file_dir', dest='logfile')
    args = parser.parse_args()

    if not args.logfile:
       logfile = ' '
    else:
       logfile = args.logfile
    if args.cfmfile and args.cmdfile:
        run_cmds_on_cfms(args.cfmfile, args.cmdfile, logfile)
    elif args.cfm and args.cmd:
        while True:
            run_cmd_on_cfm(args.cfm, args.cmd, logfile)
    elif args.cfm and args.cmdfile:
        run_cmds_on_cfm(args.cfm, args.cmdfile, logfile)
    elif args.cfmfile and args.cmd:
        run_cmd_on_cfms(args.cfmfile, args.cmd, logfile)
    else:
        print('Usage:checkset.py -cfmfile cfm_file -cmdfile cmd_file')
        print('Usage:checkset.py -cfm mgmt_ipv4_cfm -cmdfile cmd_file')
        print('Usage:checkset.py -cfm mgmt_ipv4_cfm -cmd <cli>')
        print('Usage:checkset.py -cfmfile cfm_file -cmd <cli>')

if __name__=='__main__':
    main()
