import re
import typing
from enum import Enum

import niscope
import nitsm.codemoduleapi
import numpy
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
from nitsm.pinquerycontexts import PinQueryContext

import nidevtools.common as ni_dt_common


class OutputTerminal(typing.NamedTuple):
    NONE: str
    PXI_trigger_line0_RTSI0: str
    PXI_trigger_line1_RTSI1: str
    PXI_trigger_line2_RTSI2: str
    PXI_trigger_line3_RTSI3: str
    PXI_trigger_line4_RTSI4: str
    PXI_trigger_line5_RTSI5: str
    PXI_trigger_line6_RTSI6: str
    PXI_trigger_line7_RTSI7_RTSI_clock: str
    PXI_star_trigger: str
    PFI0: str
    PFI1: str
    PFI2: str
    PFI3: str
    PFI4: str
    PFI5: str
    PFI6: str
    PFI7: str
    Clock_out: str
    AUX0_PFI0: str
    AUX0_PFI1: str
    AUX0_PFI2: str
    AUX0_PFI3: str
    AUX0_PFI4: str
    AUX0_PFI5: str
    AUX0_PFI6: str
    AUX0_PFI7: str


OUTPUT_TERMINAL = OutputTerminal(
    "VAL_NO_SOURCE",
    "VAL_RTSI_0",
    "VAL_RTSI_1",
    "VAL_RTSI_2",
    "VAL_RTSI_3",
    "VAL_RTSI_4",
    "VAL_RTSI_5",
    "VAL_RTSI_6",
    "VAL_RTSI_7",
    "VAL_PXI_STAR",
    "VAL_PFI_0",
    "VAL_PFI_1",
    "VAL_PFI_2",
    "VAL_PFI_3",
    "VAL_PFI_4",
    "VAL_PFI_5",
    "VAL_PFI_6",
    "VAL_PFI_7",
    "VAL_CLK_OUT",
    "VAL_AUX_0_PFI_0",
    "VAL_AUX_0_PFI_1",
    "VAL_AUX_0_PFI_2",
    "VAL_AUX_0_PFI_3",
    "VAL_AUX_0_PFI_4",
    "VAL_AUX_0_PFI_5",
    "VAL_AUX_0_PFI_6",
    "VAL_AUX_0_PFI_7",
)


class TriggerSource(typing.NamedTuple):
    RTSI0: str
    RTSI1: str
    RTSI2: str
    RTSI3: str
    RTSI4: str
    RTSI5: str
    RTSI6: str
    PFI0: str
    PFI1: str
    PFI2: str
    PFI3: str
    PFI4: str
    PFI5: str
    PFI6: str
    PFI7: str
    PXI_star_trigger: str
    AUX0_PFI0: str
    AUX0_PFI1: str
    AUX0_PFI2: str
    AUX0_PFI3: str
    AUX0_PFI4: str
    AUX0_PFI5: str
    AUX0_PFI6: str
    AUX0_PFI7: str


TRIGGER_SOURCE = TriggerSource(
    "VAL_RTSI_0",
    "VAL_RTSI_1",
    "VAL_RTSI_2",
    "VAL_RTSI_3",
    "VAL_RTSI_4",
    "VAL_RTSI_5",
    "VAL_RTSI_6",
    "VAL_PFI_0",
    "VAL_PFI_1",
    "VAL_PFI_2",
    "VAL_PFI_3",
    "VAL_PFI_4",
    "VAL_PFI_5",
    "VAL_PFI_6",
    "VAL_PFI_7",
    "VAL_PXI_STAR",
    "VAL_AUX_0_PFI_0",
    "VAL_AUX_0_PFI_1",
    "VAL_AUX_0_PFI_2",
    "VAL_AUX_0_PFI_3",
    "VAL_AUX_0_PFI_4",
    "VAL_AUX_0_PFI_5",
    "VAL_AUX_0_PFI_6",
    "VAL_AUX_0_PFI_7",
)


