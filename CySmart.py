"""
Code from https://github.com/odwdinc/Cy_BleBridge/blob/master/CySmart.py
modified to fit with python 3 and fix class naming to CamelCase
"""

import serial
import time
import binascii
from struct import *
import threading
import queue
import sys
import datetime


class CySerialCommand(object):
    def __init__(self, heder, cmd, payload, wait_for_payload, wait_for_complete):
        self.command = heder + cmd + payload
        self.cmd = cmd
        self.wait_for_payload = wait_for_payload
        self.wait_for_complete = wait_for_complete
        self.finished = False


class CySerialProcess(threading.Thread):
    def __init__(self, in_q: queue.PriorityQueue, out_q: queue.PriorityQueue, com_port: str, cy: 'CySmart'):
        self.cy = cy
        self.in_Q = in_q
        self.out_Q = out_q
        self.serial_in = serial.Serial(com_port, 115200)
        self.running = True
        self.nextJob = True
        self.this_job = None
        self.data_array = []
        threading.Thread.__init__(self)

    @staticmethod
    def hex_print(s):
        print('jj: ', s, s.hex())
        if type(s) is not int:
            # return ":".join("{:02x}".format(c) for c in s)
            return s.hex()
        print('returing hex: ', s.hex())
        return s.hex()  # hack
        # return "{:02x}".format(s)

    def get_timeout(self):
        if self.this_job:
            if self.this_job.starTime and not self.this_job.finished:
                a = self.this_job.starTime
                b = datetime.datetime.now()
                delta = b - a
                return int(delta.total_seconds() * 1000)
        return 0

    def run(self):
        while self.running:
            time.sleep(.1)
            # print "loop"
            if not self.in_Q.empty() and self.running and self.nextJob:
                self.nextJob = False
                self.data_array = []
                self.this_job = self.in_Q.get()
                self.this_job.starTime = datetime.datetime.now()
                self.serial_in.write(self.this_job.command)
                while self.serial_in.out_waiting:
                    pass
            if self.get_timeout() > 2000:
                print("Timeout")
                sys.stdout.flush()
                self.nextJob = True
                self.out_Q.put(True)
                self.this_job.finished = True

            if self.running and self.serial_in.inWaiting():
                # print "self.serial_in.inWaiting()"
                sys.stdout.flush()
                data = self.serial_in.read(self.serial_in.inWaiting())
                # print self.hexPrint(data)
                data = self.found_data(data)
                # cmd = self.hex_print(self.this_job.cmd)
                payload = {}
                for response in data:
                    # print response
                    if self.this_job.cmd == response['request_cmd']:
                        # print response['cmd']

                        if self.this_job.wait_for_complete:
                            if self.cy.EVT_COMMAND_COMPLETE in response['cmd']:
                                self.nextJob = True

                        else:
                            if not self.nextJob:
                                self.nextJob = True
                        if len(response['payload']) > 0 and self.cy.EVT_COMMAND_STATUS not in response['cmd'] and \
                                self.cy.EVT_COMMAND_COMPLETE not in response['cmd']:
                            if not response['cmd'] in payload:
                                payload[response['cmd']] = []
                            payload[response['cmd']].append(response['payload'])

                print("payload:", payload,  self.nextJob)

                if len(payload) > 0:
                    self.out_Q.put(payload)
                elif self.nextJob and not self.this_job.wait_for_payload:
                    self.out_Q.put(True)

                if self.nextJob:
                    self.this_job.finished = True

    def kill(self):
        self.running = False
        self.serial_in.close()

    def found_data(self, data):
        for cmd in data.split(binascii.unhexlify("bda7"))[1:]:
            data = dict()
            data['len'] = self.hex_print(cmd[0:2])
            data['cmd'] = cmd[2:4]
            data['request_cmd'] = cmd[4:6]
            data['payload'] = cmd[6:]
            self.data_array.append(data)
        return self.data_array


