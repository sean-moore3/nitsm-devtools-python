# import pytest
import time
import os
import os.path

# import numpy
import ctypes
import nitsm.codemoduleapi


from nitsm.codemoduleapi import SemiconductorModuleContext
import sys
import niscope

sys.path.append("./../src")
import nidevtools.scope as ni_dt_scope


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context=SemiconductorModuleContext):
    # ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    print("opening sessions")
    ni_dt_scope.initialize_sessions(tsm_context)
    tsmscope = ni_dt_scope.tsm_ssc_pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1"], [])
    ni_dt_scope.abort(tsmscope)
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm_context=SemiconductorModuleContext):
    tsmscope = ni_dt_scope.tsm_ssc_pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1"], [])
    ni_dt_scope.configure(tsmscope, 4e-3, 1, 0, niscope.VerticalCoupling.AC, 5e6, 20000, 50, -1, 1e6, 1, True)
    ni_dt_scope.configure_digital_edge_trigger(tsmscope, "", slope=niscope.TriggerSlope.POSITIVE)
    _, props = ni_dt_scope.get_session_properties(tsmscope)
    print("\n", props)
    print("Configuring fetch wf")
    return props


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm_context=SemiconductorModuleContext):
    tsmscope = ni_dt_scope.tsm_ssc_pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1"], [])
    ni_dt_scope.tsm_ssc_start_acquisition(tsmscope)
    _, data_capture, wf_info = ni_dt_scope.fetch_waveform(tsmscope, 20000)
    _, v_peak = ni_dt_scope.fetch_measurement(
        tsmscope, scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
    )
    _, v_max = ni_dt_scope.fetch_measurement(tsmscope, scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_MAX)
    print(wf_info)
    print(v_peak)
    print(v_max)

    return data_capture, wf_info, v_peak, v_max


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):

    print(" Closing sessions")

    tsminfo = ni_dt_scope.tsm_ssc_pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1"], [])
    ni_dt_scope.close_sessions(tsm_context)
