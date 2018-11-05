#!/usr/bin/env python

from google.cloud import bigquery
from google.cloud.bigquery import Dataset
import subprocess
import time
from datetime import datetime, timedelta
from datetime_truncate import truncate
from pytz import timezone
import json
import re

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
PST_ZONE = timezone('US/Pacific')
REMOVETZ = -6
QUERYWINDOW = 1200
TOTAL_MSG_PER_DAY = int(144*0.99)

DATASET = "storage_partner_test"
TABLE = "elastifile_test"
DTABLE = "elastifile_deployment_test"
ITABLE = "elastifile_io_test"
BTABLE = "elastifile_baseline_table"
#TINDEX = 0
#DINDEX = 0
#IINDEX = 0

BUCKET="gs://cpe-performance-storage/test_result"


HEADER_FILE  = "header.template.html"
FOOTER_FILE = "footer.template.html"
INDEX_TABLE_FILE = "index.table.template.html"
REGISTRY_TABLE_FILE = "registry.table.template.html"
DEVICE_TABLE_FILE = "device.table.template.html"
MESSAGE_TABLE_FILE = "message.table.template.html"

INDEX_HTML_FILE = "index.html"

   
DEVICE_QUERY = "select project, registry, devicename from {} \
                group by project, registry, devicename \
                order by project, registry, devicename".format(TABLE)
DEVICE_MSG_COUNT = "select count(devicename) as count, project, registry,\
                    devicename from {} \
                    group by project, registry, devicename \
                    ORDER by count(devicename) DESC, project, registry, devicename DESC".format(TABLE)
DEVICE_NUM_PROJECT_REGISTRY = "select project, registry, count(devicename) as count from ( \
                               select registry, project, devicename  FROM {} \
                               group by project, registry, devicename \
                               ) \
                               group by project, registry \
                               order by count".format(TABLE)


IOT_DEVICES_INFO = {}
IOT_DEVICES_LIST = []
new_files_list = []

def new_test_result():
    listfile = 'gsutil ls {}'.format(BUCKET)
    output= subprocess.check_output(listfile.split()).splitlines()
    return output

def parser_fio_json_file(test_log_file):
    test_file = 'temp.json'
    cmd = 'sudo gsutil cp {} {}'.format(test_log_file, test_file)
    print cmd
    output = subprocess.check_output(cmd.split())
    with open(test_file) as f:
         test_result = json.load(f)
    print test_result
    return [ test_result['jobs'][0]['job options']['bs'], test_result['global options']['iodepth'], True,  False, test_result['global options']['size'], 1, test_result['jobs'][0]['write']['bw'], test_result['jobs'][0]['write']['iops'], test_result['jobs'][0]['write']['clat']['mean'], test_result['jobs'][0]['read']['bw'], test_result['jobs'][0]['read']['iops'], test_result['jobs'][0]['read']['clat']['mean'], test_result['jobs'][0]['jobname']]



def get_baseline_data(baselinefile, test_io_type):
    print baselinefile, test_io_type
    sdata=[]
    with open(baselinefile) as f:
         test_result = json.load(f)
    print "this is baseline", test_result
    print "good"
    for result in test_result:
      print result['test_io_type'], test_io_type  
      if result['test_io_type'] == test_io_type:
         sdata = [result['writebw'], result['writeiops'], result['writelatency'], result['readebw'], result['readiops'], result['readlatency']]
         break
    print sdata, "<<<<"
    return sdata



def compare_test_result(io_result, test_io_type):
     baseline = get_baseline_data('fio_baseline.json', test_io_type)
     print "baseline", baseline
     print io_result, 
     print len(baseline), len(io_result)
     if baseline:
        for i in [0, 1, 3, 4]:
          if io_result[i] < float(baseline[i])*0.9:
            return False
        for i in [2, 5]:
          if io_result[i] > float(baseline[i])*1.1:
            return False
        print "test io fail", io_result
     return True     
     