class CySmart(object):
    Commands = {
        'CMD_Resolve_and_Set_Peer_Device_BD_Address': binascii.unhexlify("A1FE"),
        'CMD_Header': binascii.unhexlify("4359"),
        'CMD_Footer': binascii.unhexlify("0000"),
        'CMD_INIT_BLE_STACK': binascii.unhexlify("07FC"),
        'CMD_START_SCAN': binascii.unhexlify("93FE"),
        'CMD_STOP_SCAN': binascii.unhexlify("94FE"),
        'CMD_ESTABLISH_CONNECTION': binascii.unhexlify("97FE"),
        'CMD_TERMINATE_CONNECTION': binascii.unhexlify("98FE"),
        'CMD_EXCHANGE_GATT_MTU_SIZE': binascii.unhexlify("12FE"),
        'CMD_READ_CHARACTERISTIC_VALUE': binascii.unhexlify("06FE"),
        'CMD_READ_USING_CHARACTERISTIC_UUID': binascii.unhexlify("07FE"),
        'CMD_WRITE_CHARACTERISTIC_VALUE': binascii.unhexlify("0BFE"),
        'CMD_WRITE_CHARACTERISTIC_VALUE_WITHOUT_RESPONSE': binascii.unhexlify("0AFE"),
        'CMD_FIND_INCLUDED_SERVICES': binascii.unhexlify("02FE"),
        'CMD_DISCOVER_ALL_CHARACTERISTICS': binascii.unhexlify("03FE"),
        'CMD_INITIATE_PAIRING_REQUEST': binascii.unhexlify("99FE"),
        'CMD_UPDATE_CONNECTION_PARAMETER_RESPONSE': binascii.unhexlify("9FFE")
    }

    Flag_DISABLE_ALL_CHECK = 0x00
    Flag_CHECK_PARAMETER_LENGTH = 0x1
    Flag_IMMEDIATE_RESPONSE = 0x2
    Flag_API_RETURN = 0x4
    Flag_Exchange_RETURN = 0x3
    Flag_TRIGGER_COMPLETE = 0x8
    Flag_SECONDARY_CMD = 0x10

    CYSMT_EVT_HEADER_CODE = binascii.unhexlify("BDA7")
    EVT_SCAN_PROGRESS_RESULT = binascii.unhexlify("8A06")
    EVT_COMMAND_STATUS = binascii.unhexlify("7E04")
    EVT_COMMAND_COMPLETE = binascii.unhexlify("7F04")
    EVT_READ_CHARACTERISTIC_VALUE_RESPONSE = binascii.unhexlify("0606")

    dataarray = []
    flag = False
    conectioninfo = {}

    lock = threading.Lock()

    def __init__(self):
        self.Flag_RETURN = None
        self.in_q = None
        self.out_q = None
        self.myThread = None

    @staticmethod
    def hex_print(s):
        print('s: ', s)
        print('s2: ', s.hex())
        if type(s) is not int:
            return s.hex()
            # return ":".join("{:02x}".format(ord(c)) for c in s)
        return "{:02x}".format(s)

    def hex_array(self, s):
        print("hex array: ", s)
        return self.hex_print(s).split(b":")

    def send_command(self, command, payload=binascii.unhexlify("0000"), wait_for_payload=False, wait_for_complete=True):

        # __init__(self, heder, cmd, payload, whateforpayload, whateforCompleate):
        self.in_q.put(
            CySerialCommand(self.Commands['CMD_Header'], command, payload, wait_for_payload, wait_for_complete))
        while self.out_q.empty():
            pass
        return self.out_q.get()

    def start(self, _flag, com_port='\\.\COM5'):
        self.Flag_RETURN = _flag
        self.in_q = queue.PriorityQueue()
        self.out_q = queue.PriorityQueue()

        self.myThread = CySerialProcess(self.in_q, self.out_q, com_port, self)
        self.myThread.start()

        self.send_command(self.Commands['CMD_INIT_BLE_STACK'], self.Commands['CMD_Footer'])

    def get_scan_data(self, cyd):
        scan_list = []

        if self.EVT_SCAN_PROGRESS_RESULT in cyd:
            for scan in cyd[self.EVT_SCAN_PROGRESS_RESULT]:
                # print self.hexPrint(scan)
                print('scan: ', scan)
                sys.stdout.flush()

                ble = dict(BD_Address=[], RSSI=0, Advertisement_Event_Data=[], name="")
                ble['BD_Address'] = scan[1:6]
                # print self.hexPrint(scan[7:9])
                ble['RSSI'] = unpack('b', scan[8:9])
                ble['Advertisement_Event_Data'] = scan[10:-1]
                if len(scan) > 10:
                    input_string = scan
                    print(input_string)

                    if b'\t' in input_string:
                        print(input_string.split(b'\t'))
                        nm_length = int(self.hex_array(input_string.split(b'\t')[0])[-1], 16) - 1
                        ble['name'] = input_string.split(b'\t')[1][0:nm_length]
                scan_list.append(ble)
        return scan_list

    def open_connection(self, address):
        out = dict(CMD_Resolve_and_Set_Peer_Device_BD_Address={},
                   CMD_ESTABLISH_CONNECTION={},
                   EXCHANGE_GATT_MTU_SIZE={},
                   Read_using_Characteristic_UUID={})

        out['CMD_Resolve_and_Set_Peer_Device_BD_Address'] = self.send_command(
            self.Commands['CMD_Resolve_and_Set_Peer_Device_BD_Address'],
            binascii.unhexlify("0700") + address + self.Commands['CMD_Footer']
        )

        out['CMD_ESTABLISH_CONNECTION'] = self.send_command(
            self.Commands['CMD_ESTABLISH_CONNECTION'],
            binascii.unhexlify("0700") + address + self.Commands['CMD_Footer']
        )

        out['EXCHANGE_GATT_MTU_SIZE'] = self.exchange_gatt_mtu_size(0x0200)

        out['Read_using_Characteristic_UUID'] = self.read_using_characteristic_uuid(0x0001, 0xFFFF, 0x2A00)
        return out

    def close_connection(self):
        return self.send_command(self.Commands['CMD_TERMINATE_CONNECTION'], binascii.unhexlify("02000400"))

    def _return(self, _pack, prams):
        values = (self.Flag_RETURN,)
        if type(prams) == tuple and type(_pack) == str:
            values += prams

        _pack = '=H ' + _pack
        s = Struct(_pack)
        packed_data = s.pack(*values)
        h = Struct('H')
        pack_size = h.pack(s.size)
        packed_data = pack_size + packed_data
        return packed_data

    def exchange_gatt_mtu_size(self, size):
        return self.send_command(self.Commands['CMD_EXCHANGE_GATT_MTU_SIZE'], self._return('H', (size,)))

    def read_using_characteristic_uuid(self, start_handle, end_handle, uuid):
        return self.send_command(self.Commands['CMD_READ_USING_CHARACTERISTIC_UUID'],
                                 self._return('B H H H', (0x01, uuid, start_handle, end_handle)))

    def read_characteristic_value(self, attribute):
        cmd = pack('H H H', *(self.Flag_RETURN, self.Flag_RETURN, attribute))
        response = self.send_command(self.Commands['CMD_READ_CHARACTERISTIC_VALUE'], cmd)

        # print"Read_Characteristic_Value: ",response
        # event, rest = response[0:3], response[4:]
        out__response = []
        if self.EVT_READ_CHARACTERISTIC_VALUE_RESPONSE in response:
            for cs in response[self.EVT_READ_CHARACTERISTIC_VALUE_RESPONSE]:
                out__response.append(cs[4:])

        return out__response

    def write_characteristic_value(self, attribute, payload):
        pram_count = binascii.unhexlify("0400")
        le = len(payload)
        package = pram_count + pack("H", *(attribute,)) + pack("H", *(le,)) + payload
        package = pack("H", *(len(package),)) + package
        return self.send_command(self.Commands['CMD_WRITE_CHARACTERISTIC_VALUE'], package)

    def read_all_characteristics(self, data_set):
        for se in data_set:
            data_set[se] = self.read_characteristic_value(se)
        return data_set

    def initiate_pairing(self):
        cmd = pack('H H', *(self.Flag_IMMEDIATE_RESPONSE, self.Flag_RETURN))
        return self.send_command(self.Commands['CMD_INITIATE_PAIRING_REQUEST'], cmd)

    def update_connection_parameter(self, response):
        cmd = ''
        if response:
            cmd += binascii.unhexlify("040003000000")
        else:
            cmd += binascii.unhexlify("040003000100")

        return self.send_command(self.Commands['CMD_UPDATE_CONNECTION_PARAMETER_RESPONSE'], cmd)

    def close(self):
        self.myThread.kill()
        self.myThread.join()
