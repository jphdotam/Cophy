"""All of these functions receive a LabelUI (the GUI) from the TxtFile class"""

import numpy as np
import peakutils
from sklearn.metrics import auc
from scipy.signal import savgol_filter

WINDOW_LEN = 17  # Default 17

#from Code.UI.label import SAMPLE_FREQ
SAMPLE_FREQ = 200
MAX_RR_INTERVAL = SAMPLE_FREQ // 4   # //3 -> 180
MIN_PEAK_INTERVAL_OVER_SAMPLE = SAMPLE_FREQ * 6  # 6 -> 10 bpm (NB need to take into account port open etc.)

def find_peaks(trace):
    min_peaks = len(trace) / MIN_PEAK_INTERVAL_OVER_SAMPLE

    peaks = peakutils.indexes(trace, min_dist=MAX_RR_INTERVAL)

    if len(peaks) < min_peaks:
        print(f"Found {len(peaks)} but expected at least {min_peaks} - using thresh 0.2 ->")
        peaks = peakutils.indexes(trace, thres=0.2, min_dist=MAX_RR_INTERVAL)
        print(len(peaks))

        if len(peaks < min_peaks):
            print(f"Found {len(peaks)} but expected at least {min_peaks} - using thresh 0.1 ->")
            peaks = peakutils.indexes(trace, thres=0.05, min_dist=MAX_RR_INTERVAL)
            print(len(peaks))

    return peaks


def pdpa(labelui, peaks, clip_vals=(0, 4)):
    df = labelui.TxtSdyFile.df
    pd = np.array(df['pd'])
    pa = np.array(df['pa'])
    time = np.array(df['time'])
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

def pdpa_filtered(labelui, pdpa):
    x, y = pdpa['x'], pdpa['y']
    try:
        y_filtered = savgol_filter(y, window_length=WINDOW_LEN, polyorder=3)
    except ValueError:
        print(f"Insufficient data to plot PdPa - try changing Pa channel if using SDY file?")
        y_filtered = np.array([1] * len(x))
    return {'x': x, 'y': y_filtered}

def microvascular_resistance(labelui, peaks, flow_mean_or_peak='peak'):
    df = labelui.TxtSdyFile.df
    pd = np.array(df['pd'])
    flow = np.array(df['flow'])
    time = np.array(df['time'])
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

def stenosis_resistance(labelui, peaks, flow_mean_or_peak='peak'):
    df = labelui.TxtSdyFile.df
    pa = np.array(df['pa'])
    pd = np.array(df['pd'])
    flow = np.array(df['flow'])
    time = np.array(df['time'])
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
    try:
        y_filtered = savgol_filter(y, window_length=WINDOW_LEN, polyorder=3)
    except ValueError:
        print(f"Insufficient data to plot resistance - try changing Pa channel if using SDY file?")
        y_filtered = np.array([1] * len(x))
    return {'x': x, 'y': y_filtered}