def add_test_record(bigquery_client, dataset_ref, table_ref, dtable_ref, itable_ref, test_log_file, TINDEX):
    deployment_file = 'create_vheads'
    native_io_file = 'elastifile'
    another_one = 'elfs'
    insert_row = False 
    test_status = ''
    print test_log_file
    rDATE=''
    rTIME=''
    file_pattern = 'el[a-z]*.fio.[a-z]+.([\d]+.[\d]+.[0-9]+).([0-9]+.[0-9]+.[0-9]+)'
    pattern = re.compile(file_pattern)
    m = pattern.findall(test_log_file)
    if m:
       rDATE=m[0][0]
       rTIME=m[0][1]
    test_file = 'temp.log'
    efile_pattern = 'create_vheads.[a-z0-9-]+.([0-9]+).log'
    pattern = re.compile(efile_pattern)
    m = pattern.findall(test_log_file)
    if m:
       rDATE=m[0]
       rTIME=''
    print "check",  rDATE, "time:",  rTIME, type(rDATE), type(rTIME)
    #time.sleep(10)

    type_pattern = 'el[a-z]+.fio.([a-z]+).[\d]+.[\d]+.[0-9]+.[0-9]+.[0-9]+.[0-9]+'
    pattern = re.compile(type_pattern)
    m = pattern.findall(test_log_file)
    if m:
        itest_io_type = m[0]
    else:
        itest_io_type = ''


    estorage_type = 'HDD'
    eloadbalance = True
    estorage_scale = 'SMALL'
    estorage_region = 'us-east1-b'
    estorage_project = 'cpe-performance-storage'
    eservice_account = 'storage@cpe-performance-storage.iam.gserviceaccount.com'
    eservice_key = 'elastifile.json'
    ecluster = 'test-elastifile-storage'
    etotal_nodes=3
    enode_vm_type =  'custome'
    enode_vm_cpu = 4
    enode_vm_memory = 32
    eversion = 'elastifile-storage-2-7-5-6-ems'
    etotal_storage_size = '1G'
    eems_vm_type = 'n1-standard-4'
    eems_vm_cpu = 4
    eems_vm_memory = 15
    eems_vm_eip = '10.142.0.5'
    eems_vm_iip = '35.237.71.114'
    enum_disks_node = 3
    esize_disks_node = 175
    enodes_vm_eip = '10.142.0.6, 10.142.0.7, 10.142.0.8'
    enodes_vm_iip = ''



  
    iio_tool = 'fio'
    iio_tool_ver = 'fio-3.2'
    iio_tool_cmd = 'na'
    iio_client_vm_type = 'n1-standard-4'
    iio_client_vm_cpu = '4'
    iio_client_vm_memory = '32'
    iio_client_vm_version = 'na'
    iio_client_vm_region  = 'us-east1-b'
    ivolume_name = 'ZMDATA'
    ivolume_type = 'NFS'
    ivolume_server_ip ='10.142.0.6'
    ivolume_mount_cmd = 'mount -o nolock'
    deployment =  False
    iotest = False
    test_type = ''

    if deployment_file in test_log_file:
        test_type = "Elastifile_Provision_Test"
        cmd = 'sudo gsutil cp {} {}'.format(test_log_file, test_file)
        print cmd
        output = subprocess.check_output(cmd.split())
        print output, len(output)

        ffile = open(test_file, 'r')
        fileoutput =  ffile.read()
        ffile.close()
        cmd = 'sudo rm -rf {}'.format(test_file)
        print cmd
        subprocess.check_output(cmd.split())

        #print fileoutput
        if 'Apply complete' in fileoutput:
            test_status = True
            print "test pass"
        else:
            test_status = False
            print "test fails"
        test_name = 'elastifile_provision'
        deployment = True
        insert_row = True 
    elif native_io_file in test_log_file or another_one in test_log_file:
        io_result = parser_fio_json_file(test_log_file)
        for _result in io_result:
            print _result
        itest_io_blocksize = io_result[0]
        itest_io_qdepth = int(io_result[1])
        itest_io_direct = io_result[2]
        itest_io_check = io_result[3]
        itest_io_file_size = io_result[4]
        itest_io_file_number = int(io_result[5])
        iwritebw =  str(io_result[6])
        iwriteiops = str(io_result[7])
        iwritelatency = str(io_result[8])
        ireadbw =  str(io_result[9])
        ireadiops = str(io_result[10])
        ireadlatency = str(io_result[11])
        itest_io_type = io_result[12]
        test_status = compare_test_result(io_result[6:12], itest_io_type)
        if not test_status:
             print "test failure detected"
        #     time.sleep(10)
        test_type = "Elastifile_Native_IO_Test"
        test_name = 'elastifile_io'
        print test_type, test_status, test_name
        iotest = True
        insert_row = True
    else:
        insert_row = False
    print "insert ?", insert_row    
    if insert_row:
       print test_status, test_type, TINDEX
       table = bigquery_client.get_table(table_ref)  # API call
       print "table", table, table.table_id
       row_to_insert = [
          (TINDEX, test_name, u'Elastifile', test_type, test_log_file, test_status, rDATE, rTIME), 
         # rDATE, rTIME),
       ]
       print row_to_insert
       errors = bigquery_client.insert_rows(table, row_to_insert)  # API request
       assert errors == []
       print "table 1" 
       if not iotest:
           dtable = bigquery_client.get_table(dtable_ref)  # API call
           print "table", dtable, dtable.table_id
           row_to_insert = [
               (TINDEX, test_name, u'Elastifile' ,  \
               ecluster, eversion, estorage_type, eloadbalance, \
               estorage_scale, estorage_region, estorage_project, \
               eservice_account, eservice_key, etotal_storage_size,\
               eems_vm_type, eems_vm_cpu, eems_vm_memory, eems_vm_eip, eems_vm_iip, \
               etotal_nodes, enode_vm_type, enode_vm_cpu, enode_vm_memory, \
               enum_disks_node, esize_disks_node, enodes_vm_eip, enodes_vm_iip),
           ]
           print row_to_insert
           errors = bigquery_client.insert_rows(dtable, row_to_insert)  # API request
           assert errors == []
           print "table 2"
       else:    
           itable = bigquery_client.get_table(itable_ref)  # API call
           print "table", itable, itable.table_id
           row_to_insert = [
               (TINDEX, test_name, u'Elastifile',  \
                iio_tool, iio_tool_ver, iio_tool_cmd, iio_client_vm_type, \
                iio_client_vm_cpu, iio_client_vm_memory, iio_client_vm_version, \
                iio_client_vm_region, ivolume_name , ivolume_type, ivolume_server_ip, \
                ivolume_mount_cmd, itest_io_type, itest_io_blocksize, itest_io_qdepth, \
                itest_io_direct, itest_io_check, itest_io_file_size, itest_io_file_number, \
                iwritebw,iwriteiops , iwritelatency, ireadbw, ireadiops, ireadlatency),
           ]   

           print row_to_insert
           errors = bigquery_client.insert_rows(itable, row_to_insert)  # API request
           assert errors == []
           print "table 3"

       TINDEX = TINDEX + 1
    return TINDEX




def populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, TINDEX):
    new_test_files = new_test_result()
    for _test_file in new_test_files:
        print _test_file, len(_test_file)
        TINDEX = add_test_record(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, _test_file, TINDEX)
        new_dir = 'gs://cpe-performance-storage/test_result/backup/'
        nfile = _test_file.split('/')[-1]
        print nfile, _test_file
        cmd = 'gsutil mv {} {}{}'.format(_test_file, new_dir, nfile)
        print cmd
        output= subprocess.check_output(cmd.split()).splitlines()




def zip_file(zip_file_name):
    print "files t0 be passed", new_files_list
    cmd = "tar -cvf {} {}".format(zip_file_name, ' '.join(new_files_list))
    print cmd
    subprocess.check_output(cmd.split())


def query_bigquerytable(bq_client, bq_query):
    try:
        bq_query_job =bq_client.query(bq_query)  
        bq_query_result = bq_query_job.result()
    except Exception as e:
        print "big query fails"
        return [] 
    return bq_query_result


def copy_template_file_html_file(template, html_file):
    copyfile  = "sudo cp {} {}".format(template, html_file)
    subprocess.check_output(copyfile.split())


def append_template_file_html_file(template, html_file):
    source_file = open(template, 'r')
    dest_file = open(html_file, 'a+')
    dest_file.write(source_file.read())
    source_file.close()
    dest_file.close()


