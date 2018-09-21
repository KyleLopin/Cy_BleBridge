"""
Code from https://github.com/odwdinc/Cy_BleBridge/blob/master/CySmart.py
modified to fit with python 3 and fix class naming to CamelCase
"""

import binascii
import datetime
import serial
import time

from struct import *
import threading
import queue
import sys
import datetime


# Serial communication settings
BAUD_RATE = 115200
STOP_BITS = serial.STOPBITS_ONE
PARITY = serial.PARITY_NONE
BYTE_SIZE = serial.EIGHTBITS


class CySerialCommand(object):
    def __init__(self, header, cmd, payload, wait_for_payload, wait_for_complete):
        self.command = header + cmd + payload
        self.cmd = cmd
        self.wait_for_payload = wait_for_payload
        self.wait_for_complete = wait_for_complete
        self.finished = False


class CySerialProcess(threading.Thread):
    def __init__(self, in_q: queue.Queue, out_q: queue.Queue, com_port: serial.Serial, cy: 'CySmart'):
        self.cy = cy
        self.in_Q = in_q
        self.out_Q = out_q
        self.serial_in = com_port
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
        print('returning hex: ', s.hex())
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
            time.sleep(1)
            # print "loop"
            # if not self.in_Q.empty() and self.running and self.nextJob:
            if not self.in_Q.empty() and self.nextJob:
                self.nextJob = False
                self.data_array = []
                self.this_job = self.in_Q.get()
                self.this_job.starTime = datetime.datetime.now()
                print("writing to device: ", self.this_job.command)
                self.serial_in.write(self.this_job.command)
                while self.serial_in.out_waiting:
                    pass
            if self.get_timeout() > 2000:
                print("Timeout")
                sys.stdout.flush()
                self.nextJob = True
                self.out_Q.put(True)
                self.this_job.finished = True

            # if self.running and self.serial_in.inWaiting():
            if self.serial_in.inWaiting():
                # print "self.serial_in.inWaiting()"
                sys.stdout.flush()
                data = self.serial_in.read(self.serial_in.inWaiting())
                # print self.hexPrint(data)
                print('raw data: ', data)
                # print('data read:  ', convert_to_string(data))
                # data = binascii.hexlify(data)
                data = self.found_data(data)
                # cmd = self.hex_print(self.this_job.cmd)
                payload = {}
                for response in data:
                    # print('response:', response)
                    # print(self.this_job.cmd, response['request_cmd'], self.this_job.cmd == response['request_cmd'])
                    if self.this_job.cmd == response['request_cmd']:
                        self.process_response_packet(response, payload)
                        # print response['cmd']
                        # print('complete: ', self.cy.EVT_COMMAND_COMPLETE)
                        # if self.cy.EVT_COMMAND_COMPLETE in response['cmd']:
                        #     if self.this_job.wait_for_complete:
                        #         self.nextJob = True
                        #
                        # else:
                        #     if not self.nextJob:
                        #         self.nextJob = True
                        if len(response['payload']) > 0 and \
                                self.cy.EVT_COMMAND_STATUS not in response['cmd'] and \
                                self.cy.EVT_COMMAND_COMPLETE not in response['cmd']:
                            if not response['cmd'] in payload:
                                payload[response['cmd']] = []
                            payload[response['cmd']].append(response['payload'])

                print("payload:", payload,  self.nextJob, self.out_Q.qsize())

                # if len(payload) > 0:
                if payload:
                    self.out_Q.put(payload)
                elif self.nextJob and not self.this_job.wait_for_payload:
                    self.out_Q.put(True)

                if self.nextJob:
                    self.this_job.finished = True

    def process_response_packet(self, response, payload):
        if self.this_job.cmd != response['request_cmd']:  # the packet should respond
            print("[{0}] Error on response packet".format(self.time_str()))
            return
        if self.cy.EVT_COMMAND_COMPLETE in response['cmd']:
            print("[{0}] 'Command Status' event received".format(
                datetime.datetime.now().strftime("%H:%M:%S.%f")))
            if response['payload'] == b'\x00\x00':
                status_str = 'BLE_STATUS_OK'
            else:
                status_str = 'ERROR_CODE'  # TODO: fill these in
            print("[{0}] Status: {1}".format(
                  datetime.datetime.now().strftime("%H:%M:%S.%f"), status_str))
            if self.this_job.wait_for_complete:
                self.nextJob = True
            return
        else:
            if not self.nextJob:
                self.nextJob = True
        if self.cy.EVT_COMMAND_STATUS in response['cmd']:
            print("[{0}] 'Command Complete' event received".format(self.time_str()))
            if response['payload'] == b'\x00\x00':
                status_str = 'BLE_STATUS_OK'
            else:
                status_str = 'ERROR_CODE'  # TODO: fill these in
            print("[{0}] Status: {1}".format(self.time_str(), status_str))
            return
        # no COMMAND STATUS or COMPLETE send so check if there is a payload
        if len(response['payload']) > 0:
            print("response['cmd']: ", response['cmd'])
            print("payload: ", payload)


    def get_extra_bytes(self, bytes_to_get):
        time.sleep(0.2)
        if self.serial_in.inWaiting():
            data = self.serial_in.read(self.serial_in.inWaiting())
            len_data = len(data)
            print("Got {0} more bytes".format(len_data))
            print(data)
            if len_data == bytes_to_get:
                return data
        print("Tried to get more data but failed")

    def found_data(self, data):
        # print('found data: ', data, type(data), binascii.unhexlify("bda7"))
        # print('split: ', data.split(binascii.unhexlify("bda7")))
        # data = binascii.hexlify(data)
        # print('hex data: ', data)
        for cmd in data.split(binascii.unhexlify("bda7"))[1:]:
            # print('cmd: ', cmd)

            # divide len by 2 as there are 2 hex values per byte and subtract the first 2 bytes
            # which are the length
            actual_len = len(cmd)-2
            signalled_len = int.from_bytes(cmd[0:2], byteorder='little')  # how many bytes the payload is suppose to ne
            # print('len = ', actual_len, signalled_len, cmd[0:2], )
            if actual_len != signalled_len:
                print("Error in reading: add code to see if more bytes are in the serial port")
                print("look for {0} more bytes".format(signalled_len-actual_len))
                print(data)
                print(cmd)
                self.get_extra_bytes(signalled_len-actual_len)
                raise Exception()

            data = dict()
            data['len'] = signalled_len
            data['cmd'] = cmd[2:4]
            data['request_cmd'] = cmd[4:6]
            data['payload'] = cmd[6:]
            self.data_array.append(data)
            # print('data array: ', self.data_array)
        return self.data_array

    @staticmethod
    def time_str():
        return datetime.datetime.now().strftime("%H:%M:%S.%f")

    def kill(self):
        print("kill")
        self.running = False
        self.serial_in.close()


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
        'CMD_UPDATE_CONNECTION_PARAMETER_RESPONSE': binascii.unhexlify("9FFE"),

        'CMD_GET_LOCAL_SECURITY_KEYS': binascii.unhexlify("A2FE"),
        'CMD_WRITE_CHAR_DESCRIPTOR_BY_ATTR_HANDLE': binascii.unhexlify("10FE")
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
    # this should be sent after setting address with a status
    EVT_RESOLVE_SET_BD_ADDRESS_RESPONSE = binascii.unhexlify("9806")  # unsure
    EVT_READ_CHAR_UUID_RESPONSE = binascii.unhexlify("0706")  # unsure
    EVT_CHAR_VALUE_NOTIFICATION = binascii.unhexlify("0C06")
    EVT_READ_CHAR_DESC_RSP = binascii.unhexlify("0A06")

    EVENTS = {
        b'\x7E\x04': 'Command Status',
        b'\x7F\x04': 'Command Complete',
        b'\x98\x06': 'Resolve and Set Peer Device BD Address Response',
        b'\x8F\x06': 'Establish Connection Response',
        b'\x84\x06': 'Current Connection Parameters',
        b'\x99\x06': 'Get local device security keys response'
    }

    data_array = []
    flag = False
    connection_info = {}

    lock = threading.Lock()

    def __init__(self):
        self.Flag_RETURN = None
        self.in_q = None
        self.out_q = None
        self.myThread = None

    @staticmethod
    def hex_print(s):
        # print('s: ', s)
        # print('s2: ', s.hex())
        # print('s3: ', ":".join("{:02x}".format(c) for c in s))
        if type(s) is not int:
            # return s.hex()
            return ":".join("{:02x}".format(c) for c in s)
        return "{:02x}".format(s)

    def hex_array(self, s):
        # print("hex array: ", s)
        return self.hex_print(s).split(":")

    def send_command(self, command, payload=binascii.unhexlify("0000"), wait_for_payload=False, wait_for_complete=True):

        # __init__(self, heder, cmd, payload, whateforpayload, whateforCompleate):
        self.in_q.put(
            CySerialCommand(self.Commands['CMD_Header'], command, payload, wait_for_payload, wait_for_complete))
        while self.out_q.empty():
            pass
        return self.out_q.get()

    def start(self, _flag, com_port=None):
        if not com_port:
            device = self.auto_find_com_port()
            self.device = device
        self.Flag_RETURN = _flag
        self.in_q = queue.Queue(maxsize=1000)
        self.out_q = queue.Queue(maxsize=1000)

        self.myThread = CySerialProcess(self.in_q, self.out_q, device, self)
        self.myThread.start()
        print("kkkkkkkkkkkkkkkkkkkkkkkkkkkkk")
        self.send_command(self.Commands['CMD_INIT_BLE_STACK'], self.Commands['CMD_Footer'])

    def auto_find_com_port(self):
        available_ports = find_available_ports()  # list of serial devices
        id_send_message = b"43 59 0A FC 00 00"
        # id_return_section = "43 79 70 72 65 73 73"  # Cypress
        id_return_section1 = b"Cypress Semiconductor"
        id_return_section2 = b"CySmart BLE"
        for port in available_ports:  # type: serial.Serial
            device = serial.Serial(port.port, baudrate=BAUD_RATE, stopbits=STOP_BITS,
                                   parity=PARITY, bytesize=BYTE_SIZE, timeout=1)
            # device.write(binascii.unhexlify(id_send_message))
            device.write(convert_to_bytes(id_send_message))
            time.sleep(0.1)
            return_message = device.read_all()
            # return_message = convert_to_string(return_message)
            if id_return_section1 in return_message and id_return_section2 in return_message:
                print('Found Cypress Dongle')
                return device
            else:
                device.close()

    def get_scan_data(self, cyd):
        """
        Take in a packet of data from the Cypress CySmart dongle and parse out the information
        of periphiral devices that the dongles has noticed
        :param cyd: dictionary of the response command as a key, and payload as the value
        :return:
        """
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
                        print('cehck: ', )
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
        print("READ CHAR: ", response)
        if hasattr(response, '__iter__') and self.EVT_READ_CHARACTERISTIC_VALUE_RESPONSE in response:
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


