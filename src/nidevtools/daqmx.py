import nidaqmx
import nitsm.codemoduleapi
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
    """
    This class serves as a container for the properties obtained by the function get_task_properties.
    This is as instance of NamedTuple data type, so it inherits all its methods.
    Properties:
            InstrumentName: str
            Channel: str
            Pin: str
            VoltageRangeMax: float
            VoltageRangeMin: float
            SamplingRate: float
            TriggerChannel: str
            Edge: str
    """
    InstrumentName: str
    Channel: str
    Pin: str
    VoltageRangeMax: float
    VoltageRangeMin: float
    SamplingRate: float
    TriggerChannel: str
    Edge: str


class _Session(typing.NamedTuple):
    """
    This class serves as a container for a specific Task and also its context.
    This is as instance of NamedTuple data type, so it inherits all its methods.

    Properties:
        Task: Task reference
        ChannelList: Channel list related with the task
        Pins: Pins assigned to the specific task
        Site: Site in which the task is running
    """
    Task: nidaqmx.Task
    ChannelList: str
    Pins: str
    Site: int

    # Read
    def st_read_wave_multi_chan(self):
        """
        Reads one or more waveforms from the task specified in the session that contains
        one or more analog input channels.
        """
        return self.Task.read(number_of_samples_per_channel=2)

    def st_read_wave_single_chan(self):
        """
        Reads one or more waveforms from the task specified in the session that contains
        one or more analog input channels.
        """
        return self.Task.read(number_of_samples_per_channel=8)

    # Read Configuration
    def st_cnfg_chan_to_read(self):
        """
        Specifies ChannelList as a subset of channels in the task from which to read.
        """
        c_t_r = ChannelsToRead()
        c_t_r.name = self.ChannelList
        self.Task.in_stream.ChannelsToRead = c_t_r

    # Task Control
    def st_ctrl_start(self):
        """
        Transitions the task in the session to the running state to begin the measurement or generation
        Using this method is required for some applications and optional for others
        """
        self.Task.start()

    def st_ctrl_stop(self):
        """
        Stops the task referenced in the session and return it to the stats the task was before the Start method ran
        """
        self.Task.stop()

    # Task Properties
    def st_property(self):
        """
        Get the configuration properties of each pair channel-pin assigned to the task in
        this session in the pinmap, and store them in a **TaskProperties object**.
        It then returns a list of **TaskProperties object** per pair channel-pin.
        """
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
        """
        Sets the source of the Sample Clock, its rate and number of samples to acquire or generate
        for the task referenced in this session.

        Args:
            samples_per_channel: specifies the number of samples to acquire or generate for each
                channel in the task. NI-DAQmx uses this value to determine the buffer size.
                This method returns an error if the specified value is negative.
            sampling_rate_hz: specifies the sampling rate in samples per channel, per second.
                If you use an external source for the Sample Clock, set this input to the maximum
                expected rate of that clock.
            clock_source: specifies the source terminal of the Sample Clock. Leave this input
                undefined to use the default onboard clock of the device.
        """
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
            edge: Enum = nidaqmx.constants.Edge.RISING,
            level_v: float = 0.0,
            pre_trigger_samples_per_channel: int = 500
    ):
        """
        Configures the task to stop the acquisition when the device acquires all pre-trigger samples;
        an analog signal reaches the level you specify; and the device acquires all post-trigger samples.
        When you use a Reference Trigger, the default for the read RelativeTo property is First Pre-trigger
        Sample with a read Offset of 0.
        Args:
            trigger_source: (String) is the name of a virtual channel or terminal where there is an analog
                signal to use as the source of the trigger. For E Series devices, if you use a virtual channel,
                it must be the only channel in the task. The only terminal you can use for E Series devices is PFI0.
            edge: (Enum) Specifies on which edge of the signal the reference trigger occurs.
                nidaqmx.constants.Edge.RISING (Default): Trigger when the signal crosses level on a rising Edge.
                nidaqmx.constants.Edge.FALLING: Trigger when the signal crosses level on a falling Edge.
            level_v: float = specifies at what threshold to trigger. Specify this value in the units of the
                measurement or generation. Use slope to specify on which slope to trigger at this threshold.
                If not specified it has value = 0.0
            pre_trigger_samples_per_channel: specifies the minimum number of samples to acquire per channel before
            recognizing the Reference Trigger. The number of post-trigger samples per channel is equal to number
            of samples per channel in the DAQmx Timing VI minus pre-trigger samples per channel. If not specified it
            has value = 500.
        """
        self.Task.triggers.reference_trigger.cfg_anlg_edge_ref_trig(
            trigger_source, pre_trigger_samples_per_channel, edge, level_v
        )

    def st_ref_digital_edge(
            self,
            trigger_source: str,
            edge: Enum = nidaqmx.constants.Slope.RISING,
            pre_trigger_samples_per_channel: int = 500
    ):
        """
        Configures the task in this session to stop the acquisition when the device acquires all
        pre-trigger samples, detects a rising or falling edge of a digital signal, and acquires
        all post-trigger samples. When you use a Reference Trigger, the default for the read
        RelativeTo property is First Pre-trigger Sample with a read Offset of 0.

        Args:
            trigger_source: specifies the name of a terminal where there is a digital signal to use as
                the source of the trigger.
            edge: specifies on which edge of the digital signal the Reference Trigger occurs.
                nidaqmx.constants.Slope.RISING: (Default) Trigger on a rising edge of the digital signal.
                nidaqmx.constants.Slope.FALLING: Trigger on a falling edge of the digital signal.
            pre_trigger_samples_per_channel: specifies the minimum number of samples to acquire per channel
                before recognizing the Reference Trigger. The number of post-trigger samples per channel is
                equal to number of samples per channel in the DAQmx Timing VI minus pre-trigger samples per
                channel.
        """
        self.Task.triggers.reference_trigger.cfg_dig_edge_ref_trig(
            trigger_source,
            pre_trigger_samples_per_channel,
            edge)