def append_lines_html_file(lines, html_file):
    dest_file = open(html_file, 'a+')
    dest_file.write(lines)
    dest_file.close()


def replace_strings_by_strings_file(old_string, new_string, new_file):
    dest_file = open(new_file, 'r')
    newtext = dest_file.read().replace(old_string, new_string)
    dest_file.close()
    dest_file = open(new_file, 'w')
    dest_file.write(newtext)
    dest_file.close()

def convert_time_from_utc_to_pst(now_utc):
    # Convert to US/Pacific time zone
    new_tz = now_utc.astimezone(timezone('US/Pacific'))
    return new_tz.strftime(TIMEFORMAT)

 
def time_is_close(current_time, check_time):
    timedelta = datetime.strptime(current_time, TIMEFORMAT) - datetime.strptime(check_time, TIMEFORMAT)
    timediff = timedelta.days * 24 * 3600 + timedelta.seconds
    return  int(timediff) < int(QUERYWINDOW)

def query_device_summary_by_date(bqclient, project, registry, device):
    querydevicesummary = "select count(index) as count,devicename, system, machine, version, release, year, month, day from  ( \
                          SELECT index, devicename, machine, system, version, release, psttime,  \
                          EXTRACT(YEAR FROM psttime) as year, EXTRACT(MONTH FROM psttime) as month, \
                          EXTRACT(DAY FROM psttime) as day \
                          FROM ( \
                          select index, devicename, machine, system, version, release, timestamp, \
                          TIMESTAMP(DATETIME(timestamp,\"America/Los_Angeles\")) as psttime \
                          from {} where project=\"{}\" and  \
                          registry=\"{}\" and \
                          devicename=\"{}\") \
                          group by index, devicename, machine, system, version, release, timestamp, psttime \
                          order by psttime DESC ) \
                          group by devicename, system, machine, version, release, year, month, day \
                          order by year DESC, month DESC, day DESC".format(TABLE, project, registry, device)   
 #   print querydevicesummary
    result =  query_bigquerytable(bqclient, querydevicesummary)
    return result      

def query_device_msg_detail_by_date(bqclient, project, registry, devicename, date):
    qyear = int(date.split('.')[0])
    qmonth = int(date.split('.')[1])
    qday = int(date.split('.')[2])

    querydevicemsgperday = "select  index, devicename, machine, system, version, release, psttime, year, month, day from (SELECT index, devicename, machine, system, version, release, psttime, EXTRACT(YEAR FROM psttime) as year, EXTRACT(MONTH FROM psttime) as month, EXTRACT(DAY FROM psttime) as day FROM (select index, devicename, machine, system, version, release, timestamp, TIMESTAMP(DATETIME(timestamp,\"America/Los_Angeles\")) as psttime from {} \
                           where project=\"{}\" and registry=\"{}\" and devicename=\"{}\") )\
                           where year={}  and month={}  and day= {} group by index, devicename, machine, system, version, release, psttime, year, month, day   order by psttime DESC".format(TABLE, project, registry, devicename, qyear, qmonth, qday) 
    #print querydevicemsgperday

    result =  query_bigquerytable(bqclient, querydevicemsgperday)
    #print result
    return result


