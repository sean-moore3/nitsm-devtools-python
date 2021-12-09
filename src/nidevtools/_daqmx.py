import nidaqmx
from nidaqmx.constants import TerminalConfiguration
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.enums import InstrumentTypeIdConstants
from nitsm.pinquerycontexts import PinQueryContext
from enum import Enum
import typing

#Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]

class DAQmxTaskProperties(typing.NamedTuple):
    def __init__(self,
                 instrument_name: str,
                 channel: str,
                 pin: str,
                 voltage_range_max: float,
                 voltage_range_min: float,
                 sampling_rate: float,
                 trigger_channel: str,
                 edge: str):
        self.instrument_name=instrument_name
        self.channel=channel
        self.pin=pin
        self.voltage_range_max=voltage_range_max
        self.voltage_range_min=voltage_range_min
        self.sampling_rate=sampling_rate
        self.trigger_channel=trigger_channel
        self.edge=edge

class DAQmxSession(typing.NamedTuple):
    def __init__(self,
                 task: nidaqmx.Task,
                 channel: str,
                 pins: str,
                 site: int):
        self.Task=task
        self.ChannelList=channel
        self.Pins=pins
        self.Site=site
#Single task functions
#Read
    def st_rd_wfm_nchan(self):
        return self.Task.read()
    def st_rd_wfm_1chan(self):
        return self.Task.read()
#Read Configuration
    def st_cnfg_chan_to_read(self):
        self.Task.in_stream.channels_to_read(ChannelList)
#Task Control
    def st_ctrl_start(self):
        self.Task.start()
    def st_ctrl_stop(self):
        self.Task.stop()
#Task Properties
    def st_prop(self):
        task = self.Task
        channel_list = self.ChannelList.split(",")
        pins = self.Pins.split(",")
        qty = min(len(pins), len(channel_list))
        property_list=[]
        for sel in range(qty):
            pin = pins[sel]
            channel = channel_list[sel].split("/")
            instrument_name = channel[0]
            channel = channel[1]
            voltage_range_max = 0
            voltage_range_min = 0
            # daqmx_task.ai_channels.ai_max not in library https://nidaqmx-python.readthedocs.io/en/latest/ai_channel.html
            # daqmx_task.ai_channels.ai_min
            sampling_rate = daqmx_task.timing.samp_clk_rate
            trigger_channel = daqmx_task.triggers.reference_trigger.anlg_edge_src
            slope = int(daqmx_task.triggers.reference_trigger.anlg_edge_slope)
            if (slope == 10171):
                edge = nidaqmx.constants.Edge.FALLING
            elif (slope == 10280):
                edge = nidaqmx.constants.Edge.RISING
            else:
                edge = "Unsupported"
            property = DAQmxTaskProperties(instrument_name,
                                           channel,
                                           pin,
                                           voltage_range_max,
                                           voltage_range_min,
                                           sampling_rate,
                                           trigger_channel,
                                           edge)
            list.append(property)
        return list
#Timing Configuration
    def st_timing(self, samples_per_channel : int, sampling_rate_hz : float, clock_source: str):
        self.Task.timing.cfg_samp_clk_timing(
            sampling_rate_hz,
            clock_source,
            nidaqmx.constants.Edge.RISING,
            nidaqmx.constants.AcquisitionType.FINITE,
            samples_per_channel)
#Trigger
    def st_ref_anlg_edge(self, trigger_source : str, edge : Enum, level_v : float, pretrigger_samples_per_channel : int):
        self.Task.triggers.reference_trigger.cfg_anlg_edge_ref_trig(trigger_source,
                                                                    pretrigger_samples_per_channel,
                                                                    edge,
                                                                    level_v)

class DAQmxSessions(typing.NamedTuple):
    InstrumentSessions: typing.Sequence[DAQmxSession]
#Read
    def read_waveform_multichannel(self):
        waveform=[]
        for session in self.instrument_sessions:
            waveform.append(session.st_rd_wfm_nchan())
        return waveform
    def read_waveform(self):
        waveform=[]
        for session in self.instrument_sessions:
            waveform.append(session.st_rd_wfm_1chan())
        return waveform
