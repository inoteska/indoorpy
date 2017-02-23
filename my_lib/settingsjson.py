import json

# basic app settings
settings_app = json.dumps([
    {'type': 'title',
     'title': 'Basic application parameters'},
    {'type': 'options',
     'title': 'Brightness',
     'desc': 'Choose for the brightness value [%]',
     'section': 'command',
     'key': 'brightness',
     'options': ['20', '40', '60', '80', '100']},
    {"type": "bool",
     "title": "DND mode",
     "desc": "Do not disturb mode (reject incomming calls)",
     "section": "command",
     "key": "dnd_mode"},
    {'type': 'numeric',
     'title': 'Screen saver',
     'desc': 'Select time to swap do screen saver mode (0-120 min)',
     'section': 'command',
     'key': 'screen_saver'},
    {'type': 'options',
     'title': 'Watches',
     'desc': 'Choose if you want to analog or digital watches',
     'section': 'command',
     'key': 'watches',
     'options': ['analog','digital','none']}
])

# set GUI
settings_gui = json.dumps([
    {'type': 'title',
     'title': 'User interface parameters'},
    {'type': 'options',
     'title': 'Screen mode',
     'desc': 'Choose for the display option',
     'section': 'gui',
     'key': 'screen_mode',
     'options': ['1', '2', '3', '4']},
    {'type': 'string',
     'title': 'Make call button',
     'desc': 'Type text for the making call button',
     'section': 'gui',
     'key': 'btn_docall'},
    {'type': 'string',
     'title': 'Answer call button',
     'desc': 'Type text for the answer call button',
     'section': 'gui',
     'key': 'btn_call_answer'},
    {'type': 'string',
     'title': 'Hangup call button',
     'desc': 'Type text for the hangup call button',
     'section': 'gui',
     'key': 'btn_call_hangup'},
    {'type': 'string',
     'title': 'Open door 1',
     'desc': 'Type text for the open door button',
     'section': 'gui',
     'key': 'btn_door_1'},
    {'type': 'string',
     'title': 'Open door 2',
     'desc': 'Type text for the open door button',
     'section': 'gui',
     'key': 'btn_door_2'}
])

# set outdoor devices
settings_outdoor = json.dumps([
    {'type': 'title',
     'title': 'Outdoor devices parameters'},
    {'type': 'string',
     'title': 'Device address 1',
     'desc': 'Enter IP address for relay control',
     'disabled': False,
     'section': 'common',
     'key': 'server_ip_address_1'},
    {'type': 'string',
     'title': 'SIP call 1',
     'desc': 'Type SIP call number or IP address',
     'disabled': False,
     'section': 'common',
     'key': 'sip_call1'},
    {'type': 'string',
     'title': 'Stream address 1',
     'desc': 'Enter address to retrieve video stream',
     'disabled': False,
     'section': 'common',
     'key': 'server_stream_1'},
    {'type': 'string',
     'title': 'Device address 2',
     'desc': 'Enter IP address for relay control',
     'disabled': False,
     'section': 'common',
     'key': 'server_ip_address_2'},
    {'type': 'string',
     'title': 'SIP call 2',
     'desc': 'Type SIP call number or IP address',
     'disabled': False,
     'section': 'common',
     'key': 'sip_call2'},
    {'type': 'string',
     'title': 'Stream address 2',
     'desc': 'Enter address to retrieve video stream',
     'disabled': False,
     'section': 'common',
     'key': 'server_stream_2'},
    {'type': 'string',
     'title': 'Device address 3',
     'desc': 'Enter IP address for relay control',
     'disabled': False,
     'section': 'common',
     'key': 'server_ip_address_3'},
    {'type': 'string',
     'title': 'SIP call 3',
     'desc': 'Type SIP call number or IP address',
     'disabled': False,
     'section': 'common',
     'key': 'sip_call3'},
    {'type': 'string',
     'title': 'Stream address 3',
     'desc': 'Enter address to retrieve video stream',
     'disabled': False,
     'section': 'common',
     'key': 'server_stream_3'},
    {'type': 'string',
     'title': 'Device address 4',
     'desc': 'Enter IP address for relay control',
     'disabled': False,
     'section': 'common',
     'key': 'server_ip_address_4'},
    {'type': 'string',
     'title': 'SIP call 4',
     'desc': 'Type SIP call number or IP address',
     'disabled': False,
     'section': 'common',
     'key': 'sip_call4'},
    {'type': 'string',
     'title': 'Stream address 4',
     'desc': 'Enter address to retrieve video stream',
     'disabled': False,
     'section': 'common',
     'key': 'server_stream_4'}
])

