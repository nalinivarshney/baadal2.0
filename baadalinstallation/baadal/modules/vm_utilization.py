# -*- coding: utf-8 -*-
###################################################################################
import shutil, os, time, rrdtool, libvirt, re

import helper

from xml.etree import ElementTree

from gluon import IMG, URL, current

from helper import get_constant, get_context_path
from log_handler import rrd_logger
from host_helper import *

VM_UTIL_24_HOURS = 1
VM_UTIL_ONE_WEEK = 2
VM_UTIL_ONE_MNTH = 3
VM_UTIL_ONE_YEAR = 4

STEP         = 360
TIME_DIFF_MS = 700

def get_rrd_file(vm_name):

    rrd_file = get_constant("vmfiles_path") + os.sep + get_constant("vm_rrds_dir") + os.sep + vm_name + ".rrd"
    return rrd_file

def create_graph(vm_name, graph_type, rrd_file_path, graph_period):

    rrd_logger.debug(vm_name+" : "+graph_type+" : "+rrd_file_path+" : "+graph_period)
    rrd_file = vm_name + '.rrd'       

    shutil.copyfile(rrd_file_path, rrd_file)
    graph_file = vm_name + "_" + graph_type + ".png"

    start_time = None
    grid = None
    consolidation = 'MIN'
    ds = ds1 = ds2 = None
    line = line1 = line2 = None

    
    if graph_period == 'hour':
        start_time = 'now - ' + str(24*60*60)
        grid = 'HOUR:1:HOUR:1:HOUR:1:0:%k'
    elif graph_period == 'day':
        start_time = '-1w'
        grid = 'DAY:1:DAY:1:DAY:1:86400:%a'
    elif graph_period == 'month':
        start_time = '-1y'
        grid = 'MONTH:1:MONTH:1:MONTH:1:2592000:%b'
    elif graph_period == 'week':
        start_time = '-1m'
        grid = 'WEEK:1:WEEK:1:WEEK:1:604800:Week %W'
    elif graph_period == 'year':
        start_time = '-5y'
        grid = 'YEAR:1:YEAR:1:YEAR:1:31536000:%Y'
  
    if ((graph_type == 'ram') or (graph_type == 'cpu')):

        if graph_type == 'ram':
            ds = 'DEF:ram=' + vm_name + '.rrd:ram:' + consolidation
            line = 'LINE1:ram#0000FF:Memory'
            graph_type += " (KiloBytes)"
            upper_limit = ""
        elif graph_type == 'cpu':
            ds = 'DEF:cpu=' + vm_name + '.rrd:cpu:' + consolidation
            line = 'LINE1:cpu#0000FF:CPU'
            graph_type += " (%)"
            upper_limit = "-u 100"
                
#        rrdtool.graph(graph_file, '--start', start_time, '--end', 'now', '--vertical-label', graph_type, '--watermark', time.asctime(), '-t', 'VM Name: ' + vm_name, '--x-grid', grid, ds, line, "-l 0")

        rrdtool.graph(graph_file, '--start', start_time, '--end', 'now', '--vertical-label', graph_type, '--watermark', time.asctime(), '-t', 'VM Name: ' + vm_name, ds, line, "-l 0 --alt-y-grid -L 6" + upper_limit )

    else:

        if graph_type == 'nw':
            ds1 = 'DEF:nwr=' + vm_name + '.rrd:tx:' + consolidation
            ds2 = 'DEF:nww=' + vm_name + '.rrd:tw:' + consolidation
            line1 = 'LINE1:nwr#0000FF:Transmit'
            line2 = 'LINE1:nww#FF7410:Receive'

        elif graph_type == 'disk':
            ds1 = 'DEF:diskr=' + vm_name + '.rrd:dr:' + consolidation
            ds2 = 'DEF:diskw=' + vm_name + '.rrd:dw:' + consolidation
            line1 = 'LINE1:diskr#0000FF:DiskRead'
            line2 = 'LINE1:diskw#FF7410:DiskWrite'

        graph_type += " (KiloBytes)"

#        rrdtool.graph(graph_file, '--start', start_time, '--end', 'now', '--vertical-label', graph_type, '--watermark', time.asctime(), '-t', 'VM Name: ' + vm_name, '--x-grid', grid, ds1, ds2, line1, line2, "-l 0")

        rrdtool.graph(graph_file, '--start', start_time, '--end', 'now', '--vertical-label', graph_type, '--watermark', time.asctime(), '-t', 'VM Name: ' + vm_name, ds1, ds2, line1, line2, "-l 0 --alt-y-grid -L 6")


    graph_file_dir = os.path.join(get_context_path(), 'static' + get_constant('graph_file_dir'))
    shutil.copy2(graph_file, graph_file_dir)

    if os.path.exists(graph_file_dir + os.sep + graph_file):
        return True
    else:
        return False
    
