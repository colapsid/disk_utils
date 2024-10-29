#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import sys
import os
import time
import argparse
import subprocess
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

parser = argparse.ArgumentParser(prog = 'storcli_info', description = 'Storcli get healh info', epilog = 'Exmample: ./storcli_info.py -s server01.local -c 1 -p /opt/lsi/storcli/storcli -m 1')
parser.add_argument('-s', '--server', type=str,  default='localhost',                        help = 'Hostname or IP')
parser.add_argument('-c', '--count',  type=int,  default=1,                                  help = 'Controllers count')
parser.add_argument('-p', '--path',   type=str,  default='/opt/MegaRAID/storcli/storcli64',  help = 'storcli path')
parser.add_argument('-m', '--mail',   type=int,  default=0,                                  help = 'Send report 0 or 1')
namespace = parser.parse_args(sys.argv[1:])

print("Server     : " + namespace.server)
print("Ctrls count: " + str(namespace.count))
print()

r_user         = "root"                                     # Remote user
r_storcli_path = "/opt/lsi/storcli/storcli"                 # Remote strocli path
alarm_tmp_file = "/tmp/alarm_tmp_file_" + namespace.server  # Temp alarm file path

if namespace.server == 'localhost':
    from_host = os.uname()[1]
else:
    from_host = namespace.server

# Mail params
mail_send   = namespace.mail
mail_from   = "report@example.lan"
mail_to     = "user1@example.lan"
mail_sub    = "Strocli report from " + from_host
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
mail_body   = str()
###

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

lock_file = "/tmp/storcli_info.lock"
# Prevents to run second copy of script
if os.path.exists(lock_file):
    print(bcolors.FAIL + "Error: Lock file " + lock_file + " exist. Exit. " + bcolors.ENDC)
    sys.exit(1)

# Create lock file
open(lock_file, "w")

