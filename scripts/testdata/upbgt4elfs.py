#!/usr/bin/env python

from google.cloud import bigquery
from google.cloud.bigquery import Dataset
import subprocess
import time
import json
import re
from pytz import timezone

TESTNAMES=[
  "elfs-daily-e2e-lssd", "elfs-daily-e2e-pssd", "elfs-daily-e2e-phdd",  \
  "elfs-daily-io-lssd", "elfs-daily-io-pssd", "elfs-daily-io-phdd", \
  "elfs-perf-lssd", "elfs-perf-pssd", "elfs-perf-phdd", \
  "elfs-scalability-lssd", "elfs-scalability-pssd", "elfs-scalability-phdd", \
  "elfs-ha-lssd-node", "elfs-ha-pssd-node", "elfs-ha-phdd-node", \
  "elfs-ha-lssd-disk", "elfs-ha-pssd-disk", "elfs-ha-phdd-disk", \
  "longitivity-lssd-scalability", "longitivity-pssd-scalability", \
  "longitivity-phdd-scalability", \
  "longitivity-lssd-single", "longitivity-pssd-single",\
  "longitivity-phdd-single", \
  "elfs-ps-lssd", "elfs-ps-pssd", "elfs-ps-phdd" ]


DATASET = "cloud_partner_test_new"
TABLE = "partner_test"
DTABLE = "elastifile_deployment_test"
ITABLE = "elastifile_io_test"
BTABLE = "elastifile_baseline_table"


BUCKET="gs://cpe-performance-storage/test_result/backup"
NEWBUCKET="gs://cpe-performance-storage/test_result/backup/backup"

MAX_INDEX = "SELECT index FROM  {}.{} \
            order by index desc \
            LIMIT 1".format(DATASET, TABLE)


TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
PST_ZONE = timezone('US/Pacific')

testinfo = {}
iotestinfo = {}
deploytestinfo = {}

def if_tbl_exists(bqclient, table_ref):
    from google.cloud.exceptions import NotFound
    try:
        bqclient.get_table(table_ref)
        return True
    except NotFound:
        return False


def if_dataset_exists(bqclient, dataset_ref):
    from google.cloud.exceptions import NotFound
    try:
        bqclient.get_dataset(dataset_ref)
        return True
    except NotFound:
        return False


