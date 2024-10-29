#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import subprocess
import json
import sys
import os
import re
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Colors class
class bcolors:
    HEADER    = '\033[95m'
    OKBLUE    = '\033[94m'
    OKCYAN    = '\033[96m'
    OKGREEN   = '\033[92m'
    WARNING   = '\033[93m'
    FAIL      = '\033[91m'
    ENDC      = '\033[0m'
    BOLD      = '\033[1m'
    UNDERLINE = '\033[4m'
###

lock_file = "/tmp/smart_info.lock"
# Prevents to run second copy of script
if os.path.exists(lock_file):
    print(bcolors.FAIL + "Error: Lock file " + lock_file + " exist. Exit. " + bcolors.ENDC)
    sys.exit(1)

# Create lock file
open(lock_file, "w")

# Need root user
if os.geteuid() != 0:
    print(bcolors.FAIL + "Error: You need to have root privileges. Exit." + bcolors.ENDC)
    sys.exit(1)

# Where lsblk
#where_lsblk = subprocess.check_output('which lsblk', shell = True, universal_newlines=True)
where_lsblk = subprocess.run('which lsblk', shell = True, capture_output=True, text=True, check=False)
if where_lsblk.stderr:
    print(bcolors.FAIL + "Error: lsblk not found. Exit." + bcolors.ENDC)
    sys.exit(1)

# Where smartctl
where_smartctl = subprocess.run('which smartctl', shell = True, capture_output=True, text=True, check=False)
if where_smartctl.stderr:
    print(bcolors.FAIL + "Error: smartctl not found. Exit." + bcolors.ENDC)
    sys.exit(1)

# Mail params
from_host = os.uname()[1]
mail_send   = False
mail_from   = "report@example.lan"
mail_to     = "user1@example.lan"
mail_sub    = "smartctl report from " + from_host
mail_server = "smtp.example.lan"
mail_s_port = 25 #587
#mail_user  = ""
#mail_pass  = ""
mail_msg    = MIMEMultipart('alternative')
mail_msg['Subject'] = mail_sub
mail_msg['From']    = mail_from
mail_msg['To']      = mail_to
mail_head   = "<html><head></head><body>"
mail_tail   = "</body></html>"
mail_body   = ""

where_smartctl = where_smartctl.stdout.replace('\n','')
where_lsblk    = where_lsblk.stdout.replace('\n','')
lsblk_cmd      = str(where_lsblk) + " -p -S -J -o NAME,WWN,HCTL,MODEL,SERIAL,TRAN"

# Get block devices info
lsblk_req  = subprocess.check_output(lsblk_cmd, shell = True, universal_newlines=True)
lsblk_devs = json.loads(lsblk_req)

alarm = False

