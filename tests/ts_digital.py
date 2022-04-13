import ctypes
import math
import os
import os.path
import typing

from nidigital import enums
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nitsm.codemoduleapi
import nitsm.enums
import numpy


import nidevtools.digital as dt_dpi


OPTIONS = {}


@nitsm.codemoduleapi.code_module
def open_sessions(tsm: SMContext):
    dt_dpi.initialize_sessions(tsm, options=OPTIONS)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    dt_dpi.close_sessions(tsm)


@nitsm.codemoduleapi.code_module
def clock_generation(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    frequency = 25000
    dpi_pin1.ssc.modify_time_set_for_clock_generation(frequency, 0.5, "time_set")
    dpi_pin1.ssc.clock_generator_generate_clock(frequency)
    for ssc in dpi_pin1.ssc.sessions_sites_channels:
        assert ssc._channels_session.clock_generator_is_running
        assert round(ssc._channels_session.clock_generator_frequency) == frequency
    dpi_pin1.ssc.clock_generator_abort()
    for ssc in dpi_pin1.ssc.sessions_sites_channels:
        assert not ssc._channels_session.clock_generator_is_running


@nitsm.codemoduleapi.code_module
def configuration(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.clear_start_trigger_signal()
    dpi_pin1.ssc.configure_trigger_signal(dt_dpi.PXI_TRIGGER_LINE.PXI_TRIG0)
    dpi_pin1.ssc.select_function(enums.SelectedFunction.DIGITAL)
    dpi_pin1.ssc.export_opcode_trigger_signal(
        dt_dpi.SIGNAL_ID.PATTERN_OPCODE_EVENT0, dt_dpi.PXI_TRIGGER_LINE.PXI_TRIG0
    )


@nitsm.codemoduleapi.code_module
def frequency_measurement_func(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.frequency_counter_configure_measurement_time(0.5)
    per_site_per_pin_frequency_measurements = dpi_pin1.frequency_counter_measure_frequency()
    assert isinstance(per_site_per_pin_frequency_measurements, list)
    print(numpy.shape(per_site_per_pin_frequency_measurements))
    assert numpy.shape(per_site_per_pin_frequency_measurements) == (1, 2)
    for frequency_measurements in per_site_per_pin_frequency_measurements:
        for frequency_measurement in frequency_measurements:
            assert isinstance(frequency_measurement, float)


@nitsm.codemoduleapi.code_module
def hram(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    hram_configuration = dt_dpi.HRAMConfiguration()
    hram_configuration.trigger_type = enums.HistoryRAMTriggerType.PATTERN_LABEL
    hram_configuration.pattern_label = "start_burst"
    hram_configuration.cycles_to_acquire = enums.HistoryRAMCyclesToAcquire.ALL
    dpi_pin1.ssc.configure_hram(hram_configuration)
    hram_configuration = dpi_pin1.get_hram_configuration()
    dpi_pin1.ssc.burst_pattern("start_burst")
    dpi_pin1.ssc.wait_until_done()
    per_site_cycle_information = dpi_pin1.stream_hram_results()
    for cycle_information in per_site_cycle_information:
        assert not cycle_information
    files_generated = dpi_pin1.log_hram_results(
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
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])

    dpi_pin1.ssc.abort()
    dpi_pin1.ssc.burst_pattern("start_burst")
    dpi_pin1.ssc.wait_until_done()
    per_site_pass = dpi_pin1.burst_pattern_pass_fail("start_burst")
    assert isinstance(per_site_pass, list)
    print(numpy.shape(per_site_pass))
    assert numpy.shape(per_site_pass) == (1,)
    for status in per_site_pass:
        assert isinstance(status, bool)
    per_site_per_pin_fail_counts = dpi_pin1.get_fail_count()
    assert isinstance(per_site_per_pin_fail_counts, list)
    print(numpy.shape(per_site_per_pin_fail_counts))
    assert numpy.shape(per_site_per_pin_fail_counts) == (1, 2)
    for fail_counts in per_site_per_pin_fail_counts:
        for fail_count in fail_counts:
            assert isinstance(fail_count, int)
    per_site_pass = dpi_pin1.get_site_pass_fail()
    assert isinstance(per_site_pass, list)
    assert numpy.shape(per_site_pass) == (1,)
    for status in per_site_pass:
        assert isinstance(status, bool)


@nitsm.codemoduleapi.code_module
def pin_levels_and_timing(tsm: SMContext, pins: typing.List[str]):
    # ctypes.windll.user32.MessageBoxW(None, "niPythonHost Process ID:" + str(os.getpid()), "Attach debugger", 0)
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.apply_levels_and_timing("PinLevels", "Timing")
    dpi_pin1.apply_tdr_offsets_per_site_per_pin(
        [
            [
                1e-9,
            ]
        ]
        * 3
    )
    dpi_pin1.ssc.apply_tdr_offsets(
        [
            [
                1e-9,
                1e-9,
            ]
        ]
        * 1,
    )
    dpi_pin1.ssc.configure_active_load(0.0015, 0.0015, -0.0015)
    dpi_pin1.configure_single_level_per_site(dt_dpi.LevelTypeToSet.VIL, [0.0015, 0.0015, 0.0015])
    dpi_pin1.ssc.configure_single_level(dt_dpi.LevelTypeToSet.VIL, 0.0015)
    dpi_pin1.ssc.configure_termination_mode(enums.TerminationMode.HIGH_Z)
    dpi_pin1.configure_time_set_compare_edge_per_site_per_pin(
        "time_set",
        [
            [
                40e-6,
            ]
        ]
        * 3,
    )
    dpi_pin1.configure_time_set_compare_edge_per_site("time_set", [40e-6, 40e-6, 40e-6])
    dpi_pin1.ssc.configure_time_set_compare_edge("time_set", 40e-6)
    dpi_pin1.ssc.configure_voltage_levels(0.0015, 0.0015, 0.0015, 0.0015, 0.0015)
    configured_period = dpi_pin1.ssc.configure_time_set_period("time_set", 40e-6)
    assert math.isclose(configured_period, 40e-6, abs_tol=5e-6)
    for ssc in dpi_pin1.ssc.sessions_sites_channels:
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
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.ppmu_configure_aperture_time(0.01)
    dpi_pin1.ssc.ppmu_configure_current_limit_range(0.01)
    dpi_pin1.ssc.ppmu_configure_voltage_limits(0.01, 0.01)
    dpi_pin1.ssc.ppmu_source_current(0.01)
    dpi_pin1.ssc.ppmu_source_voltage_per_site_per_pin(0.01, [[0.01, 0.01]] * 3)
    dpi_pin1.ppmu_source_voltage_per_site(0.01, [0.01, 0.01, 0.01])
    dpi_pin1.ssc.ppmu_source()
    per_site_per_pin_measurements = dpi_pin1.ppmu_measure_current()
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (1, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)
    dpi_pin1.ssc.ppmu_source_voltage(0.01, 0.01)
    per_site_per_pin_measurements = dpi_pin1.ppmu_measure_voltage()
    assert isinstance(per_site_per_pin_measurements, list)
    assert numpy.shape(per_site_per_pin_measurements) == (1, 2)
    for measurements in per_site_per_pin_measurements:
        for measurement in measurements:
            assert isinstance(measurement, float)


@nitsm.codemoduleapi.code_module
def sequencer_flags_and_registers(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.write_sequencer_flag(enums.SequencerFlag.FLAG1, True)
    dpi_pin1.ssc.write_sequencer_register(enums.SequencerRegister.REGISTER1, 1)
    per_instrument_state = dpi_pin1.ssc.read_sequencer_flag(enums.SequencerFlag.FLAG1)
    assert isinstance(per_instrument_state, list)
    assert numpy.shape(per_instrument_state) == (1,)
    for state in per_instrument_state:
        assert isinstance(state, bool)
    per_instrument_register_values = dpi_pin1.ssc.read_sequencer_register(
        enums.SequencerRegister.REGISTER1
    )
    assert isinstance(per_instrument_register_values, list)
    assert numpy.shape(per_instrument_register_values) == (1,)
    for register_value in per_instrument_register_values:
        assert isinstance(register_value, int)


@nitsm.codemoduleapi.code_module
def session_properties_func(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    session_properties = dpi_pin1.ssc.get_properties()
    for session_property in session_properties:
        assert session_property[0].startswith("DPI")
        assert math.isclose(session_property[1], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[2], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[3], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[4], 0.0015, abs_tol=5e-6)
        assert math.isclose(session_property[5], 0.0015, abs_tol=5e-6)


@nitsm.codemoduleapi.code_module
def source_and_capture_waveforms(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.write_source_waveform_site_unique(
        "SourceWaveform_SiteUnique", [[1, 2, 3, 4, 5], [1, 2, 3, 4, 5], [1, 2, 3, 4, 5]], True
    )
    dpi_pin1.ssc.write_source_waveform_broadcast("SourceWaveform", [1, 2, 3, 4, 5], True)
    dpi_pin1.ssc.burst_pattern("start_capture")
    per_site_waveforms = dpi_pin1.fetch_capture_waveform("CaptureWaveform", 2)
    assert isinstance(per_site_waveforms, list)
    assert numpy.shape(per_site_waveforms) == (3, 2)
    for waveforms in per_site_waveforms:
        for waveform in waveforms:
            assert isinstance(waveform, int)


@nitsm.codemoduleapi.code_module
def static(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.write_static(enums.WriteStaticPinState.ONE)
    dpi_pin1.write_static_per_site([enums.WriteStaticPinState.ONE] * 3)
    dpi_pin1.write_static_per_site_per_pin(
        [[enums.WriteStaticPinState.ONE, enums.WriteStaticPinState.ONE]] * 3
    )
    per_site_per_pin_data = dpi_pin1.read_static()
    assert isinstance(per_site_per_pin_data, list)
    print(numpy.shape(per_site_per_pin_data))
    assert numpy.shape(per_site_per_pin_data) == (1, 2)
    for data in per_site_per_pin_data:
        for _data in data:
            assert isinstance(_data, enums.PinState)


@nitsm.codemoduleapi.code_module
def misc(tsm: SMContext, pins: typing.List[str]):
    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin11 = dt_dpi.filter_sites(dpi_pin1, [0])
    for ssc in dpi_pin11.ssc.sessions_sites_channels:
        assert ssc._pins == "site0"
    dpi_pin11 = dt_dpi.filter_sites(dpi_pin1, [1])
    for ssc in dpi_pin11.ssc.sessions_sites_channels:
        assert ssc.site_list == "site1"
    dpi_pin11 = dt_dpi.filter_sites(dpi_pin1, [2])
    for ssc in dpi_pin11.ssc.sessions_sites_channels:
        assert ssc.site_list == "site2"

    dpi_pin1 = dt_dpi.pins_to_sessions(tsm, pins[0])
    dpi_pin1.ssc.initiate()
    dpi_pin1.ssc.abort()
    per_instrument_to_per_site_lut = dpi_pin1.ssc.calculate_per_instrument_to_per_site_lut(
        dpi_pin1.sites
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
        dpi_pin1.ssc.calculate_per_instrument_to_per_site_per_pin_lut(dpi_pin1.sites, dpi_pin1.pins)
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
    ) = dpi_pin1.ssc.calculate_per_site_to_per_instrument_lut(dpi_pin1.sites)
    per_instrument_data = dt_dpi._apply_lut_per_site_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]], per_site_to_per_instrument_lut, [1, 2, 3]
    )
    # assert per_instrument_data == [[1, 2, 3], [0, 0, 0]]
    print(per_instrument_data)
    (
        per_site_per_pin_to_per_instrument_lut,
        _,
        _,
    ) = dpi_pin1.ssc.calculate_per_site_per_pin_to_per_instrument_lut(dpi_pin1.sites, dpi_pin1.pins)
    per_instrument_data = dt_dpi._apply_lut_per_site_per_pin_to_per_instrument(
        [[0, 0, 0], [0, 0, 0]],
        per_site_per_pin_to_per_instrument_lut,
        [[1, 4], [2, 5], [3, 6]],
    )
    # assert per_instrument_data == [[1, 2, 3], [4, 5, 6]]
    print(per_instrument_data)
    # dpi_pin1.publish([1.0, 1.0, 1.0], "Publish_1")
    dpi_pin1.publish([[1.0, 1.0, 1.0]], "Publish_1")
    dpi_pin1.publish([[1.0, 1.0], [1.0, 1.0], [1.0, 1.0]], "Publish_2")
    # dpi_pin1.publish([True, True, True], "Publish_3")
    dpi_pin1.publish([[True, True, True]], "Publish_3")
    dpi_pin1.publish([[True, True], [True, True], [True, True]], "Publish_4")

