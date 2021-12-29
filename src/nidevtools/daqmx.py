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
    def st_read_wave_multi_chan(self, samples_per_channel=nidaqmx.task.NUM_SAMPLES_UNSET, timeout=10):
        """
        Reads one or more waveforms from the task specified in the session that contains
        one or more analog input channels.
        Return:
            Array of data
        """
        return self.Task.read(samples_per_channel, timeout)

    def st_read_wave_single_chan(self, samples_per_channel=nidaqmx.task.NUM_SAMPLES_UNSET, timeout=10):
        """
        Reads one or more waveforms from the task specified in the session that contains
        one or more analog input channels.
        Return:
            Array of data
        """
        return self.Task.read(samples_per_channel, timeout)

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
        this session in the pin map, and store them in a **TaskProperties object**.
        It then returns a list of **TaskProperties object** per pair channel-pin.
        Return:
            List of properties per pin/channel
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
                edge,
            )
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
        pre_trigger_samples_per_channel: int = 500,
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
        pre_trigger_samples_per_channel: int = 500,
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
            trigger_source, pre_trigger_samples_per_channel, edge
        )


class _Sessions:
    """
    Class that contains a list of DAQmx sessions with methods to control all sessions inside the object
    """

    sessions: typing.List[_Session]

    # Read
    def read_waveform_multichannel(self, samples_per_channel=nidaqmx.task.NUM_SAMPLES_UNSET, timeout=10):
        """
        Reads one or more waveforms from each task specified in the list of session that contains
        one or more analog input channels.
        Args:
            samples_per_channel: Specifies the number of samples to read. If this input is not set,
                assumes samples to read is 1. Conversely, if this input is set, assumes there are
                multiple samples to read.
                If you set this input to nidaqmx.constants. READ_ALL_AVAILABLE, NI-DAQmx determines
                how many samples to read based on if the task acquires samples continuously or
                acquires a finite number of samples.
                If the task acquires samples continuously, and you set this input to
                nidaqmx.constants.READ_ALL_AVAILABLE, this method reads all the samples currently
                available in the buffer.
                If the task acquires a finite number of samples, and you set this input
                to nidaqmx.constants.READ_ALL_AVAILABLE, the method waits for the task to acquire all requested
                samples, then reads those samples. If you set the “read_all_avail_samp” property to True, the
                method reads the samples currently available in the buffer and does not wait for the task to
                acquire all requested samples.
            timeout:  Specifies the amount of time in seconds to wait for samples to become available. If the time
                elapses, the method returns an error and any samples read before the timeout elapsed. The default
                timeout is 10 seconds. If you set timeout to nidaqmx.constants.WAIT_INFINITELY, the method waits
                indefinitely. If you set timeout to 0, the method tries once to read the requested samples and
                returns an error if it is unable to.
        Return:
            Array of data
        """
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_multi_chan(samples_per_channel, timeout)
            waveform += data
        return waveform

    def read_waveform(self, samples_per_channel=nidaqmx.task.NUM_SAMPLES_UNSET, timeout=10):
        """
        Reads one or more waveforms from each task specified in the list of session that contains
        one or more analog input channels.
        Args:
            samples_per_channel: Specifies the number of samples to read. If this input is not set,
                assumes samples to read is 1. Conversely, if this input is set, assumes there are
                multiple samples to read.
                If you set this input to nidaqmx.constants. READ_ALL_AVAILABLE, NI-DAQmx determines
                how many samples to read based on if the task acquires samples continuously or
                acquires a finite number of samples.
                If the task acquires samples continuously, and you set this input to
                nidaqmx.constants.READ_ALL_AVAILABLE, this method reads all the samples currently
                available in the buffer.
                If the task acquires a finite number of samples, and you set this input
                to nidaqmx.constants.READ_ALL_AVAILABLE, the method waits for the task to acquire all requested
                samples, then reads those samples. If you set the “read_all_avail_samp” property to True, the
                method reads the samples currently available in the buffer and does not wait for the task to
                acquire all requested samples.
            timeout:  Specifies the amount of time in seconds to wait for samples to become available. If the time
                elapses, the method returns an error and any samples read before the timeout elapsed. The default
                timeout is 10 seconds. If you set timeout to nidaqmx.constants.WAIT_INFINITELY, the method waits
                indefinitely. If you set timeout to 0, the method tries once to read the requested samples and
                returns an error if it is unable to.
        Return:
            Array of data
        """
        waveform = []
        for session in self.sessions:
            data = session.st_read_wave_single_chan(samples_per_channel, timeout)
            waveform += data
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
        Return:
            List of properties per pin/channel
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
        pre_trigger_samples_per_channel: int = 500,
    ):
        """
        Configures each task  in the session list to stop the acquisition when the device acquires all pre-trigger
        samples; an analog signal reaches the level you specify; and the device acquires all post-trigger samples.
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
        pre_trigger_samples_per_channel: int = 500,
    ):
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

    pin_query_context: PinQueryContext

    def __init__(self, pin_query_context, sessions):
        """
        Returns an object with type MultipleSessions.

        Args:
            pin_query_context: Pin query context related to all the sessions in the sessions list
            sessions: List of the different sessions that can be related to the pin query context
        """
        self.pin_query_context = pin_query_context
        self.sessions = sessions


@nitsm.codemoduleapi.code_module
def clear_task(tsm_context: TSMContext):
    """
    Clears all the tasks in the TSMContext. Before clearing, this method will abort all tasks, if necessary,
    and will release any resources the tasks reserved. You cannot use a task after you clear it unless you
    set it again.
    """
    tasks_ai = tsm_context.get_all_nidaqmx_tasks("AnalogInput")
    tasks_ai_dsa = tsm_context.get_all_nidaqmx_tasks("AnalogInputDSA")
    tasks_ao_dsa = tsm_context.get_all_nidaqmx_tasks("AnalogOutputDSA")
    tasks_do = tsm_context.get_all_nidaqmx_tasks("DigitalOutput")

    for task in tasks_ai:
        task.stop()
        task.close()
    for task in tasks_ai_dsa:
        task.stop()
        task.close()
    for task in tasks_ao_dsa:
        task.stop()
        task.close()
    for task in tasks_do:
        task.stop()
        task.close()


def reset_devices(task: nidaqmx.Task):
    """
    Reset all devices, clear the task and returns a new empty task with the same name.
    Args:
        task: object to reset
    Return:
        Object after reset
    """
    devices = task.devices
    task_name = task.name
    task.close()
    for device in devices:
        device.reset_device()
    return nidaqmx.Task(task_name)


@nitsm.codemoduleapi.code_module
def set_task(tsm_context: TSMContext):
    """
    Associates each NI-DAQmx tasks with the NI-DAQmx task name defined in the pin map and
    set all the sessions accordingly
    """
    input_voltage_range = 10.0
    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AnalogInput")  # Replace String if PinMap change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.ai_channels.add_ai_voltage_chan(
                physical_channel, "", TerminalConfiguration.DIFFERENTIAL, -input_voltage_range, input_voltage_range
            )
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        except Exception:
            task = reset_devices(task)
            task.ai_channels.add_ai_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        finally:
            tsm_context.set_nidaqmx_task(task_name, task)

    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AnalogInputDSA")  # Replace String if PM change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.ai_channels.add_ai_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        except Exception:
            task = reset_devices(task)
            task.ai_channels.add_ai_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        finally:
            tsm_context.set_nidaqmx_task(task_name, task)

    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("AnalogOutputDSA")  # Replace String if PM change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.ao_channels.add_ao_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        except Exception:
            task = reset_devices(task)
            task.ao_channels.add_ao_voltage_chan(physical_channel)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        finally:
            tsm_context.set_nidaqmx_task(task_name, task)

    task_names, channel_lists = tsm_context.get_all_nidaqmx_task_names("DigitalOutput")  # Replace String if PM change
    for task_name, physical_channel in zip(task_names, channel_lists):
        task = nidaqmx.Task(task_name)
        try:
            task.do_channels.add_do_chan(physical_channel, "", nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        except Exception:
            task = reset_devices(task)
            task.do_channels.add_do_chan(physical_channel, "", nidaqmx.constants.LineGrouping.CHAN_PER_LINE)
            task.timing.samp_timing_type = nidaqmx.constants.SampleTimingType.SAMPLE_CLOCK
        finally:
            tsm_context.set_nidaqmx_task(task_name, task)


# Pin Map
@nitsm.codemoduleapi.code_module
def get_all_instrument_names(tsm_context: TSMContext, task_type: str = ""):
    """
    Returns the channel group ID and associated instrument names and channel lists of all instruments
    of type Instrument Type ID defined in the Semiconductor Module context. You can use instrument names,
    channel group IDs, and channel lists to open driver sessions. The Instrument Names and Channel Lists
    parameters always return the same number of elements. Instrument names repeat in the Instrument Names
    parameter if the instrument has multiple channel groups.
    Args:
        tsm_context: Pin context defined by pin map
        task_type: Specifies the type of NI-DAQmx task to return. Use an empty string to obtain the names of all
        tasks regardless of task type.
    Return:
        A tuple of the NI-DAQmx task names.
    """
    instruments = tsm_context.get_all_nidaqmx_task_names(task_type)
    return instruments  # Instrument Names, Channel Lists per Instrument


@nitsm.codemoduleapi.code_module
def get_all_sessions(tsm_context: TSMContext, task_type: str = ""):
    """
    Returns all sessions in the Semiconductor Module Context that belong to multiple instruments of the type DAQmx.
    Args:
        tsm_context: Pin context defined by pin map
        task_type: Specifies the type of NI-DAQmx task to return. Use an empty string to obtain the names of all
        tasks regardless of task type
    Return:
        List of tasks of the specific type
    """
    tasks = tsm_context.get_all_nidaqmx_tasks(task_type)
    return tasks


@nitsm.codemoduleapi.code_module
def pins_to_session_sessions_info(tsm_context: TSMContext, pins: PinsArg):
    """
    Returns a properly filled object of the type MultipleSessions with a session per each
    site defined in the pin map
    Args:
        tsm_context: Pin context defined by pin map
        pins: The name of the pin(s) or pin group(s) to translate to a task.
    Return:
        Multiple_Sessions: An object that tracks the task associated with this pin query. Use this object
        to publish measurements and extract data from a set of measurements.
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
    Args:
        tsm_context: Pin context defined by pin map
        pins: The name of the pin(s) or pin group(s) to translate to a set of tasks.
    Return:
        session: An object that tracks the tasks associated with this pin query. Use this object to publish
        measurements and extract data from a set of measurements.
    """
    session = tsm_context.pins_to_nidaqmx_tasks(pins)  # pin_query_context, task, channel_lists
    return session


# def set_session(tsm_context: TSMContext, instrument_name: str, daqmx_session: nidaqmx.Task):
#     tsm_context.set_nidaqmx_task(instrument_name, daqmx_session)

"""
@nitsm.codemoduleapi.code_module
def pins_to_task_and_connect(tsm_context: TSMContext, task_name: PinsArg, pins: PinsArg):
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, InstrumentTypeIdConstants.NI_DAQMX, Capability.ALL)
    multiple_session_info = pins_to_session_sessions_info(tsm_context, task_name)
    sessions = []
    for pin in pin_list:
        # sessions += abstract_switch.pin_to_session(pin)    # TODO Abstract Switch function?
        pass
    if len(sessions) != 0:
        # abstract_switch.connect_session_info(sessions)     # TODO Abstract Switch?
        pass
    return multiple_session_info
"""