def convert_to_bytes(_string: str)-> bytes:
    """
    Take an input string of hex numbers (0-F) and convert bytes string
    Note: For some reason strip() was not working when I wrote this so I used replace
    :param _string: string of hex values (0-F)
    :return: bytes string
    """
    # print('input string: ', _string)
    # print("hold: ", _string.replace(b' ', b'').replace(b':', b''))
    # print('new string: ', binascii.unhexlify(_string.replace(b' ', b'').replace(b':', b'')))
    return binascii.unhexlify(_string.replace(b' ', b'').replace(b':', b''))


def convert_to_string(_bytes: bytes)-> str:
    """
    Take in bytes and convert string of hex values of the bytes
    :param _bytes: bytes
    :return: string of hex values
    """
    # print('input bytes: ', _bytes)
    # print('string: ', binascii.hexlify(_bytes))
    # print('string2: ', _bytes.hex())
    # print('string3: ', " ".join(["{:02x}".format(x) for x in _bytes]))
    return " ".join(["{:02x}".format(x) for x in _bytes])


def find_available_ports():
    """
    Find all COM ports that are available
    :return:
    """
    import glob
    # taken from http://stackoverflow.com/questions/12090503/listing-available-com-ports-with-python

    if sys.platform.startswith('win'):
        ports = ['COM%s' % (i+1) for i in range(32)]
    elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
        ports = glob.glob('/dev/tty[A-Za-z]*')
    elif sys.platform.startswith('darwin'):
        ports = glob.glob('/dev/tty.*')
    else:
        raise EnvironmentError('Unsupported platform')

    available_ports = []
    for port in ports:
        try:
            device = serial.Serial(port=port, write_timeout=0.5,
                                   inter_byte_timeout=1, baudrate=115200,
                                   parity=serial.PARITY_EVEN, stopbits=1)
            device.close()
            available_ports.append(device)
        except (OSError, serial.SerialException):
            pass
    return available_ports
