#import pytest
import time
import os
import os.path
# import numpy
import ctypes
import nidcpower
import nitsm.codemoduleapi
#from nidcpower import enums
from nitsm.codemoduleapi import SemiconductorModuleContext
from nidevtools import dcpower as ni_dt_dcpower


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context=SemiconductorModuleContext):
    #ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    ni_dt_dcpower.initialize_sessions(tsm_context)
    tsminfo=ni_dt_dcpower.pins_to_sessions(tsm_context,["DUTPin_IN_ANA1","DUTPin_IN_ANA2"])
    tsminfo[1].reset()
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1","DUTPin_IN_ANA2"])
    tsminfo[1].abort()
    tsminfo[1].configure_settings()


@nitsm.codemoduleapi.code_module
def source_current(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1","DUTPin_IN_ANA2"])
    tsminfo[1].force_current_symmetric_limits(current_level=10e-3,current_level_range=10e-3, voltage_limit=6, voltage_limit_range=6)
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def source_voltage(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1","DUTPin_IN_ANA2"])
    tsminfo[1].force_voltage_symmetric_limits(voltage_level=3.8,voltage_level_range=6.0, current_limit=10e-3, current_limit_range=100e-3)
    time.sleep(0.5)

@nitsm.codemoduleapi.code_module
def measure(tsm_context=SemiconductorModuleContext):
    tsminfo = ni_dt_dcpower.pins_to_sessions(tsm_context, ["DUTPin_IN_ANA1","DUTPin_IN_ANA2"])
    volt_meas, curr_meas = tsminfo[1].measure()
    time.sleep(0.5)
    return volt_meas, curr_meas


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context=SemiconductorModuleContext):
    ni_dt_dcpower.close_sessions(tsm_context)