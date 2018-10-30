#!/usr/bin/env python

from google.cloud import bigquery
from google.cloud.bigquery import Dataset
import subprocess
import time
from datetime import datetime, timedelta, date
from datetime_truncate import truncate
from pytz import timezone
import pytz

gcloud_keys={
 "Google Cloud SDK":"220.0.0",
 "alpha": "2018.10.08",
 "beta":"2018.10.08",
 "bq": "2.0.34",
 "core": "2018.10.08",
 "gsutil": "4.34",
 "kubectl": "2018.10.08"
}

TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
PST_ZONE = timezone('US/Pacific')
REMOVETZ = -6
QUERYWINDOW = 1200
TOTAL_MSG_PER_DAY = int(144*0.99)

DATASET = "storage_partner_test"
TABLE = "elastifile_test"
DTABLE = "elastifile_deployment_test"
ITABLE = "elastifile_io_test"

HEADER_FILE  = "header.template.html"
FOOTER_FILE = "footer.template.html"
INDEX_TABLE_FILE = "index.table.template.html"
REGISTRY_TABLE_FILE = "registry.table.template.html"
DEVICE_TABLE_FILE = "device.table.template.html"
MESSAGE_TABLE_FILE = "message.table.template.html"

INDEX_HTML_FILE = "eindex.html"

DAILY_SUMMARY_FILE = "gindex_template.html"
DAILY_SUMMARY_HEADER_FILE = "gindex_header_template.html"
DAILY_SUMMARY_BODY_FILE = "gindex_body_template.html"
DAILY_SUMMARY_FIRST_TABLE_FILE = "gindex_table_template.html"
DAILY_SUMMARY_LAST_TABLE_FILE = "gindex_last_table_template.html"
DAILY_SUMMARY_FOOTER_FILE = "gindex_footer_template.html"



INDEX_HTML_FILE = "eindex.html"
REPORT_HTML_FILE = "gindex.html"


MAX_INDEX = "SELECT index FROM  {}.{} \
            order by index desc \
            LIMIT 1".format(DATASET, TABLE)

DEVICE_QUERY = "select project, registry, devicename from {} \
                group by project, registry, devicename \
                order by project, registry, devicename".format(TABLE)
DEVICE_MSG_COUNT = "select count(devicename) as count, project, registry,\
                    devicename from {} \
                    group by project, registry, devicename \
                    ORDER by count(devicename) DESC, project, registry, devicename DESC".format(TABLE)
DEVICE_NUM_PROJECT_REGISTRY =  "SELECT count(index) as test_count, partner, \
        type FROM  {}.{}  group by partner, type".format(DATASET, TABLE) 


DAILY_SUMMARY = "SELECT partner, status, date, count(index) as count FROM {}.{} \
group by partner, status, date \
order by status".format(DATASET, TABLE)


#ELECT  count(index) as test_count, partner, type FROM storage_partner_test.elastifile_test
#group by partner, type
IOT_DEVICES_INFO = {}
IOT_DEVICES_LIST = []
new_files_list = []