# audio settings
settings_audio = json.dumps([
    {'type': 'title',
     'title': 'Ring tone and volume settings'},
    {'type': 'options',
     'title': 'Ringtone',
     'desc': 'Choose ringtone',
     'section': 'devices',
     'key': 'ringtone',
     'options': ['oldphone.wav', 'tone1.wav', 'tone2.wav']},
    {'type': 'options',
     'title': 'Volume',
     'desc': 'Choose for the audio volume value [%]',
     'section': 'devices',
     'key': 'volume',
     'options': ['20', '40', '60', '80', '100']}
])

# SIP settings
settings_sip = json.dumps([
    {'type': 'title',
     'title': 'SIP parameters'},
    {'type': 'options',
     'title': 'SIP mode',
     'desc': 'Choose SIP account type',
     'section': 'sip',
     'key': 'sip_mode',
     'options': ['peer-to-peer', 'SIP server']},
    {'type': 'string',
     'title': 'SIP server address',
     'desc': 'Type SIP server address',
     'disabled': False,
     'section': 'sip',
     'key': 'sip_server_addr'},
    {'type': 'string',
     'title': 'SIP user name',
     'desc': 'Type SIP account name',
     'disabled': False,
     'section': 'sip',
     'key': 'sip_username'},
    {'type': 'string',
     'title': 'SIP password',
     'desc': 'Type SIP password',
     'disabled': False,
     'section': 'sip',
     'key': 'sip_p4ssw0rd'}
#    {'type': 'string',
#     'title': 'SIP ident address',
#     'desc': 'Type SIP ident address',
#     'section': 'sip',
#     'key': 'sip_ident_addr'},
#    {'type': 'string',
#     'title': 'SIP ident info',
#     'desc': 'Type SIP ident info',
#     'section': 'sip',
#     'key': 'sip_ident_info'},
#    {'type': 'string',
#     'title': 'STUNT server',
#     'desc': 'Type STUNT server address',
#     'section': 'sip',
#     'key': 'sip_stun_server'}
])

# System parameters
settings_system = json.dumps([
    {'type': 'title',
     'title': 'Network parameters'},
    {'type': 'options',
     'title': 'inet type',
     'desc': 'Choose IP address type',
     'section': 'system',
     'disabled': False,
     'key': 'inet',
     'options': ['static', 'dhcp']},
    {'type': 'string',
     'title': 'IP address',
     'desc': 'Enter Raspberry Pi IP address',
     'section': 'system',
     'disabled': False,
     'key': 'ipaddress'},
    {'type': 'string',
     'title': 'Gateway',
     'desc': 'Enter gateway address',
     'section': 'system',
     'disabled': False,
     'key': 'gateway'},
    {'type': 'string',
     'title': 'Network mask',
     'desc': 'Enter netmask address',
     'section': 'system',
     'disabled': False,
     'key': 'netmask'},
    {'type': 'string',
     'title': 'DNS server',
     'desc': 'Type DNS server address',
     'section': 'system',
     'disabled': False,
     'key': 'dns'}
])

# about app
settings_about = json.dumps([
    {'type': 'title',
     'title': 'About application'},
    {'type': 'string',
     'title': 'Name',
     'desc': 'The application name to display',
     'section': 'about',
     'disabled': True,
     'key': 'app_name'},
    {'type': 'string',
     'title': 'Version',
     'desc': 'The application version to display',
     'section': 'about',
     'disabled': True,
     'key': 'app_ver'},
    {'type': 'string',
     'title': 'Serial number',
     'desc': 'Raspberry Pi serial number',
     'section': 'about',
     'disabled': True,
     'key': 'serial'}
])

# service function
settings_services = json.dumps([
    {'type': 'title',
     'title': 'Service functions'},
    {"type": "buttons",
     "title": "Status","desc": "Show popup window with main status informations",
     "section": "service",
     "key": "buttonpress",
     "buttons": [{"title":"Status","id":"button_status"}]},
    {"type": "buttons",
     "title": "Log history","desc": "Show popup window with last 100 log messages",
     "section": "service",
     "key": "buttonlogs",
     "buttons": [{"title":"Log Msg","id":"button_loghist"}]},
    {"type": "buttons",
     "title": "Restart","desc": "Restart the application",
     "section": "service",
     "key": "app_rst",
     "buttons": [{"title":"Restart App","id":"button_app_rst"}]} #,{"title":"Del","id":"button_delete"},{"title":"Rename","id":"button_rename"}]}
])