for dev in lsblk_devs['blockdevices']:
    if 'sr' in dev['name']:
        continue

    if dev['tran']:
        if 'iscsi' in dev['tran']:
            continue

    mail_body += '<table style="border-collapse: collapse; width: 500px; height: 20px;" border="1"><tbody><tr style="text-align: center;"><td>' + dev['hctl'] + '</td><td style="background-color: #339966;">' + dev['name'] + '</td><td>' + dev['model'] + '</td><td>' + str(dev['serial']) + '</td></tr></tbody></table>'
    print(dev['hctl'] + " " + bcolors.OKCYAN + dev['name'] + bcolors.ENDC + " " + dev['model'] + " " + str(dev['serial']) )
    smart_req_str = where_smartctl + ' -a ' + dev['name'] + ' -j'
    smart_info_req = None
    try:
        smart_info_req = subprocess.run(smart_req_str, shell = True, capture_output=True, text=True, check=False)
        smart_info_req = smart_info_req.stdout
    except Exception as err:
        print(err)
        smart_info_req = subprocess.run(smart_req_str, shell = True, capture_output=True, text=True, check=False)
        smart_info_req = smart_info_req.stdout

    smart_dev = json.loads(smart_info_req)

    if 'messages' in smart_dev['smartctl']:
        mail_body += '<table style="border-collapse: collapse; width: 500px; height: 20px;" border="1"><tbody><tr style="text-align: center;"><td>Message</td><td style="background-color: #ff0000;">' + str(smart_dev['smartctl']['messages'][0]['string']) + '</td></tr></tbody></table>'
        print(bcolors.FAIL + str(smart_dev['smartctl']['messages'][0]['string']) + bcolors.ENDC)
        if smart_dev['smartctl']['messages'][0]['severity'] == 'error':
            alarm = True
            continue
    mail_body += '<table style="border-collapse: collapse; width: 500px; height: 200px;" border="1"><tbody>' + "\n"
    if 'model_name' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Model</td><td style="width: 300px;">' + smart_dev['model_name'] + '</td></tr>' + "\n"
        print("Model    : " + bcolors.WARNING + smart_dev['model_name'] + bcolors.ENDC)
    if 'model_family' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Family</td><td style="width: 300px;">' + smart_dev['model_family'] + '</td></tr>' + "\n"
        print("Family   : " + smart_dev['model_family'])
    if 'vendor' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Vendor</td><td style="width: 300px;">' + smart_dev['vendor'] + '</td></tr>' + "\n"
        print("Vendor   : " + smart_dev['vendor'])
    if 'product' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Product</td><td style="width: 300px;">' + smart_dev['product'] + '</td></tr>' + "\n"
        print("Product  : " + smart_dev['product'])
    if 'serial_number' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Serial</td><td style="width: 300px;">' + smart_dev['serial_number'] + '</td></tr>' + "\n"
        print("Serial   : " + bcolors.OKBLUE + smart_dev['serial_number'] + bcolors.ENDC)
    if 'firmware_version' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Firmware</td><td style="width: 300px;">' + smart_dev['firmware_version'] + '</td></tr>' + "\n"
        print("Firmware : " + smart_dev['firmware_version'])
    if 'wwn' in dev:
        wwn_name = 'N/A'
        if dev['wwn']:
            wwn_name = hex(int(int(int(dev['wwn'],16)) >> 2) << 2)
        mail_body += '<tr><td style="width: 200px">WWN Name</td><td style="width: 300px;">' + re.sub(r'^0X','', str(wwn_name).upper()) + '</td></tr>' + "\n"
        print("WWN Name : " + bcolors.OKBLUE + re.sub(r'^0X','', str(wwn_name).upper() + bcolors.ENDC))
    elif 'wwn' in smart_dev:
        print("WWN Name : " + bcolors.OKBLUE + str(smart_dev['wwn']['naa']) + " " + str(hex(smart_dev['wwn']['oui'])) + " " + str(hex(smart_dev['wwn']['id'])) + bcolors.ENDC)
    print("Capacity : " + str(round(smart_dev['user_capacity']['bytes'] / 1000 / 1000 / 1000)) + " Gb")
    if 'temperature' in smart_dev:
        if smart_dev['temperature']['current'] > 40:
            alarm = True
            mail_body += '<tr><td style="width: 200px">Temp</td><td style="width: 300px;background-color:#ff0000">' + str(smart_dev['temperature']['current']) +'</td></tr>' + "\n"
            print("Temp     : " + bcolors.WARNING + str(smart_dev['temperature']['current']) + bcolors.ENDC)
        else:
            mail_body += '<tr><td style="width: 200px">Temp</td><td style="width: 300px;background-color:#339966">' + str(smart_dev['temperature']['current']) +'</td></tr>' + "\n"
            print("Temp     : " + bcolors.OKGREEN + str(smart_dev['temperature']['current']) + bcolors.ENDC)
    if 'smart_status' in smart_dev:
        if smart_dev['smart_status']['passed']:
            mail_body += '<tr><td style="width: 200px">SMART</td><td style="width: 300px;background-color:#339966">' + 'PASSED' +'</td></tr>' + "\n"
            print("SMART    : " + bcolors.OKGREEN + "PASSED" + bcolors.ENDC)
        else:
            if 'scsi' in smart_dev['smart_status']:
                alarm = True
                mail_body += '<tr><td style="width: 200px">SMART</td><td style="width: 300px;background-color:#ff0000">' + smart_dev['smart_status']['scsi']['ie_string'] +'</td></tr>' + "\n"
                print("SMART    : " + bcolors.FAIL + smart_dev['smart_status']['scsi']['ie_string'] + bcolors.ENDC)
    if 'ata_smart_data' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Status</td><td style="width: 300px;background-color:#0000ff">' + str(smart_dev['ata_smart_data']['self_test']['status']['string']) +'</td></tr>' + "\n"
        print("Status   : " + bcolors.OKCYAN + str(smart_dev['ata_smart_data']['self_test']['status']['string']) + bcolors.ENDC)
    if 'logical_block_size' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Logical block size</td><td style="width: 300px;">' + str(smart_dev['logical_block_size']) + '</td></tr>' + "\n"
        print("Logical block size  : " + str(smart_dev['logical_block_size']))
    if 'physical_block_size' in smart_dev:
        mail_body += '<tr><td style="width: 200px">Physical block size</td><td style="width: 300px;">' + str(smart_dev['physical_block_size']) + '</td></tr>' + "\n"
        print("Physical block size : " + str(smart_dev['physical_block_size']))
    if 'ata_smart_attributes' in smart_dev:
        print("\tSMART Attributes:")
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 1:
                if s['raw']['value'] > 0:
                    mail_body += '<tr><td style="width: 200px">Raw Read Error Rate</td><td style="width: 300px;background-color:#ff0000">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Raw Read Error Rate     : " + bcolors.FAIL + str(s['raw']['value']) + bcolors.ENDC)
                else:
                    mail_body += '<tr><td style="width: 200px">Raw Read Error Rate</td><td style="width: 300px;background-color:#339966">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Raw Read Error Rate     : " + bcolors.OKGREEN + str(s['raw']['value']) + bcolors.ENDC)
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 5:
                if s['raw']['value'] > 0:
                    mail_body += '<tr><td style="width: 200px">Reallocated Sector</td><td style="width: 300px;background-color:#ff0000">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Reallocated Sector      : " + bcolors.FAIL + str(s['raw']['value']) + bcolors.ENDC)
                else:
                    mail_body += '<tr><td style="width: 200px">Reallocated Sector</td><td style="width: 300px;background-color:#339966">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Reallocated Sector      : " + bcolors.OKGREEN + str(s['raw']['value']) + bcolors.ENDC)
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 9:
                mail_body += '<tr><td style="width: 200px">Power On Hours</td><td style="width: 300px;background-color:#0000ff">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                print("Power On Hours          : " + bcolors.OKBLUE + str(s['raw']['value']) + bcolors.ENDC)
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 160:
                if s['raw']['value'] > 0:
                    mail_body += '<tr><td style="width: 200px">Uncorrectable Error Count</td><td style="width: 300px;background-color:#ff0000">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Uncorrectable Error Cnt : " + bcolors.FAIL + str(s['raw']['value']) + bcolors.ENDC)
                else:
                    mail_body += '<tr><td style="width: 200px">Uncorrectable Error Count</td><td style="width: 300px;background-color:#339966">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Uncorrectable Error Cnt : " + bcolors.OKGREEN + str(s['raw']['value']) + bcolors.ENDC)
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 196:
                if s['raw']['value'] > 0:
                    mail_body += '<tr><td style="width: 200px">Reallocated Event Count</td><td style="width: 300px;background-color:#ff0000">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Reallocated Event Count : " + bcolors.FAIL + str(s['raw']['value']) + bcolors.ENDC)
                else:
                    mail_body += '<tr><td style="width: 200px">Reallocated Event Count</td><td style="width: 300px;background-color:#339966">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Reallocated Event Count : " + bcolors.OKGREEN + str(s['raw']['value']) + bcolors.ENDC)
        for s in smart_dev['ata_smart_attributes']['table']:
            if s['id'] == 197:
                if s['raw']['value'] > 0:
                    mail_body += '<tr><td style="width: 200px">Current Pending Sector</td><td style="width: 300px;background-color:#ff0000">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Current Pending Sector  : " + bcolors.FAIL + str(s['raw']['value']) + bcolors.ENDC)
                else:
                    mail_body += '<tr><td style="width: 200px">Current Pending Sector</td><td style="width: 300px;background-color:#339966">' + str(s['raw']['value']) +'</td></tr>' + "\n"
                    print("Current Pending Sector  : " + bcolors.OKGREEN + str(s['raw']['value']) + bcolors.ENDC)
    if 'scsi_grown_defect_list' in smart_dev:
        print("\tHeath status:")
        if smart_dev['scsi_grown_defect_list'] > 0:
            mail_body += '<tr><td style="width: 200px">SCSI grow defect list</td><td style="width: 300px;background-color:#ff0000">' + str(smart_dev['scsi_grown_defect_list']) +'</td></tr>' + "\n"
            print("SCSI grow defect list : " + bcolors.FAIL + str(smart_dev['scsi_grown_defect_list']) + bcolors.ENDC)
        else:
            mail_body += '<tr><td style="width: 200px">SCSI grow defect list</td><td style="width: 300px;background-color:#339966">' + str(smart_dev['scsi_grown_defect_list']) +'</td></tr>' + "\n"
            print("SCSI grow defect list : " + bcolors.OKGREEN + str(smart_dev['scsi_grown_defect_list']) + bcolors.ENDC)
    mail_body += '</tbody></table>'

    if 'scsi_error_counter_log' in smart_dev:
        mail_body += '<table style="border-collapse: collapse; width: 300px; height: 20px;" border="1"><tbody><tr style="text-align: center;"><td>Scsi error counter log</td><td>Read</td><td>Write</td></tr>' + "\n"
        print("                                       Read\tWrite")

        mail_body += '<tr><td style="width: 300px">Errors corrected by eccfast</td>'
        print("Errors corrected by eccfast          : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccfast'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccfast']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccfast']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccfast']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccfast']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccfast'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccfast']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccfast']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccfast']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccfast']) + bcolors.ENDC)

        mail_body += '<tr><td style="width: 300px">Errors corrected by eccdelayed</td>'
        print("Errors corrected by eccdelayed       : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccdelayed'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccdelayed']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccdelayed']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccdelayed']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_eccdelayed']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccdelayed'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccdelayed']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccdelayed']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccdelayed']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_eccdelayed']) + bcolors.ENDC)

        mail_body += '<tr><td style="width: 300px">Errors corrected by rereads rewrites</td>'
        print("Errors corrected by rereads rewrites : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_rereads_rewrites'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_rereads_rewrites']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_rereads_rewrites']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_rereads_rewrites']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['errors_corrected_by_rereads_rewrites']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_rereads_rewrites'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_rereads_rewrites']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_rereads_rewrites']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_rereads_rewrites']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['errors_corrected_by_rereads_rewrites']) + bcolors.ENDC)

        mail_body += '<tr><td style="width: 300px">Total errors corrected</td>'
        print("Total errors corrected               : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['total_errors_corrected'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['total_errors_corrected']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['total_errors_corrected']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['total_errors_corrected']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['total_errors_corrected']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['total_errors_corrected'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['total_errors_corrected']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['total_errors_corrected']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['total_errors_corrected']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['total_errors_corrected']) + bcolors.ENDC)

        mail_body += '<tr><td style="width: 300px">Correction algorithm invocations</td>'
        print("Correction algorithm invocations     : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['correction_algorithm_invocations'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['correction_algorithm_invocations']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['correction_algorithm_invocations']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['correction_algorithm_invocations']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['correction_algorithm_invocations']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['correction_algorithm_invocations'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['correction_algorithm_invocations']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['correction_algorithm_invocations']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['correction_algorithm_invocations']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['correction_algorithm_invocations']) + bcolors.ENDC)

        mail_body += '<tr><td style="width: 300px">Gigabytes processed</td><td>' + str(smart_dev['scsi_error_counter_log']['read']['gigabytes_processed']) + '</td><td>' + str(smart_dev['scsi_error_counter_log']['write']['gigabytes_processed']) + '</td></tr>' + "\n"
        print("Gigabytes processed                  : " + str(smart_dev['scsi_error_counter_log']['read']['gigabytes_processed']) + "\t" + str(smart_dev['scsi_error_counter_log']['write']['gigabytes_processed']))

        mail_body += '<tr><td style="width: 300px">Total uncorrected errors</td>'
        print("Total uncorrected errors             : ", end='')
        if smart_dev['scsi_error_counter_log']['read']['total_uncorrected_errors'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['read']['total_uncorrected_errors']) + '</td>'
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['read']['total_uncorrected_errors']) + bcolors.ENDC + "\t", end='')
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['read']['total_uncorrected_errors']) + '</td>'
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['read']['total_uncorrected_errors']) + bcolors.ENDC + "\t", end='')
        if smart_dev['scsi_error_counter_log']['write']['total_uncorrected_errors'] > 0:
            mail_body += '<td style="background-color:#ff0000">' + str(smart_dev['scsi_error_counter_log']['write']['total_uncorrected_errors']) + '</td></tr>' + "\n"
            print(bcolors.FAIL    + str(smart_dev['scsi_error_counter_log']['write']['total_uncorrected_errors']) + bcolors.ENDC)
        else:
            mail_body += '<td style="background-color:#339966">' + str(smart_dev['scsi_error_counter_log']['write']['total_uncorrected_errors']) + '</td></tr>' + "\n"
            print(bcolors.OKGREEN + str(smart_dev['scsi_error_counter_log']['write']['total_uncorrected_errors']) + bcolors.ENDC)
        mail_body += '</tbody></table>'
    mail_body += '<br>'
    print()

if mail_send == True or alarm == True:
    # Send Mail
    def send_mail():
        print("Send report to " + mail_to)
        mail_data = mail_head + mail_body + mail_tail
        mail_body_html = MIMEText(mail_data, 'html')
        mail_msg.attach(mail_body_html)
        mail = smtplib.SMTP(mail_server, mail_s_port)
        #mail.ehlo()
        #mail.starttls()
        #mail.login(mail_user, mail_pass)
        mail.sendmail(mail_from, mail_to, mail_msg.as_string())
        mail.quit()

    try:
        send_mail()
    except Exception as err:
        print(err)

# Removing lock file
if os.path.exists(lock_file):
    os.remove(lock_file)