def get_performance_graph(graph_type, vm, graph_period):

    error = None
    img = IMG(_src = URL("static" , "images/no_graph.jpg") , _style = "height:100px")

    try:
        rrd_file = get_rrd_file(vm)
  
        if os.path.exists(rrd_file):
            if create_graph(vm, graph_type, rrd_file, graph_period):   
                img_pos = "images/vm_graphs/" + vm + "_" + graph_type + ".png"
                img = IMG(_src = URL("static", img_pos), _style = "height:100%")
                rrd_logger.info("Graph created successfully")
            else:
                rrd_logger.warn("Unable to create graph from rrd file!!!")
                error = "Unable to create graph from rrd file"
        else:
            rrd_logger.warn("VMs RRD File Unavailable!!!")
            error = "VMs RRD File Unavailable!!!"
    except: 
        rrd_logger.warn("Error occured while creating graph.")
        import sys, traceback
        etype, value, tb = sys.exc_info()
        error = ''.join(traceback.format_exception(etype, value, tb, 10))
        rrd_logger.error(error)

    finally:
        if error != None:
            return error
        else:
            rrd_logger.info("Returning image.")
            return img

def fetch_rrd_data(vm_identity, period=VM_UTIL_24_HOURS):
    rrd_file = get_rrd_file(vm_identity)

    start_time = 'now - ' + str(24*60*60)
    end_time = 'now'
    
    if period == VM_UTIL_ONE_WEEK:
        start_time = '-1w'
    elif period == VM_UTIL_ONE_MNTH:
        start_time = '-1m'
    elif period == VM_UTIL_ONE_YEAR:
        start_time = '-1y'
    cpu_data = []
    mem_data = []
    dskr_data = []
    dskw_data = []
    nwr_data = []
    nww_data = []
    if os.path.exists(rrd_file):
        rrd_ret =rrdtool.fetch(rrd_file, 'MIN', '--start', start_time, '--end', end_time)
#         time_info = rrd_ret[0]
        fld_info = rrd_ret[1]
        data_info = rrd_ret[2]
        cpu_idx = fld_info.index('cpu')
        mem_idx = fld_info.index('ram')
        dskr_idx = fld_info.index('dr')
        dskw_idx = fld_info.index('dw')
        nwr_idx = fld_info.index('tx')
        nww_idx = fld_info.index('tw')
        
        for row in data_info:
            if row[cpu_idx] != None: cpu_data.append(float(row[cpu_idx])) 
            if row[mem_idx] != None: mem_data.append(float(row[mem_idx]))
            if row[dskr_idx] != None: dskr_data.append(float(row[dskr_idx]))
            if row[dskw_idx] != None: dskw_data.append(float(row[dskw_idx]))
            if row[nwr_idx] != None: nwr_data.append(float(row[nwr_idx]))
            if row[nww_idx] != None: nww_data.append(float(row[nww_idx]))
    
    return (sum(mem_data)/float(len(mem_data)) if len(mem_data) > 0 else 0, 
            sum(cpu_data)/float(len(cpu_data)) if len(cpu_data) > 0 else 0, 
            sum(dskr_data)/float(len(dskr_data)) if len(dskr_data) > 0 else 0,
            sum(dskw_data)/float(len(dskw_data)) if len(dskw_data) > 0 else 0,
            sum(nwr_data)/float(len(nwr_data)) if len(nwr_data) > 0 else 0,
            sum(nww_data)/float(len(nww_data)) if len(nww_data) > 0 else 0)
   
def create_rrd(rrd_file):

    ret = rrdtool.create( rrd_file, "--step", str(STEP) ,"--start", str(int(time.time())),
        "DS:cpu:GAUGE:%s:0:U"   % str(TIME_DIFF_MS),
        "DS:ram:GAUGE:%s:0:U"     % str(TIME_DIFF_MS),
        "DS:dr:GAUGE:%s:0:U"    % str(TIME_DIFF_MS),
        "DS:dw:GAUGE:%s:0:U"    % str(TIME_DIFF_MS),
        "DS:tx:GAUGE:%s:0:U"      % str(TIME_DIFF_MS),
        "DS:tw:GAUGE:%s:0:U"      % str(TIME_DIFF_MS),
        "RRA:MIN:0:1:200000",
        "RRA:AVERAGE:0.5:12:100",
        "RRA:AVERAGE:0.5:288:50",
        "RRA:AVERAGE:0.5:8928:24",
        "RRA:AVERAGE:0.5:107136:10")

    if ret:
        rrd_logger.warn(rrdtool.error())

def get_dom_mem_usage(dom_name, host):

    rrd_logger.debug("fecthing memory usage of domain %s defined on host %s" % (dom_name, host))

    import paramiko
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, username='root', password='')
    cmd = "ps aux | grep '\-name " + dom_name + " ' | grep kvm"
    stdin, stdout, stderr = ssh.exec_command(cmd)
    output = stdout.readlines()
    output.sort(key=len, reverse=True)

    ssh.close()

    if len(output) == 2:
        return (int(re.split('\s+', output[0])[5])) #returned memory in KBytes by default
    else:
        rrd_logger.warn("Unable to fetch memory usage details for dom %s" % (dom_name))