def generate_daily_summary_report(bqclient, partner, testtype, testdate, dst_file):
#query_test_detail_for_provision_test(bqclient, partner, testtype, testname, testdate, dst_file):
    indexquery="SELECT index, status, logfile, date FROM {}.{} \
                where partner=\"{}\" and type=\"{}\" and  date=\"{}\" order by index DESC".format(DATASET, TABLE, partner, testtype, testdate)
    print indexquery            
    result =  query_bigquerytable(bqclient, indexquery)
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file('provision.table.template.html', dst_file)

    for _each in result:
       logfile = _each.logfile
       logfile = logfile.split('/')[-1]
       logfile = logfile.replace("gs://cpe-performance-storage/test_result","gs://cpe-performance-storage/test_result/backup")
       itest_status = _each.status
       index = _each.index
       queryiotest = "SELECT  index, testname,   cluster, version, storage_type, loadbalance, \
               storage_scale, storage_region , storage_project \
               FROM {}.{} where index={} order by index DESC".format(DATASET, DTABLE, index)
       itestresult = query_bigquerytable(bqclient, queryiotest)
       for _itest in itestresult:
   #        print _itest
           append_lines_html_file("<tr>\n", dst_file)
           line = "<td>{}</td>\n".format(index)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.testname)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.cluster)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.version)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_type)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.loadbalance)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_scale)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_region)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_project)
           append_lines_html_file(line, dst_file)
           bucket = 'cpe-performance-storage'
           fdir = 'test_result/backup'
           href = "<a href=\"https://{}.storage.googleapis.com/{}/{}\">".format(bucket, fdir, logfile)
           if itest_status:
              line = "<td class=\"green\">{}{}</a></td>\n".format(href, 'PASS')
           else:
              line = "<td class=\"red\">{}{}</a></td>\n".format(href, 'FAIL')
           append_lines_html_file(line, dst_file)
           append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    replace_strings_by_strings_file("12345678", partner, dst_file)
    replace_strings_by_strings_file("87654321", testtype, dst_file)
    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())



def update_daily_summary(bqclient, dst_file):
    copy_template_file_html_file(DAILY_SUMMARY_FILE, dst_file)
    mydate = datetime.now(PST_ZONE)
    print mydate 
    mylist = []
#    mydate = date.today()
#    print "today: ", mydate
    mydate = mydate + timedelta(days = 1)
    print "tomorrow :", mydate
#    time.sleep(10)
    sstatus = []
    datelist = []
    for i in range(8):
        mydate = mydate - timedelta(days = 1)
        mylist.append(str(mydate).split(' ')[0])
        print "the current time :", mylist[i] 
        templist = str(mylist[i]).split('-')
        cyear=templist[0]
        cmonth=templist[1]
        cdate=templist[2]
        replace_strings_by_strings_file('D{}'.format(i), cdate, dst_file)
        if i==0:
            todaydate=cdate
            todaymonth=cmonth
            todayyear=cyear
        sdate="{}-{}-{}".format(cmonth, cdate, cyear)
        datelist.append(sdate)

        query ="SELECT partner, status, count(index) as count FROM  {}.{} \
            where date=\"{}\" and  partner=\"Elastifile\" and type like \"%Provision_Test\" \
group by partner, status \
order by status".format(DATASET, TABLE, sdate)
        print query
        query_device_result = query_bigquerytable(bqclient, query)
        print query_device_result
        passed = 0 
        failed = 0
        for _result in query_device_result:
            print _result.partner, _result.status, _result.count
            if _result.status == True:
               passed = _result.count
            else:
               failed = _result.count
        print passed, failed       
        if  passed  > 0 and  failed == 0  : 
           sstatus.append(1)
        elif   failed > 0 and  passed == 0 : 
           sstatus.append(-1)
        elif  failed == 0 and passed == 0:
           sstatus.append(9) 
        else:
           sstatus.append(0)
        daily_summary_file = "Elastifile.Elastifile_Provision_Test.{}.html".format(sdate)
        generate_daily_summary_report(bqclient, "Elastifile", "Provision_Test", sdate,  daily_summary_file)

    print sstatus     
      
    monthfull = dict ({
               "10": "October",
               "11": "Novermber",
               "12": "December",
           } )       
    ok_string='bubble bubble ok'
    warning_string='bubble bubble medium'
    error_string='bubble bubble high'
    replace_strings_by_strings_file('M1234567', monthfull[todaymonth], dst_file)
    replace_strings_by_strings_file('M99', todaydate, dst_file)
    replace_strings_by_strings_file('Y1999', todayyear, dst_file)
    index = 0
    testname ='elastifile_provision_lssd'
    hreflink = "a href='http://35.232.128.2/Elastifile.Elastifile_Provision_Test.{}.{}.html".format(testname, sdate)
    for i in sstatus:
        print i
        if i == 1:
           replace_strings_by_strings_file('Status{}'.format(index), ok_string, dst_file)
        elif i == -1:
           replace_strings_by_strings_file('Status{}'.format(index), error_string, dst_file)
        elif i == 9:
           replace_strings_by_strings_file('Status{}'.format(index), ' ', dst_file)
        else:
           replace_strings_by_strings_file('Status{}'.format(index), warning_string, dst_file) 
        hreflink = "a href='http://35.232.128.2/Elastifile.Elastifile_Provision_Test.{}.html'".format(datelist[index])
        print hreflink
        replace_strings_by_strings_file('Href{}'.format(index), hreflink, dst_file)
        
        index = index + 1   

    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())




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