def get_info(cmd, count):
    alarm = False
    for c in range(0, count):
        run_cmd    = cmd + " /c" + str(c) + " show all J"
        run_cmd_cv = cmd + " /c" + str(c) + " /cv show all J"
        print(bcolors.OKBLUE + "Run: " + run_cmd + bcolors.ENDC)

        try:
            get_ctrl_info = subprocess.check_output(run_cmd, shell = True, universal_newlines=True)
        except:
            print(bcolors.FAIL + "Failed to get info" + bcolors.ENDC)
            continue
        try:
            ctrl_info = json.loads(get_ctrl_info)
        except:
            print(bcolors.WARNING + "Failed to load json data" + bcolors.ENDC)
            continue

        # Get basic info
        controller  = ctrl_info['Controllers'][0]['Response Data']['Basics']['Controller']
        cont_model  = ctrl_info['Controllers'][0]['Response Data']['Basics']['Model']
        cont_serial = ctrl_info['Controllers'][0]['Response Data']['Basics']['Serial Number']
        cont_sasadr = ctrl_info['Controllers'][0]['Response Data']['Basics']['SAS Address']
        cont_pciadr = ctrl_info['Controllers'][0]['Response Data']['Basics']['PCI Address']
        cont_status = ctrl_info['Controllers'][0]['Response Data']['Status']['Controller Status']
        if 'Drive Groups' in ctrl_info['Controllers'][0]['Response Data']:
            cont_drgr   = ctrl_info['Controllers'][0]['Response Data']['Drive Groups']
        else:
            cont_drgr = None
        if 'Physical Drives' in ctrl_info['Controllers'][0]['Response Data']:    
            cont_phdr   = ctrl_info['Controllers'][0]['Response Data']['Physical Drives']
        else:
            cont_phdr = None
        if 'PD LIST' in ctrl_info['Controllers'][0]['Response Data']:       
            cont_pdlist = ctrl_info['Controllers'][0]['Response Data']['PD LIST']
        else:
            cont_pdlist = None

        # Print basic info
        print("Controller     : " + bcolors.WARNING + str(controller) + bcolors.ENDC)
        print("Model          : " + bcolors.WARNING + cont_model + bcolors.ENDC)
        print("Serial         : " + bcolors.WARNING + cont_serial + bcolors.ENDC)
        print("SAS Address    : " + bcolors.WARNING + cont_sasadr + bcolors.ENDC)
        print("PCI Address    : " + bcolors.WARNING + cont_pciadr + bcolors.ENDC)

        mail_body = '<table style="border-collapse: collapse; width: 500px; height: 200px;" border="1"><tbody>' + "\n"
        mail_body += '<tr><td style="width: 200px">Controller</td><td style="width: 300px">' + str(controller) + '</td></tr>' + "\n"
        mail_body += '<tr><td style="width: 200px">Model</td><td style="width: 300px">' + cont_model + '</td></tr>' + "\n"
        mail_body += '<tr><td style="width: 200px">Serial</td><td style="width: 300px">' + cont_serial + '</td></tr>' + "\n"
        mail_body += '<tr><td style="width: 200px">SAS Address</td><td style="width: 300px">' + cont_sasadr + '</td></tr>' + "\n"
        mail_body += '<tr><td style="width: 200px">PCI Address</td><td style="width: 300px">' + cont_pciadr + '</td></tr>' + "\n"

        mail_body += '<tr><td style="width: 200px">Status</td><td style="width: 300px;background-color: '
        if cont_status == "Optimal" or cont_status == "OK":
            print("Status         : " + bcolors.OKGREEN + cont_status + bcolors.ENDC)
            mail_body += '#339966">' + cont_status + '</td></tr>' + "\n"
        else:
            print("Status         : " + bcolors.FAIL + cont_status + bcolors.ENDC)
            mail_body += '#ff0000">' + cont_status + '</td></tr>' + "\n"
            alarm = True

        if cont_drgr is not None:
            print("Drive Groups   : " + bcolors.WARNING + str(cont_drgr) + bcolors.ENDC)
        if cont_phdr is not None:
            print("Physical Drives: " + bcolors.WARNING + str(cont_phdr) + bcolors.ENDC)

        # CV/BBU get info
        try:
            get_cv_info = subprocess.check_output(run_cmd_cv, shell = True, universal_newlines=True)
        except:
            print(bcolors.WARNING + "Failed to get CV/BBU info" + bcolors.ENDC)
        try:
            cv_info = json.loads(get_cv_info)
        except:
            print(bcolors.WARNING + "Failed to load json data" + bcolors.ENDC)

        # CV info
        if 'cv_info' in locals():
            if 'Response Data' in cv_info['Controllers'][0]:
                mail_body += '<tr><td style="width: 200px">CV State</td><td style="width: 300px;background-color: '
                cachevault_info = cv_info['Controllers'][0]['Response Data']['Cachevault_Info']
                for cvinf in cachevault_info:
                    if 'State' in cvinf['Property']:
                        if cvinf['Value'] == "Optimal":
                            print("CV State       : " + bcolors.OKGREEN + cvinf['Value'] + bcolors.ENDC)
                            mail_body += '#339966">' + cvinf['Value'] + '</td></tr>' + "\n"
                        else:
                            print("CV State       : " + bcolors.FAIL + cvinf['Value'] + bcolors.ENDC)
                            mail_body += '#ff0000">' + cvinf['Value'] + '</td></tr>' + "\n"
                            alarm = True
            # CV FW info
                firmware_status = cv_info['Controllers'][0]['Response Data']['Firmware_Status']
                mail_body += '<tr><td style="width: 200px">CV FW status</td><td style="width: 300px;background-color: '
                for fwst in firmware_status:
                    if 'NVCache State' in fwst['Property']:
                        if fwst['Value'] == "OK":
                            print("CV FW status   : " + bcolors.OKGREEN + fwst['Value'] + bcolors.ENDC)
                            mail_body += '#339966">' + fwst['Value'] + '</td></tr>' + "\n"
                        else:
                            print("CV FW status   : " + bcolors.FAIL + fwst['Value'] + bcolors.ENDC)
                            mail_body += '#ff0000">' + fwst['Value'] + '</td></tr>' + "\n"
                            alarm = True
        mail_body += '</tbody></table>'

        # Print disks table
        print()
        print("EID:Slt DID \tState\tDG\tSize\t\tIntf\tModel")
        mail_body += '<br><table style="border-collapse: collapse; width: 500px; height: 80px;" border="1"><tbody><tr style="text-align: center;"><td>EID:Slt</td><td>DID</td><td>State</td><td>DG</td><td>Size</td><td>Intf</td><td>Model</td></tr>'

        # RAID Controller
        if cont_pdlist is not None:
            for d in cont_pdlist:
                print(d['EID:Slt'] + "\t" + str(d['DID']) + "\t" , end='')
                mail_body += '<tr style="text-align: center;"><td>' + d['EID:Slt'] + '</td><td>' + str(d['DID']) + '</td><td style="background-color: '

                if ("Onln" == d['State']) or ("UGood" == d['State']) :
                    print(bcolors.OKGREEN + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '#339966'
                if ("Failed" == d['State']) or ("UBad" == d['State']):
                    print(bcolors.FAIL    + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '#ff0000'
                    alarm = True
                if "GHS" == d['State']:
                    print(bcolors.OKCYAN  + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '##0000ff'
                if "Rbld" == d['State']:
                    print(bcolors.WARNING + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '#ffcc00'
                    alarm = True
                if "UGUnsp" == d['State']:
                    print(bcolors.WARNING + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '#ffcc00'
                if "UBUnsp" == d['State']:
                    print(bcolors.WARNING + d['State'] + bcolors.ENDC + "\t", end='')
                    bg_color = '#ffcc00'

                mail_body += bg_color + ';">' + d['State'] + '</td><td>' + str(d['DG']) + '</td><td>' + d['Size'] + '</td><td>' + d['Intf'] + '</td><td>' + str(d['Model']).replace(" ","") + '</td></tr>' + "\n"
                print(str(d['DG']) + "\t" + d['Size'] + "\t" + d['Intf'] + "\t" + str(d['Model']).replace(" ",""))
            mail_body += '</tbody></table>'

            # Get S.M.A.R.T info from disks
            print()
            for s in cont_pdlist:
                print()
                print("Get S.M.A.R.T info from " + s['EID:Slt'] + " " + s['Model'])
                run_cmd_d = cmd + " /c" + str(c) + " /e" + str(s['EID:Slt']).split(":")[0] + " /s" + str(s['EID:Slt']).split(":")[1] + " show all J"
                print(bcolors.OKBLUE + "Run: " + run_cmd_d + bcolors.ENDC)

                try:
                    get_disk_info = subprocess.check_output(run_cmd_d, shell = True, universal_newlines=True)
                    time.sleep(1)
                except:
                    print(bcolors.FAIL + "Failed to get info" + bcolors.ENDC)
                    continue
                try:
                    sm_disk = json.loads(get_disk_info)
                except:
                    print(bcolors.WARNING + "Failed to load json data" + bcolors.ENDC)
                    continue

                #Get Drive info
                if '' in str(s['EID:Slt']).split(":")[0]:
                    drive_path = "Drive /c" + str(controller) + "/e"+ str(s['EID:Slt']).split(":")[0] + "/s" + str(s['EID:Slt']).split(":")[1]
                else:
                    drive_path = "Drive /c" + str(controller) + "/s" + str(s['EID:Slt']).split(":")[1]

                print(drive_path)
                mail_body += '<br><table style="border-collapse: collapse; width: 500px; height: 200px;" border="1"><tbody>' + "\n"
                mail_body += '<tr><td style="width: 200px" colspan="2">' + drive_path + '</td></tr>' + "\n"
                shield_counter    = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " State"]['Shield Counter']
                media_error_count = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " State"]['Media Error Count']
                other_error_count = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " State"]['Other Error Count']
                drive_temperature = str(sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " State"]['Drive Temperature']).replace(" ","").split("C")[0]
                pred_fail_count   = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " State"]['Predictive Failure Count']
                sn                = str(sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['SN']).replace(" ","")
                manufacturer_id   = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Manufacturer Id']
                model_number      = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Model Number']
                wwn               = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['WWN']
                print("  Shield Counter          : ", end='')
                mail_body += '<tr><td style="width: 200px">Shield Counter</td><td style="width: 300px;background-color: '
                if shield_counter > 0:
                    print(bcolors.FAIL + str(shield_counter) + bcolors.ENDC)
                    mail_body += '#ff0000">' + str(shield_counter) + '</td></tr>' + "\n"
                    alarm = True
                else:
                    print(bcolors.OKGREEN + str(shield_counter) + bcolors.ENDC)
                    mail_body += '#339966">' + str(shield_counter) + '</td></tr>' + "\n"

                print("  Media Error Count       : ", end='')
                mail_body += '<tr><td style="width: 200px">Media Error Count</td><td style="width: 300px;background-color: '
                if media_error_count > 0:
                    print(bcolors.FAIL + str(media_error_count) + bcolors.ENDC)
                    mail_body += '#ff0000">' + str(media_error_count) + '</td></tr>' + "\n"
                    alarm = True
                else:
                    print(bcolors.OKGREEN + str(media_error_count) + bcolors.ENDC)
                    mail_body += '#339966">' + str(media_error_count) + '</td></tr>' + "\n"

                print("  Other Error Count       : ", end='')
                mail_body += '<tr><td style="width: 200px">Other Error Count</td><td style="width: 300px;background-color: '
                if other_error_count > 0:
                    print(bcolors.FAIL + str(other_error_count) + bcolors.ENDC)
                    mail_body += '#ff0000">' + str(other_error_count) + '</td></tr>' + "\n"
                    alarm = True
                else:
                    print(bcolors.OKGREEN + str(other_error_count) + bcolors.ENDC)
                    mail_body += '#339966">' + str(other_error_count) + '</td></tr>' + "\n"

                print("  Drive Temperature       : ", end='')
                mail_body += '<tr><td style="width: 200px">Drive Temperature</td><td style="width: 300px;background-color: '
                if int(drive_temperature) > 40:
                    print(bcolors.WARNING + str(drive_temperature) + bcolors.ENDC)
                    mail_body += '#ff0000">' + str(drive_temperature) + '</td></tr>' + "\n"
                    alarm = True
                else:
                    print(bcolors.OKGREEN + str(drive_temperature) + bcolors.ENDC)
                    mail_body += '#339966">' + str(drive_temperature) + '</td></tr>' + "\n"

                print("  Predictive Failure Count: ", end='')
                mail_body += '<tr><td style="width: 200px">Predictive Failure Count</td><td style="width: 300px;background-color: '
                if pred_fail_count > 0:
                    print(bcolors.FAIL + str(pred_fail_count) + bcolors.ENDC)
                    mail_body += '#ff0000">' + str(pred_fail_count) + '</td></tr>' + "\n"
                    alarm = True
                else:
                    print(bcolors.OKGREEN + str(pred_fail_count) + bcolors.ENDC)
                    mail_body += '#339966">' + str(pred_fail_count) + '</td></tr>' + "\n"

                print("  SN                      : " + str(sn))
                mail_body += '<tr><td style="width: 200px">SN</td><td style="width: 300px;">' + str(sn) + '</td></tr>' + "\n"
                print("  Manufacturer Id         : " + str(manufacturer_id))
                mail_body += '<tr><td style="width: 200px">Manufacturer Id</td><td style="width: 300px;">' + str(manufacturer_id) + '</td></tr>' + "\n"
                print("  Model Number            : " + str(model_number))
                mail_body += '<tr><td style="width: 200px">Model Number</td><td style="width: 300px;">' + str(model_number) + '</td></tr>' + "\n"
                print("  WWN                     : " + str(wwn))
                mail_body += '<tr><td style="width: 200px">WWN</td><td style="width: 300px;">' + str(wwn) + '</td></tr>' + "\n" + '</tbody></table>'

            ###

        # HBA Contoller
        if 'Physical Device Information' in ctrl_info['Controllers'][0]['Response Data']:    
            cont_phdr_inf   = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information']
 
            # Print disks table
            for d in cont_phdr_inf:
                if 'Detailed Information' not in d:
                    d_inf = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][d][0]
                    print(d_inf['EID:Slt'] + "\t" + str(d_inf['DID']) + "\t" , end='')
                    mail_body += '<tr style="text-align: center;"><td>' + d_inf['EID:Slt'] + '</td><td>' + str(d_inf['DID']) + '</td><td style="background-color: '
                    if ("JBOD" == d_inf['State']):
                        print(bcolors.OKGREEN + d_inf['State'] + bcolors.ENDC + "\t", end='')
                        bg_color = '#339966'
                    if ("Onln" == d_inf['State']) or ("UGood" == d_inf['State']) :
                        print(bcolors.OKGREEN + d_inf['State'] + bcolors.ENDC + "\t", end='')
                        bg_color = '#339966'
                    if ("Failed" == d_inf['State']) or ("UBad" == d_inf['State']):
                        print(bcolors.FAIL    + d_inf['State'] + bcolors.ENDC + "\t", end='')
                        bg_color = '#ff0000'
                        alarm = True
                    if "GHS" == d_inf['State']:
                        print(bcolors.OKCYAN  + d_inf['State'] + bcolors.ENDC + "\t", end='')
                        bg_color = '##0000ff'
                    if "Rbld" == d_inf['State']:
                        print(bcolors.WARNING + d_inf['State'] + bcolors.ENDC + "\t", end='')
                        bg_color = '#ffcc00'
                        alarm = True
                    mail_body += bg_color + ';">' + d_inf['State'] + '</td><td>' + str(d_inf['DG']) + '</td><td>' + d_inf['Size'] + '</td><td>' + d_inf['Intf'] + '</td><td>' + str(d_inf['Model']).replace(" ","") + '</td></tr>' + "\n"
                    print(str(d_inf['DG']) + "\t" + d_inf['Size'] + "\t" + d_inf['Intf'] + "\t" + str(d_inf['Model']).replace(" ",""))
            mail_body += '</tbody></table>'

            # Get info from disks
            print()
            for d in cont_phdr_inf:
                if 'Detailed Information' not in d:
                    print()
                    d_inf = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][d][0]
                    #Get Drive info
                    if str(d_inf['EID:Slt']).split(":")[0] == '':
                        drive_path = "Drive /c" + str(controller) + "/e"+ str(d_inf['EID:Slt']).split(":")[0] + "/s" + str(d_inf['EID:Slt']).split(":")[1]
                    else:
                        drive_path = "Drive /c" + str(controller) + "/s" + str(d_inf['EID:Slt']).split(":")[1]

                    print(drive_path)
                    mail_body += '<br><table style="border-collapse: collapse; width: 500px; height: 200px;" border="1"><tbody>' + "\n"
                    mail_body += '<tr><td style="width: 200px" colspan="2">' + drive_path + '</td></tr>' + "\n"
                    sn                = str(ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['SN']).replace(" ","")
                    manufacturer_id   = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Manufacturer Id']
                    model_number      = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Model Number']
                    wwn               = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['WWN']

                    print("  SN                      : " + str(sn))
                    mail_body += '<tr><td style="width: 200px">SN</td><td style="width: 300px;">' + str(sn) + '</td></tr>' + "\n"
                    print("  Manufacturer Id         : " + str(manufacturer_id))
                    mail_body += '<tr><td style="width: 200px">Manufacturer Id</td><td style="width: 300px;">' + str(manufacturer_id) + '</td></tr>' + "\n"
                    print("  Model Number            : " + str(model_number))
                    mail_body += '<tr><td style="width: 200px">Model Number</td><td style="width: 300px;">' + str(model_number) + '</td></tr>' + "\n"
                    print("  WWN                     : " + str(wwn))
                    mail_body += '<tr><td style="width: 200px">WWN</td><td style="width: 300px;">' + str(wwn) + '</td></tr>' + "\n" + '</tbody></table>'


    ###
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


    if alarm == True:
        print()
        print("Health: " + bcolors.FAIL + "Triggered alarm" + bcolors.ENDC)
        if not os.path.exists(alarm_tmp_file):
            alarm_file = open(alarm_tmp_file, "w")
            try:
                send_mail()
            except Exception as err:
                print(err)
    else:
        print()
        print("Health: " + bcolors.OKGREEN + "OK" + bcolors.ENDC)
        if os.path.exists(alarm_tmp_file):
            os.remove(alarm_tmp_file)
            try:
                send_mail()
            except Exception as err:
                print(err)
    if mail_send == 1:
        try:
            send_mail()
        except Exception as err:
            print(err)

# Where to process
if namespace.server != 'localhost':
    print("Get info from: " + namespace.server)
    #Get controllers info
    r_cmd = "ssh " + r_user + "@" + namespace.server + " " + r_storcli_path
    get_info(r_cmd, namespace.count)
else:
    print("Get info from local strocli")
    l_cmd = namespace.path
    get_info(l_cmd, namespace.count)

# Removing lock file
if os.path.exists(lock_file):
    os.remove(lock_file)