def get_dom_nw_usage(dom_obj):

    tree = ElementTree.fromstring(dom_obj.XMLDesc(0))
    rx = 0
    tx = 0

    for target in tree.findall("devices/interface/target"):
        device = target.get("dev")
        stats  = dom_obj.interfaceStats(device)
        rx   += stats[0]
        tx   += stats[4]

    rrd_logger.info("%s%s" % (rx, tx))

    return [nwr, nww] #returned value in Bytes by default

def get_dom_disk_usage(dom_obj):

    tree = ElementTree.fromstring(dom_obj.XMLDesc(0))
    bytesr = 0
    bytesw = 0
    rreq  = 0
    wreq  = 0

    for target in tree.findall("devices/disk/target"):

        device = target.get("dev")
        stats  = dom_obj.blockStats(device)
        rreq   += stats[0]
        bytesr += stats[1]
        wreq   += stats[2]
        bytesw += stats[3]

    rrd_logger.info("rreq: %s bytesr: %s wreq: %s bytesw: %s" % (rreq, bytesr, wreq, bytesw))

    return [bytesr, bytesw] #returned value in Bytes by default

def get_current_dom_resource_usage(dom, host_ip):

    dom_memusage   = get_dom_mem_usage(dom.name(), host_ip)
    dom_nw_usage   = get_dom_nw_usage(dom)
    dom_disk_usage = get_dom_disk_usage(dom)

    dom_stats =      {'rx'     : dom_nw_usage[0]}
    dom_stats.update({'tx'     : dom_nw_usage[1]})
    dom_stats.update({'diskr'   : dom_disk_usage[0]})
    dom_stats.update({'diskw'   : dom_disk_usage[1]})
    dom_stats.update({'memory'  : dom_memusage})
    dom_stats.update({'cputime' : dom.info()[4]})
    dom_stats.update({'cpus'    : dom.info()[3]})

    rrd_logger.info(dom_stats)
    rrd_logger.warn("As we get VM mem usage info from rrs size of the process running on host therefore it is observed that the memused is sometimes greater than max mem specified in case when the VM uses memory near to its mam memory")

    return dom_stats

def get_actual_usage(dom_obj, host_ip):


    dom_name = dom_obj.name()

    dom_stats = get_current_dom_resource_usage(dom_obj, host_ip)

    prev_dom_stats = current.cache.disk(str(dom_name), lambda:dom_stats, 86400) 
    rrd_logger.debug(prev_dom_stats)
        
    #cal usage
    usage = {'ram'      : dom_stats['memory']/float(1024)} #ram in MB usage
    usage.update({'cpu' : (dom_stats['cputime'] - prev_dom_stats['cputime'])/(float(prev_dom_stats['cpus'])*10000000*STEP)}) #percent cpu usage
    usage.update({'tx'  : (dom_stats['tx'] - prev_dom_stats['nwr'])/float(1024)}) #in KBytes
    usage.update({'tw'  : (dom_stats['rx'] - prev_dom_stats['nww'])/float(1024)}) #in KBytes
    usage.update({'dr'  : (dom_stats['diskr'] - prev_dom_stats['diskr'])/float(1024)}) #in KBytes
    usage.update({'dw'  : (dom_stats['diskw'] - prev_dom_stats['diskw'])/float(1024)}) #in KBytes

    current.cache.disk.clear(str(dom_name))

    latest_dom_stats = current.cache.disk(str(dom_name), lambda:dom_stats, 86400)        
    rrd_logger.debug(latest_dom_stats)
   
    return usage 


#@handle_exception
def update_rrd():

    active_host_list = current.db(current.db.host.status == HOST_STATUS_UP).select(current.db.host.host_ip)
    rrd_logger.debug(active_host_list)

    for host in active_host_list:

        hypervisor_conn = None
        try:
            host_ip = host['host_ip']
            hypervisor_conn = libvirt.open("qemu+ssh://root@" + host_ip + "/system")
            rrd_logger.debug(hypervisor_conn.getHostname())

            active_dom_ids  = hypervisor_conn.listDomainsID()
            all_dom_objs    = hypervisor_conn.listAllDomains()

            for dom_obj in all_dom_objs:

                rrd_file = get_rrd_file(dom_obj.name())

                if not (os.path.exists(rrd_file)):
                        rrd_logger.warn("RRD file (%s) does not exists" % (rrd_file))
                        rrd_logger.warn("Creating new RRD file")
                        create_rrd(rrd_file)

                else:

                    try:

                        timestamp_now = time.time()

                        if dom_obj.ID() in active_dom_ids:

                            #dom_stats = get_dom_resource_usage(dom_obj, host_ip)
                            usage = get_actual_usage(dom_obj, host_ip)
                            rrd_logger.debug(usage)
                            ret = rrdtool.update(rrd_file, "%s:%s:%s:%s:%s:%s:%s" % (timestamp_now, usage['cpu'], usage['ram'], usage['dr'], usage['dw'], usage['tx'], usage['tw']))

                        else:
                            
                            ret = rrdtool.update(rrd_file, "%s:0:0:0:0:0:0" % (timestamp_now))

                    except Exception, e:

                        rrd_logger.exception(e)
                        pass

        except:

            rrd_logger.exception("Error occured while creating/updating rrd or host.")
            pass

        finally:

            if hypervisor_conn:
                hypervisor_conn.close()

 
