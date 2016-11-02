#!/usr/bin/python -tt

### dbaStep2.py
# Kristen Crawford <kristen.crawford@centurylink.com>

"""Takes a dump of the database and sends it to the dropbox"""

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

def clcV2Auth():
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

#Main
site_json = getJSON(args.siteId)

gName = None
resGroupId = None

# Verify if Prod exists, otherwise you will need a test backup
if 'Environments' in site_json:
  for env in site_json['Environments']:
    if env['Name'] == 'Production' and env['Requested'] == True:
      gName = 'ProdDB'

if gName is None:
  gName = 'TestDB'       
# Find the Prod db server by getting the res group id and the server in it
requests.packages.urllib3.disable_warnings()
treeUrl=udpEndpoint + '/rest/resource/resGroup/tree'
tree = requests.get(treeUrl,auth=(udpUser,udpPass),verify=False)
tree_json = json.loads(tree.content)
for top in tree_json:
  for item in top['children']:
    if item['name'] == site_json['ApplicationID']:
      for i in item['children']:
        if i['name'] == gName:
          resGroupId = i['id']

if resGroupId is None:
  print time.ctime() + ": There is no database group on udeploy, so the dump cannot be performed.  Notify the dba team to take it manually and then resume the process!"
  exit(1)

dbUrl = udpEndpoint + '/rest/resource/resGroup/static/' + resGroupId + '/resources'
dbGroup = requests.get(dbUrl,auth=(udpUser,udpPass),verify=False)
db_json = json.loads(dbGroup.content)
dbId = db_json[0]['id']
  

dbDump_json = {"resource":dbId,"properties":{"resource":dbId},"processId":"0f91014f-c6ce-4443-b92c-405fc85bf491"}

reqUrl = udpEndpoint + '/rest/process/request'
runDump = requests.post(reqUrl,auth=(udpUser,udpPass),verify=False,json=dbDump_json)
dump_json = json.loads(runDump.content)
if 'workflowTraceId' not in dump_json:
  print time.ctime() + ": The database dump failed, please run it manually!"
else:
  state = requests.get(reqUrl + '/' + dump_json['id'],auth=(udpUser,udpPass),verify=False)
  state_json = json.loads(state.content)
  while state_json['trace']['state'] != 'CLOSED':
    print time.ctime() + ": Execution of Database Dump is: " + state_json['trace']['state']
    time.sleep(15)
    state = requests.get(reqUrl + '/' + dump_json['id'],auth=(udpUser,udpPass),verify=False)
    state_json = json.loads(state.content)
  print time.ctime() + ": Execution of database dump to dropbox finished with status: " + state_json['trace']['result']
  if state_json['trace']['result'] == "FAULTED":
    print time.ctime() + ": The backup of the database failed.  Please login and do it manually!"