def generate_device_msg_detail_html(bqclient, project, registry, devicename, date):
    dst_file = "{}.{}.{}.{}.html".format(project, registry, devicename, date)
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(MESSAGE_TABLE_FILE, dst_file)
    query_result = query_device_msg_detail_by_date(bqclient, project, registry, devicename, date)
    for each_device in query_result:
        index = each_device.index
        device = each_device.devicename.strip()
        machine = each_device.machine.strip()
        system = each_device.system.strip()
        version = each_device.version.strip()
        release = each_device.release.strip()
        timestamp = str(each_device.psttime)[:-6]
     
        append_lines_html_file("<tr>\n", dst_file)
        line = "<td>{}</td>\n".format(index)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(device)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(machine)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(system)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(version)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(release)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(timestamp)
        append_lines_html_file(line, dst_file)

    append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    replace_strings_by_strings_file("12345678", project, dst_file)
    replace_strings_by_strings_file("87654321", registry, dst_file)

    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())
    new_files_list.append(dst_file)
    #print new_files_list


def generate_device_summary_html(bqclient, project, registry, device, dst_file):
    timestamp = datetime.now(PST_ZONE)
    querytime = timestamp.replace(microsecond=0).isoformat(' ')[:REMOVETZ]
    print querytime
    query_result = query_device_summary_by_date(bqclient, project, registry, device)
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(DEVICE_TABLE_FILE, dst_file)
    index = 0
    for each_device in query_result:
        #print each_device
        device = each_device.devicename.strip()
        machine = each_device.machine.strip()
        system = each_device.system.strip()
        version = each_device.version.strip()
        release = each_device.release.strip()
        count = each_device.count
        cmonth  = int(each_device.month)
        cday = int(each_device.day)
        if cmonth < 10: 
           cmonth = "0{}".format(str(cmonth))
        if cday < 10:
           cday = "0{}".format(str(cday))

        day = "{}-{}-{}".format( each_device.year, cmonth, cday)

        if index == 0:
            print str(day), str(querytime)
            if str(day) in str(querytime):
                print "still on going"
                status = "In Progress"
                status_line = "<td class=\"green\">{}</td>\n".format(status)
            else:
                print "finished the current date"
                if (int(count) > TOTAL_MSG_PER_DAY):
                    status = "Pass"
                    status_line = "<td class=\"green\">{}</td>\n".format(status)

                else:
                    status = "Fail"
                    status_line = "<td class=\"red\">{}</td>\n".format(status)
        else:
             if (int(count) > TOTAL_MSG_PER_DAY):
                status = "Pass"
                status_line = "<td class=\"green\">{}</td>\n".format(status)
             else:
                status = "Fail"
                status_line = "<td class=\"red\">{}</td>\n".format(status)

        append_lines_html_file("<tr>\n", dst_file)
        line = "<td>{}</td>\n".format(device)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(machine)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(system)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(version)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(release)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(count)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(day)
        append_lines_html_file(line, dst_file)
        append_lines_html_file(status_line, dst_file)  
        daystring = str(day).split()[0].split('-')
          
        href = "<a href=\"{}.{}.{}.{}.{}.{}.html\">".format(project, \
                registry, device, int(daystring[0]), int(daystring[1]), int(daystring[2]))
        href_line = "<td>{}Messages</a></td>\n".format(href)
        append_lines_html_file(href_line, dst_file)
  
        index = index + 1
   
    append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)

    replace_strings_by_strings_file("12345678", project, dst_file)
    replace_strings_by_strings_file("87654321", registry, dst_file)

    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())
    new_files_list.append(dst_file)
    #print new_files_list

 

def generate_index_html(bqclient, dst_file):
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(INDEX_TABLE_FILE, dst_file)
    query_device_result = query_bigquerytable(bqclient, DEVICE_NUM_PROJECT_REGISTRY)
    print DEVICE_NUM_PROJECT_REGISTRY
    print "query_result: ", query_device_result
    for each_registry in query_device_result:
        append_lines_html_file("<tr>\n", dst_file)

        project = each_registry.project.strip()
        line = "<td>{}</td>\n".format(project)
        append_lines_html_file(line, dst_file)

        registry = each_registry.registry.strip()
        line = "<td>{}</td>\n".format(registry)
        append_lines_html_file(line, dst_file)

        devicecount = each_registry.count
        href = "<a href=\"{}.{}.html\">".format(project, registry)
        line = "<td>{}{}</a></td>\n".format(href, devicecount)
        append_lines_html_file(line, dst_file)

        device_registry_file = "{}.{}.html".format(project, registry)
        generate_summary_project_registry(bqclient, project, registry, device_registry_file)

    append_template_file_html_file(FOOTER_FILE, dst_file)
    copyfile  = "sudo  cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())



