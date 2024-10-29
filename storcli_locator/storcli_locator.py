#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import subprocess
import json
import sys
import os
import re

from textual import on
from textual.binding import Binding
from textual.app import App, ComposeResult
from textual.containers import Container,VerticalScroll
from textual.widgets import Header, Label, Footer, Checkbox

if os.geteuid() != 0:
    exit("Error: You need to have root privileges")
    #print("Error: You need to have root privileges")

# lsblk path
where_lsblk   = subprocess.check_output('which lsblk', shell = True, universal_newlines=True)
lsblk_cmd     = str(where_lsblk).replace('\n','') + " -S -J -o NAME,WWN,HCTL,MODEL,SERIAL"

# Get block devices info
lsblk_req     = subprocess.check_output(lsblk_cmd, shell = True, universal_newlines=True)
lsblk_devs    = json.loads(lsblk_req)

# storcli path
where_storcli = "/opt/MegaRAID/storcli/storcli64"

# storcli check
if not os.path.exists(where_storcli):
    print("Error: Storcli " + where_storcli + " not found. Exit.")
    sys.exit(1)

# Get controllers count
ctrls_count_cmd = where_storcli + " show all J"
storcli_req  = subprocess.check_output(ctrls_count_cmd, shell = True, universal_newlines=True)
storcli_cnt  = json.loads(storcli_req)

if storcli_cnt:
    ctrls_count = storcli_cnt['Controllers'][0]['Response Data']['Number of Controllers']
else:
    print("Error: Failed to get info from storcli. Exit. ")
    sys.exit(1)

# Check number of controllers
if ctrls_count < 1:
    print("Error: No controllers found. Exit.")
    sys.exit(1)
else:
    print("Info: Found (" + str(ctrls_count) + ") controllers.")

# WWN convert function
def convert_wwn(wwn):
    if wwn:
        wwn_node = (hex(int(int(int(wwn,16)) >> 2) << 2))
        return ((wwn_node).replace('0x','')).upper()
###

# stor_locate function
def stor_locate(disk_to_locate_cmd):
    locate_cmd = where_storcli + " " + disk_to_locate_cmd

    try:
        locate_req = subprocess.check_output(locate_cmd, shell = True, universal_newlines=True)
    except:
        print("Failed to run:" + locate_cmd)

    try:
        locate_inf = json.loads(locate_req)
    except:
        print("Failed get json info")
        locate_inf = None

    print(locate_inf)
    if locate_inf:
        return locate_inf
    else:
        print("Failed to locate")
###

stor_disks = list()

