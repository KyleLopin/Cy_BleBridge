# Copyright (c) 2018 Kyle Lopin (Naresuan University) <kylel@nu.ac.th>

""" Embedded matplotlib plot in a tkinter frame to graph data from AS7262 and AS7263 with extra flash """

# standard libraries
import logging
import tkinter as tk
from tkinter import messagebox
from tkinter import filedialog
# installed libraries
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib import pyplot as plt


WAVELENGTHS = [450, 500, 550, 570, 600, 650, 610, 680, 730, 760, 810, 860]
COUNT_SCALE = [0.01, 0.03, 0.1, 0.3, 1, 3, 10, 30, 50, 100, 200, 300, 500, 1000, 3000, 5000, 10000, 30000, 50000, 100000]
COLORS = ['black', 'yellow', 'blue']
MARKS = ['o', 'o', 'x']


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

        self.axis.set_ylim([0, COUNT_SCALE[self.scale_index]])
        self.axis.set_xlim([400, 900])
        self.axis.set_xlabel("wavelength (nm)")

        self.axis.set_ylabel('Counts')
        self.lines = None

    def update_data(self, new_data: list, type: str):
        self.data[type] = new_data

        if type is "Flash":
            for i, data_pt in enumerate(self.data["Flash"]):
                self.data["Diff"][i] = data_pt - self.data["No flash"][i]
            print('max data: ', max(self.data["Flash"]), COUNT_SCALE[self.scale_index])
            while max(self.data["Flash"]) > COUNT_SCALE[self.scale_index]:
                self.scale_index += 1
                self.axis.set_ylim([0, COUNT_SCALE[self.scale_index]])
            while (self.scale_index >= 1) and (max(self.data["Flash"]) < COUNT_SCALE[self.scale_index - 1]):
                self.scale_index -= 1
                self.axis.set_ylim([0, COUNT_SCALE[self.scale_index]])

            self.graph_all_data()

    def graph_all_data(self):
        if self.lines:
            print(self.lines)
            for i, _type in enumerate(["No flash", "Flash", "Diff"]):
                self.lines[i].set_ydata(self.data[_type])
        else:
            self.lines = []
            for i, _type in enumerate(["No flash", "Flash", "Diff"]):
                new_line,  = self.axis.plot(WAVELENGTHS, self.data[_type],
                                            marker=MARKS[i], ls='', c=COLORS[i])
                self.lines.append(new_line)
        self.canvas.draw()

    def save_data(self):
        SaveTopLevel(self.master, self.data)


class SaveTopLevel(tk.Toplevel):
    def __init__(self, parent: tk.Tk, data: dict, data_type="counts"):
        tk.Toplevel.__init__(self, master=parent)
        # set basic attributes
        self.attributes('-topmost', 'true')
        self.geometry('450x380')
        self.title("Save data")

        self.full_data_string = "Wavelength (nm), {0}, {1}, {2}\n".format("No flash", "Flash", "Diff")
        self.no_flash_data_string = "{0}\n".format("No flash")
        self.flash_data_string = "{0}\n".format("Flash")
        self.diff_data_string = "{0}\n".format("Difference")
        for i, wavelength in enumerate(WAVELENGTHS):
            self.full_data_string += "{0}, {1:4.3f}, {2:4.3f}, {3:4.3f}\n".format(wavelength, data['No flash'][i],
                                                                                  data['Flash'][i], data['Diff'][i])
            self.no_flash_data_string += "{0:4.3f}\n".format(data['No flash'][i])
            self.flash_data_string += "{0:4.3f}\n".format(data['Flash'][i])
            self.diff_data_string += "{0:4.3f}\n".format(data['Diff'][i])

        # make the area
        self.text_box = tk.Text(self, width=50, height=14)
        self.text_box.insert(tk.END, self.full_data_string)
        self.text_box.pack(side='top', pady=6)

        # allow user to display just the data not the wavelengths all the time
        self.display_type = tk.IntVar()
        tk.Checkbutton(self, text="Show just difference data", command=self.toggle_data_display,
                       variable=self.display_type).pack(side='top', pady=6)

        # Allow the user to add comments to the data file
        tk.Label(self, text="Comments:").pack(side='top', pady=6)

        self.comment = tk.Text(self, width=50, height=5)
        self.comment.pack(side=tk.TOP, pady=6)

        button_frame = tk.Frame(self)
        button_frame.pack(side='top', pady=6)
        tk.Button(button_frame, text="Save Data", command=self.save_data).pack(side='left', padx=10)
        tk.Button(button_frame, text="Close", command=self.destroy).pack(side='left', padx=10)

    def toggle_data_display(self):
        if self.display_type.get():  # button is checked
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, self.diff_data_string)
        else:
            self.text_box.delete(1.0, tk.END)
            self.text_box.insert(tk.END, self.full_data_string)

    def save_data(self):
        try:
            _filename = open_file(self, 'saveas')  # open the file
        except Exception as error:
            messagebox.showerror(title="Error", message=error)
        self.attributes('-topmost', 'true')

        if not _filename:
            self.destroy()
        # a file was found so open it and add the data to it
        with open(_filename, mode='a', encoding='utf-8') as _file:

            if self.comment.get(1.0, tk.END):
                self.data_string += self.comment.get(1.0, tk.END)
            try:
                _file.write(self.data_string)
                _file.close()
                self.destroy()

            except Exception as error:

                messagebox.showerror(title="Error", message=error)
                self.lift()
                _file.close()


def open_file(parent, _type: str) -> str:
    """
    Make a method to return an open file or a file name depending on the type asked for
    :param parent:  master tk.TK or toplevel that called the file dialog
    :param _type:  'open' or 'saveas' to specify what type of file is to be opened
    :return: filename user selected
    """
    """ Make the options for the save file dialog box for the user """
    file_opt = options = {}
    options['defaultextension'] = ".csv"
    # options['filetypes'] = [('All files', '*.*'), ("Comma separate values", "*.csv")]
    options['filetypes'] = [("Comma separate values", "*.csv")]
    logging.debug("saving data: 1")
    if _type == 'saveas':
        """ Ask the user what name to save the file as """
        logging.debug("saving data: 2")
        _filename = filedialog.asksaveasfilename(parent=parent, confirmoverwrite=False, **file_opt)
        return _filename

    elif _type == 'open':
        _filename = filedialog.askopenfilename(**file_opt)
        return _filename
