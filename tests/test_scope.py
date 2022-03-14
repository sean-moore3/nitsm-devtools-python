import os
import time
import typing

import nidevtools.scope as scope
import niscope
import nitsm.codemoduleapi
import pytest
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))
pin_file_names = ["Rainbow.pinmap", "MonoLithic.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]

OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "driver_setup": {"Model": "5105"}}


@pytest.fixture
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    The fixture provides the digital project files necessary for initialisation of sessions
    in a dictionary format.
    """
    print("\nTest is running on Simulated driver?", SIMULATE)
    scope.initialize_sessions(standalone_tsm, options=OPTIONS)
    yield standalone_tsm
    scope.close_sessions(standalone_tsm)


@pytest.fixture
def scope_tsm_s(tsm, tests_pins):
    """Returns LabVIEW Cluster equivalent data
    This fixture accepts single pin in string format or
    multiple pins in list of string format"""
    scope_tsms = []
    for test_pin in tests_pins:
        scope_tsms.append(scope.pins_to_sessions(tsm, test_pin, []))
    return scope_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestNIScope:
    """The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_tsm_initialize_sessions(self, tsm):
        """This Api is used in the Init routine"""
        print("tsm_context", tsm)
        queried_sessions = list(tsm.get_all_niscope_sessions())
        for session in queried_sessions:
            assert isinstance(session, niscope.Session)
        assert len(queried_sessions) == len(tsm.get_all_niscope_instrument_names())

    def test_tsm_pins_to_sessions(self, scope_tsm_s, tests_pins):
        """"""
        for scope_tsm in scope_tsm_s:
            assert isinstance(scope_tsm, scope.TSMScope)

    def test_configure_functions(self, scope_tsm_s):
        for scope_tsm in scope_tsm_s:
            scope_tsm.ssc.configure_impedance(0.5)
            scope_tsm.ssc.configure_reference_level()
            scope_tsm.ssc.configure_vertical(5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
            scope_tsm.ssc.configure(
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
            scope_tsm.ssc.configure_vertical_per_channel(
                5.0, 0.0, 1.0, niscope.VerticalCoupling.DC, True
            )
            scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)

    @staticmethod
    def subroutine_init_commit_abort(scope_tsm):
        scope_tsm.ssc.initiate()
        scope_tsm.ssc.commit()
        scope_tsm.ssc.abort()

    def test_config_trigger_immediate(self, scope_tsm_s):
        for scope_tsm in scope_tsm_s:
            scope_tsm.ssc.configure_impedance(0.5)
            scope_tsm.ssc.configure_reference_level()
            scope_tsm.ssc.configure(
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
            scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)
            scope_tsm.ssc.configure_trigger_immediate()
            scope_tsm.ssc.start_acquisition()
            data1, data2 = scope_tsm.ssc.fetch_waveform(1)
            print(data1, data2, "\n")

    def test_analog_edge_start_trigger(self, scope_tsm_s, tests_pins):
        for scope_tsm, test_pins in zip(scope_tsm_s, tests_pins):
            scope_tsm.ssc.configure_impedance(0.5)
            scope_tsm.ssc.configure_reference_level()
            scope_tsm.ssc.configure(
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
            scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)
            scope_tsm.ssc.clear_triggers()
            scope_tsm.ssc.export_analog_edge_start_trigger(test_pins[0], "/OSC1/PXI_Trig2")
            scope_tsm.ssc.start_acquisition()
            data1, data2 = scope_tsm.ssc.fetch_waveform(-1)
            print(data1, data2, "\n")

    def test_all_scope_apis(self, scope_tsm_s):
        for scope_tsm in scope_tsm_s:
            scope_tsm.ssc.configure_impedance(0.5)
            scope_tsm.ssc.configure_reference_level()
            scope_tsm.ssc.configure(
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
            scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)
            self.subroutine_init_commit_abort(scope_tsm)
            scope_tsm.ssc.configure_digital_edge_trigger(
                "/OSC1/PXI_Trig0", niscope.TriggerSlope.POSITIVE
            )
            scope_tsm.ssc.configure_trigger(
                0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE
            )
            scope_tsm.ssc.clear_triggers()
            scope_tsm.ssc.export_start_triggers("/OSC1/PXI_Trig1")
            scope_tsm.ssc.start_acquisition()
            props = scope_tsm.ssc.get_session_properties()
            print("\n", props)
            measurement1 = scope_tsm.ssc.fetch_measurement(
                niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(measurement1)
            measurement2 = scope_tsm.ssc.measure_statistics(
                niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(measurement2)
            scope_tsm.ssc.fetch_clear_stats()
            data3 = scope_tsm.ssc.fetch_meas_stats_per_channel(
                niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
            )
            print(data3)
            data1, data2 = scope_tsm.ssc.fetch_waveform(1)
            print(data1, data2, "\n")

    def test_multirecord_waveform_fetch(self, scope_tsm_s):
        for scope_tsm in scope_tsm_s:
            # scope_tsm.ssc.configure(5.0, 1.0, 0.0, niscope.VerticalCoupling.DC, 10e6, 1000, 0.0, 0.0, 1e6, 1, True)
            scope_tsm.ssc.configure_vertical(5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
            scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)
            # scope.tsm_ssc_start_acquisition(scope_tsm)
            scope_tsm.ssc.initiate()
            data1, data2 = scope_tsm.ssc.fetch_multirecord_waveform(1)
            print(data1, data2, "\n")
            scope_tsm.ssc.abort()


# @pytest.mark.sequence_file("scope.seq")
# def test_niscope(system_test_runner):
#     assert system_test_runner.run()


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: SMContext):
    scope.initialize_sessions(tsm_context, OPTIONS)


@nitsm.codemoduleapi.code_module
def pins_to_sessions_info(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    return scope.pins_to_sessions(tsm_context, pins, sites)


@nitsm.codemoduleapi.code_module
def configure(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.configure_impedance(0.5)
    scope_tsm.ssc.configure_reference_level()
    scope_tsm.ssc.configure_vertical(5.0, niscope.VerticalCoupling.DC, 0.0, 1.0, True)
    scope_tsm.ssc.configure(
        5.0, 1.0, 0.0, niscope.VerticalCoupling.DC, 10e6, 1000, 0.0, 0.0, 1e6, 1, True
    )
    scope_tsm.ssc.configure_vertical_per_channel(5.0, 0.0, 1.0, niscope.VerticalCoupling.DC, True)
    scope_tsm.ssc.configure_timing(20e6, 1000, 50, 1, True)


@nitsm.codemoduleapi.code_module
def acquisition(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.initiate()


@nitsm.codemoduleapi.code_module
def control(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.commit()
    scope_tsm.ssc.abort()


@nitsm.codemoduleapi.code_module
def session_properties(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.get_session_properties()


@nitsm.codemoduleapi.code_module
def trigger(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.configure_digital_edge_trigger(
        scope.TRIGGER_SOURCE.RTSI0, niscope.TriggerSlope.POSITIVE
    )
    scope_tsm.ssc.configure_trigger(0.0, niscope.TriggerCoupling.DC, niscope.TriggerSlope.POSITIVE)
    scope_tsm.ssc.configure_trigger_immediate()
    scope_tsm.ssc.clear_triggers()
    scope_tsm.ssc.export_start_triggers(scope.OUTPUT_TERMINAL.NONE)
    scope_tsm.ssc.start_acquisition()


@nitsm.codemoduleapi.code_module
def measure_results(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.fetch_measurement(niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def measure_stats(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.measure_statistics(niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def clear_stats(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.fetch_clear_stats()


@nitsm.codemoduleapi.code_module
def fetch_measurement_stats_per_channel(
    tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]
):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    scope_tsm.ssc.fetch_meas_stats_per_channel(niscope.ScalarMeasurement.NO_MEASUREMENT)


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    scope_tsm = scope.pins_to_sessions(tsm_context, pins, sites)
    print(scope_tsm.ssc.fetch_waveform(1))
    print(scope_tsm.ssc.fetch_multirecord_waveform(1))
    scope_tsm.ssc.abort()


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SMContext):
    print(" Closing sessions")
    scope.close_sessions(tsm_context)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SMContext):
    print("opening sessions")
    scope.initialize_sessions(tsm_context, options=OPTIONS)
    scope_tsm = scope.pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope_tsm.ssc.abort()
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm_context: SMContext):
    scope_tsm = scope.pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope_tsm.ssc.configure(
        4e-3, 1, 0, niscope.VerticalCoupling.AC, 5e6, 20000, 50, -1, 1e6, 1, True
    )
    scope_tsm.ssc.configure_digital_edge_trigger("", slope=niscope.TriggerSlope.POSITIVE)
    props = scope_tsm.ssc.get_session_properties()
    print("\n", props)
    print("Configuring fetch wf")
    return props


@nitsm.codemoduleapi.code_module
def fetch_waveform1(tsm_context: SMContext):
    scope_tsm = scope.pins_to_sessions(tsm_context, ["OSC_xA_ANA1"], [])
    scope_tsm.ssc.start_acquisition()
    data_capture, wf_info = scope_tsm.ssc.fetch_waveform(20000)
    v_peak = scope_tsm.ssc.fetch_measurement(
        scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_PEAK_TO_PEAK
    )
    v_max = scope_tsm.ssc.fetch_measurement(
        scalar_meas_function=niscope.ScalarMeasurement.VOLTAGE_MAX
    )
    print(wf_info)
    print(v_peak)
    print(v_max)
    return data_capture, wf_info, v_peak, v_max
