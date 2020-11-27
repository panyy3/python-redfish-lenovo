###
#
# Lenovo Redfish examples - Get bios boot order
#
# Copyright Notice:
#
# Copyright 2020 Lenovo Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
###


import sys
import json
import redfish
import lenovo_utils as utils


def get_bios_bootorder(ip, login_account, login_password, system_id):
    """Get bios boot order
    :params ip: BMC IP address
    :type ip: string
    :params login_account: BMC user name
    :type login_account: string
    :params login_password: BMC user password
    :type login_password: string
    :params system_id: ComputerSystem instance id(None: first instance, All: all instances)
    :type system_id: None or string
    :returns: returns bios boot order inventory when succeeded or error message when failed
    """
    result = {}
    login_host = "https://" + ip
    try:
        # Connect using the BMC address, account name, and password
        # Create a REDFISH object
        REDFISH_OBJ = redfish.redfish_client(base_url=login_host, username=login_account,
                                             password=login_password, default_prefix='/redfish/v1', cafile=utils.g_CAFILE)
        # Login into the server and create a session
        REDFISH_OBJ.login(auth=utils.g_AUTH)
    except:
        result = {'ret': False, 'msg': "Please check the username, password, IP is correct"}
        return result

    try:
        # GET the ComputerSystem resource
        system = utils.get_system_url("/redfish/v1", system_id, REDFISH_OBJ)
        if not system:
            result = {'ret': False, 'msg': "This system id is not exist or system member is None"}
            return result
        boot_info_list = []
        for i in range(len(system)):
            system_url = system[i]
            response_system_url = REDFISH_OBJ.get(system_url, None)
            if response_system_url.status != 200:
                error_message = utils.get_extended_error(response_system_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (system_url, response_system_url.status, error_message)}
                return result

            # Get boot order info via standard api for ThinkSystem servers if standard api exists
            if 'Boot' in response_system_url.dict and 'BootOrder' in response_system_url.dict['Boot'] and 'BootOptions' in response_system_url.dict['Boot']:
                # Get boot order id list
                boot_order_idlist = response_system_url.dict['Boot']['BootOrder']
                # Get boot order id's display name and support name list from BootOptions
                boot_order_idmap = {}
                boot_order_supported = list()
                boot_options_url = response_system_url.dict['Boot']['BootOptions']['@odata.id']
                response_boot_options = REDFISH_OBJ.get(boot_options_url, None)
                if response_boot_options.status != 200:
                    error_message = utils.get_extended_error(response_boot_options)
                    result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (
                        boot_options_url, response_boot_options.status, error_message)}
                    return result
                for boot_member in response_boot_options.dict['Members']:
                    boot_member_url = boot_member['@odata.id']
                    response_boot_member = REDFISH_OBJ.get(boot_member_url, None)
                    if response_boot_member.status != 200:
                        error_message = utils.get_extended_error(response_boot_member)
                        result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (
                            boot_member_url, response_boot_member.status, error_message)}
                        return result
                    boot_order_idmap[response_boot_member.dict['BootOptionReference']] = response_boot_member.dict['DisplayName']
                    boot_order_supported.append(response_boot_member.dict['DisplayName'])

                # Get boot order next id list
                boot_next_idlist = []
                if '@Redfish.Settings' in response_system_url.dict and 'SettingsObject' in response_system_url.dict['@Redfish.Settings']:
                    boot_next_url = response_system_url.dict['@Redfish.Settings']['SettingsObject']['@odata.id']
                else:
                    boot_next_url = system_url + '/Pending'
                response_boot_next = REDFISH_OBJ.get(boot_next_url, None)
                if response_boot_next.status == 200:
                    if 'Boot' in response_boot_next.dict and 'BootOrder' in response_boot_next.dict['Boot']:
                        boot_next_idlist = response_boot_next.dict['Boot']['BootOrder']
                else:
                    boot_next_idlist = boot_order_idlist

                # Set result
                if len(boot_order_supported) >= len(boot_order_idlist):
                    boot_order_current = list()
                    for item in boot_order_idlist:
                        boot_order_current.append(boot_order_idmap[item])
                    boot_order_next = list()
                    for item in boot_next_idlist:
                        boot_order_next.append(boot_order_idmap[item])
                    boot_order_info = {}
                    boot_order_info['BootOrderNext'] = boot_order_next
                    boot_order_info['BootOrderSupported'] = boot_order_supported
                    boot_order_info['BootOrderCurrent'] = boot_order_current
                    boot_info_list.append(boot_order_info)
                    result['ret'] = True
                    result['entries'] = boot_info_list
                    return result

        result = {'ret': False, 'msg': "No related resource found, fail to get bios boot order for target server."}
        return result

    except Exception as e:
        result = {'ret':False, 'msg':"error_message:%s" %(e)}
    finally:
        # Logout of the current session
        try:
            REDFISH_OBJ.logout()
        except:
            pass
        return result


if __name__ == '__main__':
    # Get parameters from config.ini and/or command line
    argget = utils.create_common_parameter_list()
    args = argget.parse_args()
    parameter_info = utils.parse_parameter(args)

    # Get connection info from the parameters user specified
    ip = parameter_info['ip']
    login_account = parameter_info["user"]
    login_password = parameter_info["passwd"]
    system_id = parameter_info['sysid']

    # Get bios boot order information and check result
    result = get_bios_bootorder(ip, login_account, login_password, system_id)
    if result['ret'] is True:
        del result['ret']
        sys.stdout.write(json.dumps(result['entries'], sort_keys=True, indent=2))
    else:
        sys.stderr.write(result['msg'] + '\n')
