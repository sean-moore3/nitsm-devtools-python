import pytest
import typing
import os
import os.path
import math
import numpy
import nitsm.codemoduleapi
from nidigital import enums
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidigital
import nidevtools.digital as ni_dt_digital
# from nitsm.pinquerycontexts import PinQueryContext

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))
pin_file_names = ["I2C.pinmap", "nidigital.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]


@pytest.fixture
def tsm_context(standalone_tsm_context: SemiconductorModuleContext):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined above.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    The fixture provides the digital project files necessary for initialisation of sessions
    in a dictionary format.
    """
    print("")
    print("entering tsm_context fixture")
    print("Test is running on Simulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        options = {"Simulate": True, "driver_setup": {"Model": "6571"}}
    else:
        options = {}  # empty dict options to run on real hardware.
    data_dir = os.path.join(os.path.dirname(__file__), "Data")
    specification1 = os.path.join(os.path.join(data_dir, "Specifications"), "Electrical Characteristics.specs")
    specification2 = os.path.join(os.path.join(data_dir, "Specifications"), "I2C Characteristic.specs")
    level = os.path.join(os.path.join(data_dir, "Levels"), "PinLevels.digilevels")
    timing = os.path.join(os.path.join(data_dir, "Timing"), "I2C Timing.digitiming")
    pattern1 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C Write Template.digipat")
    pattern2 = os.path.join(os.path.join(data_dir, "Patterns"), "I2C Read Template.digipat")
    cap_wfm = os.path.join(os.path.join(data_dir, "Waveforms"), "capture_buffer.digicapture")
    src_wfm = os.path.join(os.path.join(data_dir, "Waveforms"), "source_buffer.tdms")
    digital_project_files = {'specifications': [specification1, specification2],
                             'levels': [level], 'timing': [timing],
                             'pattern': [pattern1, pattern2],
                             'capture_waveforms': [cap_wfm], 'source_waveforms': [src_wfm]}
    print(digital_project_files)
    ni_dt_digital.tsm_initialize_sessions(standalone_tsm_context, options=options, file_paths=digital_project_files)
    yield standalone_tsm_context
    ni_dt_digital.tsm_close_sessions(standalone_tsm_context)
    print("")
    print("exiting tsm_context fixture")

#  @pytest.mark.sequence_file("/nites/nidigital.seq")
#  def test_nidigital(system_test_runner):
#    assert system_test_runner.run()


@pytest.fixture
def test_pin_s():
    """Need to improve this logic for supplying test pins
    using @pytest.mark.parametrize"""
    test_pins = ["SCL", "SDA"]
    read_pins = ["R_SCL", "R_SDA"]
    all_pins = test_pins+read_pins
    power_pins = ["VDD", "VDDIO"]
    resistor_pin = ["SMD"]
    return [test_pins, read_pins]


@pytest.fixture
def digital_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data
    This fixture accepts single pin in string format or
    multiple pins in list of string format"""
    digital_tsms = []
    for test_pin in test_pin_s:
        if isinstance(test_pin, str):
            digital_tsms.append(ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, test_pin))
        elif isinstance(test_pin, list):
            digital_tsms.append(ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, test_pin))
        else:
            assert False   # unexpected datatype
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
class TestNIDigital:
    """The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_tsm_initialize_sessions(self, tsm_context):
        """ This Api is used in the Init routine"""
        queried_sessions = list(tsm_context.get_all_nidigital_sessions())
        for session in queried_sessions:
            assert isinstance(session, nidigital.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_nidigital_instrument_names())

    def test_tsm_ssc_n_pins_to_m_sessions(self, digital_tsm_s, test_pin_s):
        """TSM SSC Digital N Pins To M Sessions.vi"""
        print(test_pin_s)
        assert isinstance(digital_tsm_s[0], ni_dt_digital.TSMDigital)
        assert isinstance(digital_tsm_s[1], ni_dt_digital.TSMDigital)

    def test_tsm_ssc_select_function(self, digital_tsm_s):
        """ TSM SSC Digital Select Function.vi
        Need to add logic to check back if the selected function is applied or not"""
        function_to_select = enums.SelectedFunction.DIGITAL
        temp_tsm = ni_dt_digital.tsm_ssc_select_function(digital_tsm_s[0], function_to_select)
        assert isinstance(temp_tsm, ni_dt_digital.TSMDigital)

    def test_tsm_ssc_write_read_static_loop_back_pin_low(self, digital_tsm_s):
        """TSM SSC Digital Write Static.vi
        This test writes data on one pin and reads back on another pin.
        digital_tsm_s[0] is write pin and digital_tsm_s[1] is read pin
        This test may pass on simulated device as low is the default value.
        Test with write ZERO and read Low
        """
        ni_dt_digital.tsm_ssc_select_function(digital_tsm_s[0], enums.SelectedFunction.DIGITAL)
        ni_dt_digital.tsm_ssc_write_static(digital_tsm_s[0], enums.WriteStaticPinState.ZERO)
        _, per_site_per_pin_data = ni_dt_digital.tsm_ssc_read_static(digital_tsm_s[1])
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert (per_pin_data == enums.PinState.L or per_pin_data == enums.PinState.M)

    def test_tsm_ssc_write_read_static_loop_back_pin_high(self, digital_tsm_s):
        """TSM SSC Digital Write Static.vi
        This test writes data on one pin and reads back on another pin.
        digital_tsm_s[0] is write pin and digital_tsm_s[1] is read pin
        Test with write ONE and read High
        """
        ni_dt_digital.tsm_ssc_select_function(digital_tsm_s[0], enums.SelectedFunction.DIGITAL)
        ni_dt_digital.tsm_ssc_write_static(digital_tsm_s[0], enums.WriteStaticPinState.ONE)
        _, per_site_per_pin_data = ni_dt_digital.tsm_ssc_read_static(digital_tsm_s[1])
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert per_pin_data == enums.PinState.H

    def test_tsm_ssc_write_read_static_same_pin_low(self, digital_tsm_s):
        """TSM SSC Digital Write Static.vi
         This test writes data on one pin and reads back on same pin.
         digital_tsm_s[0] is write pin and digital_tsm_s[0] is read pin
         Test with write ZERO and read Low
         """
        ni_dt_digital.tsm_ssc_select_function(digital_tsm_s[0], enums.SelectedFunction.DIGITAL)
        ni_dt_digital.tsm_ssc_write_static(digital_tsm_s[0], enums.WriteStaticPinState.ZERO)
        _, per_site_per_pin_data = ni_dt_digital.tsm_ssc_read_static(digital_tsm_s[0])
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert (per_pin_data == enums.PinState.L)

    def test_tsm_ssc_write_read_static_same_pin_high(self, digital_tsm_s):
        """TSM SSC Digital Write Static.vi
         This test writes data on one pin and reads back on same pin.
         digital_tsm_s[0] is write pin and digital_tsm_s[0] is read pin
         Test with write ONE and read High
         """
        ni_dt_digital.tsm_ssc_select_function(digital_tsm_s[0], enums.SelectedFunction.DIGITAL)
        ni_dt_digital.tsm_ssc_write_static(digital_tsm_s[0], enums.WriteStaticPinState.ONE)
        _, per_site_per_pin_data = ni_dt_digital.tsm_ssc_read_static(digital_tsm_s[0])
        for per_site_data in per_site_per_pin_data:
            for per_pin_data in per_site_data:
                assert isinstance(per_pin_data, enums.PinState)
                assert (per_pin_data == enums.PinState.H)

    @pytest.mark.skip
    def test_tsm_ssc_ppmu_source_voltage(self, digital_tsm_s):
        """TSM SSC Digital PPMU Source Voltage.vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_burst_pattern_pass_fail(self, digital_tsm_s):
        """TSM SSC Digital Burst Pattern [Pass Fail].vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_apply_levels_and_timing(self, digital_tsm_s):
        """TSM SSC Digital Apply Levels and Timing.vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_configure_time_set_period(self, digital_tsm_s):
        """TSM SSC Digital Configure Time Set Period.vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_write_sequencer_register(self, digital_tsm_s):
        """TSM SSC Digital Write Sequencer Register.vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_write_source_waveform_broadcast(self, digital_tsm_s):
        """TSM SSC Digital Write Source Waveform [Broadcast].vi"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_burst_pattern(self, digital_tsm_s):
        """To do"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_ppmu_source_voltage_per_site_per_pin(self, digital_tsm_s):
        """To do"""
        assert 1 == 1

    @pytest.mark.skip
    def test_tsm_ssc_get_properties(self, digital_tsm_s):
        pass


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
    ni_dt_digital.tsm_close_sessions(tsm_context)


