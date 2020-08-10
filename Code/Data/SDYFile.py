from math import sqrt
import numpy as np
import pandas as pd
import peakutils
import scipy.signal as signal

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
EXPECTED_SAMPLING_INTERVAL_MAX = int(SAMPLING_FREQ/2)


class SDYFile:
    """Thanks to Matt Shun-Shin for figuring out the fields"""

    def __init__(self, filepath, pa_channel='pa_physio', clip_wave_quantile=0.9, clip_wave_n_quantiles=1.5):
        self.studypath = filepath
        self.pa_channel = pa_channel
        self.clip_wave_quantile = clip_wave_quantile
        self.clip_wave_n_quantiles = clip_wave_n_quantiles
        self.filetype, self.datetime, self.examtype, self.demographics = None, None, None, None
        self.patient_id, self.study_date, self.export_date = None, None, None  # To mimic TxtFile
        self.raw_study_data = None
        self.pd, self.pa, self.ecg, self.flow, self.df = None, None, None, None, None
        self.calc1, self.calc2, self.calc3 = None, None, None

        self.parse_data()
        self.peaks = self.find_peaks()
        print(f"Found {len(self.peaks)}: {self.peaks}")

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
        self.patient_id = demographics['MRN']
        self.study_date = self.datetime
        self.export_date = "NA (SDY file)"

    def parse_study_data(self, file):
        """Should start in correct place following self.load_study_info()"""
        raw_study_data = np.fromfile(file, dtype=np.uint16, count=-1)
        recording_duration = len(raw_study_data) // N_CHANNELS
        raw_study_data = raw_study_data.reshape((recording_duration, N_CHANNELS))
        self.raw_study_data = raw_study_data
        self.pd = self.clip_wave(raw_study_data[:, COLS['pd']].ravel(), quantile=self.clip_wave_quantile, n_quantiles=self.clip_wave_n_quantiles)
        self.pa = self.clip_wave(raw_study_data[:, COLS[self.pa_channel]].ravel(), quantile=self.clip_wave_quantile, n_quantiles=self.clip_wave_n_quantiles, ref_wave=self.pd)
        self.ecg = raw_study_data[:, COLS['ecg']].ravel()
        self.flow = raw_study_data[:, COLS['flow']].ravel()
        self.calc1 = raw_study_data[:, COLS['calc1']].ravel()
        self.calc2 = raw_study_data[:, COLS['calc2']].ravel()
        self.calc3 = raw_study_data[:, COLS['calc3']].ravel()
        self.create_dataframe()

    def create_dataframe(self):
        """Used by Cophy, in similar format to TxtFile"""
        df = {'pa': np.array(self.pa),
              'pd': np.array(self.pd),
              'flow': np.array(self.flow),
              'ecg': np.array(self.ecg),
              'calc1': np.array(self.calc1),
              'calc2': np.array(self.calc2),
              'calc3': np.array(self.calc3),
              'time': np.linspace(0, len(self.pa) // SAMPLING_FREQ, len(self.pa))}
        self.df = pd.DataFrame.from_dict(df).astype(np.float)

    @staticmethod
    def clip_wave(wave, quantile, n_quantiles, ref_wave=None):
        wave = np.array(wave, dtype=np.float)
        if ref_wave is None:
            ref_wave = wave
        quantile = np.nanquantile(ref_wave, quantile)
        median = np.nanmedian(ref_wave)
        wave[wave > median + (n_quantiles * quantile)] = np.nan
        wave = SDYFile.numpy_fill(wave)  # Switch nans with preceding values, makes things easier
        return wave

    @staticmethod
    def numpy_fill(arr):
        '''Solution provided by Divakar. -  see https://stackoverflow.com/q/41190852'''
        arr = np.expand_dims(arr, 0)
        mask = np.isnan(arr)
        idx = np.where(~mask, np.arange(mask.shape[1]), 0)
        np.maximum.accumulate(idx, axis=1, out=idx)
        out = arr[np.arange(idx.shape[0])[:, None], idx]
        return out[0]

    def find_peaks(self, trace_name='pd'):
        def tony_detect_peaks(signal, threshold=0.5):
            """
            https://github.com/MonsieurV/py-findpeaks/blob/master/tests/libs/tony_beltramelli_detect_peaks.py
            Performs peak detection on three steps: root mean square, peak to
            average ratios and first order logic.
            threshold used to discard peaks too small """
            # compute root mean square
            root_mean_square = sqrt(np.sum(np.square(signal) / len(signal)))
            # compute peak to average ratios
            ratios = np.array([pow(x / root_mean_square, 2) for x in signal])
            # apply first order logic
            peaks = (ratios > np.roll(ratios, 1)) & (ratios > np.roll(ratios, -1)) & (ratios > threshold)
            # optional: return peak indices
            peak_indexes = []
            for i in range(0, len(peaks)):
                if peaks[i]:
                    peak_indexes.append(i)
            return peak_indexes

        PEAKMETHOD = 'peakutils'
        trace = np.array(self.df[trace_name])

        if PEAKMETHOD == 'peakutils':
            print(f"In finding peaks, trace is\n{trace}, max of {max(trace)}, min dist of {EXPECTED_SAMPLING_INTERVAL_MAX}")
            peaks = peakutils.indexes(trace, min_dist=int(EXPECTED_SAMPLING_INTERVAL_MAX))
            print(f"Got {len(peaks)} peaks: {peaks}")
        elif PEAKMETHOD == 'cwt':
            widths = [int(w) for w in np.linspace(EXPECTED_SAMPLING_INTERVAL_MAX, int(EXPECTED_SAMPLING_INTERVAL_MAX*4), 4)]
            print(f'widths are {widths}')
            peaks = signal.find_peaks_cwt(trace, widths=widths)
        elif PEAKMETHOD == 'tony':
            peaks = tony_detect_peaks(trace)
        else:
            raise ValueError()

        return peaks

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
