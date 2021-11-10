#import pytest
import time
import os
import os.path
# import numpy
import ctypes
import nidcpower
import nitsm.codemoduleapi
import importlib
#from nidcpower import enums
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidevtools.dcpower as ni_dt_dcpower
# importlib.reload(nidevtools.dcpower as ni_dt_dcpower)
# from nidevtools import dcpower as ni_dt_dcpower


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context=SemiconductorModuleContext):
    #ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    ni_dt_dcpower.initialize_sessions(tsm_context)
    tsminfo=ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo[1].reset()
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo.ssc.abort()
    tsminfo.ssc.configure_settings(20e-3, 0.0, ni_dt_dcpower.enums.Sense.LOCAL)
    #ap_time = tsminfo.ssc.get_aperture_times_in_seconds()
    #output_state = tsminfo.ssc.query_output_state
    #max_curr = tsminfo.ssc.get_max_current
    #print(ap_time)
    #print(output_state)
    #print(max_curr)

@nitsm.codemoduleapi.code_module
def configure_measurements_waveform(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo.ssc.abort()
    #tsminfo.ssc.configure_settings(20e-3, 0.0, ni_dt_dcpower.enums.Sense.LOCAL)
    tsminfo.ssc.configure_and_start_waveform_acquisition(sample_rate=10e3, buffer_length=1.0)
    wf_settings=tsminfo.ssc.get_measurement_settings()
    tsminfo.ssc.configure_output_connected(output_connected=True)
    return(wf_settings)


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    volt_wf, curr_wf=tsminfo.ssc.fetch_waveform(0, waveform_length_s= 1e-3)
    tsminfo.ssc.configure_output_connected(output_connected=False)
    print(volt_wf, curr_wf)
    return volt_wf


@nitsm.codemoduleapi.code_module
def source_current(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo.ssc.force_current_symmetric_limits(current_level=10e-3,current_level_range=10e-3, voltage_limit=6, voltage_limit_range=6)
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def source_voltage(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo.ssc.force_voltage_symmetric_limits(voltage_level=3.8, voltage_level_range=6.0, current_limit=10e-3, current_limit_range=100e-3)
    time.sleep(0.5)

@nitsm.codemoduleapi.code_module
def measure(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    volt_meas, curr_meas = tsminfo.ssc.measure()
    compliance = tsminfo.ssc.query_in_compliance()
    print(compliance)
    time.sleep(0.5)
    return volt_meas, curr_meas


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context:SemiconductorModuleContext, settings ):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA2"])
    tsminfo.ssc.abort()
    tsminfo.ssc.set_measurement_settings(settings)
    ni_dt_dcpower.close_sessions(tsm_context)