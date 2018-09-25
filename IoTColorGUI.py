# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

"""
GUI to connect to blue tooth enabled color sensor with an AS7262 and as7263
"""

# standard libraries
import logging
import struct
import time
import tkinter as tk
from tkinter import ttk

# local files
import CySmart
import pyplot_embed

__author__ = 'Kyle Vitautas Lopin'


class IoTSpectrumGUI(tk.Tk):
    """
    Class to control and display data from IoT nod with an AS7262 and AS7263 color sensors
    """
    def __init__(self, parent=None):
        tk.Tk.__init__(self, parent)
        logging.basicConfig(format='%(asctime)s %(module)s %(lineno)d: %(levelname)s %(message)s',
                            datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)
        self.graph = pyplot_embed.SpectroPlotterV2(self)
        self.graph.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        cy = CySmart.CySmart()
        cy.start(cy.Flag_API_RETURN)
        cyd = cy.send_command(cy.Commands['CMD_START_SCAN'], wait_for_payload=True, wait_for_complete=True)
        cy.send_command(cy.Commands['CMD_STOP_SCAN'])

        devices = cy.get_scan_data(cyd)

        for device in devices:
            if device['name'] and b'NU Sensor' in device['name']:
                cy.open_connection(device['BD_Address'])

        self.device = cy
        self.run_button = tk.Button(self, text="Run", command=self.run_button)
        self.run_button.pack(side=tk.BOTTOM)

    def run_button(self):
        self.run_button.config(state=tk.DISABLED)
        print("Writing")
        cy = self.device
        cy.write_characteristic_value(0x0012, b'\x01')
        # cir = cy.read_characteristic_value(0x000E)
        # print('cir = ', len(cir[0]), cir)
        time.sleep(1)
        data = cy.get_notified_respose()
        self.figure_out_data(data[b'\x0c\x06'][0], "No flash")
        time.sleep(1)
        data = cy.get_notified_respose()
        self.figure_out_data(data[b'\x0c\x06'][1], "Flash")
        self.run_button.config(state=tk.ACTIVE)

    def figure_out_data(self, raw_data, type_read):
        data = raw_data
        print(data)
        print(data[4:])
        print(len(data[4:52]))
        print(struct.unpack(">ffffffffffff", data[4:52]))
        new_data = struct.unpack(">ffffffffffff", data[4:52])
        print('new data to pass: ', new_data)
        self.graph.update_data(new_data, type_read)


if __name__ == '__main__':
    app = IoTSpectrumGUI()
    app.title("Spectrograph")
    app.geometry("900x750")
    app.mainloop()
