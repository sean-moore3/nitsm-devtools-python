import re
import typing
import niscope


class SSCScope(typing.NamedTuple):
    session: niscope.Session
    channels: str
    channel_list: str


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    site_numbers: typing.List[int]
    ssc: typing.List[SSCScope]


# Subroutines #


def _expand_ssc_to_ssc_per_channel(ssc: typing.List[SSCScope]):
    return [
        SSCScope(scope_ssc.session, channel, channel_list)
        for scope_ssc in ssc
        for channel, channel_list in (
            re.split(r"\s*,\s*", scope_ssc.channels),
            re.split(r"\s*,\s*", scope_ssc.channel_list),
        )
    ]


# Acquisition #


def initiate(tsm: TSMScope):
    for ssc in tsm.ssc:
        ssc.session.initiate()


# Configuration #


def configure_impedance(tsm: TSMScope, input_impedance: float):
    for ssc in tsm.ssc:
        ssc.session.channels[ssc.channels].configure_chan_characteristics(
            input_impedance, -1.0
        )


def configure_reference_level(tsm: TSMScope):
    for ssc in tsm.ssc:
        channels = ssc.session.channels[ssc.channels]
        channels.meas_ref_level_units = niscope.RefLevelUnits.PERCENTAGE
        channels.meas_chan_mid_ref_level = 50.0
        channels.meas_percentage_method = niscope.PercentageMethod.BASETOP


def configure_vertical(
    tsm: TSMScope,
    vertical_range=5.0,
    vertical_offset=0.0,
    vertical_coupling=niscope.VerticalCoupling.DC,
    probe_attenuation=1.0,
    channel_enabled=True,
):
    for ssc in tsm.ssc:
        ssc.session.channels[ssc.channels].configure_vertical(
            vertical_range,
            vertical_coupling,
            vertical_offset,
            probe_attenuation,
            channel_enabled,
        )


def configure(
    tsm: TSMScope,
    vertical_range=5.0,
    probe_attenuation=1.0,
    vertical_offset=0.0,
    vertical_coupling=niscope.VerticalCoupling.DC,
    min_sample_rate=10e6,
    min_record_length=1000,
    ref_position=0.0,
    max_input_frequency=0.0,
    input_impedance=1e6,
    enforce_realtime=True,
):
    for ssc in tsm.ssc:
        channels = ssc.session.channels[ssc.channels]
        channels.configure_vertical(
            vertical_range, vertical_coupling, vertical_offset, probe_attenuation
        )
        channels.configure_chan_characteristics(input_impedance, max_input_frequency)
        ssc.session.configure_horizontal_timing(
            min_sample_rate, min_record_length, ref_position, 1, enforce_realtime
        )


def configure_vertical_per_channel(
    tsm: TSMScope,
    vertical_range=5.0,
    vertical_offset=0.0,
    vertical_coupling=niscope.VerticalCoupling.DC,
    probe_attenuation=1.0,
    channel_enabled=True,
):
    for ssc in _expand_ssc_to_ssc_per_channel(tsm.ssc):
        ssc.session.channels[ssc.channels].configure_vertical(
            vertical_range,
            vertical_coupling,
            vertical_offset,
            probe_attenuation,
            channel_enabled,
        )


# Configure Timing #

# Control #

# Measure #

# Pin Map #

# Session Properties #

# Trigger #
