###
#
# Lenovo Redfish examples - Set bios boot order
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


def set_bios_bootorder(ip, login_account, login_password, system_id, bootorder):
    """set bios boot order
    :params ip: BMC IP address
    :type ip: string
    :params login_account: BMC user name
    :type login_account: string
    :params login_password: BMC user password
    :type login_password: string
    :params system_id: ComputerSystem instance id(None: first instance, All: all instances)
    :type system_id: None or string
    :params bootorder: Specify the bios boot order list,  The boot order takes effect on the next startup
    :type bootorder: list
    :returns: returns set bios boot order result when succeeded or error message when failed
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
        # Get the ComputerSystem resource
        system = utils.get_system_url("/redfish/v1", system_id, REDFISH_OBJ)
        if not system:
            result = {'ret': False, 'msg': "This system id is not exist or system member is None"}
            return result

        for i in range(len(system)):
            system_url = system[i]
            response_system_url = REDFISH_OBJ.get(system_url, None)
            if response_system_url.status != 200:
                error_message = utils.get_extended_error(response_system_url)
                result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (system_url, response_system_url.status, error_message)}
                return result

            # Set boot order info via standard api for ThinkSystem servers if standard api exists
            if 'Boot' in response_system_url.dict and 'BootOrder' in response_system_url.dict['Boot'] and 'BootOptions' in response_system_url.dict['Boot']:
                # Get the boot order settings url
                if '@Redfish.Settings' in response_system_url.dict and 'SettingsObject' in response_system_url.dict['@Redfish.Settings']:
                    boot_settings_url = response_system_url.dict['@Redfish.Settings']['SettingsObject']['@odata.id']
                else:
                    boot_settings_url = system_url + '/Pending'

                # Get the boot order supported list
                boot_order_supported = list()
                boot_order_mapid = {}
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
                    boot_order_mapid[response_boot_member.dict['DisplayName']] = response_boot_member.dict['BootOptionReference']
                    boot_order_supported.append(response_boot_member.dict['DisplayName'])

                # Check input bootorder validity
                bootorder_convert_idlist = list()
                for boot in bootorder:
                    if boot not in boot_order_supported:
                        result = {'ret': False, 'msg': "Invalid bootorder %s. You can specify one or more boot order from list:%s" %(boot, boot_order_supported)}
                        return result
                    bootorder_convert_idlist.append(boot_order_mapid[boot])

                # Set the boot order next via patch request
                body = {'Boot': {'BootOrder': bootorder_convert_idlist}}
                response_boot_order = REDFISH_OBJ.patch(boot_settings_url, body=body)
                if response_boot_order.status in [200, 204]:
                    result = {'ret': True, 'msg': "Modify Boot Order successfully. New boot order will take effect on the next startup."}
                    return result
                else:
                    error_message = utils.get_extended_error(response_boot_order)
                    result = {'ret': False, 'msg': "Url '%s' response Error code %s \nerror_message: %s" % (
                        boot_settings_url, response_boot_order.status, error_message)}
                    return result

        result = {'ret': False, 'msg': "No related resource found, fail to set bios boot order for target server."}
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


def add_helpmessage(argget):
    argget.add_argument('--bootorder', nargs='*', type=str, required=True, help='Input the bios boot order list,  The boot order takes effect on the next startup. Support:"CD/DVD Rom","Hard Disk", etc. Detailed bootorder support list can be gotten by get_bios_bootorder.py script')


def add_parameter():
    """Add set bios boot order parameter"""
    argget = utils.create_common_parameter_list()
    add_helpmessage(argget)
    args = argget.parse_args()
    parameter_info = utils.parse_parameter(args)
    if args.bootorder is not None:
        parameter_info["bootorder"] = args.bootorder
    return parameter_info


if __name__ == '__main__':
    # Get parameters from config.ini and/or command line
    parameter_info = add_parameter()

    # Get connection info from the parameters user specified
    ip = parameter_info["ip"]
    login_account = parameter_info["user"]
    login_password = parameter_info["passwd"]
    system_id = parameter_info["sysid"]

    # Get set info from the parameters user specified
    try:
        bootorder = parameter_info["bootorder"]
    except:
        sys.stderr.write("Please run the command 'python %s -h' to view the help info" % sys.argv[0])
        sys.exit(1)

    # Get set bios boot order result and check result
    result = set_bios_bootorder(ip, login_account, login_password, system_id, bootorder)
    if result['ret'] is True:
        del result['ret']
        sys.stdout.write(json.dumps(result['msg'], sort_keys=True, indent=2))
    else:
        sys.stderr.write(result['msg'] + '\n')
