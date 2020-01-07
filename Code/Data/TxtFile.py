import os
import numpy as np
import pandas as pd


class TxtFile:
    def __init__(self, studypath, pd_offset=None):
        self.studypath = studypath
        self.pd_offset = pd_offset
        self.df = self.load_data()

    def load_data(self):
        """The heading columns are so variable it's almost unbelievable... And sometimes the RWave and Timestamp columns
        are reversed in order! Easiest is just to test for all the possibilities and hard code it (ugh)

        Returns a dataframe."""
        with open(self.studypath) as f:
            """First find the row with the RWave in it; this is our column headings"""
            lines = f.readlines()
            for i_line, line in enumerate(lines):
                if "RWave" in line:
                    heading_line = line
                    heading_line_number = i_line
                    break
            else:  # If didn't break
                raise ValueError("Failed to find heading row")
        if heading_line == "Time	Pa	Pd	ECG	IPV	Pv	RWave	Tm\n":
            names = ['time', 'pa', 'pd', 'ecg', 'flow', 'pv', 'rwave', 'timestamp']
            numeric_cols = 5
        elif heading_line == "Time[s]	Pa[mmHg]	Pa_Trans[mmHg]	Pd[mmHg]	ECG[V]	IPV[cm/s]	Pv[mmHg]	TimeStamp[s]	RWave\n":
            names = ['time', 'pa', 'pa_trans', 'pd', 'ecg', 'flow', 'pv', 'timestamp', 'rwave']
            numeric_cols = 7
        elif heading_line == "Time	Pa	Pd	ECG	IPV	Pv	RWave	\n" or heading_line == "Time	Pa	Pd	ECG	IPV	Pv	RWave\n":
            names = ['time', 'pa', 'pd', 'ecg', 'flow', 'pv', 'rwave']
            numeric_cols = 5
        else:
            raise AttributeError(f"Unable to process data format {heading_line} in file {self.studypath}")
        df = pd.read_csv(self.studypath, skiprows=heading_line_number + 1, sep='\t', header=None,
                         names=names, dtype=np.object_, index_col=False)
        df = df.stack().str.replace(',', '.').unstack()
        # Don't try to convert the 'rwave' column to numeric, it's full of crap
        df.iloc[:, 0:numeric_cols] = df.iloc[:, 0:numeric_cols].apply(pd.to_numeric)

        if self.pd_offset:
            new_pd = np.concatenate((np.array(df.pd[self.pd_offset:]), np.zeros(self.pd_offset)))
            df.pd = new_pd
            # new_flow = np.concatenate((np.array(df.flow[self.pd_offset:]), np.zeros(self.pd_offset)))
            # df.flow = new_flow

        return df