class _NIScopeSSC:
    """
    _Site specific _Session and _Channel.
    Each object of this class is used to store info for a specified pin under specific Site.
    To store a _Session and _Channel(s) for different _Site(s) you need an array of this class object.
    """

    """
    Prefix cs is used in all methods that operates on a given channels in a session. 
    These are for internal use only and can be changed any time. 
    External module should not use these methods with prefix 'cs_' directly.  
    """

    def __init__(self, session: niscope.Session, channels: str, pins: str):
        self._session = session  # mostly shared session depends on pinmap file.
        self._channels = channels  # specific channel(s) of that session
        self._pins = pins  # pin names mapped to the channels

    @property
    def session(self):
        """This allows to access the session stored in each instance of the class

        Returns:
            niscope.Session : session of scope
        """
        return self._session  # This session may contain other pin's channels

    @property
    def channels(self):
        """returns the channels of the pin query context

        Returns:
            _type_: string List
        """
        return self._channels

    @property
    def channel_list(self):
        """returns the Pin names of the pin query context

        Returns:
            _type_: string List
        """
        return self._pins


# Scope Sub routines
def _expand_ssc_to_ssc_per_channel(ssc_s: typing.List[_NIScopeSSC]):
    """private function

    Args:
        ssc_s (typing.List[_NIScopeSSC]): to know the length of the list

    Returns:
        ssc list : list of sessions sites and channels
    """
    return [
        _NIScopeSSC(ssc.session, channel, channel_list)
        for ssc in ssc_s
        for channel, channel_list in zip(
            re.split(r"\s*,\s*", ssc.channels),
            re.split(r"\s*,\s*", ssc.channel_list),
        )
    ]


def _configure_vertical_per_channel_arrays(
    ssc_s: typing.List[_NIScopeSSC],
    ranges: typing.List[float],
    couplings: typing.List[niscope.VerticalCoupling],
    offsets: typing.List[float],
    probes_drop: typing.List[float],
    enabled_s: typing.List[bool],
):
    """_private function for vertical configuration_

    Args:
        ssc_s (typing.List[_NIScopeSSC]): list of session channels
        ranges (typing.List[float]): vertical range list - one for each session
        couplings (typing.List[niscope.VerticalCoupling]): vertical coupling list - one for each session
        offsets (typing.List[float]): vertical offset list - one for each session
        probes_drop (typing.List[float]): probe attenuation drop list - one for each session
        enabled_s (typing.List[bool]): channel enabled list - one for each session
    """
    for (ssc, v_range, coupling, offset, probe_drop, enabled) in zip(
        ssc_s, ranges, couplings, offsets, probes_drop, enabled_s
    ):
        ssc.session.channels[ssc.channels].configure_vertical(
            v_range, coupling, offset, probe_drop, enabled
        )


# Digital Sub routines
def _channel_list_to_pins(channel_list: str):
    """private function which maps channel list to all pins as per the pinmap file.

    Args:
        channel_list (str): comma separated list of channels that belongs to the session

    Returns:
        tuple: channels list, pin list and sites
    """
    channels = re.split(r"\s*,\s*", channel_list)
    sites = [-1] * len(channels)
    pins = channels[:]
    for i in range(len(channels)):
        try:
            site, pins[i] = re.split(r"[/\\]", channels[i])
        except ValueError:
            pass
        else:
            sites[i] = int(re.match(r"Site(\d+)", site).group(1))
    return channels, pins, sites


# DCPower Sub routines
def _expand_to_requested_array_size(
    data_in: typing.Any,
    requested_size: int,
):
    """private function for expanding to the array size

    Args:
        data_in (typing.Any): any python object
        requested_size (int): length of the output list

    Raises:
        ValueError: when the requested size is zero
        ValueError: incoming data can't be distributed to the list of session stored

    Returns:
        list: list of the incoming objects
    """
    data: typing.Any
    data_out: typing.Any = []
    if isinstance(data_in, tuple):
        i = 0
        data = data_in
        for _ in range(requested_size):
            data_out.append(data[i])
            if i == len(data):
                i = 0
            else:
                i += 1
    else:
        data = (data_in,)
        data_out = data * requested_size
    if (len(data) == 0 ^ requested_size == 0) or (requested_size % len(data) != 0):
        if len(data) == 0 or requested_size == 0:
            raise ValueError("Empty array input")
        else:
            raise ValueError("Input array does not evenly distribute into sessions")
    return data_out


