#!/usr/bin/python -tt

### webStep5.py
# Kristen Crawford <kristen.crawford@centurylink.com>

"""Tools Cleanup (udeploy,puppet,svn,splunk"""

### Module Imports

import requests
import json
import porc
import argparse
import datetime
import time
from subprocess import Popen, PIPE, STDOUT
import sys
sys.path.insert(0,"/opt/ko/scripts/lms")
import svvs
import yaml
import pysvn
import os

# Ensure that the script is not run by root user
if os.geteuid() == 0:
  exit("You are root! Please try again, this time as 'svadmin'. Exiting.")

### Configuration

# Puppet Master hostname
with open('/etc/hosts', 'r') as inF:
  for line in inF:
    if 'pup-master' in line:
      host = line.split( )[1]
userHost = 'koauto@' + host

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

def commitRemove(toDel,siteId):
  # Delete yaml to Subversion and commit 
  svnClient = pysvn.Client()

  try:
     svnClient.remove(toDel)
  except:
     svvs.exitError('Failed to delete ' + toDel + ' file from Subversion.')

  commitMsg = 'Deleting ' + str(toDel) + ' for site ' + siteId + ' sunset'

  # Commit the changes
  try:
     svnClient.checkin((toDel),commitMsg)
  except:
     svvs.exitError('Failed to commit delete of ' + toDel +
                    ' to Subversion.')

def commitToPuppet(command):
  ssh = Popen(["ssh", "%s" % userHost, command],
               shell=False,
               stdout=PIPE,
               stderr=PIPE)
  result = ssh.stdout.readlines()
  if result == []:
      error = ssh.stderr.readlines()
      print time.ctime() + ": " + command + " was not run on puppet master! Go run it manually!"
      exit(1)
  else:
    print time.ctime() + ": " + command + " was run on the puppet master successfully"

#Main
site_json = getJSON(args.siteId)

requests.packages.urllib3.disable_warnings()

# Find components and remove them
url = udpEndpoint + '/rest/deploy/application/' + site_json['ApplicationID']
components = requests.get(url + '/components',auth=(udpUser,udpPass),verify=False)
comp_json = json.loads(components.content)
for comp in comp_json:
  # Remove it from application
  rem_json = {"components":[comp['id']]}
  remove = requests.put(url + '/removeComponents',auth=(udpUser,udpPass),verify=False,json=rem_json)
  if remove.status_code is 200:
    print time.ctime() + ": Component " + comp['name'] + " was removed from " + site_json['ApplicationID'] 
  else:
    print time.ctime() + ":  Component " + comp['name'] + " was not removed from " + site_json['ApplicationID'] + "Bailing..."
    exit(1)
  # Delete it from the console
  compUrl = udpEndpoint + '/rest/deploy/component/' + comp['id']
  comp_delete = requests.delete(compUrl,auth=(udpUser,udpPass),verify=False)
  if comp_delete.status_code is 204:
    print time.ctime() + ": Component " + comp['name'] + " has been deleted"
  else:
    print time.ctime() + ": Component " + comp['name'] + " has not been deleted!! Please do it manually"
  

# Find environments and remove them
envs = requests.get(url + '/fullEnvironments',auth=(udpUser,udpPass),verify=False)
env_json = json.loads(envs.content)
for env in env_json:
  env_url = udpEndpoint + '/rest/deploy/environment/' + env['id']
  env_delete = requests.delete(env_url,auth=(udpUser,udpPass),verify=False)
  if env_delete.status_code is 204:
    print time.ctime() + ": Environment " + env['name'] + " was removed from " + site_json['ApplicationID']
  else:
    print time.ctime() + ":  Environment " + env['name'] + " was not removed from " + site_json['ApplicationID'] + "Bailing..."
    exit(1)

# Inactivate the application
get_app = requests.get(url,auth=(udpUser,udpPass),verify=False)
app_json = json.loads(get_app.content)
if app_json['active'] is True:
  inactivate = requests.put(url + '/inactivate',auth=(udpUser,udpPass),verify=False)
  if inactivate.status_code is 200:
    print time.ctime() + ": Application " + site_json['ApplicationID'] + " has been inactivated"
  else:
    print time.ctime() + ": Application " + site_json['ApplicationID'] + " has not been inactivated, please do it manually!!"

