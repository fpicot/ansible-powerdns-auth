#!/usr/bin/python
# SPDX-FileCopyrightText: 2021 Kevin P. Fleming <kevin@km6g.us>
# SPDX-License-Identifier: Apache-2.0
# -*- coding: utf-8 -*-

import sys

from ansible.module_utils.basic import AnsibleModule

from ..module_utils.api_module_args import API_MODULE_ARGS
from ..module_utils.api_wrapper import APINetworkWrapper

assert sys.version_info >= (3, 10), "This module requires Python 3.10 or newer."

DOCUMENTATION = """
%YAML 1.2
---
module: pdns_auth_network

short_description: Manages a network in a PowerDNS Authoritative server

description:
  - This module allows a task to manage the presence of a network
    in a PowerDNS Authoritative server.

requirements:
  - bravado

extends_documentation_fragment:
  - kpfleming.powerdns_auth.api_details

options:
  state:
    description:
      - If C(present) the network will be created if necessary; if it
        already exists, its configuration will be updated to match
        the provided attributes.
      - If C(absent) the network will be removed it if exists.
      - If C(exists) the network's existence will be checked, but it
        will not be modified.
    choices: [ 'present', 'absent', 'exists' ]
    type: str
    required: false
    default: 'present'
  network:
    description:
      - CIDR of the network to be managed.
    type: str
    required: true
  view:
    description:
      - The View name the network should be associated with.
      - Required when C(state) is C(present).
    type: str
    required: false
  key:
    description:
      - The base-64 encoded key value.
    type: str

author:
  - Kevin P. Fleming (@kpfleming)
"""

EXAMPLES = """
%YAML 1.2
---
- name: check that network exists
  pdns_auth_network:
    network: 10.0.0.0/8
    state: exists
    api_key: 'foobar'

- name: create network in view private
  pdns_auth_network:
    network: 10.0.0.0/8
    view: private
    state: present
    api_key: 'foobar'

- name: remove network
  pdns_auth_network:
    network: 10.0.0.0/8
    state: absent
    api_key: 'foobar'
"""

RETURN = """
%YAML 1.2
---
network:
  description: Network CIDR
  returned: always
  type: str
exists:
  description: Indicate whether the key exists
  returned: always
  type: bool
view:
  description: view associated with the network
  returned: when present
  type: str
"""


def main():
    module_args = {
        "state": {
            "type": "str",
            "default": "present",
            "choices": ["present", "absent", "exists"],
        },
        "network": {
            "type": "str",
            "required": True,
        },
        **API_MODULE_ARGS,
        "view": {
            "type": "str",
        },
    }

    module = AnsibleModule(argument_spec=module_args, supports_check_mode=True)

    state = module.params["state"]
    network = module.params["network"]

    ip, _, prefixlen = network.partition('/')
    network_info = None

    result = {
        "changed": False,
    }

    if module.check_mode:
        module.exit_json(**result)

    # create an object to proxy the raw API object
    # and curry the server_id into all API calls
    # automatically, along with handling
    # predictable exceptions
    api_client = APINetworkWrapper(module=module, result=result, object_type="networks")

    result["network"] = network
    result["exists"] = False

    partial_network_info = [k for k in api_client.listNetworks()["networks"] if k["network"] == network]
    if len(partial_network_info) == 0:
        if state in ("exists", "absent"):
            # exit as there is nothing left to do
            module.exit_json(**result)
    else:
        network_info = api_client.getNetwork(ip=ip, prefixlen=prefixlen)

        result["view"] = network_info["view"]
        result["exists"] = True

    # if only an existence check was requested,
    # the operation is complete
    if state == "exists":
        module.exit_json(**result)

    # if absence was requested, set empty view and exit
    if state == "absent":
        api_client.setNetwork(ip=ip, prefixlen=prefixlen, view='')
        result["changed"] = True
        module.exit_json(**result)

    # state must be 'present'
    if not module.params["view"]:
        module.fail_json(msg="'view' must be specified is state is present", **result)

    view = module.params["view"]

    if network_info is None or network_info["view"] != view:
        # Network is missing, or with wrong view
        api_client.setNetwork(ip=ip, prefixlen=prefixlen, view=view)
        result["view"] = view
        result["exists"] = True
        result["changed"] = True

    module.exit_json(**result)


if __name__ == "__main__":
    main()
