# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

""" Embedded matplotlib plot in a tkinter frame to graph data from AS7262 and AS7263 with extra flash """

# standard libraries
import logging
import tkinter as tk
from tkinter import messagebox
# installed libraries
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import pyplot as plt


WAVELENGTHS = [450, 500, 550, 570, 600, 650, 610, 680, 730, 760, 810, 860]
COUNT_SCALE = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 50, 100, 200, 300, 500, 1000, 3000, 5000, 10000, 30000, 50000, 100000]


class SpectroPlotterV2(tk.Frame):

    def __init__(self, parent, _size=(6, 3)):
        tk.Frame.__init__(self, master=parent)
        self.data = {"No flash": [], "Flash": [], "Diff": [0]*12}
        self.scale_index = 7
        self.figure_bed = plt.figure(figsize=_size)
        self.axis = self.figure_bed.add_subplot(111)

        # self.figure_bed.set_facecolor('white')
        self.canvas = FigureCanvasTkAgg(self.figure_bed, self)
        self.canvas._tkcanvas.config(highlightthickness=0)

        toolbar = NavigationToolbar2Tk(self.canvas, self)
        toolbar.update()

        self.canvas._tkcanvas.pack(side='top', fill=tk.BOTH, expand=True)
        self.canvas.draw()

        self.axis.set_ylim([0, 300])
        self.axis.set_xlim([300, 1000])
        self.axis.set_xlabel("wavelength (nm)")

        self.axis.set_ylabel('Counts')
        self.lines = None

    def update_data(self, new_data: list, type: str):
        self.data[type] = new_data

        if type is "Flash":
            for i, data_pt in enumerate(self.data["Flash"]):
                print('i2 = ', i, data_pt, self.data["No flash"][i])
                self.data["Diff"][i] = data_pt - self.data["No flash"][i]
                print(self.data["Diff"])

            print("all data: ", self.data)
            while max(self.data["Flash"]) > COUNT_SCALE[self.scale_index]:
                self.scale_index += 1
                self.axis.set_ylim([0, COUNT_SCALE[self.scale_index]])
            while (self.scale_index >= 1) and (max(self.data["Flash"]) < COUNT_SCALE[self.scale_index - 1]):
                self.scale_index -= 1
                self.axis.set_ylim([0, COUNT_SCALE[self.scale_index]])

            self.graph_all_data()

    def graph_all_data(self):
        if self.lines:
            for i, _type in enumerate(["No flash", "Flash", "Diff"]):
                self.lines[i].set_ydata(self.data[_type])
        else:
            self.lines = []
            for i, _type in enumerate(["No flash", "Flash", "Diff"]):
                print("Plotting lines")
                new_line = self.axis.plot(WAVELENGTHS, self.data[_type])
                self.lines.append(new_line)
        self.canvas.draw()
