#!/usr/bin/env python

from google.cloud import bigquery
from google.cloud.bigquery import Dataset
import subprocess
import time
import json
import re

TESTNAMES=[
  "elfs-daily-e2e-lssd", "elfs-daily-e2e-pssd", "elfs-daily-e2e-phdd",  \
  "elfs-daily-io-lssd", "elfs-daily-io-pssd", "elfs-daily-io-phdd", \
  "elfs-perf-lssd", "elfs-perf-pssd", "elfs-perf-phdd", \
  "elfs-scalability-lssd", "elfs-scalability-pssd", "elfs-scalability-phdd", \
  "elfs-ha-lssd", "elfs-ha-pssd", "elfs-ha-phdd", \
  "elfs-demo-lssd-scale", "elfs-demo-phdd-scale", "elfs-demo-pssd-scale", \
  "elfs-ps-lssd", "elfs-ps-pssd", "elfs-ps-phdd" ]


DATASET = "storage_partner_test"
TABLE = "elastifile_test"
DTABLE = "elastifile_deployment_test"
ITABLE = "elastifile_io_test"

BUCKET="gs://cpe-performance-storage/test_result/"
NEWBUCKET="gs://cpe-performance-storage/test_result/backup/"

MAX_INDEX = "SELECT index FROM  {}.{} \
            order by index desc \
            LIMIT 1".format(DATASET, TABLE)


def query_bigquerytable(bq_client, bq_query):
    try:
        bq_query_job =bq_client.query(bq_query)  
        bq_query_result = bq_query_job.result()
    except Exception as e:
        print "big query fails"
        return [] 
    return bq_query_result



def new_test_result():
    listfile = 'gsutil ls {} '.format(BUCKET)
    output= subprocess.check_output(listfile.split()).splitlines()
    filelist = []
    for _line in output:
        if "elfs" in _line:
            filelist.append(_line)
    print filelist
    time.sleep(10)
    return filelist

def parser_fio_json_file(test_log_file):
    test_file = 'temp.json'
    cmd = 'sudo gsutil cp {} {}'.format(test_log_file, test_file)
    output = subprocess.check_output(cmd.split())
    try:
        with open(test_file) as f:
           test_result = json.load(f)
    except Exception as e:
        print "error in loading json"
        return []
    return [ test_result['jobs'][0]['job options']['bs'], test_result['global options']['iodepth'], True,  False, test_result['global options']['size'], 1, test_result['jobs'][0]['write']['bw'], test_result['jobs'][0]['write']['iops'], test_result['jobs'][0]['write']['clat']['mean'], test_result['jobs'][0]['read']['bw'], test_result['jobs'][0]['read']['iops'], test_result['jobs'][0]['read']['clat']['mean'], test_result['jobs'][0]['jobname']]



def get_baseline_data(baselinefile, test_io_type):
    #print baselinefile, test_io_type
    sdata=[]
    with open(baselinefile) as f:
         test_result = json.load(f)
    for result in test_result:
 #       print result['test_io_type'], test_io_type
        if result['test_io_type'] == test_io_type:
            sdata = [result['writebw'], result['writeiops'], result['writelatency'], result['readebw'], result['readiops'], result['readlatency']]
            break
    return sdata



def  compare_test_result(io_result, test_io_type):
     baseline = get_baseline_data('fio_baseline.json', test_io_type)
     if baseline:
        for i in [0, 1, 3, 4]:
          if io_result[i] < float(baseline[i])*0.2:
            return False
        for i in [2, 5]:
          if io_result[i] > float(baseline[i])*3:
            return False
     return True


def add_test_record(bigquery_client, dataset_ref, table_ref, dtable_ref, itable_ref, test_log_file, rindex):
    print "Prepare to add record with index :", rindex
    insert_row=False
    print test_log_file
    test_case_info = test_log_file.split('/')[-1].split('.')
    if not len(test_case_info) == 12:
        print "logfile is not able to exported to table"
#        time.sleep(5)
        #cmd = 'gsutil rm {} '.format(test_log_file)
        return rindex 
    if not test_case_info[0] in TESTNAMES:
       print "logfile is not able to exported to table"