class _Sessions:
    """
    Class that contains a list of DAQmx sessions with methods to control all sessions inside the object
    """
    sessions: typing.List[_Session]

    # Read
    def read_waveform_multichannel(self):
        """
        Reads one or more waveforms from each task specified in the list of session that contains
        one or more analog input channels.
        """
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_multi_chan()
            waveform += data
        print(waveform)
        return waveform

    def read_waveform(self):
        """
        Reads one or more waveforms from each task specified in the list of session that contains
        one or more analog input channels.
        """
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_single_chan()
            waveform += data
        print(waveform)
        return waveform

    # Read Configuration
    def configure_channels(self):
        """
        For each session in the list specifies ChannelList as a subset of channels in the task from which to read.
        """
        for session in self.sessions:
            session.st_cnfg_chan_to_read()

    # Task Control
    def start_task(self):
        """
        Transitions each task in the session list to the running state to begin the measurement or generation
        Using this method is required for some applications and optional for others
        """
        for session in self.sessions:
            session.st_ctrl_start()

    def stop_task(self):
        """
        Stops each task referenced in the session list and return it to the stats the task was before the
        Start method ran.
        """
        for session in self.sessions:
            session.st_ctrl_stop()

    # Task Properties
    def get_task_properties(self):
        """
        Get the configuration properties of each pair channel-pin assigned to the tasks in this session list,
        and store them in a **TaskProperties object**. It then returns a list of **TaskProperties object**
        per pair channel-pin for each task in the list.
        """
        daq_properties = []
        for session in self.sessions:
            properties = session.st_property()
            daq_properties += properties
        return daq_properties

    # Timing Configuration
    def timing(self, samples_per_channel: int = 1000, sampling_rate_hz: float = 1000.0, clock_source: str = ""):
        """
        Sets the source of the Sample Clock, its rate and number of samples to acquire or generate
        for each task referenced in this session list.

        Args:
            samples_per_channel: specifies the number of samples to acquire or generate for each
                channel in the task. NI-DAQmx uses this value to determine the buffer size.
                This method returns an error if the specified value is negative. Default value = 1000
            sampling_rate_hz: specifies the sampling rate in samples per channel, per second.
                If you use an external source for the Sample Clock, set this input to the maximum
                expected rate of that clock. Default value = 1000
            clock_source: specifies the source terminal of the Sample Clock. Leave this input
                undefined to use the default onboard clock of the device.
        """
        for session in self.sessions:
            session.st_timing(samples_per_channel, sampling_rate_hz, clock_source)

    # Trigger
    def reference_analog_edge(
            self,
            trigger_source: str,
            edge: Enum = nidaqmx.constants.Slope.RISING,
            level_v: float = 0.0,
            pre_trigger_samples_per_channel: int = 500):
        """
        Configures each task  in the session list to stop the acquisition when the device acquires all pre-trigger samples;
        an analog signal reaches the level you specify; and the device acquires all post-trigger samples.
        When you use a Reference Trigger, the default for the read RelativeTo property is First Pre-trigger
        Sample with a read Offset of 0.
        Args:
            trigger_source: (String) is the name of a virtual channel or terminal where there is an analog
                signal to use as the source of the trigger. For E Series devices, if you use a virtual channel,
                it must be the only channel in the task. The only terminal you can use for E Series devices is PFI0.
            edge: (Enum) Specifies on which edge of the signal the reference trigger occurs.
                nidaqmx.constants.Edge.RISING (Default): Trigger when the signal crosses level on a rising Edge.
                nidaqmx.constants.Edge.FALLING: Trigger when the signal crosses level on a falling Edge.
            level_v: (float) specifies at what threshold to trigger. Specify this value in the units of the
                measurement or generation. Use slope to specify on which slope to trigger at this threshold.
                If not specified it has value = 0.0
            pre_trigger_samples_per_channel: specifies the minimum number of samples to acquire per channel before
                recognizing the Reference Trigger. The number of post-trigger samples per channel is equal to number
                of samples per channel in the DAQmx Timing VI minus pre-trigger samples per channel. If not specified it
                has value = 500.
        """
        for session in self.sessions:
            session.st_ref_analog_edge(trigger_source, edge, level_v, pre_trigger_samples_per_channel)

    def reference_digital_edge(
            self,
            trigger_source: str,
            edge: Enum = nidaqmx.constants.Slope.RISING,
            pre_trigger_samples_per_channel: int = 500):
        """
        Configures each task in this session list to stop the acquisition when the device acquires all
        pre-trigger samples, detects a rising or falling edge of a digital signal, and acquires
        all post-trigger samples. When you use a Reference Trigger, the default for the read
        RelativeTo property is First Pre-trigger Sample with a read Offset of 0.

        Args:
            trigger_source: specifies the name of a terminal where there is a digital signal to use as
                the source of the trigger.
            edge: specifies on which edge of the digital signal the Reference Trigger occurs.
                nidaqmx.constants.Slope.RISING: (Default) Trigger on a rising edge of the digital signal.
                nidaqmx.constants.Slope.FALLING: Trigger on a falling edge of the digital signal.
            pre_trigger_samples_per_channel: specifies the minimum number of samples to acquire per channel
                before recognizing the Reference Trigger. The number of post-trigger samples per channel is
                equal to number of samples per channel in the DAQmx Timing VI minus pre-trigger samples per
                channel.
        """
        for session in self.sessions:
            session.st_ref_digital_edge(trigger_source, edge, pre_trigger_samples_per_channel)


