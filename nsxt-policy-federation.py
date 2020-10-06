#!/usr/bin/env python
# Script to get the IP of Tier-1 downlinks and ping them.
# This script is neither supported nor endorsed by VMware but meant as an example of python.

from json import loads, dumps
from requests import get, patch
from requests.packages.urllib3 import disable_warnings
from requests.auth import HTTPBasicAuth
from copy import deepcopy
from ast import literal_eval
disable_warnings()


hostname = "10.114.218.181"
username = "admin"
password = "VMware1!VMware1!"
mgr_type = "global"
domains = ["LM-Paris","LM-London"]
resource_types =["Domain","SecurityPolicy","Group","Rule"]


class NsxMgr:
    def __init__(self, hostname, username, password, mgr_type = "local", certificate_validation = False):
        self.hostname = str(hostname)
        self.username = str(username)
        self.password = str(password)
        self.certificate_validation = certificate_validation
        self.mgr_type = mgr_type

    def path(self):
        """Method to define which path applies between GM and LM"""
        if self.mgr_type == "local":
            path = "policy/api/v1/infra"
        elif self.mgr_type == "global":
            path = "global-manager/api/v1/global-infra"
        return path

    def tree(self):
        """Method to define which tree applies between GM and LM"""
        if self.mgr_type == "local":
            tree = "/infra"
        elif self.mgr_type == "global":
            tree = "/global-infra"
        return tree

    def uri_infra(self):
        """Method to get the endpoing URI """
        path = self.path()
        return f"https://{self.hostname}/{path}"

    def get_conf(self, resource_types):
        """Method to get NSX-T logical configuration leveraging Policy Filters"""
        filter = "?filter=Type-" + "|".join(resource_types)
        uri = self.uri_infra() + filter
        res = get(  uri,
                    verify = self.certificate_validation,
                    auth = HTTPBasicAuth(self.username, self.password)
                    )
        return res.content.decode()

    def patch_conf(self, body):
        """Method to do patch against NSX-T manager"""
        uri = self.uri_infra()
        #print(uri)
        headers = {"content-type": "application/json"}
        res = patch(uri,
                    data = body,
                    headers = headers,
                    verify = self.certificate_validation,
                    auth = HTTPBasicAuth(self.username, self.password)
                    )
        return {"status_code" : res.status_code, "response_text" : res.text}

    def conf_convert_gm(self, body, manage_domain = 0, dest_domain = 'default', src_domain = 'default'):
        """Changes the path from a LM path to a GM path. Optionally changes the
        domain too"""
        body = body.replace("policy/api/v1/infra","global-manager/api/v1/global-infra")
        body = body.replace("/infra","/global-infra")

        if manage_domain != 0:
            print("Changing the domain")
            body = body.replace(f"/domains/{src_domain}", f"/domains/{dest_domain}")

        return body

    def conf_prune(self, resource_types, to_remove):
        """Allows to prune a configuration in order to remove system generated,
        default or other unwanted configuration. Covers config under Infra and
        under Domain."""
        pruned_list = []
        body = loads(self.get_conf(resource_types))

        infra_children = body["children"]
        pruned_infra_children = deepcopy(infra_children)


        for resource in resource_types:
            if resource in ["SecurityPolicy","Group","GatewayPolicy","EndpointPolicy","DomainDeploymentMap"]:
                #Resources under Domain

                for infra_child in infra_children:
                    pruned_domain_children = deepcopy(infra_child["Domain"]["children"])

                    for domain_child in infra_child["Domain"]["children"]:
                        for key in to_remove:
                            try:
                                if domain_child[resource][key] == to_remove[key]:
                                    pruned_domain_children.remove(domain_child)
                                else:
                                    pass
                            except KeyError:
                                pass
                    infra_child["Domain"]["children"] = pruned_domain_children

            else:
                for infra_child in infra_children:
                    #Resources under Infra
                    for key in to_remove:
                        try:
                            if infra_child[resource][key] == to_remove[key]:
                                pruned_infra_children = pruned_infra_children.remove(infra_child)
                            else:
                                pass
                        except KeyError:
                            pass
        infra_children = pruned_infra_children
        body = dumps(body)
        return body

    def prep_mv_to_default_domain(self, domains, resource_types):
        """Creates dictionaries per domain with rules to add and delete in
        order to move to the default domain"""
        body = self.get_conf(resource_types)
        body = loads(body)
        infra_children = body["children"]

        change_dict = dict()
        change_dict["default"] = []

        for child in infra_children:
            try:
                domain = child["Domain"]
            except KeyError:
                pass

            if domain["id"] in domains:
                change_dict[domain["id"]] =[]
                #print(domain["id"])
                for domain_child in domain["children"]:
                    for resource_type in resource_types:
                        if resource_type == "Domain":
                            pass
                        else:
                            try:
                                #We create the objects in the new domain
                                default_domain_object = deepcopy(domain_child[resource_type])
                                domain_object = deepcopy(domain_child[resource_type])
                                for domain_to_migrate in domains:
                                    default_domain_object = str(default_domain_object).replace(self.tree()  + '/domains/' + domain_to_migrate, self.tree()  + '/domains/default')
                                default_domain_object = literal_eval(default_domain_object)

                                change_dict["default"].append({resource_type:default_domain_object, "resource_type" : "Child" + resource_type})

                                #We prepare the deletion of the object under the domain migrated
                                domain_object = domain_child[resource_type]
                                domain_object["marked_for_delete"] = True
                                change_dict[domain["id"]].append({resource_type:domain_object, "resource_type" : "Child" + resource_type, "marked_for_delete":True})

                            except KeyError:
                                pass
        return change_dict

    def conf_mv_to_default_domain(self, domains, resource_types):
        """Generates the request body to move ChildObjects to default domain."""
        change_dict = self.prep_mv_to_default_domain(domains, resource_types)
        body = {        "resource_type": "Infra",
                        "children": []            }

        for domain in change_dict:
            body["children"].append({
                        "resource_type": "ChildResourceReference",
                        "id": domain,
                        "target_type": "Domain",
                        "children": change_dict[domain]
                        }
            )
        body = dumps(body)
        #print(body)
        return body


if __name__ == "__main__":
    gm = NsxMgr(hostname, username, password, mgr_type)
    conf = gm.conf_mv_to_default_domain(domains, resource_types)
    print(gm.patch_conf(conf))
