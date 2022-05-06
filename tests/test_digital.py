import ctypes
import math
import os
import os.path
import typing

from nidigital import enums
import nidigital
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nitsm.codemoduleapi
import nitsm.enums
import numpy
import pytest

import nidevtools.digital as dt_dpi

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))
pin_file_names = ["Rainbow.pinmap", "MonoLithic.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]
OPTIONS = {}  # empty dict options to run on real hardware.
if SIMULATE_HARDWARE:
    OPTIONS = {"Simulate": True, "driver_setup": {"Model": "6571"}}


@pytest.fixture
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm context fixture created by the conftest.py
    The fixture provides the digital project files necessary for initialization of sessions
    in a dictionary format.
    """
    print("\nTest is running on Simulated driver?", SIMULATE_HARDWARE)
    dt_dpi.initialize_sessions(standalone_tsm, options=OPTIONS)
    yield standalone_tsm
    dt_dpi.close_sessions(standalone_tsm)


@pytest.fixture
def digital_tsm_s(tsm, tests_pins):
    """Returns LabVIEW Cluster equivalent data
    This fixture accepts single pin in string format or
    multiple pins in list of string format"""
    digital_tsms = []
    for test_pin in tests_pins:
        if isinstance(test_pin, str):
            digital_tsms.append(dt_dpi.pins_to_sessions(tsm, test_pin))
        elif isinstance(test_pin, list):
            digital_tsms.append(dt_dpi.pins_to_sessions(tsm, test_pin))
        else:
            assert False  # unexpected datatype
    return digital_tsms


@pytest.fixture
def digital_ssc_s(digital_tsm_s):
    """Returns LabVIEW Array equivalent data"""
    # func needs to be defined.
    digital_sscs = []
    for digital_tsm in digital_tsm_s:
        digital_sscs.extend(digital_tsm.ssc)
    return digital_sscs


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestNIDigital:
    """The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_initialize_sessions(self, tsm):
        """This Api is used in the Init routine"""
        queried_sessions = list(tsm.get_all_nidigital_sessions())
        for session in queried_sessions:
            assert isinstance(session, nidigital.Session)
        assert len(queried_sessions) == len(tsm.get_all_nidigital_instrument_names())

    def test_pins_to_sessions(self, digital_tsm_s, tests_pins):
        """TSM SSC Digital N Pins To M Sessions"""
        for digital_tsm in digital_tsm_s:
            assert isinstance(digital_tsm, dt_dpi.TSMDigital)

    def test_select_function(self, digital_tsm_s):
        """TSM SSC Digital Select Function
        Need to add logic to check back if the selected function is applied or not"""
        function_to_select = enums.SelectedFunction.DIGITAL
        for tsm in digital_tsm_s:
            tsm.ssc.select_function(function_to_select)
            assert isinstance(tsm, dt_dpi.TSMDigital)

    def test_write_read_static_loop_back_pin_low(self, digital_tsm_s):
        """TSM SSC Digital Write Static
        This test writes data on one pin and reads back on another pin.
        digital_tsm_s[0] is output pin and digital_tsm_s[1] is input pin
        This test may pass on simulated device as low is the default value.
        Test with write ZERO and read Low
        """
        for tsm in digital_tsm_s:
            tsm.ssc.select_function(enums.SelectedFunction.DIGITAL)
        # digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.DIGITAL)
        # digital_tsm_s[1].ssc.select_function(enums.SelectedFunction.DIGITAL)
        digital_tsm_s[0].ssc.write_static(enums.WriteStaticPinState.ZERO)
        # digital_tsm_s[0].ssc.write_static(enums.WriteStaticPinState.ZERO)
        # sleep(1)
        per_site_per_pin_data = digital_tsm_s[1].read_static()
        print(per_site_per_pin_data)
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert per_pin_data == enums.PinState.L

    def test_write_read_static_loop_back_pin_high(self, digital_tsm_s):
        """TSM SSC Digital Write Static
        This test writes data on one pin and reads back on another pin.
        digital_tsm_s[0] is output pin and digital_tsm_s[1] is input pin
        Test with write ONE and read High
        """
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.DIGITAL)
        digital_tsm_s[1].ssc.select_function(enums.SelectedFunction.DIGITAL)
        digital_tsm_s[0].ssc.write_static(enums.WriteStaticPinState.ONE)
        per_site_per_pin_data = digital_tsm_s[1].read_static()
        print(per_site_per_pin_data)
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert per_pin_data == enums.PinState.H

    def test_write_read_static_same_pin_low(self, digital_tsm_s):
        """TSM SSC Digital Write Static
        This test writes data on one pin and reads back on same pin.
        digital_tsm_s[0] is output pin and digital_tsm_s[0] is input pin
        Test with write ZERO and read Low
        """
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.DIGITAL)
        digital_tsm_s[0].ssc.write_static(enums.WriteStaticPinState.ZERO)
        per_site_per_pin_data = digital_tsm_s[0].read_static()
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert per_pin_data == enums.PinState.L

    def test_write_read_static_same_pin_high(self, digital_tsm_s):
        """TSM SSC Digital Write Static
        This test writes data on one pin and reads back on same pin.
        digital_tsm_s[0] is output pin and digital_tsm_s[0] is input pin
        Test with write ONE and read High
        """
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.DIGITAL)
        digital_tsm_s[0].ssc.write_static(enums.WriteStaticPinState.ONE)
        per_site_per_pin_data = digital_tsm_s[0].read_static()
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert per_pin_data == enums.PinState.H

    def test_ppmu_source_voltage_loop_back_pin(self, digital_tsm_s):
        """TSM SSC Digital PPMU Source Voltage.vi"""
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.PPMU)
        test_voltages = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
        for test_voltage in test_voltages:
            digital_tsm_s[0].ssc.ppmu_source_voltage(test_voltage, 0.02)
            per_site_per_pin_measurements = digital_tsm_s[1].ppmu_measure_voltage()
            print(per_site_per_pin_measurements)
            for per_site_measurements in per_site_per_pin_measurements:
                for per_pin_measurement in per_site_measurements:
                    assert isinstance(per_pin_measurement, float)
                    assert test_voltage - 0.1 <= per_pin_measurement <= test_voltage + 0.1

    def test_ppmu_source_voltage_same_pin(self, digital_tsm_s):
        """TSM SSC Digital PPMU Source Voltage.vi"""
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.PPMU)
        test_voltages = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
        for test_voltage in test_voltages:
            digital_tsm_s[0].ssc.ppmu_source_voltage(test_voltage, 0.02)
            per_site_per_pin_measurements = digital_tsm_s[0].ppmu_measure_voltage()
            print(per_site_per_pin_measurements)
            for per_site_measurements in per_site_per_pin_measurements:
                for per_pin_measurement in per_site_measurements:
                    assert isinstance(per_pin_measurement, float)
                    assert test_voltage - 0.1 <= per_pin_measurement <= test_voltage + 0.1

    def test_burst_pattern_pass_fail(self, tsm, digital_tsm_s):
        """
        TSM SSC Digital Burst Pattern [Pass Fail]
        TSM SSC Digital Apply Levels and Timing
        """
        level = tsm.nidigital_project_levels_file_paths[0]
        timing = tsm.nidigital_project_timing_file_paths[0]
        print(level)
        print(timing)
        print(str(level))
        print(str(timing))
        digital_tsm_s[2].ssc.apply_levels_and_timing(str(level), str(timing))
        per_site_pass = digital_tsm_s[2].burst_pattern_pass_fail("I2C_Write_Loop")
        print(per_site_pass)
        for per_pass in per_site_pass:
            assert isinstance(per_pass, bool)
            assert per_pass

    def test_burst_pattern(self, tsm, digital_tsm_s):
        """
        TSM SSC Digital Apply Levels and Timing
        TSM SSC Digital Configure Time Set Period
        """
        level = tsm.nidigital_project_levels_file_paths[0]
        timing = tsm.nidigital_project_timing_file_paths[0]
        print(level)
        print(timing)
        print(str(level))
        print(str(timing))
        digital_tsm_s[2].ssc.apply_levels_and_timing(str(level), str(timing))
        configured_period = digital_tsm_s[0].ssc.configure_time_set_period("Idle", 40e-6)
        assert math.isclose(configured_period, 40e-6, abs_tol=5e-6)
        digital_tsm_s[2].ssc.burst_pattern("I2C_Read_Loop")

    def test_ppmu_source_voltage_per_site_per_pin(self, digital_tsm_s):
        """
        test for the voltage sourcing per pin and site
        """
        digital_tsm_s[0].ssc.select_function(enums.SelectedFunction.PPMU)
        test_voltages = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.5, 6.0]
        for test_voltage in test_voltages:
            digital_tsm_s[0].ssc.ppmu_source_voltage(test_voltage, 0.02)
            per_site_per_pin_measurements = digital_tsm_s[1].ppmu_measure_voltage()
            print(per_site_per_pin_measurements)
            for per_site_measurements in per_site_per_pin_measurements:
                for per_pin_measurement in per_site_measurements:
                    assert isinstance(per_pin_measurement, float)
                    assert test_voltage - 0.1 <= per_pin_measurement <= test_voltage + 0.1

    def test_get_properties(self, digital_tsm_s):
        session_properties = digital_tsm_s[0].ssc.get_properties()
        for session_property in session_properties:
            print("instrument_name")
            assert session_property[0].startswith("DPI")
            print(session_property)
            print("voh")
            assert math.isclose(session_property[1], 1.7, abs_tol=5e-4)
            print("vol")
            assert math.isclose(session_property[2], 1.6, abs_tol=5e-4)
            print("vih")
            assert math.isclose(session_property[3], 3.3, abs_tol=5e-4)
            print("vil")
            assert math.isclose(session_property[4], 3.05e-5, abs_tol=5e-4)
            print("vterm")
            assert math.isclose(session_property[5], 2.0, abs_tol=5e-4)

    def test_write_source_waveform_broadcast(self, digital_tsm_s):
        """TSM SSC Digital Write Source Waveform [Broadcast].vi"""
        digital_tsm_s[0].write_source_waveform_site_unique(
            "I2C_SiteUnique",
            [
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
                [1, 2, 3, 4, 5],
            ],
            True,
        )
        digital_tsm_s[0].ssc.write_source_waveform_broadcast("I2C_Broadcast", [1, 2, 3, 4, 5], True)

    def test_write_sequencer_register(self, digital_tsm_s):
        """TSM SSC Digital Write Sequencer Register.vi"""
        digital_tsm_s[0].ssc.write_sequencer_flag(enums.SequencerFlag.FLAG1, True)
        digital_tsm_s[0].ssc.write_sequencer_register(enums.SequencerRegister.REGISTER1, 1)
        per_instrument_state = digital_tsm_s[0].ssc.read_sequencer_flag(enums.SequencerFlag.FLAG1)
        assert isinstance(per_instrument_state, list)
        assert numpy.shape(per_instrument_state) == (1,)
        for state in per_instrument_state:
            assert isinstance(state, bool)
        register_values = digital_tsm_s[0].ssc.read_sequencer_register(
            enums.SequencerRegister.REGISTER1
        )
        assert isinstance(register_values, list)
        assert numpy.shape(register_values) == (1,)
        for register_value in register_values:
            assert isinstance(register_value, int)


