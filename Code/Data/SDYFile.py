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
        'pa_trans': (12, 13, 14, 15),
        'pa_physio': (16, 17, 18, 19),
        'ecg': (24, 26, 28, 30),
        'flow': (32, 32, 33, 33),
        'calc1': (34, 34, 35, 35),
        'calc2': (36, 36, 37, 37),
        'calc3': (38, 38, 39, 39)}

SAMPLING_FREQ = 200


class SDYFile:
    """Thanks to Matt Shun-Shin for figuring out the fields"""

    def __init__(self, filepath, pa_channel='pa_physio'):
        self.studypath = filepath
        self.pa_channel = pa_channel
        self.filetype, self.datetime, self.examtype, self.demographics = None, None, None, None
        self.raw_study_data = None
        self.pd, self.pa, self.ecg, self.flow, self.df = None, None, None, None, None
        self.calc1, self.calc2, self.calc3 = None, None, None

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
        self.pa = raw_study_data[:, COLS[self.pa_channel]].ravel()
        self.ecg = raw_study_data[:, COLS['ecg']].ravel()
        self.flow = raw_study_data[:, COLS['flow']].ravel()
        self.calc1 = raw_study_data[:, COLS['calc1']].ravel()
        self.calc2 = raw_study_data[:, COLS['calc2']].ravel()
        self.calc3 = raw_study_data[:, COLS['calc3']].ravel()
        self.create_dataframe()

    def create_dataframe(self):
        """Used by Cophy, in similar format to TxtFile"""
        df = {'pa': self.pa,
              'pd': self.pd,
              'flow': self.flow,
              'ecg': self.ecg,
              'calc1': self.calc1,
              'calc2': self.calc2,
              'calc3': self.calc3,
              'time': np.linspace(0, len(self.pa) // SAMPLING_FREQ, len(self.pa))}
        self.df = pd.DataFrame.from_dict(df).astype(np.float)

    def __repr__(self):
        try:
            return f"SDY File ({EXAM_TYPES[self.examtype]} study of \"{self.demographics['SURNAME']}, {self.demographics['FIRSTNAME']}\" on {self.datetime})"
        except TypeError:
            return f"SDY File (unparsed)"


if __name__ == "__main__":
    import matplotlib.pyplot as plt

    sdy = SDYFile("../../Data/randomsdy/CRK.sdy")
    plt.plot(np.clip(sdy.pa, 0, 800), label='pa')
    plt.plot(np.clip(sdy.pd, 0, 800), label='pd')
    plt.legend()
    plt.show()

    sdy = SDYFile("../../Data/randomsdy/VUB_IMA_LAD_060814.sdy", pa_channel='pa_trans')
    plt.plot(np.clip(sdy.pa, 0, 800), label='pa')
    plt.plot(np.clip(sdy.pd, 0, 800), label='pd')
    plt.legend()
    plt.show()
