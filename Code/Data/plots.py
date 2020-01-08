"""All of these functions receive a LabelUI (the GUI) from the TxtFile class"""

import numpy as np
import peakutils
from sklearn.metrics import auc
from scipy.signal import savgol_filter

#from Code.UI.label import SAMPLE_FREQ
SAMPLE_FREQ = 200

def pdpa(labelui, clip_vals=(0, 4)):
    df = labelui.TxtSdyFile.df
    pd = np.array(df['pd'])
    pa = np.array(df['pa'])
    time = np.array(df['time'])
    peaks = peakutils.indexes(pd, min_dist=SAMPLE_FREQ // 2)  # Max 180 bpm
    x, y = [], []
    for index_from in range(len(peaks) - 1):
        index_to = index_from + 1
        beat_pa = pa[peaks[index_from]:peaks[index_to]]
        beat_pd = pd[peaks[index_from]:peaks[index_to]]
        beat_time = time[peaks[index_from]:peaks[index_to]]
        auc_pa = auc(x=beat_time, y=beat_pa)
        auc_pd = auc(x=beat_time, y=beat_pd)
        pdpa = auc_pd / auc_pa
        if clip_vals:
            pdpa = max(pdpa, clip_vals[0])
            pdpa = min(pdpa, clip_vals[1])
        x.append(beat_time[-1])
        y.append(pdpa)
    return {'x': x, 'y': y}

def pdpa_filtered(labelui):
    results = pdpa(labelui)
    x, y = results['x'], results['y']
    y_filtered = savgol_filter(y, window_length=17, polyorder=3)
    return {'x': x, 'y': y_filtered}

def microvascular_resistance(labelui, flow_mean_or_peak='peak'):
    df = labelui.TxtSdyFile.df
    pd = np.array(df['pd'])
    flow = np.array(df['flow'])
    time = np.array(df['time'])
    peaks = peakutils.indexes(pd, min_dist=SAMPLE_FREQ // 2)  # Max 180 bpm
    x, y = [], []
    for index_from in range(len(peaks) - 1):
        index_to = index_from + 1
        beat_flow = flow[peaks[index_from]:peaks[index_to]]
        beat_pd = pd[peaks[index_from]:peaks[index_to]]
        beat_time = time[peaks[index_from]:peaks[index_to]]
        mean_pd = np.mean(beat_pd)
        x.append(beat_time[-1])
        if flow_mean_or_peak == 'peak':
            mean_flow = np.mean(beat_flow)
            resistance = mean_pd / mean_flow
        elif flow_mean_or_peak == 'peak':
            peak_flow = max(beat_flow)
            resistance = mean_pd / peak_flow
        else:
            raise ValueError(f"flow_mean_or_peak must be mean or peak, not {flow_mean_or_peak}")
        y.append(resistance)
    return {'x': x, 'y': y}

def stenosis_resistance(labelui, flow_mean_or_peak='peak'):
    df = labelui.TxtSdyFile.df
    pa = np.array(df['pa'])
    pd = np.array(df['pd'])
    flow = np.array(df['flow'])
    time = np.array(df['time'])
    peaks = peakutils.indexes(pd, min_dist=SAMPLE_FREQ // 2)  # Max 180 bpm
    x, y = [], []
    for index_from in range(len(peaks) - 1):
        index_to = index_from + 1
        beat_flow = flow[peaks[index_from]:peaks[index_to]]
        beat_pa = pa[peaks[index_from]:peaks[index_to]]
        beat_pd = pd[peaks[index_from]:peaks[index_to]]
        beat_time = time[peaks[index_from]:peaks[index_to]]
        mean_pa = np.mean(beat_pa)
        mean_pd = np.mean(beat_pd)
        delta_p = mean_pa - mean_pd
        x.append(beat_time[-1])
        if flow_mean_or_peak == 'peak':
            mean_flow = np.mean(beat_flow)
            resistance = delta_p / mean_flow
        elif flow_mean_or_peak == 'peak':
            peak_flow = max(beat_flow)
            resistance = delta_p / peak_flow
        else:
            raise ValueError(f"flow_mean_or_peak must be mean or peak, not {flow_mean_or_peak}")
        y.append(resistance)
    return {'x': x, 'y': y}


def filtered_resistance(resistance):
    x, y = resistance['x'], resistance['y']
    y_filtered = savgol_filter(y, window_length=17, polyorder=3)
    return {'x': x, 'y': y_filtered}
