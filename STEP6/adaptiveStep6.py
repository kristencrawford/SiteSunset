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

def delMIP(alias,server,ip):
  headers = clcAuth()
  delRequest = requests.delete(clcEndpoint + '/v2/servers/' + alias + '/' + server + '/publicIPAddresses/' + ip,headers=headers)
  del_json = json.loads(delRequest.content)
  if 'message' in del_json:
    print time.ctime() + ': ' + ip + ' was not deleted!! Error message: ' + del_json['message'] + '. Please complete it manually'
  else:
    print time.ctime() + ': ' + ip + ' was deleted from ' + server

def delGroup(alias,uuid,name,dc):
  headers = clcAuth()
  delRequest = requests.delete(clcEndpoint + '/v2/groups/' + alias + '/' + uuid,headers=headers)
  del_json = json.loads(delRequest.content)
  if 'message' in del_json:
    print time.ctime() + ': Group "' + name + '" was not deleted from ' + dc + '!! Error message: ' + del_json['message'] + '. Please complete it manually'
  else:
    print time.ctime() + ': Group "' + name + '" was deleted from ' + dc

def delNetwork(alias,dc):
  headers = clcAuth()
  networks = requests.get(clcEndpoint + '/v2-experimental/networks/' + alias + '/' + dc,headers=headers)
  net_json = json.loads(networks.content)
  for n in net_json:
    for l in n['links']:
      if l['rel'] == 'release':
        delNet = requests.post(clcEndpoint + l['href'],headers=headers)
        if delNet.content == '':
          print time.ctime() + ': Network "' + n['name'] + '" has been deleted from ' + dc
        else:
          delNet_json = json.loads(delNet.content)
          if delNet_json['message'] != "Cannot release network with active servers":
            print time.ctime() + ': Network "' + n['name'] + '" could not be deleted from ' + dc + '! Reason given: ' + delNet_json['message']

def delFwRules(sAlias,dAlias,dc):
  headers = clcAuth()
  intra = clcEndpoint + '/v2-experimental/firewallPolicies/' + sAlias + '/' + dc + '?destinationAccount=' + dAlias
  getRules = requests.get(intra,headers=headers)
  rules_json = json.loads(getRules.content)
  for i in rules_json:
    delUrl = clcEndpoint + i['links'][0]['href'] 
    d = requests.delete(delUrl,headers=headers)
    if d.status_code is 204:
      print time.ctime() + ': Firewall rule "' + i['id'] + '" has been deleted from ' + dc
    else:
      print time.ctime() + ': Firewall rule "' + i['id'] + '" has NOT been deleted from ' + dc + '.. Please delete it manually!'

def delXdcRules(sAlias,dAlias,dc):
  headers = clcAuth()
  xdcUrl = clcEndpoint + '/v2-experimental/crossDcFirewallPolicies/' + sAlias + '/' + dc + '?destinationAccountId=' + dAlias
  xdc = requests.get(xdcUrl,headers=headers)
  xdc_json = json.loads(xdc.content)
  for x in xdc_json:
    delXdcUrl = clcEndpoint + x['links'][0]['href']
    d = requests.delete(delXdcUrl,headers=headers)
    if d.status_code is 204:
      print time.ctime() + ': Cross Datacenter Firewall rule "' + x['id'] + '" has been deleted from ' + dc
    else:
      print time.ctime() + ': Cross Datacenter Firewall rule "' + x['id'] + '" has NOT been deleted from ' + dc + '.. Please delete it manually!'

def delLoadBalancer(alias,dc):
  headers = clcAuth()
  getLbUrl = clcEndpoint + '/v2/sharedLoadBalancers/' + alias + '/' + dc
  lb = requests.get(getLbUrl,headers=headers)
  lb_json = json.loads(lb.content)
  for l in lb_json:
    delLbUrl = clcEndpoint + l['links'][0]['href']
    d = requests.delete(delLbUrl,headers=headers)
    if d.status_code is 204:
      print time.ctime() + ': Shared Loadbalancer has been deleted from ' + dc
    else:
      print time.ctime() + ': Shared Loadbalancer has NOT been deleted from ' + dc + '.. Please delete it manually!'

def mailNotification(alias,remTicket,sendAddress):
  from mailer import Mailer
  from mailer import Message
  ccAddress = ["kristen.crawford@centurylink.com","adaptivesupport@centurylink.com"]
  message = Message(From="adaptivesupport@centurylink.com",
                    To=sendAddress,
                    CC=ccAddress)
  message.Subject = "Please close account: " + alias + ", CTL Ticket: " + remTicket
  message.Body = "Please close account: " + alias + "\nUsername: automation.tccc\nPin:725383\n\nIn the absence of an API call for 'Request to Close', this email was created by automation used to decommission account resources and finally this account. Please do the needful."

  hostname = socket.gethostname()
  dc = hostname[0:3]
  sender = Mailer('mail.' + dc + '.ko.cld')
  sender.send(message)

  print time.ctime() + ": Email sent to " + sendAddress + " to request site closure for " + alias


#Main
site_json = getJSON(args.siteId)
DC=['VA1','GB3','IL1','SG1','UC1']

clc.v1.SetCredentials(v1User,v1Pass)
if 'Environments' in site_json:
  for env in site_json['Environments']:
    if env['Requested'] == 'True':
      alias = env['Alias']
      servers = clc.v1.Server.GetAllServers(alias=alias)
      
      # Delete External VIP from site servers
      for s in servers:
        for i in s['IPAddresses']:
          if 'MIP' in i['AddressType']:
            delMIP(alias,s['Name'],i['Address'])

      # Delete Groups in each DC
      for dc in DC:
        groups = clc.v1.Group.GetGroups(alias=alias,location=dc)
        for g in groups:
          if g['ParentUUID']:
            if site_json['ApplicationID'] in g['Name']:
              delGroup(alias,g['UUID'],g['Name'],dc)

        # Delete networks in each DC
        delNetwork(alias,dc)

        # Delete all intra dc firewall rules
        delFwRules(alias,alias,dc)
        delFwRules('TCCC',alias,dc) 
        delFwRules(alias,'TCCC',dc)
        delXdcRules('TCCC',alias,dc)
        
        # Delete Shared Loadbalancer
        delLoadBalancer(alias,dc)

      # Send NOC request to close accounts
      mailNotification(alias,site_json['Sunset']['Request'],'support@t3n.zendesk.com')

else:
  alias = site_json['CLCAccountAlias']
  servers = clc.v1.Server.GetAllServers(alias=alias)
  for s in servers:
    for i in s['IPAddresses']:
      if 'MIP' in i['AddressType']:
        delMIP(alias,s['Name'],i['Address'])
  for dc in DC:
    groups = clc.v1.Group.GetGroups(alias=alias,location=dc)
    for g in groups:
      if g['ParentUUID']:
        if site_json['ApplicationID'] in g['Name']:
          delGroup(alias,g['UUID'],g['Name'],dc)
    # Delete networks in each DC
    delNetwork(alias,dc)

    # Delete all intra dc firewall rules
    delFwRules(alias,alias,dc)
    delFwRules('TCCC',alias,dc)
    delFwRules(alias,'TCCC',dc)
    delXdcRules('TCCC',alias,dc)

    # Delete Shared Loadbalancer
    delLoadBalancer(alias,dc)

mailNotification(site_json['CLCAccountAlias'],site_json['Sunset']['Request'],'support@t3n.zendesk.com')