@nitsm.codemoduleapi.code_module
def open_sessions(tsm: SMContext):
    dt_dpi.initialize_sessions(tsm, options=OPTIONS)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    dt_dpi.close_sessions(tsm)


@nitsm.codemoduleapi.code_module
def clock_generation(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])

    frequency = 25000
    dpi_tsm.ssc.modify_time_set_for_clock_generation(frequency, 0.5, "time_set")
    dpi_tsm.ssc.clock_generator_generate_clock(frequency)
    for ssc in dpi_tsm.ssc.sessions_sites_channels:
        assert ssc._channels_session.clock_generator_is_running
        assert round(ssc._channels_session.clock_generator_frequency) == frequency
    dpi_tsm.ssc.clock_generator_abort()
    for ssc in dpi_tsm.ssc.sessions_sites_channels:
        assert not ssc._channels_session.clock_generator_is_running


@nitsm.codemoduleapi.code_module
def configuration(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.clear_start_trigger_signal()
    dpi_tsm.ssc.configure_trigger_signal(dt_dpi.PXI_TRIGGER_LINE.PXI_TRIG0)
    dpi_tsm.ssc.select_function(enums.SelectedFunction.DIGITAL)
    dpi_tsm.ssc.export_opcode_trigger_signal(
        dt_dpi.SIGNAL_ID.PATTERN_OPCODE_EVENT0, dt_dpi.PXI_TRIGGER_LINE.PXI_TRIG0
    )


@nitsm.codemoduleapi.code_module
def frequency_measurement_func(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.frequency_counter_configure_measurement_time(0.5)
    per_site_per_pin_frequency_measurements = dpi_tsm.frequency_counter_measure_frequency()
    assert isinstance(per_site_per_pin_frequency_measurements, list)
    print(numpy.shape(per_site_per_pin_frequency_measurements))
    assert numpy.shape(per_site_per_pin_frequency_measurements) == (1, 2)
    for frequency_measurements in per_site_per_pin_frequency_measurements:
        for frequency_measurement in frequency_measurements:
            assert isinstance(frequency_measurement, float)


@nitsm.codemoduleapi.code_module
def hram(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    hram_configuration = dt_dpi.HRAMConfiguration()
    hram_configuration.trigger_type = enums.HistoryRAMTriggerType.PATTERN_LABEL
    hram_configuration.pattern_label = "start_burst"
    hram_configuration.cycles_to_acquire = enums.HistoryRAMCyclesToAcquire.ALL
    dpi_tsm.ssc.configure_hram(hram_configuration)
    hram_configuration = dpi_tsm.get_hram_configuration()
    assert isinstance(hram_configuration, dt_dpi.HRAMConfiguration)
    assert isinstance(hram_configuration.finite_samples, bool)
    assert isinstance(hram_configuration.cycles_to_acquire, enums.HistoryRAMCyclesToAcquire)
    assert isinstance(hram_configuration.max_samples_to_acquire_per_site, int)
    assert isinstance(hram_configuration.buffer_size_per_site, int)
    assert isinstance(hram_configuration.pretrigger_samples, int)
    assert isinstance(hram_configuration.trigger_type, enums.HistoryRAMTriggerType)
    assert isinstance(hram_configuration.cycle_number, int)
    assert isinstance(hram_configuration.pattern_label, str)
    assert isinstance(hram_configuration.vector_offset, int)
    assert isinstance(hram_configuration.cycle_offset, int)
    dpi_tsm.ssc.burst_pattern("start_burst")
    dpi_tsm.ssc.wait_until_done()
    per_site_cycle_information = dpi_tsm.stream_hram_results()
    for cycle_information in per_site_cycle_information:
        assert not cycle_information
    files_generated = dpi_tsm.log_hram_results(
        [
            [
                HistoryRAMCycleInformation(
                    "start_burst",
                    "time_set",
                    0,
                    0,
                    0,
                    [enums.PinState.X] * 3,
                    [enums.PinState.X] * 3,
                    [False] * 3,
                )
            ]
            * 2
        ]
        * 3,
        "Pattern Name",
        os.path.dirname(os.path.realpath(__file__)) + r"\log",
    )
    for file in files_generated:
        assert isinstance(file, str)


@nitsm.codemoduleapi.code_module
def pattern_actions(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])

    dpi_tsm.ssc.abort()
    dpi_tsm.ssc.burst_pattern("start_burst")
    dpi_tsm.ssc.wait_until_done()
    per_site_pass = dpi_tsm.burst_pattern_pass_fail("start_burst")
    assert isinstance(per_site_pass, list)
    print(numpy.shape(per_site_pass))
    assert numpy.shape(per_site_pass) == (1,)
    for status in per_site_pass:
        assert isinstance(status, bool)
    per_site_per_pin_fail_counts = dpi_tsm.get_fail_count()
    assert isinstance(per_site_per_pin_fail_counts, list)
    print(numpy.shape(per_site_per_pin_fail_counts))
    assert numpy.shape(per_site_per_pin_fail_counts) == (1, 2)
    for fail_counts in per_site_per_pin_fail_counts:
        for fail_count in fail_counts:
            assert isinstance(fail_count, int)
    per_site_pass = dpi_tsm.get_site_pass_fail()
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (1,)
    for status in per_site_pass:
        assert isinstance(status, bool)


@nitsm.codemoduleapi.code_module
def pin_levels_and_timing(tsm: SMContext, pins: typing.List[str]):
    # ctypes.windll.user32.MessageBoxW(None, "niPythonHost Process ID:" + str(os.getpid()), "Attach debugger", 0)
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.apply_levels_and_timing("PinLevels", "Timing")
    dpi_tsm.apply_tdr_offsets_per_site_per_pin(
        [
            [
                1e-9,
            ]
        ]
        * 3
    )
    dpi_tsm.ssc.apply_tdr_offsets(
        [
            [
                1e-9,
                1e-9,
            ]
        ]
        * 1,
    )
    dpi_tsm.ssc.configure_active_load(0.0015, 0.0015, -0.0015)
    dpi_tsm.configure_single_level_per_site(dt_dpi.LevelTypeToSet.VIL, [0.0015, 0.0015, 0.0015])
    dpi_tsm.ssc.configure_single_level(dt_dpi.LevelTypeToSet.VIL, 0.0015)
    dpi_tsm.ssc.configure_termination_mode(enums.TerminationMode.HIGH_Z)
    dpi_tsm.configure_time_set_compare_edge_per_site_per_pin(
        "time_set",
        [
            [
                40e-6,
            ]
        ]
        * 3,
    )
    dpi_tsm.configure_time_set_compare_edge_per_site("time_set", [40e-6, 40e-6, 40e-6])
    dpi_tsm.ssc.configure_time_set_compare_edge("time_set", 40e-6)
    dpi_tsm.ssc.configure_voltage_levels(0.0015, 0.0015, 0.0015, 0.0015, 0.0015)
    configured_period = dpi_tsm.ssc.configure_time_set_period("time_set", 40e-6)
    assert math.isclose(configured_period, 40e-6, abs_tol=5e-6)
    for ssc in dpi_tsm.ssc.sessions_sites_channels:
        assert math.isclose(ssc._channels_session.active_load_ioh, -0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.active_load_iol, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.active_load_vcom, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.vih, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.vil, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.voh, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.vol, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc._channels_session.vterm, 0.0015, abs_tol=5e-6)
        assert ssc._channels_session.tdr_offset.femtoseconds == 1000000


@nitsm.codemoduleapi.code_module
def ppmu(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.ppmu_configure_aperture_time(0.01)
    dpi_tsm.ssc.ppmu_configure_current_limit_range(0.01)
    dpi_tsm.ssc.ppmu_configure_voltage_limits(0.01, 0.01)
    dpi_tsm.ssc.ppmu_source_current(0.01)
    dpi_tsm.ssc.ppmu_source_voltage_per_site_per_pin(0.01, [[0.01, 0.01]] * 3)
    dpi_tsm.ppmu_source_voltage_per_site(0.01, [0.01, 0.01, 0.01])
    dpi_tsm.ssc.ppmu_source()
    per_site_per_pin_measurements = dpi_tsm.ppmu_measure_current()
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (1, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)
    dpi_tsm.ssc.ppmu_source_voltage(0.01, 0.01)
    per_site_per_pin_measurements = dpi_tsm.ppmu_measure_voltage()
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (1, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)


@nitsm.codemoduleapi.code_module
def sequencer_flags_and_registers(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.write_sequencer_flag(enums.SequencerFlag.FLAG1, True)
    dpi_tsm.ssc.write_sequencer_register(enums.SequencerRegister.REGISTER1, 1)
    per_instrument_state = dpi_tsm.ssc.read_sequencer_flag(enums.SequencerFlag.FLAG1)
    assert isinstance(per_instrument_state, list)
    assert numpy.shape(per_instrument_state) == (1,)
    for state in per_instrument_state:
        assert isinstance(state, bool)
    per_instrument_register_values = dpi_tsm.ssc.read_sequencer_register(
        enums.SequencerRegister.REGISTER1
    )
    assert isinstance(per_instrument_register_values, list)
    assert numpy.shape(per_instrument_register_values) == (1,)
    for register_value in per_instrument_register_values:
        assert isinstance(register_value, int)


@nitsm.codemoduleapi.code_module
def session_properties_func(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    session_properties = dpi_tsm.ssc.get_properties()
    for session_property in session_properties:
        assert session_property[0].startswith("DPI")
        assert math.isclose(session_property[1], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[2], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[3], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[4], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[5], 0.0015, abs_tol=5e-6)


@nitsm.codemoduleapi.code_module
def source_and_capture_waveforms(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.write_source_waveform_site_unique(
        "SourceWaveform_SiteUnique", [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]], True
    )
    dpi_tsm.ssc.write_source_waveform_broadcast("SourceWaveform", [1, 2, 3, 4, 5], True)
    dpi_tsm.ssc.burst_pattern("start_capture")
    per_site_waveforms = dpi_tsm.fetch_capture_waveform("CaptureWaveform", 2)
    assert isinstance(per_site_waveforms, list)
    assert numpy.shape(per_site_waveforms) == (3, 2)
    for waveforms in per_site_waveforms:
        for waveform in waveforms:
            assert isinstance(waveform, int)


@nitsm.codemoduleapi.code_module
def static(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.write_static(enums.WriteStaticPinState.ONE)
    dpi_tsm.write_static_per_site([enums.WriteStaticPinState.ONE] * 3)
    dpi_tsm.write_static_per_site_per_pin(
        [[enums.WriteStaticPinState.ONE, enums.WriteStaticPinState.ONE]] * 3
    )
    per_site_per_pin_data = dpi_tsm.read_static()
    assert isinstance(per_site_per_pin_data, list)
    print(numpy.shape(per_site_per_pin_data))
    assert numpy.shape(per_site_per_pin_data) == (1, 2)
    for data in per_site_per_pin_data:
        for _data in data:
            assert isinstance(_data, enums.PinState)


@nitsm.codemoduleapi.code_module
def misc(tsm: SMContext, pins: typing.List[str]):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm1 = dt_dpi.filter_sites(dpi_tsm, [0])
    for ssc in dpi_tsm1.ssc.sessions_sites_channels:
        assert ssc._pins == "site0"
    dpi_tsm1 = dt_dpi.filter_sites(dpi_tsm, [1])
    for ssc in dpi_tsm1.ssc.sessions_sites_channels:
        assert ssc.site_list == "site1"
    dpi_tsm1 = dt_dpi.filter_sites(dpi_tsm, [2])
    for ssc in dpi_tsm1.ssc.sessions_sites_channels:
        assert ssc.site_list == "site2"

    dpi_tsm = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_tsm.ssc.initiate()
    dpi_tsm.ssc.abort()
    per_instrument_to_per_site_lut = dpi_tsm.ssc.calculate_per_instrument_to_per_site_lut(
        dpi_tsm.sites
    )
    per_site_data = dt_dpi._apply_lut_per_instrument_to_per_site(
        [False, False, False],
        per_instrument_to_per_site_lut,
        [[False, False, False], [True, True, True]],
    )
    assert len(per_site_data) == len([True, True, True])
    # assert per_site_data == [True, True, True]
    print(per_site_data)
    per_site_data = dt_dpi._apply_lut_per_instrument_to_per_site(
        [[False, False]] * 3,
        per_instrument_to_per_site_lut,
        [[[False, False]] * 3, [[True, True]] * 3],
    )
    # assert per_site_data == [[True, True]] * 3
    print(per_site_data)
    per_instrument_to_per_site_per_pin_lut = (
        dpi_tsm.ssc.calculate_per_instrument_to_per_site_per_pin_lut(dpi_tsm.sites, dpi_tsm.pins)
    )
    per_site_per_pin_data = dt_dpi._apply_lut_per_instrument_to_per_site_per_pin(
        [[0, 0], [0, 0], [0, 0]],
        per_instrument_to_per_site_per_pin_lut,
        [[1, 2, 3], [4, 5, 6]],
    )
    # assert per_site_per_pin_data == [[1, 4], [2, 5], [3, 6]]
    print(per_site_per_pin_data)
    (
        per_site_to_per_instrument_lut,
        _,
        _,
    ) = dpi_tsm.ssc.calculate_per_site_to_per_instrument_lut(dpi_tsm.sites)
    per_instrument_data = dt_dpi._apply_lut_per_site_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]], per_site_to_per_instrument_lut, [1, 2, 3]
    )
    # assert per_instrument_data == [[1, 2, 3], [0, 0, 0]]
    print(per_instrument_data)
    (
        per_site_per_pin_to_per_instrument_lut,
        _,
        _,
    ) = dpi_tsm.ssc.calculate_per_site_per_pin_to_per_instrument_lut(dpi_tsm.sites, dpi_tsm.pins)
    per_instrument_data = dt_dpi._apply_lut_per_site_per_pin_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]],
        per_site_per_pin_to_per_instrument_lut,
        [[1, 4], [2, 5], [3, 6]],
    )
    # assert per_instrument_data == [[1, 2, 3], [4, 5, 6]]
    print(per_instrument_data)
    # dpi_tsm.publish([1.0, 1.0, 1.0], "Publish_1")
    dpi_tsm.publish([[1.0, 1.0, 1.0]], "Publish_1")
    dpi_tsm.publish([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], "Publish_2")
    # dpi_tsm.publish([True, True, True], "Publish_3")
    dpi_tsm.publish([[True, True, True]], "Publish_3")
    dpi_tsm.publish([[True, True], [True, True], [True, True]], "Publish_4")


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm: SMContext):
    ctypes.windll.user32.MessageBoxW(
        None,
        "Process: niPythonHost.exe & ID: " + str(os.getpid()),
        "Attach debugger",
        0,
    )
    print(tsm.pin_map_file_path)
    pins = SMContext.get_pin_names(
        tsm, instrument_type_id=nitsm.enums.InstrumentTypeIdConstants.NI_DIGITAL_PATTERN
    )
    print(pins)
    dt_dpi.initialize_sessions(tsm, options=OPTIONS)
    dpi_tsm_i_o = dt_dpi.pins_to_sessions(tsm, ["DPI_PG_Inputs", "DPI_PG_Outputs"])
    dpi_tsm_i_o.ssc.apply_levels_and_timing("I2C_Levels", "I2C_Timing")
    dpi_tsm_i_o.ssc.select_function(dt_dpi.enums.SelectedFunction.DIGITAL)


