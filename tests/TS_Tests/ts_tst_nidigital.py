#import pytest
import typing
import os
import os.path
import math
#import numpy
import nitsm.codemoduleapi
from nitsm import enums as tsm_enums
from nidigital import enums
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidigital
import ctypes

#import nidevtools.digital as ni_dt_digital

from nidevtools import digital as ni_dt_digital

@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context=SemiconductorModuleContext):
    #ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    #print(tsm_context.pin_map_file_path)
    #pins = ni_dt_digital.SemiconductorModuleContext.get_pin_names(tsm_context, instrument_type_id=tsm_enums.InstrumentTypeIdConstants.NI_DIGITAL_PATTERN)
    #print(pins)
    ni_dt_digital.tsm_initialize_sessions(tsm_context)
    tsm_i_o = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["Inputs","Outputs"])
    ni_dt_digital.tsm_ssc_apply_levels_and_timing(tsm_i_o, "PinLevels_ts", "Timing")

@nitsm.codemoduleapi.code_module
def configure_pins(tsm_context=SemiconductorModuleContext):
    tsm_o = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["Outputs"])
    ni_dt_digital.tsm_ssc_select_function(tsm_o, ni_dt_digital.enums.SelectedFunction.DIGITAL)
    ni_dt_digital.tsm_ssc_write_static(tsm_o, ni_dt_digital.enums.WriteStaticPinState.ONE)
    #time.sleep(0.5)

@nitsm.codemoduleapi.code_module
def read_pins(tsm_context=SemiconductorModuleContext):
    tsm_i = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["Inputs"])
    _, data = ni_dt_digital.tsm_ssc_read_static(tsm_i)
    print(data)
    return data

@nitsm.codemoduleapi.code_module
def burst_pattern(tsm_context=SemiconductorModuleContext):
    tsm = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["DUTPin_OUT_1", "DUTPin_IN_1"])
    ni_dt_digital.tsm_ssc_apply_levels_and_timing(tsm, "PinLevels_ts", "Timing")
    _, per_site_pass = ni_dt_digital.tsm_ssc_burst_pattern_pass_fail(tsm, "start_burst")
    print(per_site_pass)

@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context=SemiconductorModuleContext):
    ni_dt_digital.tsm_close_sessions(tsm_context)