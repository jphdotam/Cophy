import math
import numpy as np
import peakutils
from scipy.interpolate import interp1d

SAMPLE_FREQ = 200
MIN_RR_S = 0.5
MIN_RR_SAMPLES = MIN_RR_S * SAMPLE_FREQ
THRESHOLD = (0.9, 1.1)


def interpolate_beat(beat, newlen):
    y_old = beat
    x_old = np.linspace(0, 1, len(beat))
    f_interp = interp1d(x_old, y_old, kind='cubic')
    x_new = np.linspace(0, 1, newlen)
    y_new = f_interp(x_new)
    return y_new


def average_beats_from_beat_list(beat_list, measure):
    selected_beats = []
    for beat in beat_list:
        selected_beats.append(beat[measure])
    selected_beats = np.stack(selected_beats)
    return np.mean(selected_beats, axis=0)


def ensemble_beats(labelui, rest_or_hyp, max_beats=10):
    try:
        if rest_or_hyp == 'rest':
            time_from, time_to = labelui.slider_group_rest[0].getRegion()  # Can get any slider in the group
        elif rest_or_hyp == 'hyp':
            time_from, time_to = labelui.slider_group_hyp[0].getRegion()
        else:
            raise ValueError(f"rest_or_hyp must be 'rest' or 'hyp', not {rest_or_hyp}")
    except (TypeError, IndexError) as e:  # Slider doesn't yet exist
        return [], 0

    pa = np.array(labelui.TxtSdyFile.df['pa'])
    pd = np.array(labelui.TxtSdyFile.df['pd'])
    time = np.array(labelui.TxtSdyFile.df['time'])
    flow = np.array(labelui.TxtSdyFile.df['flow'])
    i_from, i_to = find_nearest(time, time_from), find_nearest(time, time_to)

    # Data
    pa = pa[i_from:i_to]
    pd = pd[i_from:i_to]
    time = time[i_from:i_to]
    flow = flow[i_from:i_to]

    # Beats
    try:
        peaks = peakutils.indexes(pa, min_dist=int(MIN_RR_SAMPLES))  # Max 180 bpm
    except ValueError as e:
        print(f"Problem finding peaks: {e}")
        return [], 0
    median_rr = np.median(np.ediff1d(peaks))
    beats = []
    n_rejected = 0
    for i_peak in range(len(peaks) - 1):
        if len(beats) >= max_beats:
            print(f"WARNING: Found > {max_beats} beats for {rest_or_hyp} ensemble - skipping remaining beats!")
            break
        if THRESHOLD[0] * median_rr < peaks[i_peak + 1] - peaks[i_peak] < THRESHOLD[1] * median_rr:
            beat_time = time[peaks[i_peak]:peaks[i_peak + 1]] - time[peaks[i_peak]]  # Substract t0
            beat_pa = pa[peaks[i_peak]:peaks[i_peak + 1]]
            beat_pd = pd[peaks[i_peak]:peaks[i_peak + 1]]
            beat_flow = flow[peaks[i_peak]:peaks[i_peak + 1]]
            beats.append({'time': interpolate_beat(beat_time, median_rr),
                          'pa': interpolate_beat(beat_pa, median_rr),
                          'pd': interpolate_beat(beat_pd, median_rr),
                          'flow': interpolate_beat(beat_flow, median_rr)})
        else:
            # print(f"Filtering beat > 10% from median")
            n_rejected += 1
    return beats, n_rejected


def find_nearest(array, value):
    idx = np.searchsorted(array, value, side="left")
    if idx > 0 and (idx == len(array) or math.fabs(value - array[idx - 1]) < math.fabs(value - array[idx])):
        return idx - 1
    else:
        return idx


def wholecycle_measure(labelui, rest_or_hyp, measure, mean_or_peak):
    if rest_or_hyp == 'rest':
        data = labelui.ensemble_data_rest
    elif rest_or_hyp == 'hyp':
        data = labelui.ensemble_data_hyp
    else:
        raise ValueError(f"Should be rest or hyp, not {rest_or_hyp}")
    data = average_beats_from_beat_list(data, measure=measure)
    if mean_or_peak == 'mean':
        return np.mean(data)
    elif mean_or_peak == 'peak':
        return max(data)
    else:
        raise ValueError(f"mean_or_peak must be mean or peak, not {mean_or_peak}")


