# -*- coding: utf-8 -*-
"""Get the UUID of the device"""
from __future__ import unicode_literals

from .logging import debug
from .misc_utils import get_system_platform

__CRYPT_KEY__ = None


def get_crypt_key():
    """
    Lazily generate the crypt key and return it
    """
    # pylint: disable=global-statement
    global __CRYPT_KEY__
    if not __CRYPT_KEY__:
        __CRYPT_KEY__ = _get_system_uuid()
    return __CRYPT_KEY__


def get_random_uuid():
    """
    Generate a random uuid
    :return: a string of a random uuid
    """
    import uuid
    return str(uuid.uuid4())


def _get_system_uuid():
    """
    Try to get an uuid from the system, if it's not possible generates a fake uuid
    :return: an uuid converted to MD5
    """
    import uuid
    uuid_value = None
    system = get_system_platform()
    if system in ['windows', 'xbox']:
        uuid_value = _get_windows_uuid()
    elif system == 'android':
        uuid_value = _get_android_uuid()
    elif system == 'linux':
        uuid_value = _get_linux_uuid()
    elif system in ['osx', 'ios']:
        uuid_value = _get_macos_uuid()
    if not uuid_value:
        debug('It is not possible to get a system UUID creating a new UUID')
        uuid_value = _get_fake_uuid(system != 'android')
    return uuid.uuid5(uuid.NAMESPACE_DNS, str(uuid_value)).bytes


def _get_windows_uuid():
    uuid_value = None
    try:
        import _winreg  # Warning on python 3 is renamed with "import winreg"
        registry = _winreg.HKEY_LOCAL_MACHINE
        address = 'SOFTWARE\\Microsoft\\Cryptography'
        keyargs = _winreg.KEY_READ | _winreg.KEY_WOW64_64KEY
        key = _winreg.OpenKey(registry, address, 0, keyargs)
        value = _winreg.QueryValueEx(key, 'MachineGuid')
        _winreg.CloseKey(key)
        uuid_value = value[0]
    except Exception:
        pass
    if not uuid_value:
        try:
            import subprocess
            output = subprocess.check_output(['vol', 'c:'])
            output = output.split()
            uuid_value = str(output[len(output) - 1:])
        except Exception:
            pass
    return uuid_value


def _get_linux_uuid():
    import subprocess
    uuid_value = None
    try:
        uuid_value = subprocess.check_output(['cat', '/var/lib/dbus/machine-id'])
    except Exception:
        pass
    if not uuid_value:
        try:
            # Fedora linux
            uuid_value = subprocess.check_output(['cat', '/etc/machine-id'])
        except Exception:
            pass
    return uuid_value


def _get_android_uuid():
    import subprocess
    import re
    values = ''
    try:
        # Due to the new android security we cannot get any type of serials
        sys_prop = ['ro.product.board', 'ro.product.brand', 'ro.product.device', 'ro.product.locale'
                    'ro.product.manufacturer', 'ro.product.model', 'ro.product.platform',
                    'persist.sys.timezone', 'persist.sys.locale', 'net.hostname']
        # Warning net.hostname property starting from android 10 is deprecated return empty
        proc = subprocess.Popen(['/system/bin/getprop'], stdout=subprocess.PIPE)
        output_data = proc.stdout.read().decode('utf-8')
        proc.stdout.close()
        list_values = output_data.splitlines()
        for value in list_values:
            value_splitted = re.sub(r'\[|\]|\s', '', value).split(':')
            if value_splitted[0] in sys_prop:
                values += value_splitted[1]
    except Exception:
        pass
    return values


def _get_macos_uuid():
    import subprocess
    sp_dict_values = None
    try:
        proc = subprocess.Popen(
            ['/usr/sbin/system_profiler', 'SPHardwareDataType', '-detaillevel', 'full', '-xml'],
            stdout=subprocess.PIPE)
        output_data = proc.stdout.read()
        proc.stdout.close()
        if output_data:
            sp_dict_values = _parse_osx_xml_plist_data(output_data)
    except Exception as exc:
        debug('Failed to fetch OSX/IOS system profile {}'.format(exc))
    if sp_dict_values:
        if 'UUID' in sp_dict_values.keys():
            return sp_dict_values['UUID']
        if 'serialnumber' in sp_dict_values.keys():
            return sp_dict_values['serialnumber']
    return None


def _parse_osx_xml_plist_data(data):
    import plistlib
    import re
    dict_values = {}
    xml_data = plistlib.readPlistFromString(data)
    items_dict = xml_data[0]['_items'][0]
    r = re.compile(r'.*UUID.*')  # Find to example "platform_UUID" key
    uuid_keys = filter(r.match, items_dict.keys())
    if uuid_keys:
        dict_values['UUID'] = items_dict[uuid_keys[0]]
    if not uuid_keys:
        r = re.compile(r'.*serial.*number.*')  # Find to example "serial_number" key
        serialnumber_keys = filter(r.match, items_dict.keys())
        if serialnumber_keys:
            dict_values['serialnumber'] = items_dict[serialnumber_keys[0]]
    return dict_values


def _get_fake_uuid(with_hostname=True):
    """
    Generate a uuid based on various system information
    """
    import xbmc
    import platform
    list_values = [xbmc.getInfoLabel('System.Memory(total)')]
    if with_hostname:
        list_values.append(platform.node())
    return '_'.join(list_values)
