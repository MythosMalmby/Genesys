# This program will create a user interface for interacting with
# the Genesys class for collecting time-dependent data.
#
# The initial design for the interface will be a notebook
# interface, with one tab for spectrometer operation, one
# for data saving, and one for plotting analyzed data.

# This program will require the Tk widgets, particularly
# the themed widgets, the Genesys class from this module,
# the Scipy module for fitting the data, the csv module
# for reading and writing the data to CSV files, and the
# matplotlib package for plotting the data.
from tkinter import *
from tkinter import ttk
from tkinter import messagebox, filedialog
from genesys import Genesys
from datetime import datetime
# from time import sleep
from csv import Sniffer, DictReader, DictWriter
from scipy.stats import linregress
from numpy import array
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import serial.tools.list_ports as list_ports
from pandas import read_csv

class TestSpec():
    '''This class will serve as a substitute for a spectrometer in
       the absence of an actual Genesys spectrophotometer. The
       class will implement all of the methods of the Genesys
       class, but most will not do anything.'''
    def reading(self):
        return 0.5
    def blank(self):
        return
    def beep(self, times=1):
        messagebox.showinfo(message="The spectrometer should have beeped {} times.".format(times))
        return
    def wavelength(self, wavelength):
        messagebox.showinfo(message="The spectrometer is set to {} nm.".format(wavelength))
        return

class SpecTab():
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(self.parent.notebook)
        self.parent.notebook.add(self.frame, text="Spectrometer")
        ttk.Label(self.frame, text="Spectrometer").grid(row=0,column=0)
        self.spectrometer = None
        self.speccombo = ttk.Combobox(self.frame)
        specvalues = ['test']
        for port in list_ports.comports():
            specvalues.append(port[0])
        self.speccombo['values'] = specvalues
        self.speccombo.bind('<<ComboboxSelected>>', self.specselect)
        self.speccombo.grid(row=0,column=1)
        self.wavelength = IntVar()
        self.wavelength.set(475)
        self.wavelength.trace("w", self.changewavelength)
        ttk.Label(self.frame, text="Wavelength (nm)").grid(row=1,column=0)
        self.waveentry = ttk.Entry(self.frame, textvariable=self.wavelength)
        self.waveentry.grid(row=1,column=1)
        self.frequency = DoubleVar()
        self.frequency.set(1)
        ttk.Label(self.frame, text="Frequency (s)").grid(row=2,column=0)
        self.freqentry = ttk.Entry(self.frame, textvariable=self.frequency)
        self.freqentry.grid(row=2,column=1)
        self.duration = DoubleVar()
        self.duration.set(120)
        ttk.Label(self.frame, text="Duration (s)").grid(row=3, column=0)
        self.durentry = ttk.Entry(self.frame, textvariable=self.duration)
        self.durentry.grid(row=3,column=1)
        self.blankbutton = ttk.Button(self.frame, text="Blank",
                                      command=self.blank)
        self.blankbutton.grid(row=4,column=0)
        self.runbutton = ttk.Button(self.frame, text="Run",
                                    command=self.collect)
        self.runbutton.grid(row=4,column=1)
        self.runprogress = DoubleVar()
        self.runprogress.set(0)
        self.progress = ttk.Progressbar(self.frame, orient=HORIZONTAL,
                                        mode='determinate',
                                        variable=self.runprogress)
        self.progress.grid(row=5,column=0,columnspan=2)
        # Create figure and canvas for figure
        self.timefigure = Figure(figsize=(5,4), dpi=100)
        self.timecanvas = FigureCanvasTkAgg(self.timefigure, master=self.frame)
        self.timecanvas.draw()
        self.timecanvas.get_tk_widget().grid(row=6, column=0, columnspan=2)

    def specselect(self, *args):
        spec = self.speccombo.get()
        if spec == "test":
            self.spectrometer = TestSpec()
        else:
            self.spectrometer = Genesys(spec)
        self.spectrometer.beep(2)
        return

    def blank(self, *args):
        self.spectrometer.blank()
        messagebox.showinfo(message="The spectrometer should be blanked.")
        return

    def changewavelength(self, *args):
        # Change the wavelength once enough digits have been typed.
        try:
            if self.wavelength.get() > 300:
                self.spectrometer.wavelength(self.wavelength.get())
                messagebox.showinfo(message="The wavelength should be changed.")
        except TclError:
            pass
        return

    def collect(self, *args):
        # Clear previous run data
        self.times = []
        self.absorbance = []
        self.timefigure.gca().clear()
        self.timecanvas.draw()
        # Set parameters from the interface
        # endtime = self.duration.get()
        self.progress["maximum"] = self.duration.get()
        # frequency = self.frequency.get()
        # Zero the clock
        starttime = datetime.now()
        # runtime = 0
        self.add_data(starttime)
        return

    def add_data(self, starttime):
        self.absorbance.append(self.spectrometer.reading())
        runtime = datetime.now() - starttime
        runtime = runtime.total_seconds()
        self.times.append(runtime)
        self.runprogress.set(runtime)
        if runtime < self.duration.get():
            self.progress.after(int(1000*self.frequency.get()),
                                self.add_data, starttime)
        else:
            # Plot the data on the graph.
            self.timefigure.gca().plot(self.times, self.absorbance, 'bo')
            # Calculate the best-fit line if slope is selected.
            if self.parent.filemanage.analysismode.get()=="Slope":
                analysis = linregress(self.times, self.absorbance)
                self.parent.filemanage.promptstrings["Slope"].set(analysis[0])
                self.parent.filemanage.promptstrings["Slope.Err"].set(analysis[4])
            # Plot the best-fit line on the graph.
                self.timefigure.gca().plot(self.times,
                                                analysis[0]*array(self.times)+analysis[1],
                                           'k-')
            self.timecanvas.draw()
            self.runprogress.set(0)
            messagebox.showinfo(message="The spectrometer collected {} timepoints and {} absorbances.".format(len(self.times),len(self.absorbance)))            
        return