# Find all servers and remove their agent, resource and group
resGroupId = None
resUrl = udpEndpoint + '/rest/resource'
tree = requests.get(resUrl + '/resGroup/tree',auth=(udpUser,udpPass),verify=False)
tree_json = json.loads(tree.content)
for t in tree_json[0]['children']:
  if t['name'] == site_json['ApplicationID']:
    resGroupId = t['id']

if resGroupId:
  servers = requests.get(resUrl + '/resGroup/static/' + resGroupId + '/inheritedResources',auth=(udpUser,udpPass),verify=False)
  serv_json = json.loads(servers.content)
  for s in serv_json:
    res_delete = requests.delete(resUrl + '/resource/' + s['id'],auth=(udpUser,udpPass),verify=False)
    if res_delete.status_code is 204:
      agentUrl = udpEndpoint + '/rest/agent'
      agents = requests.get(agentUrl,auth=(udpUser,udpPass),verify=False)
      agent_json = json.loads(agents.content)
      for a in agent_json:
        if a['name'] == s['name']:
          agent_delete = requests.delete(agentUrl + '/' + a['id'],auth=(udpUser,udpPass),verify=False)
          if agent_delete.status_code is 204:
            print time.ctime() + ": Resource and Agent have been deleted for server: " + s['name']
          else:
            print time.ctime() + ": Agent was not deleted for server: " + s['name'] + ", please do it manually!!"
    else:
      print time.ctime() + ": Resource and Agent were not deleted for server: " + s['name'] + ", please do it manually!!"

  resGroup_delete = requests.delete(resUrl + '/resGroup/static/' + resGroupId,auth=(udpUser,udpPass),verify=False)
  if resGroup_delete.status_code is 204:
    print time.ctime() + ": Resource Groups for " + site_json['ApplicationID'] + " have been deleted"
  else:
    print time.ctime() + ": Resource Groups for " + site_json['ApplicationID'] + " have NOT been deleted! Please do it manually!"


# Sunset Splunk
cmd = "sudo -u svadmin /opt/ko/scripts/lms/splunkSunset.sh " + site_json['ApplicationID']
p = Popen(cmd, shell=True, stdout=PIPE, stderr=STDOUT)
p.wait()
if p.returncode == 0:
   print time.ctime() + ": Splunk Sunset is complete for " + site_json['ApplicationID']
else:
  output,error = p.communicate()
  print time.ctime() + ": Splunk Sunset failed!! Please review the error and run it manually!"
  print output

if 'IIS' not in site_json['TechStack']:
  # Delete Server yaml files
  for y in os.listdir('/opt/ko/hieradata'):
    if y.endswith(".yaml"):
      serverYaml = os.path.join('/usr/local/svvs/home/svadmin/ko/hieradata/' + y)
      with open(serverYaml,'r') as f:
        doc = yaml.load(f)
        for k,v in doc.iteritems():
          if site_json['ApplicationID'] in v:
            commitRemove(serverYaml,site_json['ApplicationID'])

  # Delete site-config dir
  siteConfDir = os.path.join('/usr/local/svvs/home/svadmin/ko/site-configs/' + site_json['ApplicationID'])
  if os.path.exists(siteConfDir) and os.path.isdir(siteConfDir):
    commitRemove(siteConfDir,site_json['ApplicationID'])

  # Run pupdate and scupdate
  scUpdate = 'sudo /opt/ko/scripts/puppet/scupdate.sh'
  pUpdate = 'sudo /opt/ko/scripts/puppet/pupdate.sh'
  commitToPuppet(scUpdate)
  commitToPuppet(pUpdate)

# Archive and Delete SVN Repo for site
svnHost = 'koauto@vcs.va1.ko.cld'
svnCommand = 'sudo /usr/local/sbin/svn_cleanup.py ' + site_json['ApplicationID']
svnSunset = Popen(["ssh",svnHost,svnCommand],
             shell=False,
             stdout=PIPE,
             stderr=PIPE)
svnSunset.wait()
if svnSunset.returncode == 0:
   print time.ctime() + ": Svn Sunset is complete for " + site_json['ApplicationID']
else:
  output,error = svnSunset.communicate()
  print time.ctime() + ": Svn Sunset failed!! Please review the error and run it manually!"
  print output