def query_test_detail_for_provision_test(bqclient, partner, testtype, testname, testdate, dst_file):
    indexquery="SELECT index, status, logfile, date FROM {}.{} \
                where type=\"{}\" and testname=\"{}\" and date=\"{}\" order by index DESC".format(DATASET,TABLE, testtype,  testname, testdate)
    result =  query_bigquerytable(bqclient, indexquery)
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file('provision.table.template.html', dst_file)

    for _each in result:
       logfile = _each.logfile
       logfile = logfile.split('/')[-1]
       logfile = logfile.replace("gs://cpe-performance-storage/test_result","gs://cpe-performance-storage/test_result/backup") 
       itest_status = _each.status
       index = _each.index
       queryiotest = "SELECT  index, testname,   cluster, version, storage_type, loadbalance, \
               storage_scale, storage_region , storage_project \
               FROM {}.{} where index={} order by index DESC".format(DATASET, DTABLE, index)
       itestresult = query_bigquerytable(bqclient, queryiotest)
  #     print queryiotest
  #     
       for _itest in itestresult:
   #        print _itest
           append_lines_html_file("<tr>\n", dst_file)
           line = "<td>{}</td>\n".format(index)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.testname)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.cluster)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.version)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_type)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.loadbalance)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_scale)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_region)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.storage_project)
           append_lines_html_file(line, dst_file)
           bucket = 'cpe-performance-storage'
           fdir = 'test_result/backup'
           href = "<a href=\"https://{}.storage.googleapis.com/{}/{}\">".format(bucket, fdir, logfile)

           if itest_status:
              line = "<td class=\"green\">{}{}</a></td>\n".format(href, 'PASS')
           else:
              line = "<td class=\"red\">{}{}</a></td>\n".format(href, 'FAIL')
           append_lines_html_file(line, dst_file)
           append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    replace_strings_by_strings_file("12345678", partner, dst_file)
    replace_strings_by_strings_file("87654321", testtype, dst_file)

    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())






