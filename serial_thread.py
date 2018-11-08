# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

""" Classes to constantly read a serial port in a separate thread and cuts parts off and places
 it in a queue"""

# standard libraries
import datetime
import enum
import logging
import queue
import serial
import struct
import threading
import time
# local files
import cysmart_commands as sc  # serial commands

__author__ = 'Kyle Vitautas Lopin'

CYSMART_PACKET_DIVIDER = b'\xbd\xa7'


class SerialState(enum.Enum):
    READY = 1
    WAIT_FOR_ACK = 2
    WAIT_FOR_COMPLETE = 3


class ToDeviceCommand(object):
    def __init__(self, command, data, wait_for_ack=False, wait_for_complete=False):
        self.command = command
        self.data = data
        # convert the lenght number to uint16 with LSB first
        self.length = convert_to_string(struct.pack('H',len(data)))
        # print('len0: ', struct.pack('H', self.length))
        # print('len0bb: ', convert_to_string(struct.pack('H', self.length)))
        # print('len0b:', struct.unpack('H', struct.pack('H', self.length)))
        # print('len', self.length)
        self.wait_for_ack = wait_for_ack
        self.wait_for_complete = wait_for_complete


class SerialInputThread(threading.Thread):
    def __init__(self, port: serial.Serial, data_queue: queue.Queue, cutter: str):

        threading.Thread.__init__(self)
        self.port = port
        self.data_packets = data_queue
        self.splicer = cutter
        self.incoming_data = b""
        self.running = True

    def run(self):

        while self.running:
            time.sleep(0.1)
            if self.port.inWaiting():
                self.incoming_data += self.port.read_all()
                self.process_data()

    def process_data(self):

        spliced_data = self.incoming_data.split(self.splicer, 2)
        if len(spliced_data) > 2 and spliced_data == b'':
            self.data_packets.put(spliced_data[1])  # 0 index will be blanked
            self.incoming_data = spliced_data[2]


class SerialHandler(threading.Thread):
    """
    This class should handle sending data out and data packet input, a separate thread should
    take in all the actual data and just pass to this class the actual packets
    """
    def __init__(self, port: serial.Serial,
                 to_device_queue: queue.Queue, from_device_queue: queue.Queue,
                 lock: threading.Lock = None):
        threading.Thread.__init__(self)
        self.data_pkt_from_device = queue.Queue()
        self.running = True
        self.port = port
        self.serial_input_stream = SerialInputThread(port,
                                                     self.data_pkt_from_device,
                                                     CYSMART_PACKET_DIVIDER)

        self.from_device_queue = from_device_queue
        self.to_device_queue = to_device_queue
        self.lock = lock

    def run(self):
        while self.running:
            if not self.data_pkt_from_device.empty():
                self.get_event()

            if not self.to_device_queue.empty():
                # there is a data packet to send to the device
                self.send_command()

    def get_event(self):
        event_received = self.data_pkt_from_device.get()
        print("[{0}] '{1}' event received ".format(get_time(), event_received))

    def send_command(self):
        command_to_send = self.to_device_queue.get()  # type:ToDeviceCommand
        print("check0: ", command_to_send.command.value[0],
              command_to_send.command.value, command_to_send.command.name)
        print('check1: ', sc.cmd_header, command_to_send.command,
                         command_to_send.length, command_to_send.data)
        # packet_to_send = " ".join([sc.cmd_header, command_to_send.command,
        #                  command_to_send.length, command_to_send.data])
        packet_to_send = sc.cmd_header
        logging.debug("command: {0}\npacket:{1}".format(command_to_send, packet_to_send))
        print("[{0}] '{1}' request sent ".format(get_time(), command_to_send))
        self.port.write(self.to_device_queue.get())


def get_time():
    return datetime.datetime.now().strftime("%H:%M:%S.%f")


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