class CreateNewFile():
    def __init__(self, parent, filename):
        self.parent = parent
        self.filename = filename
        self.newfile = Toplevel()
        self.newfile.title("New File")
        self.newframe = ttk.Frame(self.newfile)
        self.newframe.grid()
        self.analysismode = StringVar()
        self.analysistime = ttk.Radiobutton(self.newframe, text="Raw",
                variable=self.analysismode, value="Time")
        self.analysistime.grid(row=0, column=0)
        self.analysisslope = ttk.Radiobutton(self.newframe, text="Linear",
                variable=self.analysismode, value="Slope")
        self.analysisslope.grid(row=0, column=1)
        ttk.Label(self.newframe, text="Additional Columns").grid(row=1,column=0)
        self.additionaltext = Text(self.newframe, width=40, height=10)
        self.additionaltext.grid(row=1, column=1)
        self.cancelnew = ttk.Button(self.newframe, text="Cancel",
                command=self.newfile.destroy)
        self.cancelnew.grid(row=2, column=0)
        self.savenewbutton = ttk.Button(self.newframe, text="Create",
                                   command=self.savefile)
        self.savenewbutton.grid(row=2, column=1)
    def savefile(self, *args):
        additional = self.additionaltext.get("1.0","end").splitlines()
        if self.analysismode.get() == "Time":
            self.writerfields = ["Reaction"] + additional + ["Time","Abs"]
        elif self.analysismode.get() == "Slope":
            self.writerfields = ["Reaction"] + additional + ["Slope","Slope.Err"]
        else:
            # analysismode has not been set to a correct value
            messagebox.showerror(message="Please set mode of recording.")
            return
        with open(self.filename, "w") as fileref:
            csvdict = DictWriter(fileref, fieldnames=self.writerfields)
            csvdict.writeheader()
        self.parent.csvfile.set(self.filename)
        self.newfile.destroy()
        return