def query_test_detail_for_io_test(bqclient, partner, testtype, testname, testdate, dst_file):
    indexquery="SELECT index, status, logfile, date FROM {}.{} \
                where type=\"{}\" and testname=\"{}\" and date=\"{}\" order by index DESC".format(DATASET,TABLE, testtype,  testname, testdate)
    result =  query_bigquerytable(bqclient, indexquery)
    #print indexquery
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(MESSAGE_TABLE_FILE, dst_file)

    for _each in result:
  #     print _each
       itest_status = _each.status
       index = _each.index
       queryiotest = "SELECT  index, io_tool, volume_type, test_io_type, test_io_blocksize, test_io_qdepth, \
writebw, writeiops , writelatency, readbw, readiops, readlatency FROM {}.{} where index={} order by index DESC".format(DATASET, ITABLE, index)
       itestresult = query_bigquerytable(bqclient, queryiotest)
  #     print queryiotest
       logfile = _each.logfile
  #     logfile = logfile.replace("gs://cpe-performance-storage/test_result","gs://cpe-performance-storage/test_result/backup") 
       logfile = logfile.split('/')[-1]
       for _itest in itestresult:
   #        print _itest
           append_lines_html_file("<tr>\n", dst_file)
           line = "<td>{}</td>\n".format(index)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.volume_type)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.test_io_type)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.test_io_blocksize)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.test_io_qdepth)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.writebw)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.writeiops)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.writelatency)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.readbw)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.readiops)
           append_lines_html_file(line, dst_file)
           line = "<td>{}</td>\n".format(_itest.readlatency)
           append_lines_html_file(line, dst_file)
  #         https://cpe-performance-storage.storage.googleapis.com/test_result/index.html
           bucket='cpe-performance-storage'
           fdir='test_result/backup'

           href = "<a href=\"https://{}.storage.googleapis.com/{}/{}\">".format(bucket, fdir, logfile)
           if itest_status:
               line = "<td class=\"green\">{}{}</a></td>\n".format(href, 'PASS')
           else:
               line = "<td class=\"red\">{}{}</a></td>\n".format(href, 'FAIL')
           append_lines_html_file(line, dst_file)
           append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    replace_strings_by_strings_file("12345678", partner, dst_file)
    replace_strings_by_strings_file("87654321", testtype, dst_file)

    copyfile  = "sudo cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())



def generate_index_html(bqclient, dst_file):
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(INDEX_TABLE_FILE, dst_file)
    query_device_result = query_bigquerytable(bqclient, DEVICE_NUM_PROJECT_REGISTRY)
    for each_registry in query_device_result:
        print "Start updating partner", each_registry
        append_lines_html_file("<tr>\n", dst_file)

        partner = each_registry.partner.strip()
        line = "<td>{}</td>\n".format(partner)
        append_lines_html_file(line, dst_file)

        rtype = each_registry.type.strip()
        line = "<td>{}</td>\n".format(rtype)
        append_lines_html_file(line, dst_file)

        testcount = each_registry.test_count
        href = "<a href=\"{}.{}.html\">".format(partner, rtype)
        line = "<td>{}{}</a></td>\n".format(href, testcount)
        append_lines_html_file(line, dst_file)

        test_file = "{}.{}.html".format(partner, rtype)
        generate_summary_project_registry(bqclient, partner, rtype, test_file )

    append_template_file_html_file(FOOTER_FILE, dst_file)
    copyfile  = "sudo  cp {} /var/www/html/{}".format(dst_file, dst_file)
    print "Index file is updated"
    subprocess.check_output(copyfile.split())



