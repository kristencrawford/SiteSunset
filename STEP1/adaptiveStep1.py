#!/usr/bin/python -tt

### adaptiveStep1.py
# Kristen Crawford <kristen.crawford@centurylink.com>

"""Sends Email to Site Launch, Disables managed backup, Decomms monitoris,"""
"""Sends Notification to alogic and Upates Ticket (via email)"""

### Module Imports

import requests
import json
import porc
import argparse
import mailer
import datetime
import clc
import time
from subprocess import Popen, PIPE, STDOUT
import sys
sys.path.insert(0,"/opt/ko/scripts/lms")
import svvs
import socket

### Arguments

parser = argparse.ArgumentParser(description='Get Site JSON')

parser.add_argument('-i', '--site-id',
                    dest='siteId',
                    required=True,
                    type=str,
                    help='The 6-digit site Id',
                    metavar='SITEID')

parser.add_argument('-r', '--remedy-ticket',
                    dest='remTicket',
                    required=True,
                    type=str,
                    help='The Remedy Ticket Number',
                    metavar='REMTICK')

parser.add_argument('-t', '--tech-stack',
                    dest='techStack',
                    required=True,
                    type=str,
                    help='Tech Stack',
                    metavar='TECHSTACK')

args = parser.parse_args()

### Variables
orch_key = ''
now = datetime.datetime.now()
clcEndpoint='https://api.ctl.io'
v2User=''
v2Pass=''
v2Auth={'username': v2User, 'password': v2Pass}
v1User=''
v1Pass=''
v1Auth={'APIKey': v1User, 'Password': v1Pass}
udpEndpoint=''
udpUser=''
udpPass=''

## Validate data

# Verify site ID is 6 numbers
L1 = list(args.siteId)
L1 = filter(lambda x: x in '1234567890', L1)
num_digits = len(L1)
if int(num_digits) != 6:
  svvs.exitError("Invalid Site ID!")

def clcAuth():
  url = clcEndpoint + '/v2/authentication/login'
  r = requests.post(url,json=v2Auth)
  auth_json = json.loads(r.content)
  token = auth_json['bearerToken']
  h = {"Authorization": "Bearer " + token}
  return h

def getJSON(siteId):
  client = porc.Client(orch_key)
  j = client.get('sites',siteId)
  if 'code' in j.content:
    clc.v1.SetCredentials("baaca24561704a778588cefd79f2ca5a","1]].o!UIq=aeVhX?")
    tccc = clc.v1.Account.GetAccounts(alias="TCCC")
    for item in tccc:
      if siteId in item['BusinessName']:
        dc = item['Location']
        alias = item['AccountAlias']
        p_alias = item['ParentAlias']
        b_name = item['BusinessName']
    k  = {"ApplicationID":siteId,"TechStack":args.techStack,"CLCAccountAlias":alias,"Datacenter":dc,"CLCParentAlias":p_alias,"ApplicationName":b_name}
    return k
  else:
    s = json.loads(j.content)
    return s

def putJSON(siteId,json):
  client = porc.Client(orch_key)
  u = client.put('sites',siteId,json)

def mailNotification(item,remTicket,sendAddress,dc):
  from mailer import Mailer
  from mailer import Message
  ccAddress = ["kristen.crawford@centurylink.com","adaptivesupport@centurylink.com","globalcloudops@coca-cola.com"]
  message = Message(From="adaptivesupport@centurylink.com",
                    To=sendAddress,
                    CC=ccAddress)
  if 'kositelaunch@centurylink.com' in sendAddress:
    message.Subject = "CTL Ticket: " + remTicket + " Site " + item['ApplicationID'] + " is being sunset"
    message.Body = "Remedy Ticket #: " + remTicket
  elif 'tcccorders@alertlogic.com' in sendAddress:
    message.Subject = "CTL Ticket: " + remTicket + " Sunset of Coca-Cola Site " + item['ApplicationID'] + " - " + item['ApplicationName']
    message.Body = "Site " + " - " + item['ApplicationName'] + " is being Sunset. Please stop monitoring and billing for the appliances associated with this site, as they are being decommissioned."
  elif 'kristencrawford78@gmail.com' in sendAddress:
    message.Subject = "Test!"
    message.Body = "Did you get this?"

  sender = Mailer('mail.' + dc + '.ko.cld')
  sender.send(message)

  print time.ctime() + ": Email sent to " + sendAddress + " to notify them of the Site Sunset."

def delHbMon(hbmonServ,siteServ):
  # Find which hb mon server is up and then delete the monitor
  if 'ALOGIC' not in siteServ:
    for mon in hbmonServ.split():
      cmd = '/usr/bin/curl -sL -w "%{http_code}\\n" http://' + mon + ':8087/servers -o /dev/null'
      p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
      sd = p.communicate()[0]
      rc = p.returncode
      if rc == 0:
        siteIP = socket.gethostbyname(siteServ)
        delCmd = '/usr/bin/curl -s -X DELETE http://' + mon + ':8087/servers/' + siteIP
        d = Popen(delCmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True)
        delOutput = d.communicate()[0]
        if delOutput.strip() == "not found":
          print time.ctime() + ": Heartbeat monitor for " + siteServ + " does not exist. Moving on.."
        else:
          print time.ctime() + ": Deleting heartbeat monitor for: " + siteServ
        break