class FileTab():
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(parent.notebook)
        self.parent.notebook.add(self.frame, text="CSV")
        self.csvfile = StringVar()
        self.csvfile.trace("w",self.csvchanged)
        self.writerfields = []
        self.promptentries = {}
        self.promptstrings = {}
        self.promptlabels = {}
        ttk.Label(self.frame, textvariable=self.csvfile).grid(row=0,
                                                              column=0,
                                                              columnspan=2)
        self.filebutton = ttk.Button(self.frame, text="Select...",
                                     command=self.fileselect)
        self.filebutton.grid(row=1,column=0)
        self.newbutton = ttk.Button(self.frame, text="New File",
                                    command=self.filenew)
        self.newbutton.grid(row=1,column=1)
        self.analysismode = StringVar()
        self.reactionnumber = IntVar()
        ttk.Label(self.frame, text="Reaction").grid(row=2,column=0)
        self.reactionlabel = ttk.Label(self.frame,
                                       textvariable=self.reactionnumber)
        self.reactionlabel.grid(row=2,column=1)
        self.writebutton = ttk.Button(self.frame, text="Save",
                                      command=self.writelines)
        self.writebutton.grid(row=13,column=0)
    def filenew(self, *args):
        # New file. Prompt for info from dialog.
        filename = filedialog.asksaveasfilename()
        CreateNewFile(self, filename)
        return
    def fileselect(self, *args):
        filename = filedialog.askopenfilename()
        self.csvfile.set(filename)
        return
    def csvchanged(self, *args):
        filename = self.csvfile.get()
        with open(filename, "r") as fileref:
            csvstart = fileref.read(1024)
            if len(csvstart) > 0:
                if not Sniffer().has_header(csvstart):
                    messagebox.showinfo(icon="error",
                            message="CSV file contains content but no header!")
                    return
                fileref.seek(0)
                csvdict = DictReader(fileref)
                # Determine what mode should be set for data writing
                if "Abs" in csvdict.fieldnames:
                    # CSV holds unprocessed data
                    self.writerfields = csvdict.fieldnames
                    self.analysismode.set("Time")
                    # Remove previous prompt widgets
                    for header in self.promptentries.keys():
                        self.promptentries[header].destroy()
                        self.promptlabels[header].destroy()
                    self.promptstrings = {}
                    # Create new widgets
                    additional = [field for field in self.writerfields if field not in ["Reaction","Time","Abs"]]
                    for prow, field in enumerate(additional):
                        self.promptstrings[field] = StringVar()
                        self.promptlabels[field] = ttk.Label(self.frame,
                                                             text=field)
                        self.promptlabels[field].grid(row=3+prow, column=0)
                        self.promptentries[field] = ttk.Entry(self.frame,
                                textvariable=self.promptstrings[field])
                        self.promptentries[field].grid(row=3+prow, column=1)
                    for entry in csvdict:
                        self.reactionnumber.set(entry["Reaction"])
                        for field in additional:
                            self.promptstrings[field].set(entry[field])
                elif "Slope" in csvdict.fieldnames:
                    self.writerfields = csvdict.fieldnames
                    self.analysismode.set("Slope")
                    # Remove previous prompt widgets
                    for header in self.promptentries.keys():
                        self.promptentries[header].destroy()
                        self.promptlabels[header].destroy()
                    self.promptstrings = {}
                    # Create new widgets
                    additional = [field for field in self.writerfields if field != "Reaction"]
                    for prow, field in enumerate(additional):
                        self.promptstrings[field] = StringVar()
                        self.promptlabels[field] = ttk.Label(self.frame,
                                                             text=field)
                        self.promptlabels[field].grid(row=3+prow, column=0)
                        self.promptentries[field] = ttk.Entry(self.frame,
                                textvariable=self.promptstrings[field])
                        self.promptentries[field].grid(row=3+prow, column=1)
                    for entry in csvdict:
                        self.reactionnumber.set(entry["Reaction"])
                        for field in additional:
                            self.promptstrings[field].set(entry[field])
                    # Create appropriate values for plotting combobox
                    self.parent.plotting.plotcombo['values'] = [field for field in additional if field not in ('Slope', 'Slope.Err')]
                    self.parent.plotting.groupcombo['values'] = [field for field in additional if field not in ('Slope', 'Slope.Err')]
                else:
                    # Headers don't correspond to a set generated by this program
                    messagebox.showerror(message="CSV file doesn't match those generated by this program.")
            else:
                messagebox.showerror(message="CSV file doesn't contain any content.")
        return

    def writelines(self, *args):
        self.reactionnumber.set(self.reactionnumber.get()+1)
        with open(self.csvfile.get(), "a") as csvfile:
            csvdict = DictWriter(csvfile, fieldnames=self.writerfields)
            # Create the dictionary for writing
            record = {}
            record["Reaction"] = self.reactionnumber.get()
            for field in self.promptstrings.keys():
                record[field] = self.promptstrings[field].get()
            if self.analysismode.get() == "Time":
                # Record a line for each timepoint
                for timepoint, absorbance in zip(self.parent.spectrometer.times,
                                                 self.parent.spectrometer.absorbance):
                    record["Time"] = timepoint
                    record["Abs"] = absorbance
                    csvdict.writerow(record)
            elif self.analysismode.get() == "Slope":
                # All data should be ready to be written to the file.
                csvdict.writerow(record)
                # Update the plot in the plotting tab
                self.parent.plotting.plotanalysis()
        return