def _fetch_measurement_stats_arrays(
    ssc_s: typing.List[_NIScopeSSC],
    scalar_measurements: typing.List[niscope.ScalarMeasurement],
):
    """private function for fetching statics for selected functions

    Args:
        ssc_s (typing.List[_NIScopeSSC]): _description_
        scalar_measurements (typing.List[niscope.ScalarMeasurement]): _description_

    Returns:
        _type_: _description_
    """
    stats: typing.List[niscope.MeasurementStats] = []
    for ssc, scalar_meas_function in zip(ssc_s, scalar_measurements):
        stats.append(
            ssc.session.channels[ssc.channels].fetch_measurement_stats(scalar_meas_function)
        )  # function with unknown type
    return stats


class _NIScopeTSM:
    """This is private class exposed via an object with different name. mostly all operations in this
    class will be performed on all sessions of selected channels stored in this class.
    """

    def __init__(self, sessions_sites_channels: typing.Iterable[_NIScopeSSC]):
        self._sscs = sessions_sites_channels

    def _obtain_trigger_path(self, trigger_source: str, setup_type: str):
        trigger_paths: typing.List[str] = []
        if setup_type == "STSM1":
            for ssc in self._sscs:
                chassis_string = re.match(r"_C[1-4]_", ssc.session.io_resource_descriptor).group()
                timing_card = "SYNC_6674T_C{}_S10".format(chassis_string[2])
                trigger_path = "/" + timing_card + "/" + "PFI0"
                trigger_paths.append(trigger_path)
        else:
            for _ in self._sscs:
                trigger_paths.append(trigger_source)
        return trigger_paths

    # Configure
    def configure_impedance(self, input_impedance: float):
        """
        Configures the properties that control the electrical characteristics of
        the channels in the current TSMScope object—the input impedance and selects full bandwidth.

        Args:
            input_impedance (float): The input impedance for the channel; NI-SCOPE sets
                input_impedance to this value.
        """
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].configure_chan_characteristics(input_impedance, -1.0)
        return

    def configure_reference_level(self, channel_based_mid_ref_level=50.0):
        """Configures the reference level for the channels in the current TSMScope object

        Args:
            channel_based_mid_ref_level (float, optional): Valid values from 0 to 100. Defaults to 50.0.
        """
        for ssc in self._sscs:
            channels = ssc.session.channels[ssc.channels]
            channels.meas_ref_level_units = niscope.RefLevelUnits.PERCENTAGE
            channels.meas_chan_mid_ref_level = channel_based_mid_ref_level
            channels.meas_percentage_method = niscope.PercentageMethod.BASETOP
        return

    def configure_vertical(
        self,
        v_range: float,
        coupling: niscope.VerticalCoupling = niscope.VerticalCoupling.DC,
        offset: float = 0.0,
        probe_attenuation: float = 1.0,
        enabled: bool = True,
    ):
        """Configures the vertical scale settings for the channels in the current TSMScope object

        Args:
            v_range (float): vertical range
            coupling (niscope.VerticalCoupling, optional): Vertical Coupling AC or DC.
                Defaults to niscope.VerticalCoupling.DC.
            offset (float, optional): Vertical offset. Defaults to 0.0.
            probe_attenuation (float, optional): Vertical probe attenuation like 1x or 10x. Defaults to 1.0.
            enabled (bool, optional): Channels enabled or disabled for data capture. Defaults to True.
        """
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].configure_vertical(
                v_range, coupling, offset, probe_attenuation, enabled
            )
        return

    def configure(
        self,
        vertical_range: float = 5.0,
        probe_attenuation: float = 1.0,
        offset: float = 0.0,
        coupling: niscope.VerticalCoupling = niscope.VerticalCoupling.DC,
        min_sample_rate: float = 10e6,
        min_record_length: int = 1000,
        ref_position: float = 0.0,
        max_input_frequency: float = 0.0,
        input_impedance: float = 1e6,
        num_records: int = 1,
        enforce_realtime: bool = True,
    ):
        """Configures the vertical scale and timescale for the channels in the current TSMScope object

        Args:
            vertical_range (float, optional): _description_. Defaults to 5.0.
            probe_attenuation (float, optional): _description_. Defaults to 1.0.
            offset (float, optional): _description_. Defaults to 0.0.
            coupling (niscope.VerticalCoupling, optional): _description_. Defaults to niscope.VerticalCoupling.DC.
            min_sample_rate (float, optional): _description_. Defaults to 10e6.
            min_record_length (int, optional): _description_. Defaults to 1000.
            ref_position (float, optional): _description_. Defaults to 0.0.
            max_input_frequency (float, optional): _description_. Defaults to 0.0.
            input_impedance (float, optional): _description_. Defaults to 1e6.
            num_records (int, optional): _description_. Defaults to 1.
            enforce_realtime (bool, optional): _description_. Defaults to True.
        """
        for ssc in self._sscs:
            channels = ssc.session.channels[ssc.channels]
            channels.configure_vertical(vertical_range, coupling, offset, probe_attenuation)
            channels.configure_chan_characteristics(input_impedance, max_input_frequency)
            ssc.session.configure_horizontal_timing(
                min_sample_rate, min_record_length, ref_position, num_records, enforce_realtime
            )
        return

    def configure_vertical_per_channel(
        self,
        vertical_range: float,
        offset: float,
        probe_attenuation: float,
        coupling: niscope.VerticalCoupling,
        channel_enabled: bool,
    ):
        """Configures the vertical scale settings for the channels in the current TSMScope object

        Args:
            vertical_range (float): Vertical range
            offset (float): vertical offset
            probe_attenuation (float): vertical probe attenuation
            coupling (niscope.VerticalCoupling): vertical coupling
            channel_enabled (bool): channel enabled
        """
        ssc_per_channel = _expand_ssc_to_ssc_per_channel(list(self._sscs))
        size = len(ssc_per_channel)
        probe_drops = _expand_to_requested_array_size(probe_attenuation, size)
        couplings = _expand_to_requested_array_size(coupling, size)
        ranges = _expand_to_requested_array_size(vertical_range, size)
        offsets = _expand_to_requested_array_size(offset, size)
        enabled_out = _expand_to_requested_array_size(channel_enabled, size)
        _configure_vertical_per_channel_arrays(
            ssc_per_channel, ranges, couplings, offsets, probe_drops, enabled_out
        )
        return

    # Configure Timing
    def configure_timing(
        self,
        min_sample_rate: float = 20e6,
        min_num_pts: int = 1000,
        ref_position: float = 50.0,
        num_records: int = 1,
        enforce_realtime: bool = True,
    ):
        """Configures the timescale settings for the channels in the current TSMScope object

        Args:
            min_sample_rate (float, optional): minimum samples per second. Defaults to 20e6.
            min_num_pts (int, optional): minimum number of points. Defaults to 1000.
            ref_position (float, optional): reference position. Defaults to 50.0.
            num_records (int, optional): number of records. Defaults to 1.
            enforce_realtime (bool, optional): enforcing real time acquisition. Defaults to True.
        """
        for ssc in self._sscs:
            ssc.session.configure_horizontal_timing(
                min_sample_rate,
                min_num_pts,
                ref_position,
                num_records,
                enforce_realtime,
            )
        return

    # Session Properties
    def get_session_properties(self):
        """returns the list of session properties of all channels in the current TSMScope object

        Returns:
            List[ScopeSessionProperties] : list of Scope Session properties
        """
        instrument_name: str
        voltage_range: float
        attenuation: float
        sampling_rate: float
        input_impedance: float
        trigger_channel: str
        scope_properties: typing.List[ScopeSessionProperties] = []
        for ssc in self._sscs:
            instrument_name = ssc.session.io_resource_descriptor
            pin = ssc.channel_list
            channel = ssc.channels
            voltage_range = ssc.session.channels[ssc.channels].vertical_range
            attenuation = ssc.session.channels[ssc.channels].probe_attenuation
            sampling_rate = ssc.session.horz_sample_rate
            input_impedance = ssc.session.channels[ssc.channels].input_impedance
            if ssc.session.channels[ssc.channels].vertical_coupling.value == 0:
                coupling = "AC"
            elif ssc.session.channels[ssc.channels].vertical_coupling.value == 1:
                coupling = "DC"
            elif ssc.session.channels[ssc.channels].vertical_coupling.value == 2:
                coupling = "Ground"
            else:
                coupling = "Unsupported"
            trigger_channel = ssc.session.trigger_source
            if ssc.session.trigger_slope.value == 0:
                edge = "Negative"
            elif ssc.session.trigger_slope.value == 1:
                edge = "Positive"
            else:
                edge = "Unsupported"
            scope_properties.append(
                ScopeSessionProperties(
                    instrument_name,
                    channel,
                    pin,
                    voltage_range,
                    coupling,
                    attenuation,
                    sampling_rate,
                    input_impedance,
                    trigger_channel,
                    edge,
                )
            )
        return scope_properties

    # Trigger
    def configure_digital_edge_trigger(
        self,
        trigger_source: str,
        slope: niscope.TriggerSlope,
        holdoff: float = 0.0,
        delay: float = 0.0,
    ):
        """configures trigger as digital for all channels in the current TSMScope object

        Args:
            trigger_source (str): Specifies the trigger source. Refer to trigger_source
                for defined values
            slope (niscope.TriggerSlope): Specifies whether you want a rising edge or a falling edge to trigger
                the digitizer. Refer to trigger_slope for more
                information
            holdoff (float, optional): The length of time the digitizer waits after detecting a trigger before
                enabling NI-SCOPE to detect another trigger. Refer to
                trigger_holdoff for more information. Defaults to 0.0.
            delay (float, optional): How long the digitizer waits after receiving the trigger to start
                acquiring data. Refer to trigger_delay_time for more
                information. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.session.configure_trigger_digital(
                trigger_source,
                slope,
                holdoff,
                delay,
            )
            ssc.session.trigger_modifier = niscope.TriggerModifier.NO_TRIGGER_MOD
        return

    def configure_trigger(
        self,
        level: float,
        trigger_coupling: niscope.TriggerCoupling,
        slope: niscope.TriggerSlope,
        holdoff: float = 0.0,
        delay: float = 0.0,
    ):
        """configures trigger for all channels in the current TSMScope object

        Args:
            level (float): The voltage threshold for the trigger. Refer to
                trigger_level for more information.
            trigger_coupling (niscope.TriggerCoupling): Applies coupling and filtering options to the trigger signal.
                Refer to trigger_coupling for more information.
            slope (niscope.TriggerSlope):  Specifies whether you want a rising edge or a falling edge to trigger
                the digitizer. Refer to trigger_slope for more
                information.
            holdoff (float, optional): The length of time the digitizer waits after detecting a trigger before
                enabling NI-SCOPE to detect another trigger. Refer to
                trigger_holdoff for more information. Defaults to 0.0.
            delay (float, optional): How long the digitizer waits after receiving the trigger to start
                acquiring data. Refer to trigger_delay_time for more
                information. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.session.configure_trigger_edge(
                ssc.channels,
                level,
                trigger_coupling,
                slope,
                holdoff,
                delay,
            )
        return

    def configure_trigger_immediate(self):
        """Configures common properties for immediate triggering on all channels in the
        current TSMScope object. Immediate
        triggering means the digitizer triggers itself.

        When you initiate an acquisition, the digitizer waits for a trigger. You
        specify the type of trigger that the digitizer waits for with
        Configure Trigger method, such as configure_trigger_immediate.
        """
        for ssc in self._sscs:
            ssc.session.configure_trigger_immediate()
        return

    def clear_triggers(self):
        """
        clears the triggers for all channels in the current TSMScope object.
        """
        for ssc in self._sscs:
            ssc.session.abort()
            ssc.session.configure_trigger_immediate()
            ssc.session.exported_start_trigger_output_terminal = OUTPUT_TERMINAL.NONE
            ssc.session.commit()
        return

    def export_start_triggers(self, output_terminal: str):
        """exports the start triggers on the selected output terminal

        Args:
            output_terminal (str): provide a valid resource name system like pxi trigger 0

        Returns:
            str: start trigger details
        """
        start_trigger: str = ""
        for ssc in self._sscs:
            if self._sscs.index(ssc) == 0:
                ssc.session.configure_trigger_immediate()
                ssc.session.exported_start_trigger_output_terminal = output_terminal
                ssc.session.commit()
                start_trigger = "/" + ssc.session.io_resource_descriptor + "/" + output_terminal
            else:
                ssc.session.configure_trigger_digital(
                    start_trigger,
                    niscope.TriggerSlope.POSITIVE,
                    holdoff=0.0,
                    delay=0.0,
                )
                ssc.session.initiate()
        return start_trigger

    def export_analog_edge_start_trigger(
        self,
        analog_trigger_pin_name: str,
        output_terminal: str,
        trigger_level: float = 0.0,
        trigger_slope=niscope.TriggerSlope.POSITIVE,
    ):
        """Configure the selected pin for analog edge trigger and make other channels to wait for trigger"""
        start_trigger: str = ""
        trigger_source: str = "0"
        i = 0
        flag = 0
        for ssc in self._sscs:
            j = 0
            for channel in ssc.channel_list.split(","):
                if analog_trigger_pin_name in channel:
                    flag = 1
                    trigger_source = ssc.channels.split(",")[j]
                    trigger_source = trigger_source.strip()
                    break
                j += 1
            if flag == 1:
                break
            i += 1
        data = self._sscs.pop(i)
        self._sscs.insert(0, data)
        for ssc in self._sscs:
            if self._sscs.index(ssc) == 0:
                ssc.session.configure_trigger_edge(
                    trigger_source, trigger_level, niscope.TriggerCoupling.DC, trigger_slope
                )
                ssc.session.exported_start_trigger_output_terminal = output_terminal
                ssc.session.commit()
                start_trigger = "/" + ssc.session.io_resource_descriptor + "/" + output_terminal
            else:
                ssc.session.configure_trigger_digital(
                    start_trigger, trigger_slope, holdoff=0.0, delay=0.0
                )
                ssc.session.initiate()
        return start_trigger

    # Acquisition
    def initiate(self):
        for ssc in self._sscs:
            ssc.session.initiate()
        return

    # Control
    def abort(self):
        for ssc in self._sscs:
            ssc.session.abort()
        return

    def commit(self):
        for ssc in self._sscs:
            ssc.session.commit()
        return

    def start_acquisition(self):
        for ssc in reversed(self._sscs):
            ssc.session.abort()
            ssc.session.initiate()
        return

    # Measure
    def fetch_measurement(self, scalar_meas_function: niscope.ScalarMeasurement):
        """fetch the selected measurement from all the channels in the current TSMScope object

        Args:
            scalar_meas_function (niscope.ScalarMeasurement): select the type of measurement.

        Returns:
            varies: based on the type of measurement the return datatype varies but mostly numeric list.
        """
        measurements: typing.List[float] = []
        for ssc in self._sscs:
            measurement_stats = ssc.session.channels[ssc.channels].fetch_measurement_stats(
                scalar_meas_function, num_records=1
            )  # Single channel and record
            for measurement_stat in measurement_stats:
                measurements.append(measurement_stat.result)
        return measurements

    def fetch_waveform(self, meas_num_samples: int):
        """fetch waveforms from all channels in the current TSMScope object

        Args:
            meas_num_samples (int): number of samples to fetch

        Returns:
            list: list of fetched data samples
        """
        waveforms: typing.Any = []
        waveform_info: typing.List[niscope.WaveformInfo] = []
        for ssc in self._sscs:
            channels, pins, sites = _channel_list_to_pins(
                ssc.channel_list
            )  # Unused no waveform attribute in python
            waveform = ssc.session.channels[ssc.channels].fetch(
                meas_num_samples, relative_to=niscope.FetchRelativeTo.PRETRIGGER
            )
            waveform_info.append(waveform)
            for wfm in waveform:
                waveforms.append(list(wfm.samples))  # waveform in memory view
        return waveform_info, waveforms

    def fetch_multirecord_waveform(self, num_records=-1):
        """fetch multi-record waveform from all channels in the current TSMScope object

        Args:
            num_records (int, optional): number of records to fetch. fetch everything by default. Defaults to -1.

        Returns:
            list records: multi-record waveform from all channels in list
        """
        waveforms: typing.Any = []
        waveform_info: typing.List[niscope.WaveformInfo] = []
        for ssc in self._sscs:
            channels, pins, sites = _channel_list_to_pins(
                ssc.channel_list
            )  # Unused no waveform attribute in python
            ssc.session._fetch_num_records = num_records
            waveform = ssc.session.channels[ssc.channels].fetch(
                relative_to=niscope.FetchRelativeTo.PRETRIGGER,
                num_records=num_records,
            )
            waveform_info.append(waveform)
            for wfm in waveform:
                waveforms.append(list(wfm.samples))  # waveform in memory view
        return waveform_info, waveforms

    def fetch_clear_stats(self):
        """clear all measurements stats on all channels in the current TSMScope object"""
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].clear_waveform_measurement_stats(
                clearable_measurement_function=niscope.ClearableMeasurement.ALL_MEASUREMENTS
            )
        return

    def measure_statistics(self, scalar_meas_function: niscope.ScalarMeasurement):
        """get measure statistics for all channels in the current TSMScope object

        Args:
            scalar_meas_function (niscope.ScalarMeasurement): measurement function to use for statistics

        Returns:
            varies : returns the list of measurement statistics
        """
        measurement_stats: typing.List[niscope.MeasurementStats] = []
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].clear_waveform_measurement_stats(
                clearable_measurement_function=niscope.ClearableMeasurement.ALL_MEASUREMENTS
            )
            ssc.session.initiate()
            measurement_stats.append(
                ssc.session.channels[ssc.channels].fetch_measurement_stats(scalar_meas_function)
            )
        return measurement_stats

    def fetch_meas_stats_per_channel(self, scalar_measurement: niscope.ScalarMeasurement):
        """fetches the measurement statistics per channel in the current TSMScope object

        Args:
            scalar_measurement (niscope.ScalarMeasurement): _description_

        Returns:
            _type_: _description_
        """
        ssc_per_channel = _expand_ssc_to_ssc_per_channel(list(self._sscs))
        scalar_measurements = _expand_to_requested_array_size(
            scalar_measurement, len(ssc_per_channel)
        )
        measurement_stats = _fetch_measurement_stats_arrays(ssc_per_channel, scalar_measurements)
        return measurement_stats


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    ssc: _NIScopeTSM
    sites: typing.List[int]


