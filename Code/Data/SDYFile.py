import numpy as np
import pandas as pd

DEMOGRAPHICS = ["SURNAME", "FIRSTNAME", "MIDDLENAME", "SEX", "MRN", "CONSULTANT", "DOB", "PROCEDURE", "PROCEDURE_ID",
                "ACCESSION_NUMBER", "FFR", "FFR SUID", "REFERRING PHYSICIAN", "PATIENT HISTORY", "IVUS SUID",
                "DEPARTMENT", "INSTITUTION", "CATHLAB ID"]

EXAM_TYPES = {3: 'Pressure',
              4: 'Flow',
              5: 'Combo'}

N_CHANNELS = 1123

COLS = {'pd': (5, 7, 9, 11),
        'pa': (12, 13, 14, 15),
        'ecg': (24, 26, 28, 30),
        'flow': (32, 32, 33, 33)}

SAMPLING_FREQ = 200

class SDYFile:
    """Thanks to Matt Shun-Shin for figuring out the fields"""

    def __init__(self, filepath):
        self.studypath = filepath
        self.filetype, self.datetime, self.examtype, self.demographics = None, None, None, None
        self.raw_study_data = None
        self.pd, self.pa, self.ecg, self.flow, self.df = None, None, None, None, None

        self.parse_data()

    def parse_data(self):
        with open(self.studypath, 'rb') as f:
            self.load_study_info(f)
            self.parse_study_data(f)

    def load_study_info(self, file):
        self.filetype = np.fromfile(file, dtype=np.uint32, count=1)[0]
        self.datetime = np.fromfile(file, dtype=np.uint32, count=2)
        self.examtype = np.fromfile(file, dtype=np.int32, count=1)[0]
        demographics = {}
        for demographic_name in DEMOGRAPHICS:
            demographics[demographic_name] = file.read(512).decode('utf-16').replace('\x00', '').strip()
        self.demographics = demographics

    def parse_study_data(self, file):
        """Should start in correct place following self.load_study_info()"""
        raw_study_data = np.fromfile(file, dtype=np.uint16, count=-1)
        recording_duration = len(raw_study_data) // N_CHANNELS
        raw_study_data = raw_study_data.reshape((recording_duration, N_CHANNELS))
        self.raw_study_data = raw_study_data
        self.pd = raw_study_data[:, COLS['pd']].ravel()
        self.pa = raw_study_data[:, COLS['pa']].ravel()
        self.ecg = raw_study_data[:, COLS['ecg']].ravel()
        self.flow = raw_study_data[:, COLS['flow']].ravel()
        self.create_dataframe()

    def create_dataframe(self):
        """Used by Cophy, in similar format to TxtFile"""
        df = {'pa': self.pa,
              'pd': self.pd,
              'flow': self.flow,
              'ecg': self.ecg,
              'time': np.linspace(0, len(self.pa)//SAMPLING_FREQ, len(self.pa))}
        self.df = pd.DataFrame.from_dict(df).astype(np.float)

    def __repr__(self):
        try:
            return f"SDY File ({EXAM_TYPES[self.examtype]} study of \"{self.demographics['SURNAME']}, {self.demographics['FIRSTNAME']}\" on {self.datetime})"
        except TypeError:
            return f"SDY File (unparsed)"