def generate_summary_project_registry(bqclient, project, registry, dst_file):
    copy_template_file_html_file(HEADER_FILE, dst_file)
    append_template_file_html_file(REGISTRY_TABLE_FILE, dst_file)
    DEVICE_MSG_COUNT = "select count(index) as count, \
                    testname, date from {}.{} \
                    where partner=\"{}\" and type=\"{}\"  \
                    group by  date, testname  \
                    ORDER by  date DESC, testname DESC".format(DATASET,TABLE, project, registry)
    query_device_result = query_bigquerytable(bqclient, DEVICE_MSG_COUNT)
    # generate table for all devices
    for each_device in query_device_result:
        devicename = each_device.testname.strip()
        ddate = each_device.date.strip()
        print ddate
        if not '2018' in ddate:
            continue
        print "start updating partner {} test {} testname {} date {}".format(project, registry, devicename, ddate)
        DEVICE_MSG_COUNT_T = "select count(index) as count, status \
                           from {}.{} \
                           where partner=\"{}\" and type=\"{}\" and date=\"{}\" \
                           and testname=\"{}\"  \
                           group by testname, status, date  \
                           ".format(DATASET, TABLE, project, registry, ddate, devicename)
        query_device_result_t = query_bigquerytable(bqclient, DEVICE_MSG_COUNT_T)

        append_lines_html_file("<tr>\n", dst_file)

        line = "<td>{}</td>\n".format(project)
        append_lines_html_file(line, dst_file)

        line = "<td>{}</td>\n".format(registry)
        append_lines_html_file(line, dst_file)

        devicename = each_device.testname.strip()
        href = "<a href=\"{}.{}.{}.{}.html\">".format(project, registry, devicename, ddate)
        line = "<td>{}{}</a></td>\n".format(href, devicename)
        append_lines_html_file(line, dst_file)
        line = "<td>{}</td>\n".format(ddate.replace('.','-'))
        append_lines_html_file(line, dst_file)


        count = each_device.count
        line = "<td>{}</td>\n".format(count)
        append_lines_html_file(line, dst_file)
        for result in query_device_result_t:
            if result.status == True:
                tcount =  result.count
                fcount = count - tcount
            else:
                fcount =result.count
                tcount = count - fcount
        line = "<td class=\"red\">{}</td>\n".format(fcount)
        append_lines_html_file(line, dst_file)

        line = "<td class=\"green\">{}</td>\n".format(tcount)
        append_lines_html_file(line, dst_file)
        ts = time.gmtime()
        today_date = time.strftime("%m-%d-%Y %H.%M.%S", ts).split()[0]
        #mydate = date.today()
        print "today:",today_date
        #time.sleep(10)
        #adata = ''.join(today_date.split('-'))
        #print adata
        #today_clock = time.strftime("%m.%d.%Y %H.%M.%S", ts).split()[1]
#20181013
        print ddate 
        now=datetime.now(pytz.timezone('US/Pacific'))
        tdate = now.isoformat().split('T')[0].split('-')
        cdate = ddate.split('-')
        print cdate, tdate
        if cdate[0] == tdate[1] and cdate[1] == tdate[2] and cdate[2] == tdate[0]: 
#        if True:
            print "start updating today page"
#            if 'io' in devicename:
#               query_test_detail_for_io_test(bqclient, project, \
#                    registry, devicename, ddate,  "{}.{}.{}.{}.html".format(project, registry, devicename, ddate))
            if 'provision' in devicename:
               query_test_detail_for_provision_test(bqclient, project, \
                    registry, devicename, ddate,  "{}.{}.{}.{}.html".format(project, registry, devicename, ddate))
            else:
               query_test_detail_for_io_test(bqclient, project, \
                    registry, devicename, ddate,  "{}.{}.{}.{}.html".format(project, registry, devicename, ddate))


    append_template_file_html_file(FOOTER_FILE, dst_file)
    append_lines_html_file("</tr>\n\n", dst_file)
    append_template_file_html_file(FOOTER_FILE, dst_file)
    copyfile = "sudo  cp {} /var/www/html/{}".format(dst_file, dst_file)
    subprocess.check_output(copyfile.split())
    new_files_list.append(dst_file)
    print "Summary pages for all tests are updated"

def main():
    bqclient = bigquery.Client.from_service_account_json('bqe.json')
    dataset_ref = bqclient.dataset(DATASET)
    rindex = 0
    update_daily_summary(bqclient, REPORT_HTML_FILE)
    query_device_result = query_bigquerytable(bqclient, MAX_INDEX)
    for _record in query_device_result:
        rindex = _record.index
        print "Max index is:", rindex
        break
    old_index = rindex - 1
    while True:
        #print "======= Start polling"
        query_device_result = query_bigquerytable(bqclient, MAX_INDEX)
        print "Max index query: ", MAX_INDEX, query_device_result
        for _record in query_device_result:
            rindex = _record.index
            print "Max index is ", rindex
            break
        if rindex > old_index:
            print "found new test"
            update_daily_summary(bqclient, REPORT_HTML_FILE)
            generate_index_html(bqclient, INDEX_HTML_FILE)
            print "==== done polling and webpage update===="
            old_index = rindex
        time.sleep(60)

if __name__ == '__main__':
    main()
