import nidaqmx
from nitsm.enums import Capability
from nidaqmx.constants import TerminalConfiguration
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.enums import InstrumentTypeIdConstants
from nitsm.pinquerycontexts import PinQueryContext
from enum import Enum
import typing

# Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


class Task(typing.NamedTuple):
    Ref: nidaqmx.Task
    AI_min: int
    AI_max: int


class TaskProperties(typing.NamedTuple):
    InstrumentName: str
    Channel: str
    Pin: str
    VoltageRangeMax: float
    VoltageRangeMin: float
    SamplingRate: float
    TriggerChannel: str
    Edge: str


class Session(typing.NamedTuple):
    Task: Task
    ChannelList: str
    Pins: str
    Site: int

# Read
    def _st_read_wave_multi_chan(self):
        return self.Task.Ref.read(number_of_samples_per_channel=2)

    def _st_read_wave_single_chan(self):
        return self.Task.Ref.read(number_of_samples_per_channel=8)

# Read Configuration
    def _st_cnfg_chan_to_read(self):
        self.Task.Ref.in_stream.channels_to_read(self.ChannelList)

# Task Control
    def _st_ctrl_start(self):
        self.Task.Ref.start()

    def _st_ctrl_stop(self):
        self.Task.Ref.stop()

# Task Properties
    def _st_property(self):
        task = self.Task
        channel_list = self.ChannelList.split(",")
        pins = self.Pins.split(",")
        # qty = min(len(pins), len(channel_list))
        property_list = []
        # for sel in range(qty):
        for pin, cha in zip(pins, channel_list):
            # pin = pins[sel]
            # channel_ref = channel_list[sel].split("/")
            channel_ref = cha.split("/")
            instrument_name = channel_ref[0]
            channel = channel_ref[1]
            voltage_range_max = task.AI_max
            voltage_range_min = task.AI_min
            sampling_rate = task.Ref.timing.samp_clk_rate
            trigger_channel = task.Ref.triggers.reference_trigger.anlg_edge_src
            slope = int(task.Ref.triggers.reference_trigger.anlg_edge_slope)
            if slope == 10171:
                edge = nidaqmx.constants.Edge.FALLING
            elif slope == 10280:
                edge = nidaqmx.constants.Edge.RISING
            else:
                edge = "Unsupported"
            task_property = TaskProperties(instrument_name,
                                           channel,
                                           pin,
                                           voltage_range_max,
                                           voltage_range_min,
                                           sampling_rate,
                                           trigger_channel,
                                           edge)
            property_list.append(task_property)
        return property_list

# Timing Configuration
    def _st_timing(self, samples_per_channel: int, sampling_rate_hz: float, clock_source: str):
        self.Task.Ref.timing.cfg_samp_clk_timing(
            sampling_rate_hz,
            clock_source,
            nidaqmx.constants.Edge.RISING,
            nidaqmx.constants.AcquisitionType.FINITE,
            samples_per_channel)

# Trigger
    def _st_ref_analog_edge(self,
                            trigger_source: str,
                            edge: Enum,
                            level_v: float,
                            pre_trigger_samples_per_channel: int):
        self.Task.Ref.triggers.reference_trigger.cfg_anlg_edge_ref_trig(trigger_source,
                                                                        pre_trigger_samples_per_channel,
                                                                        edge,
                                                                        level_v)


class Sessions(typing.NamedTuple):
    sessions: typing.List[Session] = []

# Read
    def read_waveform_multichannel(self):
        waveform = []
        for session in self.sessions:
            waveform.append(session._st_read_wave_multi_chan())
        return waveform

    def read_waveform(self):
        waveform = []
        for session in self.sessions:
            waveform.append(session._st_read_wave_single_chan())
        return waveform

# Read Configuration
    def configure_channels(self):
        for session in self.sessions:
            session._st_cnfg_chan_to_read()

# Task Control
    def start_task(self):
        for session in self.sessions:
            session._st_ctrl_start()

    def stop_task(self):
        for session in self.sessions:
            session._st_ctrl_stop()

# Task Properties
    def get_task_properties(self):
        daq_properties = []
        for session in self.sessions:
            properties = session._st_property()
            daq_properties.append(properties)
        return daq_properties

