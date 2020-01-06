import os
import sys
import pickle
import traceback
import numpy as np
import pyqtgraph as pg
from glob import glob

from PyQt5 import QtCore, QtWidgets

from Code.Data import plots
import Code.Data.calculations as c
from Code.Data.TxtFile import TxtFile
from Code.Data.SDYFile import SDYFile
from _Old.protocols import protocols
from Code.UI.layout_label import Ui_MainWindow

if QtCore.QT_VERSION >= 0x50501:
    def excepthook(type_, value, traceback_):
        traceback.print_exception(type_, value, traceback_)
        QtCore.qFatal('')


    sys.excepthook = excepthook

PROTOCOL = protocols['combowire']
SAMPLE_FREQ = 200
PD_OFFSET_TIME = 0.00
PD_OFFSET_POINT = int(PD_OFFSET_TIME * SAMPLE_FREQ)


class LabelledLinearRegionItem(pg.LinearRegionItem):
    def __init__(self, values, movable, label):
        super(LabelledLinearRegionItem, self).__init__(values=values, movable=movable)
        self.label = pg.InfLineLabel(self.lines[1], label, position=0.3, rotateAxis=(1, 0), anchor=(1, 1))


class LabelUI(Ui_MainWindow):
    def __init__(self, mainwindow):
        super(LabelUI, self).__init__()
        self.setupUi(mainwindow)
        self.actionLoad_study.triggered.connect(self.load_study_folder)
        self.comboBox_txtsdyFiles.activated.connect(self.load_txtsdyFile)
        self.GraphicsLayout = pg.GraphicsLayout()
        self.graphicsView_.setCentralItem(self.GraphicsLayout)
        self.graphicsView_.show()
        self.protocol = PROTOCOL
        self.verticalLayout_Buttons.setAlignment(QtCore.Qt.AlignTop)

        self.studyFolderPath = None
        self.studyData = dict()
        self.TxtSdyFile = None
        self.calculations = dict()

        with open("./information.txt", 'r') as f:
            self.textBrowser.setHtml("\n".join(f.readlines()))

        self.plot_pressure = None
        self.plot_flow = None
        self.plot_pressure_ratios = None
        self.plot_resistances = None
        self.plot_ensemble_rest = None
        self.plot_ensemble_hyp = None

        self.slider_group_rest = None
        self.slider_group_hyp = None

        self.ensemble_data_rest = None
        self.ensemble_data_hyp = None

        self.slider_notch_rest = None
        self.slider_notch_hyp = None
        self.slider_enddiastole_rest = None
        self.slider_enddiastole_hyp = None

    def refresh_ui(self):
        if self.studyFolderPath:
            self.comboBox_txtsdyFiles.setEnabled(True)
            self.label_PatientID.setText(f"Patient ID: {self.studyData.get('id', 'NA')}")

            # Get rid of the old files list and add the new ones
            self.comboBox_txtsdyFiles.clear()
            self.comboBox_txtsdyFiles.addItem("Please select a file")

            txt_file_paths = glob(os.path.join(self.studyFolderPath, "*.txt"))
            sdy_file_paths = glob(os.path.join(self.studyFolderPath, "*.sdy"))
            for txt_file_path in txt_file_paths:
                labels = self.load_cph(f"{txt_file_path}.cph")
                self.comboBox_txtsdyFiles.addItem("{} - {} labels".format(txt_file_path, len(labels)))
            for sdy_file_path in sdy_file_paths:
                labels = self.load_cph(f"{sdy_file_path}.cph")
                self.comboBox_txtsdyFiles.addItem("{} - {} labels".format(sdy_file_path, len(labels)))

            # Clear the plot window
            self.GraphicsLayout = pg.GraphicsLayout()
            self.graphicsView_.setCentralItem(self.GraphicsLayout)
            self.graphicsView_.show()
        else:  # If a study folder path isn't set, the file box shouldn't be clickable
            self.comboBox_txtsdyFiles.setEnabled(False)

    def load_study_folder(self):
        self.studyFolderPath = QtWidgets.QFileDialog.getExistingDirectory(None, "Select a folder", "./data/",
                                                                          QtWidgets.QFileDialog.ShowDirsOnly)
        self.refresh_ui()

    def load_txtsdyFile(self):
        self.studyFolderPath = None
        self.studyData = dict()
        self.TxtSdyFile = None
        self.calculations = dict()

        self.plot_pressure = None
        self.plot_flow = None
        self.plot_pressure_ratios = None
        self.plot_resistances = None
        self.plot_ensemble_rest = None
        self.plot_ensemble_hyp = None

        self.slider_group_rest = None
        self.slider_group_hyp = None

        self.ensemble_data_rest = None
        self.ensemble_data_hyp = None

        self.slider_notch_rest = None
        self.slider_notch_hyp = None
        self.slider_enddiastole_rest = None
        self.slider_enddiastole_hyp = None

        study_path = self.comboBox_txtsdyFiles.currentText().rsplit(' ', 3)[0]
        try:
            if os.path.splitext(study_path)[-1] == ".txt":
                self.TxtSdyFile = TxtFile(studypath=study_path, pd_offset=PD_OFFSET_POINT)
            elif os.path.splitext(study_path)[-1] == ".sdy":
                self.TxtSdyFile = SDYFile(filepath=study_path)
        except FileNotFoundError:
            print(f"!!!UNABLE TO FIND FILE {study_path}!!!")

        self.plot_txtsdyFile()
        self.draw_buttons()
        self.load()
        self.perform_calculations_and_save()

    def plot_txtsdyFile(self):
        pg.setConfigOptions(antialias=True)

        self.GraphicsLayout = pg.GraphicsLayout()
        self.GraphicsLayout.setSpacing(0)
        self.GraphicsLayout.setContentsMargins(0., 0., 0., 0.)
        self.graphicsView_.setCentralItem(self.GraphicsLayout)
        self.graphicsView_.show()

        # data
        data_pa = np.array(self.TxtSdyFile.df['pa'])
        data_pd = np.array(self.TxtSdyFile.df['pd'])
        data_time = np.array(self.TxtSdyFile.df['time'])
        data_flow = np.array(self.TxtSdyFile.df['flow'])
        data_pdpa = plots.pdpa(self)
        data_pdpa_filtered = plots.pdpa_filtered(self)
        data_microvascular_resistance = plots.microvascular_resistance(self)
        data_microvascular_resistance_filtered = plots.microvascular_resistance_filtered(self)
        data_stenosis_resistance = plots.stenosis_resistance(self)
        data_stenosis_resistance_filtered = plots.stenosis_resistance(self)

        # plots
        self.plot_pressure = self.GraphicsLayout.addPlot(row=0, col=0, colspan=2, title='Pressure')
        self.plot_flow = self.GraphicsLayout.addPlot(row=1, col=0, colspan=2, title='Flow')
        self.plot_pressure_ratios = self.GraphicsLayout.addPlot(row=2, col=0, colspan=2,
                                                                title='Distal:Proximal Pressure')
        self.plot_resistances = self.GraphicsLayout.addPlot(row=3, col=0, colspan=2, title='Resistances')
        self.plot_ensemble_rest = self.GraphicsLayout.addPlot(row=4, col=0, colspan=1, title='Resting Ensemble')
        self.plot_ensemble_hyp = self.GraphicsLayout.addPlot(row=4, col=1, colspan=1, title='Hyperaemic Ensemble')
        for p in (self.plot_pressure, self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            p.addLegend()
        for p in (self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            p.setXLink(self.plot_pressure)

        # Lines
        # print(data_pa)
        # print(data_pa[0])
        # print(type(data_pa[0]))
        self.plot_pressure.plot(x=data_time, y=data_pa, name='Pa', pen='r')
        self.plot_pressure.plot(x=data_time, y=data_pd, name='Pd', pen='y')
        self.plot_flow.plot(x=data_time, y=data_flow, name='Flow', pen='g')
        self.plot_pressure_ratios.plot(x=data_pdpa['x'], y=data_pdpa['y'], name='PdPa (beat-wise)',
                                       pen=(255, 255, 0, 100))
        self.plot_pressure_ratios.plot(x=data_pdpa_filtered['x'], y=data_pdpa_filtered['y'], name='PdPa (filtered)',
                                       pen=(255, 255, 0, 200))
        self.plot_resistances.plot(x=data_microvascular_resistance['x'],
                                   y=data_microvascular_resistance['y'],
                                   name='Microvascular (beat-wise)',
                                   pen=(0, 255, 255, 100))
        self.plot_resistances.plot(x=data_microvascular_resistance_filtered['x'],
                                   y=data_microvascular_resistance_filtered['y'],
                                   name='Microvascular (filtered)',
                                   pen=(0, 255, 255, 200))
        self.plot_resistances.plot(x=data_stenosis_resistance['x'],
                                   y=data_stenosis_resistance['y'],
                                   name='Stenosis (beat-wise)',
                                   pen=(255, 0, 255, 100))
        self.plot_resistances.plot(x=data_stenosis_resistance_filtered['x'],
                                   y=data_stenosis_resistance_filtered['y'],
                                   name='Stenosis (filtered)',
                                   pen=(255, 0, 255, 200))

    def click_button_rest(self):
        if self.button_rest.slider_active:
            self.button_rest.slider_active = False
            self.button_rest.setStyleSheet(f"background-color: 'red'")
            self.destroy_slider_group_rest()
            self.perform_calculations_and_save()
        else:
            self.button_rest.slider_active = True
            self.button_rest.setStyleSheet(f"background-color: 'green'")
            self.create_slider_group_rest()

    def click_button_hyp(self):
        if self.button_hyp.slider_active:
            self.button_hyp.slider_active = False
            self.button_hyp.setStyleSheet(f"background-color: 'red'")
            self.destroy_slider_group_hyp()
            self.perform_calculations_and_save()
        else:
            self.button_hyp.slider_active = True
            self.button_hyp.setStyleSheet(f"background-color: 'green'")
            self.create_slider_group_hyp()

    def click_button_marker(self, button, type):
        if button.slider_active:
            button.slider_active = False
            button.setStyleSheet(f"background-color: 'red'")
            self.destroy_marker_slider(type)
            self.perform_calculations_and_save()
        else:
            button.slider_active = True
            button.setStyleSheet(f"background-color: 'green'")
            self.create_marker_slider(type)

    def create_marker_slider(self, type, value=None):
        slider = pg.InfiniteLine(pos=0.2, movable=True, label='',
                                 labelOpts={'position': 0.5, 'rotateAxis': (1, 0), 'anchor': (1, 1)})
        slider.sigPositionChangeFinished.connect(lambda: self.perform_calculations_and_save())
        if type == 'notch_rest':
            slider.label = pg.InfLineLabel(slider, text="Dicrotic notch")
            if value:
                slider.setValue(value)
            self.plot_ensemble_rest.addItem(slider)
            self.slider_notch_rest = slider
        elif type == 'notch_hyp':
            slider.label = pg.InfLineLabel(slider, text="Dicrotic notch")
            if value:
                slider.setValue(value)
            self.plot_ensemble_hyp.addItem(slider)
            self.slider_notch_hyp = slider
        elif type == 'enddiastole_rest':
            slider.label = pg.InfLineLabel(slider, text="End diastole")
            if value:
                slider.setValue(value)
            self.plot_ensemble_rest.addItem(slider)
            self.slider_enddiastole_rest = slider
        elif type == 'enddiastole_hyp':
            slider.label = pg.InfLineLabel(slider, text="End diastole")
            if value:
                slider.setValue(value)
            self.plot_ensemble_hyp.addItem(slider)
            self.slider_enddiastole_hyp = slider
        else:
            raise ValueError(f"Unknown button type pressed: {type}")

    def destroy_marker_slider(self, type):
        if type == 'notch_rest':
            self.plot_ensemble_rest.removeItem(self.slider_notch_rest)
            self.slider_notch_rest = None
        elif type == 'notch_hyp':
            self.plot_ensemble_hyp.removeItem(self.slider_notch_hyp)
            self.slider_notch_hyp = None
        elif type == 'enddiastole_rest':
            self.plot_ensemble_rest.removeItem(self.slider_enddiastole_rest)
            self.slider_enddiastole_rest = None
        elif type == 'enddiastole_hyp':
            self.plot_ensemble_hyp.removeItem(self.slider_enddiastole_hyp)
            self.slider_enddiastole_hyp = None
        else:
            raise ValueError(f"Unknown button type pressed: {type}")

    def create_slider_group_rest(self, range_from=None, range_to=None):
        if range_from is None or range_to is None:
            x_lower, x_upper = self.plot_pressure.getAxis('bottom').range
            range_from = ((x_upper - x_lower) * 0.20) + x_lower
            range_to = ((x_upper - x_lower) * 0.25) + x_lower
        self.slider_group_rest = []
        for p in (self.plot_pressure, self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            slider = LabelledLinearRegionItem(values=(range_from, range_to), movable=True, label='Rest')
            slider.sigRegionChangeFinished.connect(
                lambda s=slider, group='rest': self.adjust_all_sliders_in_group(s, group))
            p.addItem(slider, ignoreBounds=True)
            self.slider_group_rest.append(slider)

    def destroy_slider_group_rest(self, ):
        for p in (self.plot_pressure, self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            for slider in self.slider_group_rest:  # Try to remove each slider from plot, as a list
                p.removeItem(slider)
        self.slider_group_rest = []
        self.perform_calculations_and_save()

    def create_slider_group_hyp(self, range_from=None, range_to=None):
        if range_from is None or range_to is None:
            x_lower, x_upper = self.plot_pressure.getAxis('bottom').range
            range_from = ((x_upper - x_lower) * 0.80) + x_lower
            range_to = ((x_upper - x_lower) * 0.85) + x_lower
        self.slider_group_hyp = []
        for p in (self.plot_pressure, self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            slider = LabelledLinearRegionItem(values=(range_from, range_to), movable=True, label='Hyperaemia')
            slider.sigRegionChangeFinished.connect(
                lambda s=slider, group='hyp': self.adjust_all_sliders_in_group(s, group))
            p.addItem(slider, ignoreBounds=True)
            self.slider_group_hyp.append(slider)

    def destroy_slider_group_hyp(self, ):
        for p in (self.plot_pressure, self.plot_flow, self.plot_pressure_ratios, self.plot_resistances):
            for slider in self.slider_group_hyp:  # Try to remove each slider from plot, as a list
                p.removeItem(slider)
        self.slider_group_hyp = []
        self.perform_calculations_and_save()

    def draw_buttons(self):
        def clear_layout(layout):
            for i in reversed(range(layout.count())):
                try:
                    layout.itemAt(i).widget().setParent(None)
                except AttributeError:
                    pass

        clear_layout(self.verticalLayout_Buttons)

        self.button_rest = QtWidgets.QPushButton(self.centralwidget)
        self.button_rest.setText('Rest')
        self.button_rest.slider_active = False
        self.button_rest.clicked.connect(lambda state: self.click_button_rest())
        self.button_rest.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_rest)

        self.button_hyp = QtWidgets.QPushButton(self.centralwidget)
        self.button_hyp.setText('Hyperaemia')
        self.button_hyp.slider_active = False
        self.button_hyp.clicked.connect(lambda state, button=self.button_hyp: self.click_button_hyp())
        self.button_hyp.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_hyp)

        self.button_notch_rest = QtWidgets.QPushButton(self.centralwidget)
        self.button_notch_rest.setText('Dicrotic notch (rest)')
        self.button_notch_rest.slider_active = False
        self.button_notch_rest.clicked.connect(lambda state,
                                                      button=self.button_notch_rest,
                                                      type='notch_rest': self.click_button_marker(button, type))
        self.button_notch_rest.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_notch_rest)

        self.button_enddiastole_rest = QtWidgets.QPushButton(self.centralwidget)
        self.button_enddiastole_rest.setText('End diastole (rest)')
        self.button_enddiastole_rest.slider_active = False
        self.button_enddiastole_rest.clicked.connect(lambda state,
                                                            button=self.button_enddiastole_rest,
                                                            type='enddiastole_rest': self.click_button_marker(button,
                                                                                                              type))
        self.button_enddiastole_rest.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_enddiastole_rest)

        self.button_notch_hyp = QtWidgets.QPushButton(self.centralwidget)
        self.button_notch_hyp.setText('Dicrotic notch (hyperaemia)')
        self.button_notch_hyp.slider_active = False
        self.button_notch_hyp.clicked.connect(lambda state,
                                                     button=self.button_notch_hyp,
                                                     type='notch_hyp': self.click_button_marker(button, type))
        self.button_notch_hyp.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_notch_hyp)

        self.button_enddiastole_hyp = QtWidgets.QPushButton(self.centralwidget)
        self.button_enddiastole_hyp.setText('End diastole (hyperaemia)')
        self.button_enddiastole_hyp.slider_active = False
        self.button_enddiastole_hyp.clicked.connect(lambda state,
                                                           button=self.button_enddiastole_hyp,
                                                           type='enddiastole_hyp': self.click_button_marker(button,
                                                                                                            type))
        self.button_enddiastole_hyp.setStyleSheet(f"background-color: 'red'")
        self.verticalLayout_Buttons.addWidget(self.button_enddiastole_hyp)

    def adjust_all_sliders_in_group(self, slider, slider_group):
        slider_min, slider_max = slider.getRegion()
        if slider_group == 'rest':
            slider_group = self.slider_group_rest
        elif slider_group == 'hyp':
            slider_group = self.slider_group_hyp
        else:
            raise ValueError(f"Unknown slider group")
        for slider in slider_group:
            slider.setRegion((slider_min, slider_max))
        self.perform_calculations_and_save()

    def calculate_ensemble_rest(self):
        self.plot_ensemble_rest.clear()
        self.ensemble_data_rest, n_rejected = c.ensemble_beats(self, 'rest')
        if self.ensemble_data_rest:
            t0 = self.ensemble_data_rest[0]['time']
            for beat in self.ensemble_data_rest:
                self.plot_ensemble_rest.plot(x=t0, y=beat['pa'], pen=(192, 192, 192, 100))
            mean_pa = c.average_beats_from_beat_list(self.ensemble_data_rest, measure='pa')
            self.plot_ensemble_rest.plot(x=t0, y=mean_pa, pen='g', width=100)
        self.plot_ensemble_rest.setTitle(
            f"Resting Ensemble ({len(self.ensemble_data_rest)} beats; {n_rejected} rejected)")
        if self.slider_notch_rest:
            self.plot_ensemble_rest.addItem(self.slider_notch_rest)
        if self.slider_enddiastole_rest:
            self.plot_ensemble_rest.addItem(self.slider_enddiastole_rest)

    def calculate_ensemble_hyp(self):
        self.plot_ensemble_hyp.clear()
        self.ensemble_data_hyp, n_rejected = c.ensemble_beats(self, 'hyp')
        if self.ensemble_data_hyp:
            t0 = self.ensemble_data_hyp[0]['time']
            for beat in self.ensemble_data_hyp:
                self.plot_ensemble_hyp.plot(x=t0, y=beat['pa'], pen=(192, 192, 192, 100))
            mean_pa = c.average_beats_from_beat_list(self.ensemble_data_hyp, measure='pa')
            self.plot_ensemble_hyp.plot(x=t0, y=mean_pa, pen='g', width=100)
        self.plot_ensemble_hyp.setTitle(
            f"Hyperaemic Ensemble ({len(self.ensemble_data_hyp)} beats; {n_rejected} rejected)")
        if self.slider_notch_hyp:
            self.plot_ensemble_hyp.addItem(self.slider_notch_hyp)
        if self.slider_enddiastole_hyp:
            self.plot_ensemble_hyp.addItem(self.slider_enddiastole_hyp)

    def perform_calculations(self):
        self.calculations['pressures'] = []
        self.calculations['pressure_ratios'] = []
        self.calculations['flows'] = []
        self.calculations['flow_ratios'] = []
        self.calculations['resistances'] = []
        if self.ensemble_data_rest:
            self.calculations['pressures'].append({'name': 'Pa',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.wholecycle_measure(self, 'rest', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Pd',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.wholecycle_measure(self, 'rest', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Pa',
                                                   'state': 'rest',
                                                   'phase': 'peak',
                                                   'value': c.wholecycle_measure(self, 'rest', 'pa', 'peak')})
            self.calculations['pressures'].append({'name': 'Pd',
                                                   'state': 'rest',
                                                   'phase': 'peak',
                                                   'value': c.wholecycle_measure(self, 'rest', 'pd', 'peak')})

            pdpa = c.wholecycle_measure(self, 'rest', 'pd', 'mean') / c.wholecycle_measure(self, 'rest', 'pa', 'mean')
            self.calculations['pressure_ratios'].append({'name': 'PdPa', 'value': pdpa})

            dfr = c.dpr_measure(self, 'rest', 'pd', 'mean') / c.dpr_measure(self, 'rest', 'pa', 'mean')
            self.calculations['pressure_ratios'].append({'name': 'dPR', 'value': dfr})

            self.calculations['pressure_ratios'].append({'name': 'RFR', 'value': c.rfr(self)})

            self.calculations['flows'].append({'name': 'Flow',
                                               'state': 'rest',
                                               'phase': 'mean',
                                               'value': c.wholecycle_measure(self, 'rest', 'flow', 'mean')})
            self.calculations['flows'].append({'name': 'Flow',
                                               'state': 'rest',
                                               'phase': 'peak',
                                               'value': c.wholecycle_measure(self, 'rest', 'flow', 'peak')})

            p_delta = c.wholecycle_measure(self, 'rest', 'pa', 'mean') - c.wholecycle_measure(self, 'rest', 'pd',
                                                                                              'mean')
            bsr_mean = p_delta / c.wholecycle_measure(self, 'rest', 'flow', 'mean')
            bsr_peak = p_delta / c.wholecycle_measure(self, 'rest', 'flow', 'peak')
            self.calculations['resistances'].append({'name': 'BSR',
                                                     'phase': 'mean',
                                                     'value': bsr_mean})
            self.calculations['resistances'].append({'name': 'BSR',
                                                     'phase': 'peak',
                                                     'value': bsr_peak})

            bmr_mean = c.wholecycle_measure(self, 'rest', 'pd', 'mean') / c.wholecycle_measure(self, 'rest', 'flow',
                                                                                               'mean')
            bmr_peak = c.wholecycle_measure(self, 'rest', 'pd', 'mean') / c.wholecycle_measure(self, 'rest', 'flow',
                                                                                               'peak')
            self.calculations['resistances'].append({'name': 'BMR',
                                                     'phase': 'mean',
                                                     'value': bmr_mean})
            self.calculations['resistances'].append({'name': 'BMR',
                                                     'phase': 'peak',
                                                     'value': bmr_peak})

        if self.ensemble_data_hyp:
            self.calculations['pressures'].append({'name': 'Pa',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.wholecycle_measure(self, 'hyp', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Pd',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.wholecycle_measure(self, 'hyp', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Pa',
                                                   'state': 'hyp',
                                                   'phase': 'peak',
                                                   'value': c.wholecycle_measure(self, 'hyp', 'pa', 'peak')})
            self.calculations['pressures'].append({'name': 'Pd',
                                                   'state': 'hyp',
                                                   'phase': 'peak',
                                                   'value': c.wholecycle_measure(self, 'hyp', 'pd', 'peak')})

            ffr = c.wholecycle_measure(self, 'hyp', 'pd', 'mean') / c.wholecycle_measure(self, 'hyp', 'pa', 'mean')
            self.calculations['pressure_ratios'].append({'name': 'FFR', 'value': ffr})

            self.calculations['flows'].append({'name': 'Flow',
                                               'state': 'hyp',
                                               'phase': 'mean',
                                               'value': c.wholecycle_measure(self, 'hyp', 'flow', 'mean')})
            self.calculations['flows'].append({'name': 'Flow',
                                               'state': 'hyp',
                                               'phase': 'peak',
                                               'value': c.wholecycle_measure(self, 'hyp', 'flow', 'peak')})

            p_delta = c.wholecycle_measure(self, 'hyp', 'pa', 'mean') - c.wholecycle_measure(self, 'hyp', 'pd', 'mean')
            hsr_mean = p_delta / c.wholecycle_measure(self, 'hyp', 'flow', 'mean')
            hsr_peak = p_delta / c.wholecycle_measure(self, 'hyp', 'flow', 'peak')
            self.calculations['resistances'].append({'name': 'HSR',
                                                     'phase': 'mean',
                                                     'value': hsr_mean})
            self.calculations['resistances'].append({'name': 'HSR',
                                                     'phase': 'peak',
                                                     'value': hsr_peak})

            hmr_mean = c.wholecycle_measure(self, 'hyp', 'pd', 'mean') / c.wholecycle_measure(self, 'hyp', 'flow',
                                                                                              'mean')
            hmr_peak = c.wholecycle_measure(self, 'hyp', 'pd', 'mean') / c.wholecycle_measure(self, 'hyp', 'flow',
                                                                                              'peak')
            self.calculations['resistances'].append({'name': 'HMR',
                                                     'phase': 'mean',
                                                     'value': hmr_mean})
            self.calculations['resistances'].append({'name': 'HMR',
                                                     'phase': 'peak',
                                                     'value': hmr_peak})

        if self.ensemble_data_rest and self.ensemble_data_hyp:
            cfr_mean = c.wholecycle_measure(self, 'hyp', 'flow', 'mean') / c.wholecycle_measure(self, 'rest', 'flow',
                                                                                                'mean')
            cfr_peak = c.wholecycle_measure(self, 'hyp', 'flow', 'peak') / c.wholecycle_measure(self, 'rest', 'flow',
                                                                                                'peak')
            self.calculations['flow_ratios'].append({'name': 'CFR',
                                                     'phase': 'mean',
                                                     'value': cfr_mean})
            self.calculations['flow_ratios'].append({'name': 'CFR',
                                                     'phase': 'peak',
                                                     'value': cfr_peak})

        if self.slider_notch_rest and self.slider_enddiastole_rest:
            self.calculations['pressures'].append({'name': 'Sysolic Pa',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'rest', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Sysolic Pd',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'rest', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pa',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.wavefree_measure(self, 'rest', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pd',
                                                   'state': 'rest',
                                                   'phase': 'mean',
                                                   'value': c.wavefree_measure(self, 'rest', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pa',
                                                   'state': 'rest',
                                                   'phase': 'peak',
                                                   'value': c.wavefree_measure(self, 'rest', 'pa', 'peak')})
            self.calculations['pressures'].append({'name': 'Wavefree Pd',
                                                   'state': 'rest',
                                                   'phase': 'peak',
                                                   'value': c.wavefree_measure(self, 'rest', 'pd', 'peak')})

            ifr = c.wavefree_measure(self, 'rest', 'pd', 'mean') / c.wavefree_measure(self, 'rest', 'pa', 'mean')
            self.calculations['pressure_ratios'].append({'name': 'iFR', 'value': ifr})

            self.calculations['flows'].append({'name': 'Wavefree flow',
                                               'state': 'rest',
                                               'phase': 'mean',
                                               'value': c.wavefree_measure(self, 'rest', 'flow', 'mean')})
            self.calculations['flows'].append({'name': 'Wavefree flow',
                                               'state': 'rest',
                                               'phase': 'peak',
                                               'value': c.wavefree_measure(self, 'rest', 'flow', 'peak')})

        if self.slider_notch_hyp and self.slider_enddiastole_hyp:
            self.calculations['pressures'].append({'name': 'Sysolic Pa',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'hyp', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Sysolic Pd',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'hyp', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pa',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'hyp', 'pa', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pd',
                                                   'state': 'hyp',
                                                   'phase': 'mean',
                                                   'value': c.systolic_measure(self, 'hyp', 'pd', 'mean')})
            self.calculations['pressures'].append({'name': 'Wavefree Pa',
                                                   'state': 'hyp',
                                                   'phase': 'peak',
                                                   'value': c.systolic_measure(self, 'hyp', 'pa', 'peak')})
            self.calculations['pressures'].append({'name': 'Wavefree Pd',
                                                   'state': 'hyp',
                                                   'phase': 'peak',
                                                   'value': c.systolic_measure(self, 'hyp', 'pd', 'peak')})

            ifrh = c.wavefree_measure(self, 'hyp', 'pd', 'mean') / c.wavefree_measure(self, 'hyp', 'pa', 'mean')
            self.calculations['pressure_ratios'].append({'name': 'iFR (hyp.)', 'value': ifrh})

            self.calculations['flows'].append({'name': 'Wavefree flow',
                                               'state': 'hyp',
                                               'phase': 'mean',
                                               'value': c.wavefree_measure(self, 'hyp', 'flow', 'mean')})
            self.calculations['flows'].append({'name': 'Wavefree flow',
                                               'state': 'hyp',
                                               'phase': 'peak',
                                               'value': c.wavefree_measure(self, 'hyp', 'flow', 'peak')})

        if self.slider_notch_rest and self.slider_notch_hyp and \
                self.slider_enddiastole_rest and self.slider_enddiastole_hyp:
            sys_cfr_mean = c.systolic_measure(self, 'hyp', 'flow', 'mean') / c.systolic_measure(self, 'rest', 'flow',
                                                                                                'mean')
            sys_cfr_peak = c.systolic_measure(self, 'hyp', 'flow', 'peak') / c.systolic_measure(self, 'rest', 'flow',
                                                                                                'peak')
            self.calculations['flow_ratios'].append({'name': 'Systolic CFR',
                                                     'phase': 'mean',
                                                     'value': sys_cfr_mean})
            self.calculations['flow_ratios'].append({'name': 'Systolic CFR',
                                                     'phase': 'peak',
                                                     'value': sys_cfr_peak})

            wf_cfr_mean = c.wavefree_measure(self, 'hyp', 'flow', 'mean') / c.wavefree_measure(self, 'rest', 'flow',
                                                                                               'mean')
            wf_cfr_peak = c.wavefree_measure(self, 'hyp', 'flow', 'peak') / c.wavefree_measure(self, 'rest', 'flow',
                                                                                               'peak')
            self.calculations['flow_ratios'].append({'name': 'Wavefree CFR',
                                                     'phase': 'mean',
                                                     'value': wf_cfr_mean})
            self.calculations['flow_ratios'].append({'name': 'Wavefree CFR',
                                                     'phase': 'peak',
                                                     'value': wf_cfr_peak})

    def display_calculations(self):
        tables = [self.tableWidget_Pressures, self.tableWidget_Flows]
        calc_dicts = [self.calculations['pressures'], self.calculations['flows']]
        for table, calcs in zip(tables, calc_dicts):
            table.setRowCount(len(calcs))
            table.setColumnCount(4)
            table.setHorizontalHeaderLabels(("Parameter", "State", "Phase", "Value"))
            for i_calc, calc_dict in enumerate(calcs):
                try:
                    table.setItem(i_calc, 0, QtWidgets.QTableWidgetItem(str(calc_dict['name'])))
                    table.setItem(i_calc, 1, QtWidgets.QTableWidgetItem(str(calc_dict['state'])))
                    table.setItem(i_calc, 2, QtWidgets.QTableWidgetItem(str(calc_dict['phase'])))
                    table.setItem(i_calc, 3, QtWidgets.QTableWidgetItem(str(round(calc_dict['value'], 2))))
                except KeyError as e:
                    print(f"Failed to find {e} in {calc_dict}")

        tables = [self.tableWidget_FlowRatios, self.tableWidget_Resistances]
        calc_dicts = [self.calculations['flow_ratios'], self.calculations['resistances']]
        for table, calcs in zip(tables, calc_dicts):
            table.setRowCount(len(calcs))
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(("Parameter", "Phase", "Value"))
            for i_calc, calc_dict in enumerate(calcs):
                table.setItem(i_calc, 0, QtWidgets.QTableWidgetItem(str(calc_dict['name'])))
                table.setItem(i_calc, 1, QtWidgets.QTableWidgetItem(str(calc_dict['phase'])))
                table.setItem(i_calc, 2, QtWidgets.QTableWidgetItem(str(round(calc_dict['value'], 2))))

        tables = [self.tableWidget_PressureRatios]
        calc_dicts = [self.calculations['pressure_ratios']]
        for table, calcs in zip(tables, calc_dicts):
            table.setRowCount(len(calcs))
            table.setColumnCount(2)
            table.setHorizontalHeaderLabels(("Parameter", "Value"))
            for i_calc, calc_dict in enumerate(calcs):
                table.setItem(i_calc, 0, QtWidgets.QTableWidgetItem(str(calc_dict['name'])))
                table.setItem(i_calc, 1, QtWidgets.QTableWidgetItem(str(round(calc_dict['value'], 2))))

    def save_cph(self):
        save_dict = {}
        try:
            save_dict['range_rest'] = self.slider_group_rest[0].getRegion()
        except TypeError: pass
        try:
            save_dict['range_hyp'] = self.slider_group_hyp[0].getRegion()
        except TypeError: pass
        try:
            save_dict['notch_rest'] = self.slider_notch_rest.value()
        except AttributeError: pass
        try:
            save_dict['notch_hyp'] = self.slider_notch_hyp.value()
        except AttributeError: pass
        try:
            save_dict['enddiastole_rest'] = self.slider_enddiastole_rest.value()
        except AttributeError: pass
        try:
            save_dict['enddiastole_hyp'] = self.slider_enddiastole_hyp.value()
        except AttributeError: pass
        with open(f"{self.TxtSdyFile.studypath}.cph", 'wb') as f:
            pickle.dump(save_dict, f)
        print("Saved")

    def load(self):
        cph_path = f"{self.TxtSdyFile.studypath}.cph"
        saved_cph = self.load_cph(cph_path)
        range_rest = saved_cph.get('range_rest', None)
        range_hyp = saved_cph.get('range_hyp', None)
        notch_rest = saved_cph.get('notch_rest', None)
        notch_hyp = saved_cph.get('notch_hyp', None)
        enddiastole_rest = saved_cph.get('enddiastole_rest', None)
        enddiastole_hyp = saved_cph.get('enddiastole_hyp', None)
        if range_rest:
            self.create_slider_group_rest(range_from=range_rest[0], range_to=range_rest[1])
            self.button_rest.slider_active = True
            self.button_rest.setStyleSheet(f"background-color: 'green'")
        if range_hyp:
            self.create_slider_group_hyp(range_from=range_hyp[0], range_to=range_hyp[1])
            self.button_hyp.slider_active = True
            self.button_hyp.setStyleSheet(f"background-color: 'green'")
        if notch_rest:
            self.create_marker_slider(type='notch_rest', value=notch_rest)
            self.button_notch_rest.slider_active = True
            self.button_notch_rest.setStyleSheet(f"background-color: 'green'")
        if notch_hyp:
            self.create_marker_slider(type='notch_hyp', value=notch_hyp)
            self.button_notch_hyp.slider_active = True
            self.button_notch_hyp.setStyleSheet(f"background-color: 'green'")
        if enddiastole_rest:
            self.create_marker_slider(type='enddiastole_rest', value=enddiastole_rest)
            self.button_enddiastole_rest.slider_active = True
            self.button_enddiastole_rest.setStyleSheet(f"background-color: 'green'")
        if enddiastole_hyp:
            self.create_marker_slider(type='enddiastole_hyp', value=enddiastole_hyp)
            self.button_enddiastole_hyp.slider_active = True
            self.button_enddiastole_hyp.setStyleSheet(f"background-color: 'green'")

    @staticmethod
    def load_cph(filename):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                return pickle.load(f)
        else:
            # Save file not found
            return {}


    def perform_calculations_and_save(self):
        self.calculate_ensemble_rest()
        self.calculate_ensemble_hyp()
        self.perform_calculations()
        self.display_calculations()
        self.save_cph()


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = LabelUI(MainWindow)
    MainWindow.show()
    print('Showing')
    sys.exit(app.exec_())
