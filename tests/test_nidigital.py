import pytest
import typing
import os
import math
import numpy
import digital
import nitsm.codemoduleapi
from nidigital import enums
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext


OPTIONS = "Simulate = true, DriverSetup = Model : 6570"


@pytest.mark.sequence_file("nidigital.seq")
def test_nidigital(system_test_runner):
    assert system_test_runner.run()


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: SemiconductorModuleContext):
    digital.tsm_initialize_sessions(tsm_context, OPTIONS)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
    digital.tsm_close_sessions(tsm_context)


@nitsm.codemoduleapi.code_module
def clock_generation(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    frequency = 25000
    digital.tsm_ssc_modify_time_set_for_clock_generation(tsm, frequency, 0.5, "time_set")
    digital.tsm_ssc_clock_generator_generate_clock(tsm, frequency)
    for ssc in tsm.ssc:
        assert ssc.session.channels[ssc.channel_list].clock_generator_is_running == True
        assert round(ssc.session.channels[ssc.channel_list].clock_generator_frequency) == frequency
    digital.tsm_ssc_clock_generator_abort(tsm)
    for ssc in tsm.ssc:
        assert ssc.session.channels[ssc.channel_list].clock_generator_is_running == False


@nitsm.codemoduleapi.code_module
def configuration(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_clear_start_trigger_signal(tsm)
    digital.tsm_ssc_configure_trigger_signal(tsm, digital.PXI_TRIGGER_LINE.PXI_TRIG0)
    digital.tsm_ssc_select_function(tsm, enums.SelectedFunction.DIGITAL)
    digital.tsm_ssc_export_opcode_trigger_signal(
        tsm, digital.SIGNAL_ID.PATTERN_OPCODE_EVENT0, digital.PXI_TRIGGER_LINE.PXI_TRIG0
    )


@nitsm.codemoduleapi.code_module
def frequency_measurement(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_frequency_counter_configure_measurement_time(tsm, 0.5)
    (
        _,
        per_site_per_pin_frequency_measurements,
    ) = digital.tsm_ssc_frequency_counter_measure_frequency(tsm)
    assert isinstance(per_site_per_pin_frequency_measurements, list)
    assert numpy.shape(per_site_per_pin_frequency_measurements) == (3, 2)
    for frequency_measurements in per_site_per_pin_frequency_measurements:
        for frequency_measurement in frequency_measurements:
            assert isinstance(frequency_measurement, float)


@nitsm.codemoduleapi.code_module
def hram(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    hram_configuration = digital.HRAM_Configuration()
    hram_configuration.trigger_type = enums.HistoryRAMTriggerType.PATTERN_LABEL
    hram_configuration.pattern_label = "start_burst"
    hram_configuration.cycles_to_acquire = enums.HistoryRAMCyclesToAcquire.ALL
    digital.tsm_ssc_configure_hram(tsm, hram_configuration)
    _, hram_configuration = digital.tsm_ssc_get_hram_configuration(tsm)
    assert isinstance(hram_configuration, digital.HRAM_Configuration)
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
    digital.tsm_ssc_burst_pattern(tsm, "start_burst")
    digital.tsm_ssc_wait_until_done(tsm)
    _, per_site_cycle_information = digital.tsm_ssc_stream_hram_results(tsm)
    for cycle_informations in per_site_cycle_information:
        assert not cycle_informations
    _, files_generated = digital.tsm_ssc_log_hram_results(
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
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_abort(tsm)
    digital.tsm_ssc_burst_pattern(tsm, "start_burst")
    digital.tsm_ssc_wait_until_done(tsm)
    _, per_site_pass = digital.tsm_ssc_burst_pattern_pass_fail(tsm, "start_burst")
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (3,)
    for status in per_site_pass:
        assert isinstance(status, bool)
    _, per_site_per_pin_fail_counts = digital.tsm_ssc_get_fail_count(tsm)
    assert isinstance(per_site_per_pin_fail_counts, list)
    assert numpy.shape(per_site_per_pin_fail_counts) == (3, 2)
    for fail_counts in per_site_per_pin_fail_counts:
        for fail_count in fail_counts:
            assert isinstance(fail_count, int)
    _, per_site_pass = digital.tsm_ssc_get_site_pass_fail(tsm)
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (3,)
    for status in per_site_pass:
        assert isinstance(status, bool)


@nitsm.codemoduleapi.code_module
def pin_levels_and_timing(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_apply_levels_and_timing(tsm, "PinLevels", "Timing")
    digital.tsm_ssc_apply_tdr_offsets_per_site_per_pin(tsm, [[1e-9, 1e-9]] * 3)
    digital.tsm_ssc_apply_tdr_offsets(tsm, [[1e-9, 1e-9, 1e-9]] * 2)
    digital.tsm_ssc_configure_active_load(tsm, 0.0015, 0.0015, -0.0015)
    digital.tsm_ssc_configure_single_level_per_site(
        tsm, digital.LevelTypeToSet.VIL, [0.0015, 0.0015, 0.0015]
    )
    digital.tsm_ssc_configure_single_level(tsm, digital.LevelTypeToSet.VIL, 0.0015)
    digital.tsm_ssc_configure_termination_mode(tsm, enums.TerminationMode.HIGH_Z)
    digital.tsm_ssc_configure_time_set_compare_edge_per_site_per_pin(
        tsm, "time_set", [[40e-6, 40e-6]] * 3
    )
    digital.tsm_ssc_configure_time_set_compare_edge_per_site(tsm, "time_set", [40e-6, 40e-6, 40e-6])
    digital.tsm_ssc_configure_time_set_compare_edge(tsm, "time_set", 40e-6)
    digital.tsm_ssc_configure_voltage_levels(tsm, 0.0015, 0.0015, 0.0015, 0.0015, 0.0015)
    _, configured_period = digital.tsm_ssc_configure_time_set_period(tsm, "time_set", 40e-6)
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
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_ppmu_configure_aperture_time(tsm, 0.01)
    digital.tsm_ssc_ppmu_configure_current_limit_range(tsm, 0.01)
    digital.tsm_ssc_ppmu_configure_voltage_limits(tsm, 0.01, 0.01)
    digital.tsm_ssc_ppmu_source_current(tsm, 0.01)
    digital.tsm_ssc_ppmu_source_voltage_per_site_per_pin(tsm, 0.01, [[0.01, 0.01]] * 3)
    digital.tsm_ssc_ppmu_source_voltage_per_site(tsm, 0.01, [0.01, 0.01, 0.01])
    digital.tsm_ssc_ppmu_source(tsm)
    _, per_site_per_pin_measurements = digital.tsm_ssc_ppmu_measure_current(tsm)
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (3, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)
    digital.tsm_ssc_ppmu_source_voltage(tsm, 0.01, 0.01)
    _, per_site_per_pin_measurements = digital.tsm_ssc_ppmu_measure_voltage(tsm)
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (3, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)


@nitsm.codemoduleapi.code_module
def sequencer_flags_and_registers(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_write_sequencer_flag(tsm, enums.SequencerFlag.FLAG1, True)
    digital.tsm_ssc_write_sequencer_register(tsm, enums.SequencerRegister.REGISTER1, 1)
    _, per_instrument_state = digital.tsm_ssc_read_sequencer_flag(tsm, enums.SequencerFlag.FLAG1)
    assert isinstance(per_instrument_state, list)
    assert numpy.shape(per_instrument_state) == (2,)
    for state in per_instrument_state:
        assert isinstance(state, bool)
    _, per_instrument_register_values = digital.tsm_ssc_read_sequencer_register(
        tsm, enums.SequencerRegister.REGISTER1
    )
    assert isinstance(per_instrument_register_values, list)
    assert numpy.shape(per_instrument_register_values) == (2,)
    for register_value in per_instrument_register_values:
        assert isinstance(register_value, int)


@nitsm.codemoduleapi.code_module
def session_properties(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    _, session_properties = digital.tsm_ssc_get_properties(tsm)
    for session_property in session_properties:
        assert session_property[0].startswith("DigitalPattern")
        assert math.isclose(session_property[1], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[2], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[3], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[4], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[5], 0.0015, abs_tol=5e-6)


@nitsm.codemoduleapi.code_module
def source_and_capture_waveforms(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_write_source_waveform_site_unique(
        tsm,
        "SourceWaveform_SiteUnique",
        [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]],
        True,
    )
    digital.tsm_ssc_write_source_waveform_broadcast(
        tsm, "SourceWaveform_Broadcast", [1, 2, 3, 4, 5], True
    )
    digital.tsm_ssc_burst_pattern(tsm, "start_capture")
    _, per_site_waveforms = digital.tsm_ssc_fetch_capture_waveform(tsm, "CaptureWaveform", 2)
    assert isinstance(per_site_waveforms, list)
    assert numpy.shape(per_site_waveforms) == (3, 2)
    for waveforms in per_site_waveforms:
        for waveform in waveforms:
            assert isinstance(waveform, int)


@nitsm.codemoduleapi.code_module
def static(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    digital.tsm_ssc_write_static(tsm, enums.WriteStaticPinState.ONE)
    digital.tsm_ssc_write_static_per_site(tsm, [enums.WriteStaticPinState.ONE] * 3)
    digital.tsm_ssc_write_static_per_site_per_pin(
        tsm, [[enums.WriteStaticPinState.ONE, enums.WriteStaticPinState.ONE]] * 3
    )
    _, per_site_per_pin_data = digital.tsm_ssc_read_static(tsm)
    assert isinstance(per_site_per_pin_data, list)
    assert numpy.shape(per_site_per_pin_data) == (3, 2)
    for data in per_site_per_pin_data:
        for _data in data:
            assert isinstance(_data, enums.PinState)


@nitsm.codemoduleapi.code_module
def misc(tsm_context: SemiconductorModuleContext, pins: typing.List[str]):
    tsm = digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, pins[0])

    _tsm = digital.tsm_ssc_filter_sites(tsm, [0])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site0"
    _tsm = digital.tsm_ssc_filter_sites(tsm, [1])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site1"
    _tsm = digital.tsm_ssc_filter_sites(tsm, [2])
    for ssc in _tsm.ssc:
        assert ssc.site_list == "site2"
    digital.tsm_ssc_initiate(tsm)
    digital.tsm_ssc_abort(tsm)
    per_instrument_to_per_site_lut = digital._ssc_calculate_per_instrument_to_per_site_lut(
        tsm.ssc, tsm.site_numbers
    )
    per_site_data = digital._apply_lut_per_instrument_to_per_site(
        [False, False, False],
        per_instrument_to_per_site_lut,
        [[False, False, False], [True, True, True]],
    )
    assert per_site_data == [True, True, True]
    per_site_data = digital._apply_lut_per_instrument_to_per_site(
        [[False, False]] * 3,
        per_instrument_to_per_site_lut,
        [[[False, False]] * 3, [[True, True]] * 3],
    )
    assert per_site_data == [[True, True]] * 3
    per_instrument_to_per_site_per_pin_lut = (
        digital._ssc_calculate_per_instrument_to_per_site_per_pin_lut(
            tsm.ssc, tsm.site_numbers, tsm.pins_info
        )
    )
    per_site_per_pin_data = digital._apply_lut_per_instrument_to_per_site_per_pin(
        [[0, 0], [0, 0], [0, 0]],
        per_instrument_to_per_site_per_pin_lut,
        [[1, 2, 3], [4, 5, 6]],
    )
    assert per_site_per_pin_data == [[1, 4], [2, 5], [3, 6]]
    (
        per_site_to_per_instrument_lut,
        _,
        _,
    ) = digital._ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    per_instrument_data = digital._apply_lut_per_site_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]], per_site_to_per_instrument_lut, [1, 2, 3]
    )
    assert per_instrument_data == [[1, 2, 3], [0, 0, 0]]
    (
        per_site_per_pin_to_per_instrument_lut,
        _,
        _,
    ) = digital._ssc_calculate_per_site_per_pin_to_per_instrument_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins_info
    )
    per_instrument_data = digital._apply_lut_per_site_per_pin_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]],
        per_site_per_pin_to_per_instrument_lut,
        [[1, 4], [2, 5], [3, 6]],
    )
    assert per_instrument_data == [[1, 2, 3], [4, 5, 6]]
    digital.tsm_ssc_publish(tsm, [1.0, 1.0, 1.0], "Publish_1")
    digital.tsm_ssc_publish(tsm, [[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], "Publish_2")
    digital.tsm_ssc_publish(tsm, [True, True, True], "Publish_3")
    digital.tsm_ssc_publish(tsm, [[True, True], [True, True], [True, True]], "Publish_4")
