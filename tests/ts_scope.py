import ctypes
import os
import time
import typing

import nidevtools.scope as scope
import niscope
import nitsm.codemoduleapi
import pytest
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# modules added for matplotlib
import matplotlib.pyplot as plt
import numpy as np
import math


#  code added to support Matplotlib
def on_close(event):
    global closed
    closed = True


def plot_data(measurements, record_length):

    # record_length = 10
    buffer_multiplier = 10
    voltage_level = 1.0

    # Setup a plot to draw the captured waveform.
    fig = plt.figure("Waveform Graph")
    fig.show()
    fig.canvas.draw()

    # Handle closing of plot window.
    global closed
    closed = False

    fig.canvas.mpl_connect("close_event", on_close)

    # print("\nReading values in loop. CTRL+C or Close window to stop.\n")

    # Create a buffer for fetching the values.
    y_axis = [0] * (record_length * buffer_multiplier)
    x_start = 0

    try:
        # Clear the plot and setup the axis.
        plt.clf()
        plt.axis()
        plt.xlabel("Samples")
        plt.ylabel("Amplitude")

        voltages = []
        # measurements = session.channels[0].fetch_multiple(count=record_length)
        print(len(measurements))
        for i in range(len(measurements)):
            voltages.append(measurements[i])
        # Append the fetched values in the buffer.
        y_axis.extend(voltages)
        y_axis = y_axis[record_length:]

        # Updating the precision of the fetched values.
        y_axis_new = []
        for value in y_axis:
            if value < voltage_level:
                y_axis_new.append(math.floor(value * 100) / 100)
            else:
                y_axis_new.append(math.ceil(value * 100) / 100)

        # Plotting
        y_axis = y_axis_new
        x_axis = np.arange(start=x_start, stop=x_start + record_length * buffer_multiplier, step=1)
        x_start = x_start + record_length
        plt.plot(x_axis, y_axis)
        while not closed:
            plt.pause(0.001)
            time.sleep(0.1)
    except KeyboardInterrupt:
        pass


@nitsm.codemoduleapi.code_module
def open_sessions(tsm: SMContext):
    scope.initialize_sessions(tsm,)


@nitsm.codemoduleapi.code_module
def configure(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.configure_impedance(0.5)
    osc_pin1.ssc.configure_reference_level()
    osc_pin1.ssc.configure_vertical(5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
    osc_pin1.ssc.configure(
        5.0, 1.0, 0.0, niscope.VerticalCoupling.DC, 10e6, 1000, 0.0, 0.0, 1e6, 1, True
    )
    osc_pin1.ssc.configure_vertical_per_channel(5.0, 0.0, 1.0, niscope.VerticalCoupling.DC, True)
    osc_pin1.ssc.configure_timing(20e6, 1000, 50, 1, True)


@nitsm.codemoduleapi.code_module
def acquisition(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.initiate()


@nitsm.codemoduleapi.code_module
def control(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.commit()
    osc_pin1.ssc.abort()


@nitsm.codemoduleapi.code_module
def session_properties(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.get_session_properties()


@nitsm.codemoduleapi.code_module
def trigger(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.configure_digital_edge_trigger(
        scope.TRIGGER_SOURCE.RTSI0, niscope.TriggerSlope.POSITIVE
    )
    osc_pin1.ssc.configure_trigger(0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE)
    osc_pin1.ssc.configure_trigger_immediate()
    osc_pin1.ssc.clear_triggers()
    osc_pin1.ssc.export_start_triggers(scope.OUTPUT_TERMINAL.NONE)
    osc_pin1.ssc.start_acquisition()


@nitsm.codemoduleapi.code_module
def measure_results(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.fetch_measurement(niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def measure_stats(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.measure_statistics(niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def clear_stats(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.fetch_clear_stats()


@nitsm.codemoduleapi.code_module
def fetch_measurement_stats_per_channel(
    tsm: SMContext, pins: typing.List[str], sites: typing.List[int]
):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.fetch_meas_stats_per_channel(niscope.ScalarMeasurement.NO_MEASUREMENT)

@nitsm.codemoduleapi.code_module
def configure_measurements(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.configure(
        4e-3, 1, 0, niscope.VerticalCoupling.AC, 5e6, 2000, 50, -1, 1e6, 1, True
    )
    osc_pin1.ssc.configure_trigger_immediate()


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm: SMContext, pins: typing.List[str], sites: typing.List[int]):
    osc_pin1 = scope.pins_to_sessions(tsm, pins, sites)
    osc_pin1.ssc.start_acquisition()
    data1, info = osc_pin1.ssc.fetch_waveform(2000)
    v_peak = osc_pin1.ssc.fetch_measurement(
        scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
    )
    v_max = osc_pin1.ssc.fetch_measurement(
        scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_MAX
    )
    print("v_peak", v_peak)
    print("v_max", v_max)
    print(data1[0][0].samples)
    # data2 = osc_pin1.ssc.fetch_multirecord_waveform(1)
    # print(data2)
    osc_pin1.ssc.abort()
    plot_data(data1[0][0].samples, 1000)
    return data1, info, v_peak, v_max



@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    print(" Closing sessions")
    scope.close_sessions(tsm)