def generate_summary_project_registry(bqclient, project, registry, dst_file):
    iot_device_index = 1
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(REGISTRY_TABLE_FILE, dst_file)
    DEVICE_MSG_COUNT = "select count(index) as count, \
                    devicename from {} \
                    where project=\"{}\" and registry=\"{}\" \
                    group by devicename  \
                    ORDER by  devicename DESC".format(TABLE, project, registry)

    query_device_result = query_bigquerytable(bqclient, DEVICE_MSG_COUNT)
    print DEVICE_MSG_COUNT
    print query_device_result
    # generate table for all devices
    for each_device in query_device_result:
        append_lines_html_file("<tr>\n", dst_file)

        line = "<td>{}</td>\n".format(project)
        append_lines_html_file(line, dst_file)

        line = "<td>{}</td>\n".format(registry)
        append_lines_html_file(line, dst_file)

        devicename = each_device.devicename.strip()
        href = "<a href=\"{}.{}.{}.html\">".format(project, registry, devicename)
        line = "<td>{}{}</a></td>\n".format(href, devicename)
    #print line
        append_lines_html_file(line, dst_file)
        
        count = each_device.count
        line = "<td>{}</td>\n".format(count)
        append_lines_html_file(line, dst_file)
    
        timestamp = datetime.now(PST_ZONE)
        querytime = timestamp.replace(microsecond=0).isoformat(' ')[:REMOVETZ]
        line = "<td>{}</td>\n".format(querytime)
        append_lines_html_file(line, dst_file)

        last_mgr_query = "select project, registry, devicename, timestamp \
                          from {}  \
                          WHERE project=\"{}\" and registry=\"{}\" \
                          and devicename=\"{}\" \
                          ORDER by timestamp DESC Limit 1".format(TABLE, project,\
                          registry, devicename)
        last_msg_device = query_bigquerytable(bqclient, last_mgr_query)
        for _last_msg_device in last_msg_device:
            last_msg_timestamp = _last_msg_device.timestamp
        new_tz = convert_time_from_utc_to_pst(last_msg_timestamp)  
        line = "<td>{}</td>\n".format(new_tz)
        append_lines_html_file(line, dst_file)
    
        if time_is_close(querytime, new_tz):
            device_state = "ONLINE"
            line = "<td class=\"green\">{}</td>\n".format(device_state)
        else:
            device_state = "OFFLINE"
            line = "<td class=\"red\">{}</td>\n".format(device_state) 
        append_lines_html_file(line, dst_file)

        append_lines_html_file("</tr>\n\n", dst_file)
    #    append_template_file_html_file(FOOTER_FILE, dst_file)
    #    copyfile  = "gsutil cp {} gs://iot_html_report/{}".format(dst_file, dst_file)
    #    subprocess.check_output(copyfile.split())
        new_files_list.append(dst_file)
        #print new_files_list
        currentHourDateTime =  last_msg_timestamp -  timedelta(hours = 7)
        msg_current_day = "{}.{}.{}".format(currentHourDateTime.year, currentHourDateTime.month, currentHourDateTime.day)
        pervious_day = datetime.now(PST_ZONE) - timedelta(days = 1)
        msg_last_day = "{}.{}.{}".format(pervious_day.year, pervious_day.month, pervious_day.day)
        IOT_DEVICES_INFO["index"] = iot_device_index 
        IOT_DEVICES_INFO["project"] = project
        IOT_DEVICES_INFO["registry"] = registry
        IOT_DEVICES_INFO["devicename"] = devicename
        IOT_DEVICES_INFO["device_summary_page"] = "{}.{}.{}.html".format(project, registry, devicename)
        IOT_DEVICES_INFO["device_detail_page"] = "{}.{}.{}.{}.html".format(project, registry, devicename, msg_current_day)        
        IOT_DEVICES_INFO["device_last_detail_page"] = "{}.{}.{}.{}.html".format(project, registry, devicename, msg_last_day)
        IOT_DEVICES_INFO["device_state"] = device_state
        IOT_DEVICES_LIST.append(IOT_DEVICES_INFO)
  
        iot_device_index = iot_device_index + 1
        generate_device_summary_html(bqclient, project, registry, devicename, "{}.{}.{}.html".format(project, registry, devicename))
        generate_device_msg_detail_html(bqclient, project, registry, devicename, msg_current_day)
        if int(currentHourDateTime.hour) < 0 and int(currentHourDateTime.min) < 10:
           generate_device_msg_detail_html(bqclient, project, registry, devicename, msg_last_day)
        #print IOT_DEVICES_LIST
    append_template_file_html_file(FOOTER_FILE, dst_file)
    append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    copyfile  = "sudo  cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())
    new_files_list.append(dst_file)

