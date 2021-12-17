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


class ChannelsToRead:
    name: str


class TaskProperties(typing.NamedTuple):
    InstrumentName: str
    Channel: str
    Pin: str
    VoltageRangeMax: float
    VoltageRangeMin: float
    SamplingRate: float
    TriggerChannel: str
    Edge: str


class _Session(typing.NamedTuple):
    Task: nidaqmx.Task
    ChannelList: str
    Pins: str
    Site: int

    # Read
    def st_read_wave_multi_chan(self):
        return self.Task.read(number_of_samples_per_channel=2)

    def st_read_wave_single_chan(self):
        return self.Task.read(number_of_samples_per_channel=8)

    # Read Configuration
    def st_cnfg_chan_to_read(self):
        c_t_r = ChannelsToRead()
        c_t_r.name = self.ChannelList
        self.Task.in_stream.ChannelsToRead = c_t_r

    # Task Control
    def st_ctrl_start(self):
        self.Task.start()

    def st_ctrl_stop(self):
        self.Task.stop()

    # Task Properties
    def st_property(self):
        task = self.Task
        channel_list = self.ChannelList.split(",")
        pins = self.Pins.split(",")
        property_list = []
        for pin, cha in zip(pins, channel_list):
            channel_ref = cha.split("/")
            instrument_name = channel_ref[0]
            channel = channel_ref[1]
            voltage_range_max = task.channels.ai_max
            voltage_range_min = task.channels.ai_min
            sampling_rate = task.timing.samp_clk_rate
            trigger_channel = task.triggers.reference_trigger.anlg_edge_src
            slope = task.triggers.reference_trigger.anlg_edge_slope
            if slope == nidaqmx.constants.Slope.FALLING:
                edge = nidaqmx.constants.Edge.FALLING
            elif slope == nidaqmx.constants.Slope.RISING:
                edge = nidaqmx.constants.Edge.RISING
            else:
                edge = "Unsupported"
            task_property = TaskProperties(
                instrument_name,
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
    def st_timing(self, samples_per_channel: int, sampling_rate_hz: float, clock_source: str = ""):
        self.Task.timing.cfg_samp_clk_timing(
            sampling_rate_hz,
            clock_source,
            nidaqmx.constants.Edge.RISING,
            nidaqmx.constants.AcquisitionType.FINITE,
            samples_per_channel,
        )

    # Trigger
    def st_ref_analog_edge(
            self,
            trigger_source: str,
            edge: Enum = nidaqmx.constants.Slope.RISING,
            level_v: float = 0.0,
            pre_trigger_samples_per_channel: int = 500
    ):
        self.Task.triggers.reference_trigger.cfg_anlg_edge_ref_trig(
            trigger_source, pre_trigger_samples_per_channel, edge, level_v
        )


class _Sessions:
    sessions: typing.List[_Session]

    # Read
    def read_waveform_multichannel(self):
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_multi_chan()
            waveform += data
        print(waveform)
        return waveform

    def read_waveform(self):
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_single_chan()
            waveform += data
        print(waveform)
        return waveform

    # Read Configuration
    def configure_channels(self):
        for session in self.sessions:
            session.st_cnfg_chan_to_read()

    # Task Control
    def start_task(self):
        for session in self.sessions:
            session.st_ctrl_start()

    def stop_task(self):
        for session in self.sessions:
            session.st_ctrl_stop()

    # Task Properties
    def get_task_properties(self):
        daq_properties = []
        for session in self.sessions:
            properties = session.st_property()
            daq_properties += properties
        return daq_properties

    # Timing Configuration
    def timing(self, samples_per_channel: int = 1000, sampling_rate_hz: float = 1000, clock_source: str = ""):
        for session in self.sessions:
            session.st_timing(samples_per_channel, sampling_rate_hz, clock_source)

    # Trigger
    def reference_analog_edge(
            self,
            trigger_source: str,
            edge: Enum = nidaqmx.constants.Slope.RISING,
            level_v: float = 0.0,
            pre_trigger_samples_per_channel: int = 500):
        for session in self.sessions:
            session.st_ref_analog_edge(trigger_source, edge, level_v, pre_trigger_samples_per_channel)


class MultipleSessions(_Sessions):
    pin_query_contex: PinQueryContext

    def __init__(self, pin_query_contex, session):
        self.pin_query_contex = pin_query_contex
        self.sessions = session


def clear_task(tsm_context: TSMContext):
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()


def set_task(tsm_context: TSMContext, input_voltage_range: float = 10):
    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AI")  # Replace String in case PinMap change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.ai_channels.add_ai_voltage_chan(
                physical_channel, "", TerminalConfiguration.DIFFERENTIAL, -input_voltage_range, input_voltage_range)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
            task.start()
        except:
            devices = task.devices
            task.close()
            for device in devices:
                device.reset_device()
            task.ai_channels.add_ai_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
            task.start()
        finally:
            task.AI_max = input_voltage_range
            task.AI_min = -input_voltage_range
            tsm_context.set_nidaqmx_task(task_name, task)


# Pin Map
def get_all_instrument_names(tsm_context: TSMContext):
    instruments = tsm_context.get_all_nidaqmx_task_names("")
    return instruments


def get_all_sessions(tsm_context: TSMContext):
    tasks = tsm_context.get_all_nidaqmx_tasks("")
    return tasks


def pins_to_session_sessions_info(tsm_context: TSMContext, pins: PinsArg):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, InstrumentTypeIdConstants.NI_DAQMX, Capability.ALL)
    (pin_query_contex, task, channel_list) = tsm_context.pins_to_nidaqmx_task(pin_list)
    sites = tsm_context.site_numbers
    multiple_session_info = MultipleSessions(pin_query_contex, [])
    for site in sites:
        pin_data = ",".join(pin_list)
        session = _Session(task, channel_list, pin_data, site)
        multiple_session_info.sessions.append(session)
    return multiple_session_info


def pins_to_sessions_sessions(tsm_context: TSMContext, pins: PinsArg):
    session = tsm_context.pins_to_nidaqmx_tasks(pins)  # pin_query_context, task, channel_lists
    return session


def set_session(tsm_context: TSMContext, instrument_name: str, daqmx_session: nidaqmx.Task):
    tsm_context.set_nidaqmx_task(instrument_name, daqmx_session)
