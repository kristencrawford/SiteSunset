#!/usr/bin/python -tt

### unixStep3.py
# Kristen Crawford <kristen.crawford@centurylink.com>

"""Shuts down all site servers and then sends an email which upates the Ticket"""

### Module Imports

import requests
import json
import porc
import argparse
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

def powerOff(alias,server):
  headers = clcAuth()
  server_json = [ server ]
  pdRequest = requests.post(clcEndpoint + '/v2/operations/' + alias + '/servers/powerOff',json=server_json,headers=headers)
  pd_json = json.loads(pdRequest.content)
  if pd_json[0]['isQueued'] == True:
    statusUrl = clcEndpoint + pd_json[0]['links'][0]['href']
    getStatus = requests.get(statusUrl,headers=headers)
    status_json = json.loads(getStatus.content)
    while status_json['status'] != 'succeeded':
      print time.ctime() + ': ' + server + ' is powering down..'
      time.sleep(15)
      getStatus = requests.get(statusUrl,headers=headers)
      status_json = json.loads(getStatus.content)
    print time.ctime() + ': ' + server + ' power down has finished with a status of: ' + status_json['status']
  else:
    print time.ctime() + ': ' + server + ' failed to power down! Please go do it manually..'

#Main
site_json = getJSON(args.siteId)

# Find the hardware group id and stop all servers in it
clc.v1.SetCredentials(v1User,v1Pass)
if 'Environments' in site_json:
  for env in site_json['Environments']:
    if env['Requested'] == 'True':
      alias = env['Alias']
      servers = clc.v1.Server.GetAllServers(alias=alias)
      for s in servers:
        if s['PowerState'] == 'Stopped':
          print time.ctime() + ': ' + s['Name'] + ' is already stopped, moving on..'
        else:
          if 'ALOGIC' not in s['Name']:
            powerOff(alias,s['Name'])

else:
  alias = site_json['CLCAccountAlias']
  servers = clc.v1.Server.GetAllServers(alias=alias)
  for s in servers:
    if s['PowerState'] == 'Stopped':
      print time.ctime() + ': ' + s['Name'] + ' is already stopped, moving on..'
    else:
      if 'ALOGIC' not in s['Name']:
        powerOff(alias,s['Name'])
