import pytest
import typing
import os
import time
import niscope
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMClass
import nidevtools.scope as scope

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))
pin_file_names = ["scope.pinmap", "Rainbow.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]
if SIMULATE:
    pin_file_name = pin_file_names[1]

OPTIONS = {"Simulate": True, "driver_setup": {"Model": "5105"}}


@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    The fixture provides the digital project files necessary for initialisation of sessions
    in a dictionary format.
    """
    print("\nTest is running on Simulated driver?", SIMULATE)
    if SIMULATE:
        options = OPTIONS
    else:
        options = {}  # empty dict options to run on real hardware.

    scope.initialize_sessions(standalone_tsm, options=options)
    yield standalone_tsm
    scope.close_sessions(standalone_tsm)


@pytest.fixture
def scope_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data
    This fixture accepts single pin in string format or
    multiple pins in list of string format"""
    scope_tsms = []
    for test_pin in tests_pins:
        scope_tsms.append(scope.tsm_ssc_pins_to_sessions(tsm_context, test_pin, []))
    return scope_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestNIScope:
    """The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_tsm_initialize_sessions(self, tsm_context):
        """This Api is used in the Init routine"""
        print("tsm_context", tsm_context)
        queried_sessions = list(tsm_context.get_all_niscope_sessions())
        for session in queried_sessions:
            assert isinstance(session, niscope.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_niscope_instrument_names())

    def test_tsm_pins_to_sessions(self, scope_tsm_s, tests_pins):
        """"""
        for scope_tsm in scope_tsm_s:
            assert isinstance(scope_tsm, scope.TSMScope)

    def test_configure_vertical(self, scope_tsm_s):
        for tsm_scope in scope_tsm_s:
            scope.configure_impedance(tsm_scope, 0.5)
            scope.configure_reference_level(tsm_scope)
            scope.configure_vertical(tsm_scope, 5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
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
                tsm_scope, 5.0, 0.0, 1.0, niscope.VerticalCoupling.DC, True
            )
            scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)

    @staticmethod
    def subroutine_init_commit_abort(tsm_scope):
        scope.initiate(tsm_scope)
        scope.commit(tsm_scope)
        scope.abort(tsm_scope)

    def test_config_immediate_trigger(self, scope_tsm_s):
        for tsm_scope in scope_tsm_s:
            scope.configure_impedance(tsm_scope, 0.5)
            scope.configure_reference_level(tsm_scope)
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
            scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)
            scope.configure_immediate_trigger(tsm_scope)
            scope.tsm_ssc_start_acquisition(tsm_scope)
            _, data1, data2 = scope.fetch_waveform(tsm_scope, 1)
            print(data1, data2, "\n")

    def test_analog_edge_start_trigger(self, scope_tsm_s, tests_pins):
        for tsm_scope, test_pins in zip(scope_tsm_s, tests_pins):
            scope.configure_impedance(tsm_scope, 0.5)
            scope.configure_reference_level(tsm_scope)
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
            scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)
            scope.tsm_ssc_clear_triggers(tsm_scope)
            scope.tsm_ssc_export_analog_edge_start_trigger(
                tsm_scope, test_pins[0], "/OSC1/PXI_Trig2"
            )
            scope.tsm_ssc_start_acquisition(tsm_scope)
            _, data1, data2 = scope.fetch_waveform(tsm_scope, 1)
            print(data1, data2, "\n")

    def test_all_scope_apis(self, scope_tsm_s):
        for tsm_scope in scope_tsm_s:
            scope.configure_impedance(tsm_scope, 0.5)
            scope.configure_reference_level(tsm_scope)
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
            scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)
            self.subroutine_init_commit_abort(tsm_scope)
            scope.configure_digital_edge_trigger(
                tsm_scope, "/OSC1/PXI_Trig0", niscope.TriggerSlope.POSITIVE
            )
            scope.configure_trigger(
                tsm_scope, 0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE
            )
            scope.tsm_ssc_clear_triggers(tsm_scope)
            scope.tsm_ssc_export_start_triggers(tsm_scope, "/OSC1/PXI_Trig1")
            scope.tsm_ssc_start_acquisition(tsm_scope)
            _, props = scope.get_session_properties(tsm_scope)
            print("\n", props)
            _, measurement1 = scope.fetch_measurement(
                tsm_scope, niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(measurement1)
            _, measurement2 = scope.measure_statistics(
                tsm_scope, niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(measurement2)
            scope.ssc_fetch_clear_stats(tsm_scope.ssc)
            _, data3 = scope.tsm_ssc_fetch_meas_stats_per_channel(
                tsm_scope, niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(data3)
            _, data1, data2 = scope.fetch_waveform(tsm_scope, 1)
            print(data1, data2, "\n")

    def test_multirecord_waveform_fetch(self, scope_tsm_s):
        for tsm_scope in scope_tsm_s:
            # scope.configure(tsm_scope, 5.0, 1.0, 0.0, niscope.VerticalCoupling.DC, 10e6, 1000, 0.0, 0.0, 1e6, 1, True)
            scope.configure_vertical(tsm_scope, 5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
            scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)
            # scope.tsm_ssc_start_acquisition(tsm_scope)
            scope.initiate(tsm_scope)
            _, data1, data2 = scope.fetch_multirecord_waveform(tsm_scope, 1)
            print(data1, data2, "\n")
            scope.abort(tsm_scope)


class SSCScope(typing.NamedTuple):
    session: niscope.Session
    channels: str
    channel_list: str


class TSMScope(typing.NamedTuple):
    pin_query_context: typing.Any
    sites: typing.List[int]
    ssc: typing.List[SSCScope]


# @pytest.mark.sequence_file("scope.seq")
# def test_niscope(system_test_runner):
#     assert system_test_runner.run()


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: SMClass):
    scope.initialize_sessions(tsm_context, OPTIONS)


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    return scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)


@nitsm.codemoduleapi.code_module
def configure(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.configure_impedance(tsm_scope, 0.5)
    scope.configure_reference_level(tsm_scope)
    scope.configure_vertical(tsm_scope, 5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
    scope.configure(
        tsm_scope, 5.0, 1.0, 0.0, niscope.VerticalCoupling.DC, 10e6, 1000, 0.0, 0.0, 1e6, 1, True
    )
    scope.configure_vertical_per_channel(
        tsm_scope, 5.0, 0.0, 1.0, niscope.VerticalCoupling.DC, True
    )
    scope.configure_timing(tsm_scope, 20e6, 1000, 50, 1, True)


@nitsm.codemoduleapi.code_module
def acquisition(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.initiate(tsm_scope)


@nitsm.codemoduleapi.code_module
def control(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.commit(tsm_scope)
    scope.abort(tsm_scope)


@nitsm.codemoduleapi.code_module
def session_properties(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.get_session_properties(tsm_scope)


@nitsm.codemoduleapi.code_module
def trigger(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.configure_digital_edge_trigger(
        tsm_scope, scope.TRIGGER_SOURCE.RTSI0, niscope.TriggerSlope.POSITIVE
    )
    scope.configure_trigger(
        tsm_scope, 0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE
    )
    scope.configure_immediate_trigger(tsm_scope)
    scope.tsm_ssc_clear_triggers(tsm_scope)
    scope.tsm_ssc_export_start_triggers(tsm_scope, scope.OUTPUT_TERMINAL.NONE)
    scope.tsm_ssc_start_acquisition(tsm_scope)


@nitsm.codemoduleapi.code_module
def measure_results(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.fetch_measurement(tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def measure_stats(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.measure_statistics(tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def clear_stats(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.ssc_fetch_clear_stats(tsm_scope.ssc)


@nitsm.codemoduleapi.code_module
def fetch_measurement_stats_per_channel(
    tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]
):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    scope.tsm_ssc_fetch_meas_stats_per_channel(tsm_scope, niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm_context: SMClass, pins: typing.List[str], sites: typing.List[int]):
    tsm_scope = scope.tsm_ssc_pins_to_sessions(tsm_context, pins, sites)
    print(scope.fetch_waveform(tsm_scope, 1))
    print(scope.fetch_multirecord_waveform(tsm_scope, 1))
    scope.abort(tsm_scope)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SMClass):
    print(" Closing sessions")
    scope.close_sessions(tsm_context)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SMClass):
    # ctypes.windll.user32.MessageBoxW(None, "Process name: niPythonHost.exe and Process ID: " + str(os.getpid()), "Attach debugger", 0)
    print("opening sessions")
    scope.initialize_sessions(tsm_context)
    tsmscope = scope.tsm_ssc_pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope.abort(tsmscope)
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm_context: SMClass):
    tsmscope = scope.tsm_ssc_pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope.configure(
        tsmscope, 4e-3, 1, 0, niscope.VerticalCoupling.AC, 5e6, 20000, 50, -1, 1e6, 1, True
    )
    scope.configure_digital_edge_trigger(tsmscope, "", slope=niscope.TriggerSlope.POSITIVE)
    _, props = scope.get_session_properties(tsmscope)
    print("\n", props)
    print("Configuring fetch wf")
    return props


@nitsm.codemoduleapi.code_module
def fetch_waveform1(tsm_context: SMClass):
    tsmscope = scope.tsm_ssc_pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope.tsm_ssc_start_acquisition(tsmscope)
    _, data_capture, wf_info = scope.fetch_waveform(tsmscope, 20000)
    _, v_peak = scope.fetch_measurement(
        tsmscope, scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
    )
    _, v_max = scope.fetch_measurement(
        tsmscope, scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_MAX
    )
    print(wf_info)
    print(v_peak)
    print(v_max)
    return data_capture, wf_info, v_peak, v_max
