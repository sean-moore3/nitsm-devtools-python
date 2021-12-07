import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
from nitsm.enums import InstrumentTypeIdConstants
from enum import Enum
import typing

@nitsm.codemoduleapi.code_module
def tsm_clear_daqmx_task(tsm_context: SemiconductorModuleContext):
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()


@nitsm.codemoduleapi.code_module
def tsm_set_daqmx_task(tsm_context: SemiconductorModuleContext, input_voltage_range : float = 10):
    try:
        task_names, task_channels = tsm_context.get_all_nidaqmx_task_names("AnalogInput")
        id = len(task_names)
        for task_id in range(id):
            task_name = task_names[task_id]
            task_channel = task_channels[task_id]
            task = nidaqmx.Task()
            task.ai_channels.add_ai_voltage_chan(task_channel, "", TerminalConfiguration.DIFFERENTIAL, -input_voltage_range, input_voltage_range)
            task.timing.samp_timing_type.SAMPLE_CLOCK
            task.start()
    except:
        devices=task.devices
        task.close()
        for device in devices:
            device.reset_device()
        task.ai_channels.add_ai_voltage_chan(task_channel)
        task.timing.samp_timing_type.SAMPLE_CLOCK
        task.start()
    tsm_context.set_nidaqmx_task(task_name,task)

#Pin Map
def daqmx_instrument_type_id(instrument_type_id : str):
    return instrument_type_id

def daqmx_get_all_instrument_names(tsm_context: SemiconductorModuleContext, instrument_type_id: typing.Union[InstrumentTypeIdConstants ,str]): #did not match with labview entrances
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(instrument_type_id)
    return instrument_names, channel_group_ids, channel_lists

def get_all_sessions(tsm_context: SemiconductorModuleContext, instrument_type_id: typing.Union[InstrumentTypeIdConstants ,str]): #did not match with labview entrances
    daqmx_task , channel_group_ids , channel_lists = tsm_context.get_all_custom_sessions(instrument_type_id)
    return daqmx_task

def daqmx_pins_to_session_sessions_info(tsm_context: SemiconductorModuleContext, pins: typing.Sequence(str)):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, nitsm.codemoduleapi.InstrumentTypeIdConstants.NI_DAQMX)
    data_id = tsm_context.pins_to_custom_session(nitsm.codemoduleapi.InstrumentTypeIdConstants.NI_DAQMX, pin_list)
    tsm_context.get_site_data(data_id)

def daqmx_pins_to_sessions_sessions(tsm_context: SemiconductorModuleContext, pins: typing.Union[InstrumentTypeIdConstants ,str], instrument_type_id: typing.Union[str, typing.Sequence[str]]):
    pin_query_context, daqmx_task, channel_group_ids,  channel_lists = tsm_context.pins_to_custom_sessions(instrument_type_id, pins)
    return pin_query_context, daqmx_task, channel_group_ids,  channel_lists


def daqmx_set_session(tsm_context: SemiconductorModuleContext, instrument_name: str, channel_group_id: str, instrument_type_id: str, daqmx_session):
    tsm_context.set_custom_session(instrument_type_id, instrument_name, channel_group_id, daqmx_session)

#Read
@nitsm.codemoduleapi.code_module
def daqmx_read_waveform_multichannel(daqmx_sessions):
    for daqmx_task in daqmx_sessions:
        #daqmx_task = nidaqmx.Task()
        daqmx_task.read() # Review function
    return daqmx_sessions

@nitsm.codemoduleapi.code_module
def daqmx_read_waveform(daqmx_sessions):
    for daqmx_task in daqmx_sessions:
        #daqmx_task = nidaqmx.Task()
        daqmx_task.read() # Review function
    return daqmx_sessions

#Read Configuration

#Task Control
@nitsm.codemoduleapi.code_module
def daqmx_start_task(daqmx_sessions):
    for daqmx_task in daqmx_sessions:
        #daqmx_task = nidaqmx.Task()
        daqmx_task.start()
    return daqmx_sessions

@nitsm.codemoduleapi.code_module
def daqmx_start_task(daqmx_sessions):
    for daqmx_task in daqmx_sessions:
        #daqmx_task = nidaqmx.Task()
        daqmx_task.stop()
    return daqmx_sessions

#Task Properties


#Timing Configuration WIP Type def review output of daq task y sessions
@nitsm.codemoduleapi.code_module
def daqmx_timing(daqmx_sessions, samples_per_channel : int, sampling_rate_hz : float, clock_source):
    for daqmx_task in daqmx_sessions:
        daqmx_task.timing.cfg_samp_clk_timing(
            sampling_rate_hz,
            clock_source,
            nidaqmx.constants.Edge.RISING,
            nidaqmx.constants.AcquisitionType.FINITE,
            samples_per_channel
        )
        daqmx_task.timing.cfg_samp_clk_timing()
    return daqmx_sessions

#Trigger WIP Type def review output of daq task y sessions
@nitsm.codemoduleapi.code_module
def daqmx_reference_analog_edge(daqmx_sessions , trigger_source : str, edge : Enum, level_v : float, pretrigger_samples_per_channel : int):
    for daqmx_task in daqmx_sessions:
        daqmx_task.triggers._reference_trigger.cfg_anlg_edge_ref_trig(
            trigger_source,
            pretrigger_samples_per_channel,
            edge,
            level_v
        )
    return daqmx_sessions

#Types


