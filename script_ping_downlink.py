#!/usr/bin/env python
# Script to get the IP of Tier-1 downlinks and ping them.
# This script is neither supported nor endorsed by VMWare.

from requests import get
from requests.auth import HTTPBasicAuth
from os import system, name
import json

#variables:
hostname = "" #hostname of the NSX-T Manager
username = "" #username which should be admin or auditor. Does not support Remote header
password = ""

def get_tier1s_id(hostname, username, password, certificate_validation = False):
    """Function getting the id(s) of your Tier-1 routers. From the MP API."""
    request = get('https://' + hostname + '/api/v1/logical-routers?router_type=TIER1', verify=certificate_validation, auth=HTTPBasicAuth(username, password))
    json = request.json()
    tier1s_id = [tier1['id'] for tier1 in json['results']]
    return tier1s_id


def get_tier1s_downlink_ips(hostname, username, password, tier1s_id, certificate_validation = False):
    """Function getting the downlink IPs of your Tier-1 routers. From the MP API."""
    request = get('https://' + hostname + '/api/v1/logical-router-ports', verify=certificate_validation, auth=HTTPBasicAuth(username, password))
    json = request.json()
    tier1s_downlink_ips = {}
    for tier1_id in tier1s_id:
        tier1s_downlink_ips[tier1_id] = [ port["subnets"][0]["ip_addresses"][0] for port in json['results'] if port["logical_router_id"] == tier1_id and port["resource_type"]=="LogicalRouterDownLinkPort" ]
    return tier1s_downlink_ips

def ping_ips(list_ips, ping_options = ""):
    """Function leveraging your OS ping to test a list of IPs. The ping option depends of your OS."""
    for ip in list_ips:
        print(f"We are pinging {ip}")
        ping = system('ping ' + ping_options + ip)
    return(ping)

if __name__ == "__main__":
    "This script pings a list of IPs it gets from Tier-1 downlink interface. It assumes the VM has connectivity to those IPs and this IPs are not used somewhere else."
    tier1s_id = get_tier1s_id(hostname, username, password)
    tier1s_downlink_ips = get_tier1s_downlink_ips(hostname, username, password, tier1s_id)

    for id in tier1s_id:
        print(f"We are pinging the interfaces of tier1 {id}, those interfaces have the following IPs {tier1s_downlink_ips[id]}")
        print(ping_ips(tier1s_downlink_ips[id],"-c 2 ")) #This option works for Linux or Mac, you can remove it for windows or put windows specific options