def initialization(project, service_acct_key):
    bqclient = bigquery.Client().from_service_account_json(service_acct_key)
    dataset_id = DATASET
    dataset_ref = bqclient.dataset(dataset_id)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = 'US'
    if not if_dataset_exists(bqclient, dataset_ref):
        print "need to create dataset"
        dataset = bqclient.create_dataset(dataset)
        assert dataset.dataset_id == DATASET
    else:
        print "dataset exist"
        dataset = bigquery.Dataset(dataset_ref)

    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('status', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('logfile', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('runner', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('date', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('time', 'STRING', mode='NULLABLE')
    ]
    table_ref = dataset_ref.table(TABLE)
    table = bigquery.Table(table_ref, schema=schema)

    if not if_tbl_exists(bqclient, table_ref):
        table = bqclient.create_table(table)  # API request
        print('table {} created.'.format(table.table_id))
        assert table.table_id == TABLE



    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('cluster_name', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('image', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('template_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('project', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('zone', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('disk_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('disk_number_config', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('disk_size_config', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('use_lb', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('subnetwork', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('use_public_ip', 'BOOLEAN', mode='NULLABLE'),
            bigquery.SchemaField('min_cluster', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('num_of_vms', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('vm_os_ver', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('vm_cpu_config', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('vm_memory_config', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('ems_os_ver', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('ems_cpu_config', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('ems_memory_config', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('client_name', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('duration', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('failurecode', 'INTEGER', mode='NULLABLE'),
    ]

    dtable_ref = dataset_ref.table(DTABLE)
    dtable = bigquery.Table(dtable_ref, schema=schema)
    if not if_tbl_exists(bqclient, dtable_ref):
        dtable = bqclient.create_table(dtable)  # API request
        print('table {} created.'.format(dtable.table_id))
        assert dtable.table_id == DTABLE


    schema = [
            bigquery.SchemaField('index', 'INTEGER', mode='REQUIRED'),
            bigquery.SchemaField('name', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('partner', 'STRING', mode='REQUIRED'),
            bigquery.SchemaField('disktype', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('iotool', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('iotype', 'STRING', mode='NULLABLE'),

            bigquery.SchemaField('io_client_vm_name', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_type', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_cpu', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_memory', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_version', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_project', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_vm_zone', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('io_client_sequence', 'INTEGER', mode='NULLABLE'),


            bigquery.SchemaField('io_tool_ver', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_blocksize', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_qdepth', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('test_io_file_size', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_file_number', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('test_io_direct', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_engine', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('test_io_check', 'BOOLEAN', mode='NULLABLE'),

            bigquery.SchemaField('writebw', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('writeiops', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('writelatency', 'STRING', mode='NULLABLE'),

            bigquery.SchemaField('readbw', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('readiops', 'STRING', mode='NULLABLE'),
            bigquery.SchemaField('readlatency', 'STRING', mode='NULLABLE'),

            bigquery.SchemaField('duration', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('ioerror', 'INTEGER', mode='NULLABLE'),
            bigquery.SchemaField('failurecode', 'INTEGER', mode='NULLABLE'),
    ]
    itable_ref = dataset_ref.table(ITABLE)
    itable = bigquery.Table(itable_ref, schema=schema)
    if not if_tbl_exists(bqclient, itable_ref):
       itable = bqclient.create_table(itable)  # API request
       print('table {} created.'.format(itable.table_id))
       assert itable.table_id == ITABLE

    btable_ref = dataset_ref.table(BTABLE)
    btable = bigquery.Table(btable_ref, schema=schema)
    if not if_tbl_exists(bqclient, btable_ref):
        btable = bqclient.create_table(btable)  # API request
        print('table {} created.'.format(btable.table_id))
        assert btable.table_id == BTABLE

    return bqclient



def query_bigquerytable(bq_client, bq_query):
    try:
        bq_query_job = bq_client.query(bq_query)
        bq_query_result = bq_query_job.result()
    except Exception as e:
        print "Big query fails."
        return []
    return bq_query_result


def new_test_result():
    listfile = 'gsutil ls {}'.format(BUCKET)
    output= subprocess.check_output(listfile.split()).splitlines()
    filelist = []
    for _line in output:
        filelist.append(_line)
    return filelist


def extract_test_info(testlogfile):
    print "Check testlog file {}".format(testlogfile)
    testinfo['logfile'] = testlogfile
    test_case_info = testlogfile.split('/')[-1].split('.')
    if not len(test_case_info) == 12:
        print "logfile is not able to be exported to table."
        print len(test_case_info)
        print test_case_info
        #cmd = 'gsutil rm {} '.format(testlogfile)
        return False
    print "test name is: ", test_case_info[0]
    if not test_case_info[0] in TESTNAMES:
       print "testname {} is not accepted".format(test_case_info[0])
       #cmd = 'gsutil rm {} '.format(testlogfile)
       return  False

    print test_case_info

    testname=test_case_info[0]
    testinfo['name'] = testname

    if 'elfs' in test_case_info:
        testinfo['partner'] = 'Elastifile'
    else:
        testinfo['partner']='Elastifile'

    if 'terraform' in test_case_info[1]:
        testtype = 'Provision_Test'
    elif "elfs" in test_case_info[0]:
        if '-ha-' in test_case_info[0]:
            testtype = 'High_Availability_Test'
        elif '-perf-' in test_case_info[0]:
            testtype = 'Performance_Test'
        elif '-stress-' in test_case_info[0]:
            testtype = 'Stress_Test'
        elif '-ps-' in test_case_info[0]:
            testtype = 'Post_Submit_Test'
        elif '-scalability-' in test_case_info[0]:
            testtype = 'Scalability_Test'
        elif 'daily-io' in test_case_info[0]:
            testtype = 'Daily_IO_Test'
        elif 'daily-e2e' in test_case_info[0]:
            testtype = 'Daily_E2E_Test'
    elif 'longitivity' in test_case_info[0]:
       if '-scalability-' in test_case_info[0]:
            testtype = 'Longitivity_Scalability_Test'
       else:
            testtype = "Longitivity_IO_Test"
    else:
        testtype = 'unknown'
    print testtype
    testinfo['type'] = testtype

    testdate = '-'.join(test_case_info[4:7])
    testtime = ':'.join(test_case_info[7:10])
    testinfo['date'] = testdate
    testinfo['time'] = testtime

    if 'fio' in test_case_info[1]:
      testinfo['iotype']=test_case_info[2]
      testinfo['iotool']='fio'
    print "len for {} is {}".format(test_case_info[3],\
          len(test_case_info[3].split('-')))
    dut_pattern="^[a-z]+\-.*\-([1-9][0-9]*)$"
    if re.search(dut_pattern, test_case_info[3]) and \
        int(test_case_info[3].split('-')[-1]) > 0 and \
        int(test_case_info[3].split('-')[-1]) < 1025:
        testinfo['dut']='-'.join(test_case_info[3].split('-')[0:-1])
        testinfo['dutseq']=int(test_case_info[3].split('-')[-1])
    else:
        testinfo['dut']=test_case_info[3]
        testinfo['dutseq']='0'

    testinfo['disktype'] = test_case_info[10]
    testinfo['runner'] = 'google'
    return True



def parse_provision_log(testlogfile):
    print "plan to add provision result, ", testlogfile
    test_file = 'temp.log'
    cmd = 'gsutil cp {} {}'.format(testlogfile, test_file)
    try:
        output = subprocess.check_output(cmd.split())
    except:
        print "copy file fail from {} to {}".format(testlogfile, test_file)
    ffile = open(test_file, 'r')
    fileoutput =  ffile.read()
    ffile.close()
    cmd = 'rm -rf {}'.format(test_file)
    subprocess.check_output(cmd.split())

    if "Apply complete!" in fileoutput:
        deploytestinfo['status'] = True
        deploytestinfo['failurecode']=0

    else:
        deploytestinfo['status'] = False
        deploytestinfo['failurecode']=1

    terraform_cfg_keywords = ["IMAGE", "TEMPLATE_TYPE",  "CLUSTER_NAME",\
                              "ZONE", "PROJECT", "NUM_OF_VMS", "VM_CONFIG",\
                              "DISK_TYPE", "DISK_CONFIG", "USE_LB", \
                              "MIN_CLUSTER", "SUBNETWORK", "CREDENTIALS", \
                              "SERVICE_EMAIL" , "USE_PUBLIC_IP"]
    for keyword in terraform_cfg_keywords:
        print "loooking for {}".format(keyword)
        terraform_cfg_pattern="{}\s*=\s*\"([a-z0-9\-_]+)\".*".format(keyword)
        if re.search(terraform_cfg_pattern, fileoutput):
            deploytestinfo[keyword.lower()]=re.search(terraform_cfg_pattern, \
                                                     fileoutput).group(1)
            if keyword == 'VM_CONFIG':
                temp = re.search(terraform_cfg_pattern, fileoutput).group(1)

                deploytestinfo['vm_cpu_config'] = int(temp.split('_')[0])
                deploytestinfo['vm_memory_config'] = int(temp.split('_')[0])
            if keyword == 'DISK_CONFIG':
                temp = re.search(terraform_cfg_pattern, fileoutput).group(1)
                deploytestinfo['disk_number_config'] = int(temp.split('_')[0])
                deploytestinfo['disk_size_config'] = int(temp.split('_')[0])
        else:
            if keyword == 'USE_PUBLIC_IP':
                deploytestinfo[keyword.lower()] = False
    if not "cluster_name" in deploytestinfo.keys():
        ems_pattern = "EMS_NAME:\s([a-z0-9\-]+)"
        found = re.search(ems_pattern, fileoutput)
        if found:
            deploytestinfo['cluster_name'] = found.group(1)
        else:
            deploytestinfo['cluster_name'] = 'unknown'

    duration_pattern = "Creation complete after ([0-9]+)m([0-9]*)s"
    matched = re.search(duration_pattern, fileoutput)
    if matched:
       deploytestinfo['duration'] = int(matched.group(1))*60 + int(matched.group(2))


def parse_io_log(testlogfile):
    test_file = 'temp.json'
    print "Fio result file {}".format(testlogfile)
    cmd = 'gsutil cp {} {}'.format(testlogfile, test_file)
    output = subprocess.check_output(cmd.split())
    try:
        with open(test_file) as f:
            test_result = json.load(f)
    except Exception as e:
        print "Failure in loading json file {}".format(testlogfile)
        return False

    try:
        iotestinfo['test_job_name'] = test_result['jobs'][0]['jobname']
        iotestinfo['test_fio_version'] = test_result['fio version']
        iotestinfo['test_fio_bs'] = test_result['jobs'][0]['job options']['bs']
        iotestinfo['test_fio_iodepth'] = test_result['global options']['iodepth']
        iotestinfo['test_fio_size'] = test_result['global options']['size']
        iotestinfo['test_fio_type'] = test_result['jobs'][0]['job options']['rw']
        iotestinfo['test_fio_direct'] = test_result['global options']['direct']
        iotestinfo['test_write_bw'] = test_result['jobs'][0]['write']['bw']
        iotestinfo['test_write_iops'] = test_result['jobs'][0]['write']['iops']
        iotestinfo['test_write_lat'] = test_result['jobs'][0]['write']['clat']['mean']
        iotestinfo['test_read_bw'] =test_result['jobs'][0]['read']['bw']
        iotestinfo['test_read_iops'] = test_result['jobs'][0]['read']['iops']
        iotestinfo['test_read_lat'] = test_result['jobs'][0]['read']['clat']['mean']
        iotestinfo['test_duration'] = test_result['jobs'][0]['elapsed']
        iotestinfo['test_error_count'] = test_result['jobs'][0]['error']
        if 'ioengine' in  test_result['global options'].keys():
            iotestinfo['test_io_engine'] = test_result['global options']['ioengine']
        else:
            iotestinfo['test_io_engine'] = 'unknown'
        if 'verify' in test_result['global options'].keys():
            iotestinfo['test_fio_verify'] = True
        else:
            iotestinfo['test_fio_verify'] = False
    except Exception as e:
        print "Failure in parsing json file {}".format(testlogfile)
    iotestinfo['test_io_file_number'] = 1
    iotestinfo['failurecode'] = 0
    return True


def update_test_table(bigquery_client, table_ref, rindex):
    table = bigquery_client.get_table(table_ref)
    row_to_insert = [
        (rindex, testinfo['name'], testinfo['partner'], testinfo['type'], \
         testinfo['status'], testinfo['logfile'], testinfo['runner'], \
         testinfo['date'], testinfo['time']),
    ]
    try:
        errors = bigquery_client.insert_rows(table, row_to_insert )
    except Exception as e:
        print "failure in inserting row in table".format(table_ref)
        rindex  = rindex - 1
    return rindex


def update_elfs_deployment_test_table(bigquery_client, table_ref, rindex):
    dtable = bigquery_client.get_table(table_ref)
    deploytestinfo['vm_os_ver'] = 'centos-7'
    deploytestinfo['ems_os_ver'] = 'centos-7'
    deploytestinfo['ems_cpu_config'] = 4
    deploytestinfo['ems_memory_config'] = "15GB"

    row_to_insert = [
        (rindex, testinfo['name'], testinfo['partner'] , \
         deploytestinfo['cluster_name'], deploytestinfo['image'], \
         deploytestinfo['template_type'], deploytestinfo['project'], \
         deploytestinfo['zone'], deploytestinfo['disk_type'], \
         deploytestinfo['disk_number_config'], \
         deploytestinfo['disk_size_config'],  deploytestinfo['use_lb'], \
         deploytestinfo['subnetwork'], deploytestinfo['use_public_ip'], \
         deploytestinfo['min_cluster'], deploytestinfo['num_of_vms'], \
         deploytestinfo['vm_os_ver'], deploytestinfo['vm_cpu_config'], \
         deploytestinfo['vm_memory_config'], deploytestinfo['ems_os_ver'], \
         deploytestinfo['ems_cpu_config'], deploytestinfo['ems_memory_config'], \
         testinfo['dut'], deploytestinfo['duration'], \
         deploytestinfo['failurecode'] )
    ]
    try:
        errors = bigquery_client.insert_rows(dtable, row_to_insert)
    except Exception as e:
        print "failure in inserting row in table".format(table_ref)
        rindex  = rindex - 1
    return rindex


def update_elfs_io_test_table(bigquery_client, table_ref, rindex):
    itable = bigquery_client.get_table(table_ref)
    testinfo['io_client_vm_name'] =  testinfo['dut']
    testinfo['io_client_vm_type'] = 'n1-standard-1'
    testinfo['io_client_vm_cpu'] = 1
    testinfo['io_client_vm_memory'] = '3.75GB'
    testinfo['io_client_vm_version'] = 'Google Drawfork Debian GNU/Linux 9'
    if 'project' in deploytestinfo.keys():
        testinfo['io_client_vm_project'] =  deploytestinfo['project']
    else:
        testinfo['io_client_vm_project'] = 'unknown'
    if 'zone' in deploytestinfo.keys():
        testinfo['io_client_vm_zone'] = deploytestinfo['zone']
    else:
        testinfo['io_client_vm_zone'] = 'unknown'
    testinfo['io_client_sequence'] = testinfo['dutseq']

    row_to_insert = [
             (rindex, testinfo['name'], testinfo['partner'],testinfo['disktype'], \
              testinfo['iotool'], testinfo['iotype'], \
              testinfo['io_client_vm_name'], testinfo['io_client_vm_type'], \
              testinfo['io_client_vm_cpu'], testinfo['io_client_vm_memory'], \
              testinfo['io_client_vm_version'], testinfo['io_client_vm_project'], \
              testinfo['io_client_vm_zone'], testinfo['io_client_sequence'], \
              iotestinfo['test_fio_version'], iotestinfo['test_fio_bs'], \
              iotestinfo['test_fio_iodepth'], iotestinfo['test_fio_size'], \
              iotestinfo['test_io_file_number'],\
              iotestinfo['test_fio_direct'], iotestinfo['test_io_engine'], \
              iotestinfo['test_fio_verify'], \
              iotestinfo['test_write_bw'], iotestinfo['test_write_iops'], \
              iotestinfo['test_write_lat'], \
              iotestinfo['test_read_bw'], iotestinfo['test_read_iops'], \
              iotestinfo['test_read_lat'], \
              iotestinfo['test_duration'], iotestinfo['test_error_count'], \
              iotestinfo['failurecode'])
    ]
    try:
        errors = bigquery_client.insert_rows(itable, row_to_insert)
    except Exception as e:
        print "failure in inserting row in table".format(table_ref)
        rindex  = rindex - 1
    return rindex


def add_test_record(bigquery_client, dataset_ref, table_ref, dtable_ref,\
                    itable_ref, btable_ref, testlogfile, rindex):
    print "Prepare to add record with index :", rindex
    deployment=False
    iotest=False

    if not extract_test_info(testlogfile):
        return rindex
    print testinfo['type']
    if "Provision" in testinfo['type']:
       print "parse terrform info"
       parse_provision_log(testlogfile)
       deployment = True
       iotest = False
       testinfo['status'] = deploytestinfo['status']
    else:
       print "parse fio info"
       parse_io_log(testlogfile)
       deployment = False
       iotest = True
       iothroughtput = float(iotestinfo['test_read_bw']) \
                    + float(iotestinfo['test_write_bw'])
       if iotestinfo['test_error_count'] == 0 and iothroughtput > 0:
           testinfo['status'] =  True
       else:
           testinfo['status'] =  False
    if deployment or iotest:
        update_test_table(bigquery_client, table_ref, rindex)
    if deployment:
        update_elfs_deployment_test_table(bigquery_client, dtable_ref, rindex)
    if iotest:
        update_elfs_io_test_table(bigquery_client, itable_ref, rindex)
    if deployment or iotest:
        rindex = rindex + 1
    return rindex


def populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, \
                        itable_ref, btable_ref, rindex):
    new_test_files = new_test_result()
    for _test_file in new_test_files:
        rindex = add_test_record(bqclient, dataset_ref, table_ref, dtable_ref,\
                                 itable_ref, btable_ref, _test_file, rindex)
    return rindex

def main():
    project="gtp-cpe-integration-testing"
    service_account_key="bqe.json"
    bqclient = initialization(project, service_account_key)

    dataset_id = DATASET
    dataset_ref = bqclient.dataset(dataset_id)
    dtable_ref = dataset_ref.table(DTABLE)
    itable_ref = dataset_ref.table(ITABLE)
    table_ref = dataset_ref.table(TABLE)
    btable_ref = dataset_ref.table(BTABLE)

    rindex = 0
    query_device_result = query_bigquerytable(bqclient, MAX_INDEX)
    print "Max index query: ", MAX_INDEX, query_device_result
    for _record in query_device_result:
        rindex = _record.index
        print "max index is ", rindex
        break
    rindex = rindex + 1
    while True:
        rindex = populate_test_table(bqclient, dataset_ref, table_ref, dtable_ref, \
                                     itable_ref, btable_ref, rindex)
        time.sleep(600)


if __name__ == '__main__':
    main()