#Read Configuration
    def configure_channels(self):
        for session in self.instrument_sessions:
            self.st_cnfg_chan_to_read()
#Task Control
    def start_task(self):
        for session in self.InstrumentSessions:
            session.st_ctrl_start()
    def stop_task(self):
        for session in self.InstrumentSessions:
            session.st_ctrl_stop()
#Task Properties
    def get_task_properties(self):
        daq_properties = []
        for session in self.InstrumentSessions:
                daq_properties.append(session.st_prop())
        return daq_properties
#Timing Configuration
    def timing(self, samples_per_channel : int, sampling_rate_hz : float, clock_source: str):
        for session in self:
            session.st_timing(samples_per_channel,sampling_rate_hz,clock_source)
#Trigger
    def reference_analog_edge(self, trigger_source : str, edge : Enum, level_v : float, pretrigger_samples_per_channel : int):
        for session in self.InstrumentSessions:
            session.st_ref_anlg_edge(
                trigger_source,
                pretrigger_samples_per_channel,
                edge,
                level_v)

class DAQmxMultipleSessions(DAQmxSessions):
    pin_query_contex: PinQueryContext

def tsm_clear_daqmx_task(tsm_context: TSMContext):
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()

def tsm_set_daqmx_task(tsm_context: TSMContext, input_voltage_range : float = 10):
    try:
        task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AnalogInput")
        id = len(task_names)
        for task_id in range(id):
            task_name = task_names[task_id]
            physical_channel = channel_lists[task_id]
            #task = nidaqmx.Task()
            task.ai_channels.add_ai_voltage_chan(physical_channel, "", TerminalConfiguration.DIFFERENTIAL, -input_voltage_range, input_voltage_range)
            task.timing.samp_timing_type.SAMPLE_CLOCK
            task.start()
    except:
        devices=task.devices
        task.close()
        for device in devices:
            device.reset_device()
        task.ai_channels.add_ai_voltage_chan(physical_channel)
        task.timing.samp_timing_type.SAMPLE_CLOCK
        task.start()
    tsm_context.set_nidaqmx_task(task_name,task)

#Pin Map
def daqmx_instrument_type_id(instrument_type_id : str = "DAQmx"):
    return instrument_type_id

def daqmx_get_all_instrument_names(tsm_context: TSMContext):
    instrument_type_id = daqmx_instrument_type_id()
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(instrument_type_id)
    return instrument_names, channel_group_ids, channel_lists

def get_all_sessions(tsm_context: TSMContext):
    instrument_type_id = daqmx_instrument_type_id()
    daqmx_task, channel_group_ids, channel_lists = tsm_context.get_all_custom_sessions(instrument_type_id)
    return daqmx_task
#review
def daqmx_pins_to_session_sessions_info(tsm_context: TSMContext,
                                        pins: PinsArg):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, InstrumentTypeIdConstants.NI_DAQMX)
    pin_query_context, daqmx_task, channel_group_id, channel_list = tsm_context.pins_to_custom_session(InstrumentTypeIdConstants.NI_DAQMX, pin_list)
    sites = tsm_context.get_site_data(channel_group_id)
    instruments_sesions=[]
    for site in sites:
        instruments_sesions.append((pin_list, daqmx_task, channel_list, site))
    return pin_query_context, instruments_sesions
def daqmx_pins_to_sessions_sessions(tsm_context: TSMContext,
                                    pins: PinsArg):
    instrument_type_id = daqmx_instrument_type_id()
    pin_query_context, daqmx_task, channel_group_ids, channel_lists = tsm_context.pins_to_custom_sessions(instrument_type_id, pins)
    return pin_query_context, daqmx_task, channel_group_ids, channel_lists
def daqmx_set_session(tsm_context: TSMContext,
                      instrument_name: str,
                      channel_group_id: str,
                      daqmx_session: Any):
    instrument_type_id=daqmx_instrument_type_id()
    tsm_context.set_custom_session(instrument_type_id, instrument_name, channel_group_id, daqmx_session)
#Read
#@nitsm.codemoduleapi.code_module
#def daqmx_read_waveform_multichannel(daqmx_sessions: DAQmxSessions):
#    waveform=[]
#    for daqmx_session in daqmx_sessions.instrument_sessions:
#        daqmx_task = daqmx_session.daqmx_task
#        data=daqmx_task.read()
#        waveform.append(data)
#    return daqmx_sessions, waveform