class PlotTab():
    def __init__(self, parent):
        self.parent = parent
        self.frame = ttk.Frame(self.parent.notebook)
        self.parent.notebook.add(self.frame, text="Plot")
        ttk.Label(self.frame, text="Plot slope as a function of").grid(row=0,
                                                                       column=0)
        self.plotx = StringVar()
        self.plotcombo = ttk.Combobox(self.frame, textvariable=self.plotx)
        self.plotcombo.bind('<<ComboboxSelected>>', self.plotanalysis)
        self.plotcombo['values'] = ('To', 'Be', 'Computed')
        self.plotcombo.grid(row=0,column=1)
        # Add a combo box to select grouping parameter
        ttk.Label(self.frame, text="Group data by").grid(row=1,column=0)
        self.groupx = StringVar()
        self.groupcombo = ttk.Combobox(self.frame, textvariable=self.groupx)
        self.groupcombo.bind('<<ComboboxSelected>>', self.plotanalysis)
        self.groupcombo.grid(row=1,column=1)
        self.analysisfigure = Figure(figsize=(5,4), dpi=100)
        self.analysiscanvas = FigureCanvasTkAgg(self.analysisfigure,
                                                master=self.frame)
        self.analysiscanvas.draw()
        self.analysiscanvas.get_tk_widget().grid(row=11,column=0,columnspan=2)

    def plotanalysis(self, *args):
        if self.plotx.get() != "":
            self.analysisfigure.gca().clear()
            self.analysiscanvas.draw()
            dataframe = read_csv(self.parent.filemanage.csvfile.get())
            if self.groupx.get() != "":
                for label, group in dataframe.groupby(self.groupx.get()):
                    self.analysisfigure.gca().plot(self.plotx.get(), "Slope",
                                                   marker='o', label=label,
                                                   linestyle='',
                                                   data=group)
                    self.analysisfigure.legend()
            else:
                self.analysisfigure.gca().plot(self.plotx.get(), 'Slope', 'o',
                                               data=dataframe)
            self.analysiscanvas.draw()
        return

class KineticsGUI():
    def __init__(self, root):
        self.root = root
        self.root.title("Absorbance Kinetics")
        self.notebook = ttk.Notebook(root)
        self.notebook.grid(row=0, column=0)
        self.operation = SpecTab(self)
        self.filemanage = FileTab(self)
        self.plotting = PlotTab(self)
        
root = Tk()
KineticsGUI(root)
root.mainloop()
