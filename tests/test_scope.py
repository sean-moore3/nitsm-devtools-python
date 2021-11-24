import pytest
import typing
import os
import niscope
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidevtools.scope as scope

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))
pin_file_names = ["simulated.pinmap", "scope.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
if SIMULATE_HARDWARE:
    pin_file_name = pin_file_names[0]
    pass

OPTIONS = "Simulate = true, DriverSetup = Model : 5122"


@pytest.fixture
def tsm_context(standalone_tsm_context: SemiconductorModuleContext):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    The fixture provides the digital project files necessary for initialisation of sessions
    in a dictionary format.
    """
    print("\nTest is running on Simulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        # options = {"Simulate": True, "driver_setup": {"Model": "5122"}}
        options = "Simulate = true, DriverSetup = Model : 5122"
    else:
        options = {}  # empty dict options to run on real hardware.

    scope.tsm_scope_initialize_sessions(standalone_tsm_context, options_input=options)
    yield standalone_tsm_context
    scope.tsm_scope_close_sessions(standalone_tsm_context)


@pytest.fixture
def scope_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data
    This fixture accepts single pin in string format or
    multiple pins in list of string format"""
    scope_tsms = []
    for test_pin in test_pin_s:
        scope_tsms.append(scope.tsm_ssc_scope_pins_to_sessions(tsm_context, test_pin,[0]))
    return scope_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestNIScope:
    """The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_tsm_initialize_sessions(self, tsm_context):
        """This Api is used in the Init routine"""
        queried_sessions = list(tsm_context.get_all_niscope_sessions())
        for session in queried_sessions:
            assert isinstance(session, niscope.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_niscope_instrument_names())

    def test_tsm_ssc_n_pins_to_m_sessions(self, scope_tsm_s, test_pin_s):
        """TSM SSC Digital N Pins To M Sessions.vi"""
        for scope_tsm in scope_tsm_s:
            assert isinstance(scope_tsm, scope.TSMScope)

class SSCScope(typing.NamedTuple):
    session: niscope.Session
    channels: str
    channel_list: str


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    site_numbers: typing.List[int]
    ssc: typing.List[SSCScope]


# @pytest.mark.sequence_file("niscope.seq")
# def test_niscope(system_test_runner):
#     assert system_test_runner.run()


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