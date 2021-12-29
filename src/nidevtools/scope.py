import re
import typing
import numpy
import niscope
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.pinquerycontexts import PinQueryContext
from enum import Enum
import nidevtools.common as ni_dt_common


class SSCScope(typing.NamedTuple):
    session: niscope.Session
    channels: str
    channel_list: str


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    site_numbers: typing.List[int]
    ssc: typing.List[SSCScope]


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


# Scope Sub routines
def _expand_ssc_to_ssc_per_channel(ssc_s: typing.List[SSCScope]):
    return [
        SSCScope(ssc.session, channel, channel_list)
        for ssc in ssc_s
        for channel, channel_list in zip(
            re.split(r"\s*,\s*", ssc.channels),
            re.split(r"\s*,\s*", ssc.channel_list),
        )
    ]


def _ssc_configure_vertical_per_channel_arrays(
    ssc_s: typing.List[SSCScope],
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


def _ssc_fetch_measurement_stats_arrays(
    ssc_s: typing.List[SSCScope],
    scalar_measurements: typing.List[niscope.ScalarMeasurement],
):
    stats: typing.List[niscope.MeasurementStats] = []
    for ssc, scalar_meas_function in zip(ssc_s, scalar_measurements):
        stats.append(
            ssc.session.channels[ssc.channels].fetch_measurement_stats(scalar_meas_function)
        )  # function with unknown type
    return stats


def _ssc_obtain_trigger_path(tsm: TSMScope, trigger_source: str, setup_type: str):
    trigger_paths: typing.List[str] = []
    if setup_type == "STSM1":
        for ssc in tsm.ssc:
            chassis_string = re.match(r"_C[1-4]_", ssc.session.io_resource_descriptor).group()
            timing_card = "SYNC_6674T_C{}_S10".format(chassis_string[2])
            trigger_path = "/" + timing_card + "/" + "PFI0"
            trigger_paths.append(trigger_path)
    else:
        for _ in tsm.ssc:
            trigger_paths.append(trigger_source)
    return trigger_paths


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


# Pinmap
def tsm_ssc_pins_to_sessions(
    tsm_context: TSMContext, pins: typing.List[str], sites: typing.List[int]
):
    ssc_s: typing.List[SSCScope] = []
    pin_query_context, sessions, channels = tsm_context.pins_to_niscope_sessions(pins)
    sites_out, channel_list_per_session = _pin_query_context_to_channel_list(
        pin_query_context, [], sites
    )
    # sites_out, channel_list_per_session = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], sites)
    for session, channel, channel_list in zip(sessions, channels, channel_list_per_session):
        ssc_s.append(SSCScope(session=session, channels=channel, channel_list=channel_list))
    return TSMScope(pin_query_context, sites_out, ssc_s)


# Configure
def configure_impedance(tsm: TSMScope, input_impedance: float):
    for ssc in tsm.ssc:
        ssc.session.channels[ssc.channels].configure_chan_characteristics(input_impedance, -1.0)
    return tsm


def configure_reference_level(tsm: TSMScope, channel_based_mid_ref_level=50.0):
    for ssc in tsm.ssc:
        channels = ssc.session.channels[ssc.channels]
        channels.meas_ref_level_units = niscope.RefLevelUnits.PERCENTAGE
        channels.meas_chan_mid_ref_level = channel_based_mid_ref_level
        channels.meas_percentage_method = niscope.PercentageMethod.BASETOP
    return tsm


def configure_vertical(
    tsm: TSMScope,
    range: float,
    coupling: niscope.VerticalCoupling = niscope.VerticalCoupling.DC,
    offset: float = 0.0,
    probe_attenuation: float = 1.0,
    enabled: bool = True,
):
    for ssc in tsm.ssc:
        ssc.session.channels[ssc.channels].configure_vertical(
            range, coupling, offset, probe_attenuation, enabled
        )
    return tsm


def configure(
    tsm: TSMScope,
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
    for ssc in tsm.ssc:
        channels = ssc.session.channels[ssc.channels]
        channels.configure_vertical(vertical_range, coupling, offset, probe_attenuation)
        channels.configure_chan_characteristics(input_impedance, max_input_frequency)
        ssc.session.configure_horizontal_timing(
            min_sample_rate, min_record_length, ref_position, num_records, enforce_realtime
        )
    return tsm


def configure_vertical_per_channel(
    tsm: TSMScope,
    vertical_range: float,
    offset: float,
    probe_attenuation: float,
    coupling: niscope.VerticalCoupling,
    channel_enabled: bool,
):
    ssc_per_channel = _expand_ssc_to_ssc_per_channel(tsm.ssc)
    size = len(ssc_per_channel)
    probe_drops = _expand_to_requested_array_size(probe_attenuation, size)
    couplings = _expand_to_requested_array_size(coupling, size)
    ranges = _expand_to_requested_array_size(vertical_range, size)
    offsets = _expand_to_requested_array_size(offset, size)
    enabled_out = _expand_to_requested_array_size(channel_enabled, size)
    _ssc_configure_vertical_per_channel_arrays(
        ssc_per_channel, ranges, couplings, offsets, probe_drops, enabled_out
    )
    return tsm


# Configure Timing
def configure_timing(
    tsm: TSMScope,
    min_sample_rate: float = 20e6,
    min_num_pts: int = 1000,
    ref_position: float = 50.0,
    num_records: int = 1,
    enforce_realtime: bool = True,
):
    for ssc in tsm.ssc:
        ssc.session.configure_horizontal_timing(
            min_sample_rate,
            min_num_pts,
            ref_position,
            num_records,
            enforce_realtime,
        )
    return tsm


# Acquisition
def initiate(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.initiate()
    return tsm


# Control
def abort(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.abort()
    return tsm


def commit(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.commit()
    return tsm


# Session Properties
def get_session_properties(tsm: TSMScope):
    instrument_name: str
    voltage_range: float
    attenuation: float
    sampling_rate: float
    input_impedance: float
    trigger_channel: str
    scope_properties: typing.List[ScopeSessionProperties] = []
    for ssc in tsm.ssc:
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
    return tsm, scope_properties


# Trigger
def configure_digital_edge_trigger(
    tsm: TSMScope,
    trigger_source: str,
    slope: niscope.TriggerSlope,
    holdoff: float = 0.0,
    delay: float = 0.0,
):
    for ssc in tsm.ssc:
        ssc.session.configure_trigger_digital(
            trigger_source,
            slope,
            holdoff,
            delay,
        )
        ssc.session.trigger_modifier = niscope.TriggerModifier.NO_TRIGGER_MOD
    return tsm


def configure_trigger(
    tsm: TSMScope,
    level: float,
    trigger_coupling: niscope.TriggerCoupling,
    slope: niscope.TriggerSlope,
    holdoff: float = 0.0,
    delay: float = 0.0,
):
    for ssc in tsm.ssc:
        ssc.session.configure_trigger_edge(
            ssc.channels,
            level,
            trigger_coupling,
            slope,
            holdoff,
            delay,
        )
    return tsm


def configure_immediate_trigger(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.configure_trigger_immediate()
    return tsm


def tsm_ssc_clear_triggers(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.abort()
        ssc.session.configure_trigger_immediate()
        ssc.session.exported_start_trigger_output_terminal = OUTPUT_TERMINAL.NONE
        ssc.session.commit()
    return tsm


def tsm_ssc_export_start_triggers(tsm: TSMScope, output_terminal: str):
    start_trigger: str = ""
    for ssc in tsm.ssc:
        if tsm.ssc.index(ssc) == 0:
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
    return tsm, start_trigger


def tsm_ssc_export_analog_edge_start_trigger(
    tsm: TSMScope,
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
    for ssc in tsm.ssc:
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
    data = tsm.ssc.pop(i)
    tsm.ssc.insert(0, data)
    for ssc in tsm.ssc:
        if tsm.ssc.index(ssc) == 0:
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
    return tsm, start_trigger


def tsm_ssc_start_acquisition(tsm: TSMScope):
    for ssc in reversed(tsm.ssc):
        ssc.session.abort()
        ssc.session.initiate()
    return tsm


# Measure
def fetch_measurement(
    tsm: TSMScope,
    scalar_meas_function: niscope.ScalarMeasurement,
):
    measurements: typing.List[float] = []
    for ssc in tsm.ssc:
        measurement_stats = ssc.session.channels[ssc.channels].fetch_measurement_stats(
            scalar_meas_function, num_records=1
        )  # Single channel and record
        for measurement_stat in measurement_stats:
            measurements.append(measurement_stat.result)
    return tsm, measurements


def fetch_waveform(
    tsm: TSMScope,
    meas_num_samples: int,
):
    waveforms: typing.Any = []
    waveform_info: typing.List[niscope.WaveformInfo] = []
    for ssc in tsm.ssc:
        channels, pins, sites = _channel_list_to_pins(
            ssc.channel_list
        )  # Unused no waveform attribute in python
        waveform = ssc.session.channels[ssc.channels].fetch(
            meas_num_samples, relative_to=niscope.FetchRelativeTo.PRETRIGGER
        )
        waveform_info.append(waveform)
        for wfm in waveform:
            waveforms.append(list(wfm.samples))  # waveform in memory view
    return tsm, waveform_info, waveforms


def fetch_multirecord_waveform(tsm: TSMScope, num_records=-1):
    waveforms: typing.Any = []
    waveform_info: typing.List[niscope.WaveformInfo] = []
    for ssc in tsm.ssc:
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
    return tsm, waveform_info, waveforms


def measure_statistics(tsm: TSMScope, scalar_meas_function: niscope.ScalarMeasurement):
    measurement_stats: typing.List[niscope.MeasurementStats] = []
    for ssc in tsm.ssc:
        ssc.session.channels[ssc.channels].clear_waveform_measurement_stats(
            clearable_measurement_function=niscope.ClearableMeasurement.ALL_MEASUREMENTS
        )
        ssc.session.initiate()
        measurement_stats.append(
            ssc.session.channels[ssc.channels].fetch_measurement_stats(scalar_meas_function)
        )
    return tsm, measurement_stats


def ssc_fetch_clear_stats(ssc_s: typing.List[SSCScope]):
    for ssc in ssc_s:
        ssc.session.channels[ssc.channels].clear_waveform_measurement_stats(
            clearable_measurement_function=niscope.ClearableMeasurement.ALL_MEASUREMENTS
        )
    return ssc_s


def tsm_ssc_fetch_meas_stats_per_channel(
    tsm: TSMScope, scalar_measurement: niscope.ScalarMeasurement
):
    ssc_per_channel = _expand_ssc_to_ssc_per_channel(tsm.ssc)
    scalar_measurements = _expand_to_requested_array_size(scalar_measurement, len(ssc_per_channel))
    measurement_stats = _ssc_fetch_measurement_stats_arrays(ssc_per_channel, scalar_measurements)
    return tsm, measurement_stats


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