#@nitsm.codemoduleapi.code_module
#def daqmx_read_waveform(daqmx_sessions: DAQmxSessions):
#    waveform=[]
#    for daqmx_session in daqmx_sessions.instrument_sessions:
#        daqmx_task = daqmx_session.daqmx_task
#        data=daqmx_task.read()
#        waveform.append(data)
#    return daqmx_sessions, waveform

#Read Configuration
#@nitsm.codemoduleapi.code_module
#def daqmx_configure_channels(daqmx_sessions: DAQmxSessions):
#    for daqmx_session in daqmx_sessions.instrument_sessions:
#        daqmx_task = daqmx_session.daqmx_task
#        channel_list = daqmx_session.channel_list
#        daqmx_task.in_stream.channels_to_read(channel_list)
#    return daqmx_sessions


#Task Control
#@nitsm.codemoduleapi.code_module
#def daqmx_start_task(daqmx_sessions: DAQmxSessions):
#    for daqmx_session in daqmx_sessions:
#        daqmx_task = daqmx_session[0]
#        daqmx_task.start()
#    return daqmx_sessions

#@nitsm.codemoduleapi.code_module
#def daqmx_start_task(daqmx_sessions: DAQmxSessions):
#    for daqmx_session in daqmx_sessions:
#        daqmx_task = daqmx_session[0]
#        daqmx_task.stop()
#    return daqmx_sessions

#Task Properties
#def daqmx_get_task_properties(daq_tasks: DAQmxSessions):
#    daq_properties = []
#    for daq_task in daq_tasks:
#        daqmx_task = daq_task[0]
#        channel_list = daq_task[1].split(",")
#        pins = daq_task[2].split(",")
#        qty = min(len(pins),len(channel_list))
#        for count in range(qty):
#            pin = pins[count]
#            channel = channel_list[count].split("/")
#            instrument_name = channel[0]
#            channel = channel[1]
#            voltage_range_max = 0
#            voltage_range_min = 0
#            #daqmx_task.ai_channels.ai_max not in library https://nidaqmx-python.readthedocs.io/en/latest/ai_channel.html
#            #daqmx_task.ai_channels.ai_min
#            sampling_rate = daqmx_task.timing.samp_clk_rate
#            trigger_channel = daqmx_task.triggers.reference_trigger.anlg_edge_src
#            slope=int(daqmx_task.triggers.reference_trigger.anlg_edge_slope)
#            if (slope==10171):
#                edge = nidaqmx.constants.Edge.FALLING
#            elif (slope==10280):
#                edge = nidaqmx.constants.Edge.RISING
#            else:
#                edge = "Unsupported"
#            property=(pin,
#                      instrument_name,
#                      channel,
#                      voltage_range_max,
#                      voltage_range_min,
#                      trigger_channel,
#                      edge)
#            daq_properties.append(property)
#    return (daq_tasks, daq_properties)

#Timing Configuration
#@nitsm.codemoduleapi.code_module
#def daqmx_timing(daqmx_sessions: DAQmxSessions, samples_per_channel : int, sampling_rate_hz : float, clock_source):
#    for daqmx_session in daqmx_sessions:
#        daqmx_task = daqmx_session[0]
#        daqmx_task.timing.cfg_samp_clk_timing(
#            sampling_rate_hz,
#            clock_source,
#            nidaqmx.constants.Edge.RISING,
#            nidaqmx.constants.AcquisitionType.FINITE,
#            samples_per_channel
#        )
#    return daqmx_sessions

#Trigger
#@nitsm.codemoduleapi.code_module
#def daqmx_reference_analog_edge(daqmx_sessions: DAQmxSessions, trigger_source : str, edge : Enum, level_v : float, pretrigger_samples_per_channel : int):
#    for daqmx_session in daqmx_sessions:
#        daqmx_task = daqmx_session[0]
#        daqmx_task.triggers._reference_trigger.cfg_anlg_edge_ref_trig(
#            trigger_source,
#            pretrigger_samples_per_channel,
#            edge,
#            level_v
#        )
#    return daqmx_sessions