for c in range(0, ctrls_count):
    run_cmd = where_storcli + " /c" + str(c) + " show all J"
    print("Info: Run " + run_cmd)

    try:
        get_ctrl_info = subprocess.check_output(run_cmd, shell = True, universal_newlines=True)
    except:
        print("Error: Failed to get info")
        continue

    try:
        ctrl_info = json.loads(get_ctrl_info)
    except:
        print("Error: Failed to load json data")
        continue

    cont_model      = ctrl_info['Controllers'][0]['Response Data']['Basics']['Model']

    if 'PD LIST' in ctrl_info['Controllers'][0]['Response Data']:
        cont_pdlist = ctrl_info['Controllers'][0]['Response Data']['PD LIST']
    else:
        cont_pdlist = None

    # RAID Controller
    if cont_pdlist is not None:
        for d in cont_pdlist:
            run_cmd_d = where_storcli + " /c" + str(c) + " /e" + str(d['EID:Slt']).split(":")[0] + " /s" + str(d['EID:Slt']).split(":")[1] + " show all J"
            print("Info: Run " + run_cmd_d)

            try:
                get_disk_info = subprocess.check_output(run_cmd_d, shell = True, universal_newlines=True)
            except:
                print("Error: Failed to get info")
                continue

            try:
                sm_disk = json.loads(get_disk_info)
            except:
                print("Error: Failed to load json data")
                continue

            if str(d['EID:Slt']).split(":")[0] != '':
                drive_path = "Drive /c" + str(c) + "/e"+ str(d['EID:Slt']).split(":")[0] + "/s" + str(d['EID:Slt']).split(":")[1]
            else:
                drive_path = "Drive /c" + str(c) + "/s" + str(d['EID:Slt']).split(":")[1]

            sn              = str(sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['SN']).replace(' ','')
            manufacturer_id = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Manufacturer Id']
            model_number    = str(sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Model Number']).replace('__','').replace(' ','')
            wwn             = sm_disk['Controllers'][0]['Response Data'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['WWN']

            stor_disk = {'Controller':c,'disk':drive_path,'wwn':wwn,'model':model_number,'sn':sn,'cont_model':cont_model}
            stor_disks.append(stor_disk)

    # HBA Contoller
    if 'Physical Device Information' in ctrl_info['Controllers'][0]['Response Data']:
        cont_phdr_inf   = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information']

        for d in cont_phdr_inf:
            if 'Detailed Information' not in d:
                d_inf = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][d][0]
                #Get Drive info
                if str(d_inf['EID:Slt']).split(":")[0] == '':
                    drive_path = "Drive /c" + str(c) + "/e"+ str(d_inf['EID:Slt']).split(":")[0] + "/s" + str(d_inf['EID:Slt']).split(":")[1]
                else:
                    drive_path = "Drive /c" + str(c) + "/s" + str(d_inf['EID:Slt']).split(":")[1]

                sn              = str(ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['SN']).replace(" ","")
                manufacturer_id = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Manufacturer Id']
                model_number    = str(ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['Model Number']).replace('__','').replace(' ','')
                wwn             = ctrl_info['Controllers'][0]['Response Data']['Physical Device Information'][drive_path + " - Detailed Information"][drive_path + " Device attributes"]['WWN']

                stor_disk = {'Controller':c,'disk':drive_path,'wwn':wwn,'model':model_number,'sn':sn,'cont_model':cont_model}
                stor_disks.append(stor_disk)

if stor_disks:
    print(stor_disks)
else:
    print("Info: No disks found.")

all_disks = list()

for disk in stor_disks:
    found = False
    for dev in lsblk_devs['blockdevices']:
        disk_wwn = convert_wwn(disk['wwn'])
        dev_wwn  = convert_wwn(dev['wwn'])
        if dev_wwn == disk_wwn:
            print("Match device: " + str(disk))

            dev_disk = {'disk':disk['disk'],'wwn':disk['wwn'],'wwnn':disk_wwn,'sn':disk['sn'],'model':disk['model'],'dev':dev['name'],'cont_model':disk['cont_model']}
            all_disks.append(dev_disk)
            found = True
            continue
    if found == False:
        print("No match device: " + str(disk))

        dev_disk = {'disk':disk['disk'],'wwn':disk['wwn'],'wwnn':disk_wwn,'sn':disk['sn'],'model':disk['model'],'cont_model':disk['cont_model']}
        all_disks.append(dev_disk)

print(all_disks)

class ListDisk(VerticalScroll):
    DEFAULT_CSS = """
    .label {
        width: 10;
        max-height: 1;
        height: 1;
        content-align: center middle;
    }

    .checkbox {
        width: 100;
        height: auto;
        background: black;
        border: dashed orange;
    }

    .container {
        border: solid red;
        layout: horizontal;
        width: 100;
        height: 5;
        overflow: auto auto;
    }
    """

    def __init__(self):
        super().__init__()

    def compose(self):

        self.label = Label()
        yield Container(
            Label("INFO: "),
            self.label, classes="container")

        with VerticalScroll():
            for stordev in all_disks:
                dev_id = 'id-' + stordev['wwn']
                if 'dev' in stordev:
                    yield Checkbox(str(stordev['disk']) + " wwn:" + stordev['wwn'] + " (" + stordev['wwnn']+ ")" + " (" + stordev['dev'] + ") at " + stordev['cont_model'], id=dev_id, classes="checkbox")
                else:
                    yield Checkbox(str(stordev['disk']) + " wwn:" + stordev['wwn'] + " (" + stordev['wwnn'] + ") at " + stordev['cont_model'], id=dev_id, classes="checkbox")

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        ch_id    = event.checkbox.id
        ch_state = event.checkbox.value
        for sdev in all_disks:
            if sdev['wwn'] in ch_id:
                d_disk  = sdev['disk'].replace('Drive ','')
                d_model = sdev['model']
                d_sn    = sdev['sn']
                d_wwn   = sdev['wwn']

        if ch_state:
            run_locate = stor_locate(str(d_disk + " start locate J"))
            self.query_one(str('#' + ch_id), Checkbox).styles.border = ("dashed", "blue")
        else:
            run_locate = stor_locate(str(d_disk + " stop locate J"))
            self.query_one(str('#' + ch_id), Checkbox).styles.border = ("dashed", "orange")


        locate_status = run_locate['Controllers'][0]['Command Status']['Status']
        locate_descr  = run_locate['Controllers'][0]['Command Status']['Description']

        self.label.update("Status:" + str(locate_status) + " (" + locate_descr + ")" + "\nDisk:" + str(d_disk) + " Model:" + d_model + "\nSN:" + d_sn + " WWN:" + d_wwn)

class StorApp(App):
    BINDINGS = [Binding(key="q", action="quit", description="Quit")]
    DEFAULT_CSS = """
    Container {
        background: black;
        color: white;
        text-style: bold;
    }
    """
    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        yield Container(ListDisk())
        self.title = "TUI to blink devices for Storcli"

StorApp().run()
