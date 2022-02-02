import re
import typing
import numpy
import niscope
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.pinquerycontexts import PinQueryContext
from enum import Enum
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
        return self._channels

    @property
    def channel_list(self):
        return self._pins

    def cs_xyz(self):
        pass  # template


# Scope Sub routines
def _expand_ssc_to_ssc_per_channel(ssc_s: typing.List[_NIScopeSSC]):
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
    for (ssc, v_range, coupling, offset, probe_drop, enabled) in zip(
        ssc_s, ranges, couplings, offsets, probes_drop, enabled_s
    ):
        ssc.session.channels[ssc.channels].configure_vertical(
            v_range, coupling, offset, probe_drop, enabled
        )


# Digital Sub routines
def _channel_list_to_pins(channel_list: str):
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
    i = 0
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
    stats: typing.List[niscope.MeasurementStats] = []
    for ssc, scalar_meas_function in zip(ssc_s, scalar_measurements):
        stats.append(
            ssc.session.channels[ssc.channels].fetch_measurement_stats(scalar_meas_function)
        )  # function with unknown type
    return stats


class _NIScopeTSM:
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
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].configure_chan_characteristics(input_impedance, -1.0)
        return

    def configure_reference_level(self, channel_based_mid_ref_level=50.0):
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
        ssc_per_channel = _expand_ssc_to_ssc_per_channel(self._sscs)
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
        for ssc in self._sscs:
            ssc.session.configure_trigger_immediate()
        return

    def clear_triggers(self):
        for ssc in self._sscs:
            ssc.session.abort()
            ssc.session.configure_trigger_immediate()
            ssc.session.exported_start_trigger_output_terminal = OUTPUT_TERMINAL.NONE
            ssc.session.commit()
        return

    def export_start_triggers(self, output_terminal: str):
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
        """Export Analog Edge Start Trigger.vi"""
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
        measurements: typing.List[float] = []
        for ssc in self._sscs:
            measurement_stats = ssc.session.channels[ssc.channels].fetch_measurement_stats(
                scalar_meas_function, num_records=1
            )  # Single channel and record
            for measurement_stat in measurement_stats:
                measurements.append(measurement_stat.result)
        return measurements

    def fetch_waveform(self, meas_num_samples: int):
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
        for ssc in self._sscs:
            ssc.session.channels[ssc.channels].clear_waveform_measurement_stats(
                clearable_measurement_function=niscope.ClearableMeasurement.ALL_MEASUREMENTS
            )
        return

    def measure_statistics(self, scalar_meas_function: niscope.ScalarMeasurement):
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
        ssc_per_channel = _expand_ssc_to_ssc_per_channel(self._sscs)
        scalar_measurements = _expand_to_requested_array_size(scalar_measurement, len(ssc_per_channel))
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
    tsm_context = pin_query_context._tsm_context
    tsm_context1 = nitsm.codemoduleapi.SemiconductorModuleContext(pin_query_context._tsm_context)
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
        pin_types, pin_names = ni_dt_common._check_for_pin_group(tsm_context, pin_names)
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
def pins_to_sessions(
    tsm_context: TSMContext, pins: typing.List[str], sites: typing.List[int] = []
):
    if len(sites) == 0:
        sites = list(tsm_context.site_numbers)  # This is tested and works
    pin_query_context, sessions, channels = tsm_context.pins_to_niscope_sessions(pins)
    sites, pin_lists = _pin_query_context_to_channel_list(pin_query_context, [], sites)
    # sites, pin_lists = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], sites)
    sscs = [_NIScopeSSC(session, channel, pin_list)
            for session, channel, pin_list in zip(sessions, channels, pin_lists)]
    scope_tsm = _NIScopeTSM(sscs)
    return TSMScope(pin_query_context, scope_tsm, sites)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: TSMContext, options: dict = {}):
    """Opens sessions for all instrument channels that are associated with the tsm context"""
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
def close_sessions(tsm_context: TSMContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm_context.get_all_niscope_sessions()
    for session in sessions:
        session.reset()
        session.close()


if __name__ == "__main__":
    pass