# Timing Configuration
    def timing(self, samples_per_channel: int, sampling_rate_hz: float, clock_source: str):
        for session in self:
            session._st_timing(samples_per_channel, sampling_rate_hz, clock_source)

# Trigger
    def reference_analog_edge(self,
                              trigger_source: str,
                              edge: Enum,
                              level_v: float,
                              pre_trigger_samples_per_channel: int):
        for session in self.sessions:
            session._st_ref_analog_edge(trigger_source, edge, level_v, pre_trigger_samples_per_channel)


class MultipleSessions(typing.NamedTuple):
    pin_query_contex: PinQueryContext
    InstrumentSessions: Sessions = []


def clear_task(tsm_context: TSMContext):
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()


def set_task(tsm_context: TSMContext,
             input_voltage_range: float = 10):
    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AI")
    # qty = min(len(task_names), len(channel_lists))
    ch_list_str = channel_lists[0]
    ch_list = ch_list_str.split(",")
    print(channel_lists, task_names)
    task = Task(nidaqmx.Task(), 0, 0)
    for task_name, physical_channel in zip(task_names, channel_lists):
        # task_name = task_names[sel]
        # physical_channel = channel_lists[sel] 'Dev1/ai0, Dev1/ai1, Dev1/ai2, Dev1/ai3, Dev1/ai4, Dev1/ai5, Dev1/ai6, Dev1/ai7, Dev1/ai8, Dev1/ai9, Dev1/ai10, Dev1/ai11, Dev1/ai12, Dev1/ai13'
        try:
            print(type(physical_channel), physical_channel)
            channel = task.Ref.ai_channels.add_ai_voltage_chan(physical_channel,
                                                               "",
                                                               TerminalConfiguration.DIFFERENTIAL,
                                                               -input_voltage_range,
                                                               input_voltage_range)
            # task.Ref.timing.cfg_samp_clk_timing(task.Ref.timing.samp_timing_type.SAMPLE_CLOCK)
            task.Ref.start()
        except:
            devices = task.Ref.devices
            task.Ref.close()
            for device in devices:
                device.reset_device()
            channel = task.Ref.ai_channels.add_ai_voltage_chan(physical_channel)
            task.Ref.timing.samp_timing_type.SAMPLE_CLOCK()
            task.Ref.start()
        finally:
            task.AI_min = channel.ai_min
            task.AI_max = channel.ai_max
            tsm_context.set_nidaqmx_task(task_name, task)


# Pin Map
def instrument_type_id(instrument_type: str = "DAQmx"):
    return instrument_type


def get_all_instrument_names(tsm_context: TSMContext):
    instrument_type = instrument_type_id()
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(instrument_type)
    return instrument_names, channel_group_ids, channel_lists

def get_all_sessions(tsm_context: TSMContext):
    instrument_type = instrument_type_id()
    tasks, channel_group_ids, channel_lists = tsm_context.get_all_custom_sessions(instrument_type)
    return tasks


def pins_to_session_sessions_info(tsm_context: TSMContext,
                                  pins: PinsArg):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins,
                                                          InstrumentTypeIdConstants.NI_DAQMX,
                                                          Capability.ALL)
    (
    pin_query_context,
    task,
    channel_group_id,
    channel_list
    ) = tsm_context.pins_to_nidaqmx_task(pin_list)
    sites = tsm_context.site_numbers
    # sites = tsm_context.get_site_data(channel_group_id)
    multiple_session_info = MultipleSessions(pin_query_context)
    for site in sites:
        session = Session(task, channel_list, ','.join(pin_list), site)
        multiple_session_info.InstrumentSessions.sessions.append(session)
    return multiple_session_info


def pins_to_sessions_sessions(tsm_context: TSMContext,
                              pins: PinsArg):
    instrument_type = instrument_type_id()
    pin_query_context, task, channel_group_ids, channel_lists = tsm_context.pins_to_custom_sessions(instrument_type, pins)
    return pin_query_context, task, channel_group_ids, channel_lists


def set_session(tsm_context: TSMContext,
                instrument_name: str,
                channel_group_id: str,
                daqmx_session: Any):
    instrument_type = instrument_type_id()
    tsm_context.set_custom_session(instrument_type, instrument_name, channel_group_id, daqmx_session)