#Main
site_json = getJSON(args.siteId)

# Set DC Specific variables
if site_json['Datacenter'] == 'VA1':
  resource = '9caea7ca-c3e1-400a-86c8-2080d7781b7e'
  hbmon = '10.152.10.32 10.152.10.31'
elif site_json['Datacenter'] == 'UC1':
  resource = "bc83beaa-0eee-4bee-8074-2b5ef5283afa"
  hbmon = '10.152.9.32 10.152.9.33'
elif site_json['Datacenter'] == 'GB3':
  resource = "abc29416-f5ea-4231-97c3-d4161f872b6f"
  hbmon = '10.152.12.32 10.152.12.33'
elif site_json['Datacenter'] == 'SG1':
  resource = "7c944ae6-97b5-4de7-861e-b9782be6345c"
  hbmon = '10.152.14.29 10.152.14.30'
elif site_json['Datacenter'] == 'IL1':
  resource = "169ea1a4-a623-4673-b524-5d0bb7b4cb7c"
  hbmon = '10.152.2.29 10.152.2.30'
else:
  svvs.exitError("Datacenter not found!")

#Add Remedy Ticket and start time to Site JSON
if 'Sunset' not in site_json:
  mailNotification(site_json,args.remTicket,"kositelaunch@centurylink.com",site_json['Datacenter'])
  site_json['Sunset'] = {"Request": args.remTicket,"Date": now.strftime('%Y-%m-%d %H:%M %Z').strip() }

# Run Sunset Process in udeploy
udp_json = {"siteID":args.siteId,"appType":args.techStack,"resource":resource,"properties":{"siteID":args.siteId,"appType":args.techStack,"resource":resource},"processId":"7cd52f9c-d202-449c-8388-f1e064c28ec4"}

requests.packages.urllib3.disable_warnings()
proc_url=udpEndpoint + '/rest/process/request'
udp_sunset = requests.post(proc_url,auth=(udpUser,udpPass),verify=False,json=udp_json)
resp_json = json.loads(udp_sunset.content)
if 'workflowTraceId' not in resp_json:
  print time.ctime() + ": uDeploy Sunset Process did not run, please run it manually!"
else:
  state = requests.get(proc_url + '/' + resp_json['id'],auth=(udpUser,udpPass),verify=False)
  state_json = json.loads(state.content)
  while state_json['trace']['state'] != 'CLOSED':
    print time.ctime() + ": Execution of Sunset Process is: " + state_json['trace']['state']
    time.sleep(15)
    state = requests.get(proc_url + '/' + resp_json['id'],auth=(udpUser,udpPass),verify=False)
    state_json = json.loads(state.content)
  print time.ctime() + ": Execution of Sunset Process has completed with a status: " + state_json['trace']['result']

if 'SecurityTier' in site_json:
  if 'alogic' not in site_json['Sunset']:
    if site_json['SecurityTier'] == "1" or site_json['SecurityTier'] == "2":
      mailNotification(site_json,args.remTicket,"tcccorders@alertlogic.com",site_json['Datacenter'])
      site_json['Sunset']['alogic'] = "notified"
else:
  if 'alogic' not in site_json['Sunset']:
    alias = site_json['CLCAccountAlias']
    clc.v1.SetCredentials("baaca24561704a778588cefd79f2ca5a","1]].o!UIq=aeVhX?")
    servers = clc.v1.Server.GetAllServers(alias=alias)
    for n in servers:
      if 'ALOGIC' in n['Name']:
        mailNotification(site_json,args.remTicket,"tcccorders@alertlogic.com",site_json['Datacenter'])
        site_json['Sunset']['alogic'] = "notified"
        site_json['SecurityTier'] = "1"
        break

# Find all site servers and send them to the delete hb mon function
clc.v1.SetCredentials(v1User,v1Pass)
if 'Environments' in site_json:
  for env in site_json['Environments']:
    if env['Requested'] == 'True':
      if 'Alias' in env:
        alias = env['Alias']
      else:
        alias = site_json['CLCAccountAlias']
      servers = clc.v1.Server.GetAllServers(alias=alias)
      for s in servers:
        delHbMon(hbmon,s['Name'])

else:
  alias = site_json['CLCAccountAlias']
  servers = clc.v1.Server.GetAllServers(alias=alias)
  for s in servers:
    print s['Name']
    if site_json['Datacenter'] in s['Name']:
      delHbMon(hbmon,s['Name'])

putJSON(args.siteId,site_json)