#        time.sleep(5)
        #cmd = 'gsutil rm {} '.format(test_log_file)
       return rindex 

    print test_case_info
    testname=test_case_info[0]
    if 'elfs' in test_case_info:
        testpartner = 'Elastifile'
    else:
        testpartner='Elastifile'
    print testpartner    
    print test_case_info[0], test_case_info[0]
    if 'terraform' in test_case_info[1]:
        testcatagory = 'Provision_Test'
    elif '-ha-' in test_case_info[0]:
        testcatagory = 'High_Availability_Test'
    elif '-perf-' in test_case_info[0]:
        testcatagory = 'Performance_Test'
    elif '-stress-' in test_case_info[0]:
        testcatagory = 'Stress_Test'
    elif '-ps-' in test_case_info[0]:
        testcatagory = 'Post_Submit_Test'
    elif '-scalability-' in test_case_info[0]:
        testcatagory = 'Scalability_Test'
    elif 'daily-io' in test_case_info[0]:
        testcatagory = 'Daily_IO_Test'
    elif 'daily-e2e' in test_case_info[0]:
        testcatagory = 'Daily_E2E_Test'
    elif 'demo' in test_case_info[0]:
        testcatagory = "Standard_IO_Test"
    else:
        testcatagory = ''
    print testcatagory
    if 'fio' in test_case_info[1]:
        testiotype=test_case_info[2]
    testdut=test_case_info[3]
    testdisktype = test_case_info[10]
    testdate = '-'.join(test_case_info[4:7])
    testtime = ':'.join(test_case_info[7:10])
    print testdate, testtime

    eloadbalance = True
    estorage_scale = 'SMALL'
    estorage_region = 'us-east1-b'
    estorage_project = 'cpe-performance-storage'
    eservice_account = 'storage@cpe-performance-storage.iam.gserviceaccount.com'
    eservice_key = 'elastifile.json'
    ecluster = "{}-elsf".format(testdisktype)
    etotal_nodes=3
    enode_vm_type =  'custome'
    enode_vm_cpu = 4
    enode_vm_memory = 42
    eversion = 'elastifile-storage-2-7-5-12-ems'
    etotal_storage_size = '1G'
    eems_vm_type = 'n1-standard-1'
    eems_vm_cpu = 4
    eems_vm_memory = 15
    eems_vm_eip = ''
    eems_vm_iip = ''
    enum_disks_node = 3
    esize_disks_node = 175
    enodes_vm_eip = ''
    enodes_vm_iip = ''

    iio_tool = 'fio'
    iio_tool_ver = 'fio-3.2'
    iio_tool_cmd = 'na'
    iio_client_vm_type = 'n1-standard-1'
    iio_client_vm_cpu = '4'
    iio_client_vm_memory = '32'
    iio_client_vm_version = 'na'
    iio_client_vm_region  = 'us-east1-b'
    ivolume_name = 'DC01'
    ivolume_type = 'NFS'
    ivolume_server_ip =''
    ivolume_mount_cmd = 'mount -o nolock'

    deployment =  False
    iotest = False


    if "demo" in test_case_info[0]:
        if "lssd" in test_case_info[0]:
             eloadbalance = True
             estorage_scale = 'local'
             estorage_region = 'us-east1-b'
             estorage_project = 'cpe-performance-storage'
             eservice_account = 'storage@cpe-performance-storage.iam.gserviceaccount.com'
             eservice_key = 'elastifile.json'
             ecluster = "demo-{}-vm".format(testdisktype)
             etotal_nodes=3
             enode_vm_type =  'custome'
             enode_vm_cpu =16
             enode_vm_memory = 96
             eversion = 'elastifile-storage-2-7-5-12-ems'
             etotal_storage_size = '10.3TB'
             eems_vm_type = 'n1-standard-4'
             eems_vm_cpu = 4
             eems_vm_memory = 15
             eems_vm_eip = ''
             eems_vm_iip = ''
             enum_disks_node = 8
             esize_disks_node = 375

        elif "phdd" in test_case_info[0]:
             eloadbalance = True
             estorage_scale = 'standard'
             estorage_region = 'us-east1-b'
             estorage_project = 'cpe-performance-storage'
             eservice_account = 'storage@cpe-performance-storage.iam.gserviceaccount.com'
             eservice_key = 'elastifile.json'
             ecluster = "demo-{}-vm".format(testdisktype)
             etotal_nodes=4
             enode_vm_type =  'custome'
             enode_vm_cpu = 6
             enode_vm_memory = 64
             eversion = 'elastifile-storage-2-7-5-12-ems'
             etotal_storage_size = '33.7TB'
             eems_vm_type = 'n1-standard-4'
             eems_vm_cpu = 4
             eems_vm_memory = 15
             eems_vm_eip = ''
             eems_vm_iip = ''
             enum_disks_node = 4
             esize_disks_node = 1000
        else:
             eloadbalance = True
             estorage_scale = 'large'
             estorage_region = 'us-east1-b'
             estorage_project = 'cpe-performance-storage'
             eservice_account = 'storage@cpe-performance-storage.iam.gserviceaccount.com'
             eservice_key = 'elastifile.json'
             ecluster = "demo-{}-vm".format(testdisktype)
             etotal_nodes=3
             enode_vm_type = 'custome'
             enode_vm_cpu = 16
             enode_vm_memory = 96
             eversion = 'elastifile-storage-2-7-5-12-ems'
             etotal_storage_size = '69.4TB'
             eems_vm_type = 'n1-standard-4'
             eems_vm_cpu = 4
             eems_vm_memory = 15
             eems_vm_eip = ''
             eems_vm_iip = ''
             enum_disks_node = 8
             esize_disks_node = 2500



    if "terraform" in test_log_file:
        test_file = 'temp.log'
        cmd = 'sudo gsutil cp {} {}'.format(test_log_file, test_file)
        try:
            output = subprocess.check_output(cmd.split())
        except:
            print "error "
        ffile = open(test_file, 'r')
        fileoutput =  ffile.read()
        ffile.close()
        cmd = 'sudo rm -rf {}'.format(test_file)
        subprocess.check_output(cmd.split())

        #print fileoutput
        if 'create_instances_job Complete' in fileoutput:
            teststatus = True
        else:
            teststatus = False
        deployment = True
        insert_row = True
    elif "fio" in test_log_file:
        io_result = parser_fio_json_file(test_log_file)
        if io_result:
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
           itest_io_type = io_result[12].split('.')[0]
           print itest_io_type
           teststatus = compare_test_result(io_result[6:12], itest_io_type)
           if not teststatus:
               print "test failure detected, fail to parse testlog file {}".format(test_log_file)
           iotest = True
           insert_row = True
    else:
        insert_row = False
    if insert_row:
       table = bigquery_client.get_table(table_ref)  # API call
       row_to_insert = [
          (rindex, testname, testpartner, testcatagory, test_log_file, teststatus, testdate, testtime, testdut, testdisktype),
       ]
       try:
           errors = bigquery_client.insert_rows(table, row_to_insert)  # API request
       except Exception as e:
           print "failure in inserting row"
           rindex  = rindex - 1

       if not iotest:
           dtable = bigquery_client.get_table(dtable_ref)  # API call
           row_to_insert = [
               (rindex, testname, testpartner ,  \
               ecluster, eversion, testdisktype, eloadbalance, \
               estorage_scale, estorage_region, estorage_project, \
               eservice_account, eservice_key, etotal_storage_size,\
               eems_vm_type, eems_vm_cpu, eems_vm_memory, eems_vm_eip, eems_vm_iip, \
               etotal_nodes, enode_vm_type, enode_vm_cpu, enode_vm_memory, \
               enum_disks_node, esize_disks_node, enodes_vm_eip, enodes_vm_iip, testdut),
           ]
           try:
               errors = bigquery_client.insert_rows(dtable, row_to_insert)  # API request
           except Exception as e:
               print "failure in inserting row"
               rindex  = rindex - 1

       else:
           itable = bigquery_client.get_table(itable_ref)  # API call
           row_to_insert = [
               (rindex, testname, testpartner,  \
                iio_tool, iio_tool_ver, iio_tool_cmd, iio_client_vm_type, \
                iio_client_vm_cpu, iio_client_vm_memory, iio_client_vm_version, \
                iio_client_vm_region, ivolume_name , ivolume_type, ivolume_server_ip, \
                ivolume_mount_cmd, itest_io_type, itest_io_blocksize, itest_io_qdepth, \
                itest_io_direct, itest_io_check, itest_io_file_size, itest_io_file_number, \
                iwritebw,iwriteiops , iwritelatency, ireadbw, ireadiops, ireadlatency,testdisktype, testdut),
           ]
           try:
              errors = bigquery_client.insert_rows(itable, row_to_insert)  # API request
           except Exception as e:
              print "failure in inserting row"
              rindex  = rindex - 1
       rindex = rindex + 1
       print rindex, "<====increase index by 1"
    print "new index", rindex   
    return rindex

def populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, rindex):
    new_test_files = new_test_result()
    for _test_file in new_test_files:
        rindex = add_test_record(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, _test_file, rindex)
        new_dir = NEWBUCKET
        nfile = _test_file.split('/')[-1]
        #time.sleep(300)
        print _test_file, _test_file[-1]
    #    time.sleep(10)
    #    print [ _test_file[-1] == '/']
    #    time.sleep(10)
    #    if not [ _test_file[-1] == '/']:
        cmd = 'gsutil mv {} {}{}'.format(_test_file, new_dir, nfile)
        print cmd
        output= subprocess.check_output(cmd.split()).splitlines()
   #     time.sleep(20)   
    return rindex

def main():
    bqclient = bigquery.Client().from_service_account_json('bqe.json')
    dataset_id = DATASET
    dataset_ref = bqclient.dataset(dataset_id)
    dtable_ref = dataset_ref.table(DTABLE)
    itable_ref = dataset_ref.table(ITABLE)
    table_ref = dataset_ref.table(TABLE)

    rindex = 0
    query_device_result = query_bigquerytable(bqclient, MAX_INDEX)
    #print "Max index query: ", MAX_INDEX, query_device_result
    for _record in query_device_result:
        rindex = _record.index
        print "max index is ", rindex
        break
    rindex = rindex + 1
    while True:
        rindex = populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, itable_ref, rindex)
        time.sleep(60)


if __name__ == '__main__':
    main()

