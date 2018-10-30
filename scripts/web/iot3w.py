#!/usr/bin/env python

from google.cloud import bigquery
from google.cloud.bigquery import Dataset
import subprocess
import time
from datetime import datetime, timedelta
from datetime_truncate import truncate
from pytz import timezone


TIMEFORMAT = "%Y-%m-%d %H:%M:%S"
PST_ZONE = timezone('US/Pacific')
REMOVETZ = -6
QUERYWINDOW = 1200
TOTAL_MSG_PER_DAY = int(144*0.99)

DATASET = "iotpubdata"
TABLE = "iotpubdata.iotpubmessages"

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
    bqclient = bigquery.Client.from_service_account_json('iot-bq.json')
    dataset_ref = bqclient.dataset(DATASET)
    current =  datetime.now(PST_ZONE)
    while True:
        new_files_list = []
        current =  datetime.now(PST_ZONE)
        if  True or current.minute % 20 == 0 or current.minute == 1:
            print "======= start polling"
            generate_index_html(bqclient, INDEX_HTML_FILE)
            time.sleep(600)
            print "==== done polling"
        time.sleep(1)
#        break

if __name__ == '__main__':
    main()