def main():
    bqclient = bigquery.Client().from_service_account_json('bqe.json')
    dataset_id = DATASET 
    dataset_ref = bqclient.dataset(dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = 'US'
    dataset = bqclient.create_dataset(dataset)
    assert dataset.dataset_id == DATASET


    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('status', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('logfile', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('disktype', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('testrunner', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('date', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('time', 'STRING', mode='NULLABLE')
    ]
    table_ref = dataset_ref.table(TABLE)
    table = bigquery.Table(table_ref, schema=schema)
    table = bqclient.create_table(table)  # API request
    print('table {} created.'.format(table.table_id))
    assert table.table_id == TABLE


    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('cluster', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('version', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('total_nodes', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('disktype', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('loadbalance', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('scale', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('failure_tolerate', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('project', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('region', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('total_size', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('ems_vm_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('ems_vm_cpu', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('ems_vm_memory', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('node_vm_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('node_vm_cpu', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('node_vm_memory', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('num_disks', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('disk_size', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('client_name', 'STRING', mode='NULLABLE'),
    ]

    dtable_ref = dataset_ref.table(DTABLE)
    dtable = bigquery.Table(dtable_ref, schema=schema)
    dtable = bqclient.create_table(dtable)  # API request
    print('table {} created.'.format(dtable.table_id))
    assert dtable.table_id == DTABLE

    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('disktype', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_tool', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_tool_ver', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_tool_cmd', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_name', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_cpu', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_memory', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_version', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_project', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_region', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('volume_name', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('volume_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('volume_mount_cmd', 'STRING', mode='NULLABLE'),

            bigquery.SchemaField('test_io_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_blocksize', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_qdepth', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('test_io_direct', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('test_io_check', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('test_io_file_size', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_file_number', 'INTEGER', mode='NULLABLE'),


            bigquery.SchemaField('writebw', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('writeiops', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('writelatency', 'STRING', mode='NULLABLE'),

            bigquery.SchemaField('readbw', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('readiops', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('readlatency', 'STRING', mode='NULLABLE'),
    ]
    itable_ref = dataset_ref.table(ITABLE)
    itable = bigquery.Table(itable_ref, schema=schema)
    itable = bqclient.create_table(itable)  # API request
    print('table {} created.'.format(itable.table_id))
    assert itable.table_id == ITABLE

    btable_ref = dataset_ref.table(BTABLE)
    btable = bigquery.Table(btable_ref, schema=schema)
    btable = bqclient.create_table(btable)  # API request
    print('table {} created.'.format(btable.table_id))
    assert btable.table_id == BTABLE




    TINDEX = 0 

#    populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, TINDEX)

if __name__ == '__main__':
    main()