@nitsm.codemoduleapi.code_module
def clock_generation(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    frequency = 25000
    ni_dt_digital.tsm_ssc_modify_time_set_for_clock_generation(tsm, frequency, 0.5, "time_set")
    ni_dt_digital.tsm_ssc_clock_generator_generate_clock(tsm, frequency)
    for ssc in tsm.ssc:
        assert ssc.session.channels[ssc.channel_list].clock_generator_is_running
        assert round(ssc.session.channels[ssc.channel_list].clock_generator_frequency) == frequency
    ni_dt_digital.tsm_ssc_clock_generator_abort(tsm)
    for ssc in tsm.ssc:
        assert not ssc.session.channels[ssc.channel_list].clock_generator_is_running


@nitsm.codemoduleapi.code_module
def configuration(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_clear_start_trigger_signal(tsm)
    ni_dt_digital.tsm_ssc_configure_trigger_signal(tsm, ni_dt_digital.PXI_TRIGGER_LINE.PXI_TRIG0)
    ni_dt_digital.tsm_ssc_select_function(tsm, enums.SelectedFunction.DIGITAL)
    ni_dt_digital.tsm_ssc_export_opcode_trigger_signal(
        tsm, ni_dt_digital.SIGNAL_ID.PATTERN_OPCODE_EVENT0, ni_dt_digital.PXI_TRIGGER_LINE.PXI_TRIG0
    )


@nitsm.codemoduleapi.code_module
def frequency_measurement_func(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_frequency_counter_configure_measurement_time(tsm, 0.5)
    (
        _,
        per_site_per_pin_frequency_measurements,
    ) = ni_dt_digital.tsm_ssc_frequency_counter_measure_frequency(tsm)
    assert isinstance(per_site_per_pin_frequency_measurements, list)
    assert numpy.shape(per_site_per_pin_frequency_measurements) == (3, 2)
    for frequency_measurements in per_site_per_pin_frequency_measurements:
        for frequency_measurement in frequency_measurements:
            assert isinstance(frequency_measurement, float)


@nitsm.codemoduleapi.code_module
def hram(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    hram_configuration = ni_dt_digital.HRAM_Configuration()
    hram_configuration.trigger_type = enums.HistoryRAMTriggerType.PATTERN_LABEL
    hram_configuration.pattern_label = "start_burst"
    hram_configuration.cycles_to_acquire = enums.HistoryRAMCyclesToAcquire.ALL
    ni_dt_digital.tsm_ssc_configure_hram(tsm, hram_configuration)
    _, hram_configuration = ni_dt_digital.tsm_ssc_get_hram_configuration(tsm)
    assert isinstance(hram_configuration, ni_dt_digital.HRAM_Configuration)
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
    ni_dt_digital.tsm_ssc_burst_pattern(tsm, "start_burst")
    ni_dt_digital.tsm_ssc_wait_until_done(tsm)
    _, per_site_cycle_information = ni_dt_digital.tsm_ssc_stream_hram_results(tsm)
    for cycle_information in per_site_cycle_information:
        assert not cycle_information
    _, files_generated = ni_dt_digital.tsm_ssc_log_hram_results(
        tsm,
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
def pattern_actions(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_abort(tsm)
    ni_dt_digital.tsm_ssc_burst_pattern(tsm, "start_burst")
    ni_dt_digital.tsm_ssc_wait_until_done(tsm)
    _, per_site_pass = ni_dt_digital.tsm_ssc_burst_pattern_pass_fail(tsm, "start_burst")
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (3,)
    for status in per_site_pass:
        assert isinstance(status, bool)
    _, per_site_per_pin_fail_counts = ni_dt_digital.tsm_ssc_get_fail_count(tsm)
    assert isinstance(per_site_per_pin_fail_counts, list)
    assert numpy.shape(per_site_per_pin_fail_counts) == (3, 2)
    for fail_counts in per_site_per_pin_fail_counts:
        for fail_count in fail_counts:
            assert isinstance(fail_count, int)
    _, per_site_pass = ni_dt_digital.tsm_ssc_get_site_pass_fail(tsm)
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (3,)
    for status in per_site_pass:
        assert isinstance(status, bool)


@nitsm.codemoduleapi.code_module
def pin_levels_and_timing(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_apply_levels_and_timing(tsm, "PinLevels", "Timing")
    ni_dt_digital.tsm_ssc_apply_tdr_offsets_per_site_per_pin(tsm, [[1e-9, 1e-9]] * 3)
    ni_dt_digital.tsm_ssc_apply_tdr_offsets(tsm, [[1e-9, 1e-9, 1e-9]] * 2)
    ni_dt_digital.tsm_ssc_configure_active_load(tsm, 0.0015, 0.0015, -0.0015)
    ni_dt_digital.tsm_ssc_configure_single_level_per_site(
        tsm, ni_dt_digital.LevelTypeToSet.VIL, [0.0015, 0.0015, 0.0015]
    )
    ni_dt_digital.tsm_ssc_configure_single_level(tsm, ni_dt_digital.LevelTypeToSet.VIL, 0.0015)
    ni_dt_digital.tsm_ssc_configure_termination_mode(tsm, enums.TerminationMode.HIGH_Z)
    ni_dt_digital.tsm_ssc_configure_time_set_compare_edge_per_site_per_pin(
        tsm, "time_set", [[40e-6, 40e-6]] * 3
    )
    ni_dt_digital.tsm_ssc_configure_time_set_compare_edge_per_site(tsm, "time_set", [40e-6, 40e-6, 40e-6])
    ni_dt_digital.tsm_ssc_configure_time_set_compare_edge(tsm, "time_set", 40e-6)
    ni_dt_digital.tsm_ssc_configure_voltage_levels(tsm, 0.0015, 0.0015, 0.0015, 0.0015, 0.0015)
    _, configured_period = ni_dt_digital.tsm_ssc_configure_time_set_period(tsm, "time_set", 40e-6)
    assert math.isclose(configured_period, 40e-6, abs_tol=5e-6)
    for ssc in tsm.ssc:
        assert math.isclose(
            ssc.session.channels[ssc.channel_list].active_load_ioh,
            -0.0015,
            abs_tol=5e-6,
        )
        assert math.isclose(
            ssc.session.channels[ssc.channel_list].active_load_iol, 0.0015, abs_tol=5e-6
        )
        assert math.isclose(
            ssc.session.channels[ssc.channel_list].active_load_vcom,
            0.0015,
            abs_tol=5e-6,
        )
        assert math.isclose(ssc.session.channels[ssc.channel_list].vih, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc.session.channels[ssc.channel_list].vil, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc.session.channels[ssc.channel_list].voh, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc.session.channels[ssc.channel_list].vol, 0.0015, abs_tol=5e-6)
        assert math.isclose(ssc.session.channels[ssc.channel_list].vterm, 0.0015, abs_tol=5e-6)
        assert ssc.session.channels[ssc.channel_list].tdr_offset.femtoseconds == 1000000


@nitsm.codemoduleapi.code_module
def ppmu(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_ppmu_configure_aperture_time(tsm, 0.01)
    ni_dt_digital.tsm_ssc_ppmu_configure_current_limit_range(tsm, 0.01)
    ni_dt_digital.tsm_ssc_ppmu_configure_voltage_limits(tsm, 0.01, 0.01)
    ni_dt_digital.tsm_ssc_ppmu_source_current(tsm, 0.01)
    ni_dt_digital.tsm_ssc_ppmu_source_voltage_per_site_per_pin(tsm, 0.01, [[0.01, 0.01]] * 3)
    ni_dt_digital.tsm_ssc_ppmu_source_voltage_per_site(tsm, 0.01, [0.01, 0.01, 0.01])
    ni_dt_digital.tsm_ssc_ppmu_source(tsm)
    _, per_site_per_pin_measurements = ni_dt_digital.tsm_ssc_ppmu_measure_current(tsm)
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (3, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)
    ni_dt_digital.tsm_ssc_ppmu_source_voltage(tsm, 0.01, 0.01)
    _, per_site_per_pin_measurements = ni_dt_digital.tsm_ssc_ppmu_measure_voltage(tsm)
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (3, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)


@nitsm.codemoduleapi.code_module
def sequencer_flags_and_registers(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_write_sequencer_flag(tsm, enums.SequencerFlag.FLAG1, True)
    ni_dt_digital.tsm_ssc_write_sequencer_register(tsm, enums.SequencerRegister.REGISTER1, 1)
    _, per_instrument_state = ni_dt_digital.tsm_ssc_read_sequencer_flag(tsm, enums.SequencerFlag.FLAG1)
    assert isinstance(per_instrument_state, list)
    assert numpy.shape(per_instrument_state) == (2,)
    for state in per_instrument_state:
        assert isinstance(state, bool)
    _, per_instrument_register_values = ni_dt_digital.tsm_ssc_read_sequencer_register(
        tsm, enums.SequencerRegister.REGISTER1
    )
    assert isinstance(per_instrument_register_values, list)
    assert numpy.shape(per_instrument_register_values) == (2,)
    for register_value in per_instrument_register_values:
        assert isinstance(register_value, int)


@nitsm.codemoduleapi.code_module
def session_properties_func(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    _, session_properties = ni_dt_digital.tsm_ssc_get_properties(tsm)
    for session_property in session_properties:
        assert session_property[0].startswith("DigitalPattern")
        assert math.isclose(session_property[1], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[2], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[3], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[4], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[5], 0.0015, abs_tol=5e-6)


@nitsm.codemoduleapi.code_module
def source_and_capture_waveforms(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_write_source_waveform_site_unique(
        tsm,
        "SourceWaveform_SiteUnique",
        [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]],
        True,
    )
    ni_dt_digital.tsm_ssc_write_source_waveform_broadcast(
        tsm, "SourceWaveform_Broadcast", [1, 2, 3, 4, 5], True
    )
    ni_dt_digital.tsm_ssc_burst_pattern(tsm, "start_capture")
    _, per_site_waveforms = ni_dt_digital.tsm_ssc_fetch_capture_waveform(tsm, "CaptureWaveform", 2)
    assert isinstance(per_site_waveforms, list)
    assert numpy.shape(per_site_waveforms) == (3, 2)
    for waveforms in per_site_waveforms:
        for waveform in waveforms:
            assert isinstance(waveform, int)


@nitsm.codemoduleapi.code_module
def static(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    ni_dt_digital.tsm_ssc_write_static(tsm, enums.WriteStaticPinState.ONE)
    ni_dt_digital.tsm_ssc_write_static_per_site(tsm, [enums.WriteStaticPinState.ONE] * 3)
    ni_dt_digital.tsm_ssc_write_static_per_site_per_pin(
        tsm, [[enums.WriteStaticPinState.ONE, enums.WriteStaticPinState.ONE]] * 3
    )
    _, per_site_per_pin_data = ni_dt_digital.tsm_ssc_read_static(tsm)
    assert isinstance(per_site_per_pin_data, list)
    assert numpy.shape(per_site_per_pin_data) == (3, 2)
    for data in per_site_per_pin_data:
        for _data in data:
            assert isinstance(_data, enums.PinState)


@nitsm.codemoduleapi.code_module
def misc(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = ni_dt_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    _tsm = ni_dt_digital.tsm_ssc_filter_sites(tsm, [0])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site0"
    _tsm = ni_dt_digital.tsm_ssc_filter_sites(tsm, [1])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site1"
    _tsm = ni_dt_digital.tsm_ssc_filter_sites(tsm, [2])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site2"
    ni_dt_digital.tsm_ssc_initiate(tsm)
    ni_dt_digital.tsm_ssc_abort(tsm)
    per_instrument_to_per_site_lut = ni_dt_digital._ssc_calculate_per_instrument_to_per_site_lut(
        tsm.ssc, tsm.site_numbers
    )
    per_site_data = ni_dt_digital._apply_lut_per_instrument_to_per_site(
        [False, False, False],
        per_instrument_to_per_site_lut,
        [[False, False, False], [True, True, True]],
    )
    assert per_site_data == [True, True, True]
    per_site_data = ni_dt_digital._apply_lut_per_instrument_to_per_site(
        [[False, False]] * 3,
        per_instrument_to_per_site_lut,
        [[[False, False]] * 3, [[True, True]] * 3],
    )
    assert per_site_data == [[True, True]] * 3
    per_instrument_to_per_site_per_pin_lut = (
        ni_dt_digital._ssc_calculate_per_instrument_to_per_site_per_pin_lut(
            tsm.ssc, tsm.site_numbers, tsm.pins_info
        )
    )
    per_site_per_pin_data = ni_dt_digital._apply_lut_per_instrument_to_per_site_per_pin(
        [[0, 0], [0, 0], [0, 0]],
        per_instrument_to_per_site_per_pin_lut,
        [[1, 2, 3], [4, 5, 6]],
    )
    assert per_site_per_pin_data == [[1, 4], [2, 5], [3, 6]]
    (
        per_site_to_per_instrument_lut,
        _,
        _,
    ) = ni_dt_digital._ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    per_instrument_data = ni_dt_digital._apply_lut_per_site_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]], per_site_to_per_instrument_lut, [1, 2, 3]
    )
    assert per_instrument_data == [[1, 2, 3], [0, 0, 0]]
    (
        per_site_per_pin_to_per_instrument_lut,
        _,
        _,
    ) = ni_dt_digital._ssc_calculate_per_site_per_pin_to_per_instrument_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins_info
    )
    per_instrument_data = ni_dt_digital._apply_lut_per_site_per_pin_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]],
        per_site_per_pin_to_per_instrument_lut,
        [[1, 4], [2, 5], [3, 6]],
    )
    assert per_instrument_data == [[1, 2, 3], [4, 5, 6]]
    ni_dt_digital.tsm_ssc_publish(tsm, [1.0, 1.0, 1.0], "Publish_1")
    ni_dt_digital.tsm_ssc_publish(tsm, [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], "Publish_2")
    ni_dt_digital.tsm_ssc_publish(tsm, [True, True, True], "Publish_3")
    ni_dt_digital.tsm_ssc_publish(tsm, [[True, True], [True, True], [True, True]], "Publish_4")