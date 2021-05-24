#!/usr/bin/env python
# Requires Python 3.x
# Author: Thomas Vigneron <tvigneron>
# Additions: Madhukar Krishnarao <madhukark>
# Script to move delete groups from specific domains on GM
# This script is neither supported nor endorsed by VMware but meant as an example

import json
import warnings
from json import loads, dumps
from requests import get, patch, delete
from requests.packages.urllib3 import disable_warnings
from requests.auth import HTTPBasicAuth
from copy import deepcopy
from ast import literal_eval
disable_warnings()
warnings.filterwarnings("ignore")

#put your Global Manager IP or FQDN
hostname = "gm-paris.corp.local"

#put your username
username = "admin"

#put your password
password = "VMware1!VMware1!"

#put the list of Region / Locations from which you want to make Global
domains = ["LM_Paris","LM_London"]


class NsxMgr:
    def __init__(self, hostname, username, password, mgr_type = "global", certificate_validation = False):
        self.hostname = str(hostname)
        self.username = str(username)
        self.password = str(password)
        self.certificate_validation = certificate_validation
        self.mgr_type = mgr_type
        self.tree = "/global-infra"
        self.path = "/global-manager/api/v1/global-infra"
        self.url = "https://" + self.hostname + self.path

    def patch_group(self, body, domain, id):
        """Method to do patch against NSX-T manager"""
        print(domain)
        uri = self.url + "/domains" + domain + "/groups/" + id
        #print(uri)
        headers = {"content-type": "application/json"}
        res = patch(uri,
                    data = body,
                    headers = headers,
                    verify = self.certificate_validation,
                    auth = HTTPBasicAuth(self.username, self.password)
                    )
        return {"status_code" : res.status_code, "response_text" : res.text}

    def get_groups(self, domain):
        """Return groups of a given domain"""
        print(domain)
        uri = self.url + "/domains/" + domain + "/groups/"
        print(uri)
        res = get(  uri,
                    verify = self.certificate_validation,
                    auth = HTTPBasicAuth(self.username, self.password)
                    )
        return res.content.decode()

    def delete_group(self, domain, id):
        """Delete a given group"""
        uri = self.url + "/domains/" + domain + "/groups/" + id
        print(uri)
        res = delete(uri,
                    verify = self.certificate_validation,
                    auth = HTTPBasicAuth(self.username, self.password)
                    )
        return {"status_code" : res.status_code, "response_text" : res.text}

    def delete_groups(self, domains):
        print(domains)
        for domain in domains:
            groups = loads(self.get_groups(domain))
            print(groups)
            for group in groups["results"]:
                print("Trying to delete the following group: %s" % group["id"])
                print(self.delete_group(domain, group["id"]))


if __name__ == "__main__":
    #Logs against the Global Manager:
    print ("")
    print ("Connecting to Global Manager: %s" % hostname)
    gm = NsxMgr(hostname, username, password)
    #Delete Groups from domains:
    gm.delete_groups(domains)