def systolic_measure(labelui, rest_or_hyp, measure, mean_or_peak):
    if rest_or_hyp == 'rest':
        data = labelui.ensemble_data_rest
        slider_notch = labelui.slider_notch_rest
        slider_enddiastole = labelui.slider_enddiastole_rest
    elif rest_or_hyp == 'hyp':
        data = labelui.ensemble_data_hyp
        slider_notch = labelui.slider_notch_hyp
        slider_enddiastole = labelui.slider_enddiastole_hyp
    else:
        raise ValueError(f"Should be rest or hyp, not {rest_or_hyp}")
    time_notch = slider_notch.value()
    time_enddiastole = slider_enddiastole.value()
    time = data[0]['time']
    i_notch = find_nearest(time, time_notch)
    i_enddiastole = find_nearest(time, time_enddiastole)
    sys_measure = np.concatenate((average_beats_from_beat_list(data, measure=measure)[:i_notch],
                                  average_beats_from_beat_list(data, measure=measure)[i_enddiastole:]))
    if mean_or_peak == 'mean':
        return np.mean(sys_measure)
    elif mean_or_peak == 'peak':
        return max(sys_measure)
    else:
        raise ValueError(f"mean_or_peak must be mean or peak, not {mean_or_peak}")


def wavefree_measure(labelui, rest_or_hyp, measure, mean_or_peak):
    if rest_or_hyp == 'rest':
        data = labelui.ensemble_data_rest
        slider_notch = labelui.slider_notch_rest
        slider_enddiastole = labelui.slider_enddiastole_rest
    elif rest_or_hyp == 'hyp':
        data = labelui.ensemble_data_hyp
        slider_notch = labelui.slider_notch_hyp
        slider_enddiastole = labelui.slider_enddiastole_hyp
    else:
        raise ValueError(f"Should be rest or hyp, not {rest_or_hyp}")
    time_notch = slider_notch.value()
    time_enddiastole = slider_enddiastole.value()
    time_wavefree_start = time_notch + ((time_enddiastole - time_notch) * 0.25)
    time_wavefree_end = time_enddiastole - 0.005
    time = data[0]['time']
    i_wavefree_start = find_nearest(time, time_wavefree_start)
    i_wavefree_end = find_nearest(time, time_wavefree_end)

    wavefree_measure = average_beats_from_beat_list(data, measure=measure)[i_wavefree_start: i_wavefree_end]
    try:
        if mean_or_peak == 'mean':
            return np.mean(wavefree_measure)
        elif mean_or_peak == 'peak':
            return max(wavefree_measure)
        else:
            raise ValueError(f"mean_or_peak must be mean or peak, not {mean_or_peak}")
    except ValueError as e:
        print(f"Error - did you put the sliders the wrong way around? ({e})")
        return 0


def diastolic_measure(labelui, rest_or_hyp, measure, mean_or_peak):
    if rest_or_hyp == 'rest':
        data = labelui.ensemble_data_rest
        slider_notch = labelui.slider_notch_rest
        slider_enddiastole = labelui.slider_enddiastole_rest
    elif rest_or_hyp == 'hyp':
        data = labelui.ensemble_data_hyp
        slider_notch = labelui.slider_notch_hyp
        slider_enddiastole = labelui.slider_enddiastole_hyp
    else:
        raise ValueError(f"Should be rest or hyp, not {rest_or_hyp}")
    time_notch = slider_notch.value()
    time_enddiastole = slider_enddiastole.value()
    time = data[0]['time']
    i_notch = find_nearest(time, time_notch)
    i_enddiastole = find_nearest(time, time_enddiastole)
    dias_measure = average_beats_from_beat_list(data, measure=measure)[i_notch:i_enddiastole]
    if mean_or_peak == 'mean':
        return np.mean(dias_measure)
    elif mean_or_peak == 'peak':
        return max(dias_measure)
    else:
        raise ValueError(f"mean_or_peak must be mean or peak, not {mean_or_peak}")


def dpr_measure(labelui, rest_or_hyp, measure, mean_or_peak):
    if rest_or_hyp == 'rest':
        data = labelui.ensemble_data_rest
    elif rest_or_hyp == 'hyp':
        data = labelui.ensemble_data_hyp
    else:
        raise ValueError(f"Should be rest or hyp, not {rest_or_hyp}")
    pa = average_beats_from_beat_list(data, measure='pa')
    mean_pa = np.mean(pa)
    data = average_beats_from_beat_list(data, measure=measure)
    # print(f"Pre filtering: {data.shape}")
    diastolic_data = data[pa < mean_pa]
    # print(f"Filtered to {diastolic_data.shape} - {np.sum(pa < mean_pa)}")
    if mean_or_peak == 'mean':
        return np.mean(diastolic_data)
    elif mean_or_peak == 'peak':
        return max(diastolic_data)
    else:
        raise ValueError(f"mean_or_peak must be mean or peak, not {mean_or_peak}")


def rfr(labelui):
    data = labelui.ensemble_data_rest
    pa = average_beats_from_beat_list(data, measure='pa')
    pd = average_beats_from_beat_list(data, measure='pd')
    rfr_cycle = pd/pa
    # import matplotlib.pyplot as plt
    # plt.plot(rfr_cycle)
    # plt.show()
    return min(rfr_cycle)