class MultipleSessions(_Sessions):
    """
    Class that contains a list of DAQmx sessions with methods to control all sessions inside the object.
    It also contains the pin query contex that can be related to each of the sessions inside the sessions list.
    """
    pin_query_contex: PinQueryContext

    def __init__(self, pin_query_contex, sessions):
        """
        Returns an object with type MultipleSessions.

        Args:
            pin_query_contex: Pin query context related to all the sessions in the sessions list
            sessions: List of the different sessions that can be related to the pin query context
        """
        self.pin_query_contex = pin_query_contex
        self.sessions = sessions


@nitsm.codemoduleapi.code_module
def clear_task(tsm_context: TSMContext):
    """
    Clears all the tasks in the TSMContext. Before clearing, this method will abort all tasks, if necesary,
    and will release any resources the tasks reserved. You cannot use a task after you clear it unless you
    set it again.
    """
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AI")
    tasks_ao = tsm_context.get_all_nidaqmx_tasks("AO")
    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ao:
        task.stop()
        task.close()


@nitsm.codemoduleapi.code_module
def set_task(tsm_context: TSMContext):
    """
    Associates each NI-DAQmx tasks with the NI-DAQmx task name defined in the pin map and
    set all the sessions accordingly
    """
    input_voltage_range = 10.0
    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AI")  # Replace String in case PinMap change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.ai_channels.add_ai_voltage_chan(
                physical_channel, "", TerminalConfiguration.DIFFERENTIAL, -input_voltage_range, input_voltage_range)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
            # task.start()
        except:
            devices = task.devices
            task.close()
            for device in devices:
                device.reset_device()
            task.ai_channels.add_ai_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
            # task.start()
        finally:
            task.AI_max = input_voltage_range
            task.AI_min = -input_voltage_range
            tsm_context.set_nidaqmx_task(task_name, task)