class PinType(Enum):
    DUT_Pin = 0
    System_Pin = 1
    Pin_Group = 2
    Not_Determined = 3


class ExpandedPinInformation(typing.NamedTuple):
    Pin: str
    Type: PinType
    Index: int


class PinsCluster(typing.NamedTuple):
    Pins: typing.List[str]


class ScopeSessionProperties(typing.NamedTuple):
    instrument_name: str
    channel: str
    pin: str
    voltage_range: float
    coupling: str
    attenuation: float
    sampling_rate: float
    input_impedance: float
    trigger_channel: str
    edge: str


# TSMContext Pin Abstraction Sub routines
def _pin_query_context_to_channel_list(
    pin_query_context: PinQueryContext,
    expanded_pins_information: typing.List[ExpandedPinInformation],
    sites: typing.List[int],
):
    """Private function for getting the channel list from pin query context"""
    tsm_context = pin_query_context._tsm_context
    tsm_context1 = nitsm.codemoduleapi.SemiconductorModuleContext(tsm_context)
    if len(sites) == 0:
        sites = list(tsm_context1.site_numbers)
    if expanded_pins_information:
        pin_names = []
        pin_types = []
        for exp_pin_info in expanded_pins_information:
            pin_names.append(exp_pin_info.Pin)
            pin_types.append(exp_pin_info.Type)
    else:
        """
        The list of pins from Pin Query Context Read Pins
        doesn't expand pin groups, it only contains the
        initial strings provided to pins to sessions

        If a pin group is found when identifying pin types,
        expand pin groups
        """
        pin_names = pin_query_context._pins
        pin_types, pin_names = ni_dt_common._check_for_pin_group(tsm_context1, pin_names)
    pins_array_for_session_input: typing.List[PinsCluster] = []
    channel_list_per_session = ()
    (
        number_of_pins_per_channel,
        channel_group_indices,
        channel_indices,
    ) = tsm_context.GetChannelGroupAndChannelIndex(pin_names)
    for number_of_pins in number_of_pins_per_channel:
        """
        Create a pins list for each session of the correct size
        """
        initialized_pins: typing.List[str] = [""] * number_of_pins
        pins_array_for_session_input.append(PinsCluster(Pins=initialized_pins))
    for (
        per_site_transposed_channel_group_indices,
        per_site_transposed_channel_indices,
        site_number,
    ) in zip(
        numpy.transpose(channel_group_indices),
        numpy.transpose(channel_indices),
        sites,
    ):
        for (
            per_pin_transposed_channel_group_index,
            per_pin_transposed_channel_index,
            pin,
            pin_type,
        ) in zip(
            per_site_transposed_channel_group_indices,
            per_site_transposed_channel_indices,
            pin_names,
            pin_types,
        ):
            if pin_type.value == 1:
                pins_array_for_session_input[per_pin_transposed_channel_group_index].Pins[
                    per_pin_transposed_channel_index
                ] = pin
            else:
                pins_array_for_session_input[per_pin_transposed_channel_group_index].Pins[
                    per_pin_transposed_channel_index
                ] = "Site{}/{}".format(site_number, pin)
    for pins_array_for_session in pins_array_for_session_input:
        channel_list = ",".join(pins_array_for_session.Pins)
        channel_list_per_session += (channel_list,)
    return sites, channel_list_per_session