@nitsm.codemoduleapi.code_module
def configure_pins(tsm: SMContext):
    dpi_tsm_o = dt_dpi.pins_to_sessions(tsm, ["DPI_PG_Outputs"])
    dpi_tsm_o.ssc.select_function(dt_dpi.enums.SelectedFunction.DIGITAL)
    dpi_tsm_o.ssc.write_static(dt_dpi.enums.WriteStaticPinState.ZERO)


@nitsm.codemoduleapi.code_module
def read_pins(tsm: SMContext):
    dpi_tsm_i = dt_dpi.pins_to_sessions(tsm, ["DPI_PG_Inputs"])
    # dpi_tsm_i.ssc.select_function(ni_dt_digital.enums.SelectedFunction.DIGITAL)
    data = dpi_tsm_i.read_static()
    print(data)
    return data


@nitsm.codemoduleapi.code_module
def burst_pattern(tsm: SMContext):
    dpi_tsm = dt_dpi.pins_to_sessions(tsm, ["DPI_DO_SCL", "DPI_DO_SDA"])
    dpi_tsm.ssc.apply_levels_and_timing("I2C_Levels", "I2C_Timing")
    per_site_pass = dpi_tsm.burst_pattern_pass_fail("I2C_Read_Loop")
    print(per_site_pass)