# Pin Map
@nitsm.codemoduleapi.code_module
def get_all_instrument_names(tsm_context: TSMContext):
    """
    Returns the channel group ID and associated instrument names and channel lists of all instruments
    of type Instrument Type Id defined in the Semiconductor Module context. You can use instrument names,
    channel group IDs, and channel lists to open driver sessions. The Instrument Names and Channel Lists
    parameters always return the same number of elements. Instrument names repeat in the Instrument Names
    parameter if the instrument has multiple channel groups.
    """
    instruments = tsm_context.get_all_nidaqmx_task_names("")
    return instruments  # Instrument Names, Channel Lists per Instrument


@nitsm.codemoduleapi.code_module
def get_all_sessions(tsm_context: TSMContext):
    """
    Returns all sessions in the Semiconductor Module Context that belong to instruments of the type DAQmx.
    """
    tasks = tsm_context.get_all_nidaqmx_tasks("")
    return tasks


@nitsm.codemoduleapi.code_module
def pins_to_session_sessions_info(tsm_context: TSMContext, pins: PinsArg):
    """
    Returns a properly filled object of the type MultipleSessions with a session per each
    site defined in the pin map
    """
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, InstrumentTypeIdConstants.NI_DAQMX, Capability.ALL)
    (pin_query_contex, task, channel_list) = tsm_context.pins_to_nidaqmx_task(pin_list)
    sites = tsm_context.site_numbers
    multiple_session_info = MultipleSessions(pin_query_contex, [])
    for site in sites:
        pin_data = ",".join(pin_list)
        session = _Session(task, channel_list, pin_data, site)
        multiple_session_info.sessions.append(session)
    return multiple_session_info


@nitsm.codemoduleapi.code_module
def pins_to_sessions_sessions(tsm_context: TSMContext, pins: PinsArg):
    """
    Returns a pin query contex and a list of properties defined in the pin map.
    The list of properties returned can be used to fill a new object type MultipleSessions
    """
    session = tsm_context.pins_to_nidaqmx_tasks(pins)  # pin_query_context, task, channel_lists
    return session


# @nitsm.codemoduleapi.code_module
# def set_session(tsm_context: TSMContext, instrument_name: str, daqmx_session: nidaqmx.Task):
#     tsm_context.set_nidaqmx_task(instrument_name, daqmx_session)


@nitsm.codemoduleapi.code_module
def pins_to_task_and_connect(tsm_context: TSMContext, task_name: PinsArg, pins: PinsArg):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, InstrumentTypeIdConstants.NI_DAQMX, Capability.ALL)
    multiple_session_info = pins_to_session_sessions_info(tsm_context, task_name)
    array = []
    for pin in pin_list:
        # TODO Abstract Switch function?
        data = ''
        array += data
    if len(array) == 0:
        pass
    else:
        pass
        # TODO Abstract Switch?
