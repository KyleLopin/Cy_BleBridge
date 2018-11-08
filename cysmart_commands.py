# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

"""
COMMANDS that can be sent to a CySmart device through a UART and EVENTS that can be received.
The commands and events are attribute dictionaries where they can be accessed
as dictionary keywords, or as attributes.
"""

import enum

__author__ = "Kyle Vitatus Lopin"


class AttributeDict(dict):
    def __init__(self, **kwarg):
        super().__init__(**kwarg)

    def __getattr__(self, attr):
        if isinstance(attr, str):
            return self[attr]
        elif isinstance(attr, bytes):
            return

    def __setattr__(self, key, value):
        self[key] = value


# commands are sent to the MCU
command_structure = "[ cmd_header | address | command | length | data ]"
# events received from MCU
event_structure = "[ evt_header | len | event | req_cmd | data ]"

cmd_header = '43 59'
cmd_footer = '00 00'

# commands = AttributeDict(
#     Resolve_and_Set_Peer_Device_BD_Address="A1FE",
#     INIT_BLE_STACK="07FC",
#     START_SCAN="93FE",
#     STOP_SCAN="94FE",
# )
#
# event_header = "BDA7"
#
# events = AttributeDict(
#     SCAN_PROGRESS_RESULT="8A06",
#     COMMAND_STATUS="7E04",
#     COMMAND_COMPLETE="7F04"
# )
#
# flags = AttributeDict(
#     DISABLE_ALL_CHECK="00",
#     CHECK_PARAMETER_LENGTH="01",
#     IMMEDIATE_RESPONSE="02",
#     EXCHANGE_RETURN="03",
#     API_RETURN="04",
#     TRIGGER_COMPLETE="08",
#     SECONDARY_CMD="10"
# )


class Commands(enum.Enum):
    Resolve_and_Set_Peer_Device_BD_Address = "A1 FE",
    INIT_BLE_STACK = "07 FC",
    START_SCAN = "93 FE",
    STOP_SCAN = "94 FE"

    def __str__(self):
        return str(self.value[0])


class Events(enum.Enum):
    SCAN_PROGRESS_RESULT = "8A 06",
    COMMAND_STATUS = "7E 04",
    COMMAND_COMPLETE = "7F 04"


class Flags(enum.Enum):
    DISABLE_ALL_CHECK = "00",
    CHECK_PARAMETER_LENGTH = "01",
    IMMEDIATE_RESPONSE = "02",
    EXCHANGE_RETURN = "03",
    API_RETURN = "04",
    TRIGGER_COMPLETE = "08",
    SECONDARY_CMD = "10"
