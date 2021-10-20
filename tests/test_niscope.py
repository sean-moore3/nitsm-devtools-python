import pytest
import typing
import os
import niscope
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
import _scope as scope


OPTIONS = "Simulate = true, DriverSetup = Model : 5122"


class SSCScope(typing.NamedTuple):
    session: niscope.Session
    channels: str
    channel_list: str


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    site_numbers: typing.List[int]
    ssc: typing.List[SSCScope]


@pytest.mark.sequence_file("niscope.seq")
def test_niscope(system_test_runner):
    assert system_test_runner.run()


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: SemiconductorModuleContext):
    scope.tsm_scope_initialize_sessions(tsm_context, OPTIONS)


@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    return scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)


@nitsm.codemoduleapi.code_module
def configure(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.configure_impedance(tsm_scope, 0.5)
    scope.configure_reference_level(tsm_scope)
    scope.configure_vertical(tsm_scope, 5.0, 0.0, niscope.VerticalCoupling.DC, 1.0, True)
    scope.configure(
        tsm_scope,
        5.0,
        1.0,
        0.0,
        niscope.VerticalCoupling.DC,
        10e6,
        1000,
        0.0,
        0.0,
        1e6,
        1,
        True,
    )
    scope.configure_vertical_per_channel(
        tsm_scope, 5.0, 0.0, niscope.VerticalCoupling.DC, 1.0, True
    )
    scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)


@nitsm.codemoduleapi.code_module
def acquisition(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.initiate(tsm_scope)


@nitsm.codemoduleapi.code_module
def control(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.commit(tsm_scope)
    scope.abort(tsm_scope)


@nitsm.codemoduleapi.code_module
def session_properties(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.scope_get_session_properties(tsm_scope)


@nitsm.codemoduleapi.code_module
def trigger(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.scope_configure_digital_edge_trigger(
        tsm_scope, scope.TRIGGER_SOURCE.RTSI0, niscope.TriggerSlope.POSITIVE
    )
    scope.scope_configure_trigger(
        tsm_scope, 0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE
    )
    scope.tsm_ssc_scope_clear_triggers(tsm_scope)
    scope.tsm_ssc_scope_export_start_triggers(tsm_scope, scope.OUTPUT_TERMINAL.NONE)
    scope.tsm_ssc_scope_start_acquisition(tsm_scope)


@nitsm.codemoduleapi.code_module
def measure_results(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.scope_fetch_measurement(tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def measure_stats(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.scope_measure_statistics(tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def clear_stats(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.ssc_scope_fetch_clear_stats(tsm_scope.ssc)


@nitsm.codemoduleapi.code_module
def fetch_measurement_stats_per_channel(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.tsm_ssc_scope_fetch_meas_stats_per_channel(
        tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT
    )


@nitsm.codemoduleapi.code_module
def fetch_waveform(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int],
):
    tsm_scope = scope.tsm_ssc_scope_pins_to_sessions(tsm_context, pins, site_numbers)
    scope.scope_fetch_waveform(tsm_scope, 1)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
    scope.tsm_scope_close_sessions(tsm_context)