# Pinmap
@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int] = []):
    """Returns the pin-query context object for the given pins at given sites.

    Args:
        tsm_context (TSMContext): Semiconductor module Reference from the TestStand.
        pins (typing.List[str]): Pins names defined in the current the pinmap.
        sites (typing.List[int], optional): if you need to control only on specific sites,
        then provide site numbers. Defaults to [].

    Returns:
        TSMScope object :  for the selected pins. All instrument specific operations
        are available as properties and methods of this object.
    """
    if len(sites) == 0:
        sites = list(tsm_context.site_numbers)  # This is tested and works
    pin_query_context, sessions, channels = tsm_context.pins_to_niscope_sessions(pins)
    sites, pin_lists = _pin_query_context_to_channel_list(pin_query_context, [], sites)
    # sites, pin_lists = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], sites)
    sscs = [
        _NIScopeSSC(session, channel, pin_list)
        for session, channel, pin_list in zip(sessions, channels, pin_lists)
    ]
    scope_tsm = _NIScopeTSM(sscs)
    return TSMScope(pin_query_context, scope_tsm, sites)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SMContext, options: dict = {}):
    """Opens sessions for all NI-SCOPE instrument channels that are defined in pinmap associated with the tsm context"""
    instrument_names = tsm_context.get_all_niscope_instrument_names()
    for instrument_name in instrument_names:
        session = niscope.Session(instrument_name, reset_device=True, options=options)
        try:
            session.commit()
        except Exception:
            session.reset_device()
        session.configure_chan_characteristics(1e6, -1)
        session.commit()
        tsm_context.set_niscope_session(instrument_name, session)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SMContext):
    """Resets and Closes all the NI-SCOPE instruments sessions from the pinmap file associated
    with the Semiconductor Module Context."""
    sessions = tsm_context.get_all_niscope_sessions()
    for session in sessions:
        session.reset()
        session.close()


if __name__ == "__main__":
    pass
