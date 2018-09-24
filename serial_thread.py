# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

""" Classes to constantly read a serial port in a separate thread and cuts parts off and places
 it in a queue"""

# standard libraries
import queue
import serial
import threading
import time

__author__ = 'Kyle Vitautas Lopin'

CYSMART_PACKET_DIVIDER = b'\xbd\xa7'


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
    This class should handle output and data packet input, a seperate thread should take in
    all the actual data and just pass to this class the actual packets
    """
    def __init__(self, port: serial.Serial,
                 to_device_queue:queue.Queue, from_device_queue:queue.Queue):

        self.data_pkt_from_device = queue.Queue()
        self.running = True
        serial_input_stream = SerialInputThread(port, self.data_pkt_from_device, )

    def run(self):
        while self.running:
            if not self.data_pkt_from_device.empty():
                # there is a data packet coming in that needs to be processed
                pass

