"""
Refactoring of the CySmart program from https://github.com/odwdinc/Cy_BleBridge/blob/master/CySmart.py

Will give a set of common APIs to use the CySmart dongle from Cypress

email: kylel@nu.ac.th if you desire another API call added to this program
"""

# standard libraries
import binascii
import logging
import queue
import serial
import serial.tools.list_ports
import time

# local files
import cysmart_commands as serial_attr
import serial_thread

# Serial communication settings
BAUD_RATE = 921600
STOP_BITS = serial.STOPBITS_ONE
PARITY = serial.PARITY_NONE
BYTE_SIZE = serial.EIGHTBITS
DONGLE_PORT_DESC = "KitProg USB-UART"
ID_MESSAGE_TO_DEVICE = b"43 59 0A FC 00 00"
ID_MESSAGE_FROM_DEVICE_1 = b"Cypress Semiconductor"
ID_MESSAGE_FROM_DEVICE_2 = b"CySmart BLE"

__author__ = 'Kyle Vitautas Lopin'


class CySmart(object):
    """

    """

    def __init__(self):
        self.device = self.auto_find_com_port()
        self.to_device_queue = queue.Queue()
        self.from_device_queue = queue.Queue()
        self.serial_thread = None  # type: serial_thread.SerialHandler
        self.flag_return_type = serial_attr.Flags.API_RETURN

    def start(self, _flag=None):
        if _flag:
            self.flag_return_type = _flag  # TODO: figure out what this does
        if not self.device:
            logging.error("No device detected")
            return False
        self.serial_thread = serial_thread.SerialHandler(self.device,
                                                         self.to_device_queue,
                                                         self.from_device_queue)
        self.serial_thread.start()
        self.send_command(serial_attr.Commands.INIT_BLE_STACK)

    def send_command(self, command, payload="", wait_for_payload=False, wait_for_complete=True):
        self.to_device_queue.put(serial_thread.ToDeviceCommand(command,
                                                               payload,
                                                               wait_for_payload,
                                                               wait_for_complete))

    @staticmethod
    def auto_find_com_port():
        # available_ports = find_available_ports()  # list of serial devices
        available_ports = serial.tools.list_ports
        print(available_ports.comports())

        for port in available_ports.comports():  # type: serial.Serial
            print("port:", port)
            print(port.device)
            print(port.name)
            print(port.description)

            if DONGLE_PORT_DESC in port.description:  # check the name associated with the port

                device = serial.Serial(port.device, baudrate=BAUD_RATE, stopbits=STOP_BITS,
                                       parity=PARITY, bytesize=BYTE_SIZE, timeout=1)
                print('writing message: ', convert_to_bytes(ID_MESSAGE_TO_DEVICE))
                device.write(convert_to_bytes(ID_MESSAGE_TO_DEVICE))
                time.sleep(0.5)
                return_message = device.read_all()
                print(return_message)
                # return_message = convert_to_string(return_message)
                if (ID_MESSAGE_FROM_DEVICE_1 in return_message
                        and ID_MESSAGE_FROM_DEVICE_2 in return_message):
                    print('Found Cypress Dongle')
                    return device
                else:
                    print("No device at: {0}".format(port))
                    device.close()


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
