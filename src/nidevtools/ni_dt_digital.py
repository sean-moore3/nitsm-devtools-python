import re
import typing
import os
import copy
import numpy
import nidigital
from enum import Enum
from nidigital import enums
from datetime import datetime
from nidigital.history_ram_cycle_information import HistoryRAMCycleInformation
from nitsm.codemoduleapi import SemiconductorModuleContext


class SSCDigital(typing.NamedTuple):
    session: nidigital.Session
    channel_list: str
    site_list: str


class TSMDigital(typing.NamedTuple):
    pin_query_context: typing.Any
    ssc: typing.List[SSCDigital]
    site_numbers: typing.List[int]
    pins: typing.List[str]


class Location_1D_Array(typing.NamedTuple):
    location_1d_array: typing.List[int]


class Location_2D(typing.NamedTuple):
    row: int
    col: int


class Location_2D_Array(typing.NamedTuple):
    location_2d_array: typing.List[Location_2D]


class Session_Properties(typing.NamedTuple):
    instrument_name: str
    voh: float
    vol: float
    vih: float
    vil: float
    vterm: float
    measurement_time: float


class LevelTypeToSet(Enum):
    VIL = 0
    VIH = 1
    VOL = 2
    VOH = 3
    VTERM = 4
    LOL = 5
    LOH = 6
    VCOM = 7


class HRAM_Configuration:
    finite_samples: bool = True
    cycles_to_acquire: enums.HistoryRAMCyclesToAcquire = enums.HistoryRAMCyclesToAcquire.FAILED
    max_samples_to_acquire_per_site: int = 8191
    buffer_size_per_site: int = 32000
    pretrigger_samples: int = 0
    trigger_type: enums.HistoryRAMTriggerType = enums.HistoryRAMTriggerType.FIRST_FAILURE
    cycle_number: int = 0
    pattern_label: str = ""
    vector_offset: int = 0
    cycle_offset: int = 0


class PXITriggerLine(typing.NamedTuple):
    NONE: str
    PXI_TRIG0: str
    PXI_TRIG1: str
    PXI_TRIG2: str
    PXI_TRIG3: str
    PXI_TRIG4: str
    PXI_TRIG5: str
    PXI_TRIG6: str
    PXI_TRIG7: str


PXI_TRIGGER_LINE = PXITriggerLine(
    "",
    "PXI_Trig0",
    "PXI_Trig1",
    "PXI_Trig2",
    "PXI_Trig3",
    "PXI_Trig4",
    "PXI_Trig5",
    "PXI_Trig6",
    "PXI_Trig7",
)


class SignalId(typing.NamedTuple):
    PATTERN_OPCODE_EVENT0: str
    PATTERN_OPCODE_EVENT1: str
    PATTERN_OPCODE_EVENT2: str
    PATTERN_OPCODE_EVENT3: str


SIGNAL_ID = SignalId(
    "patternOpcodeEvent0",
    "patternOpcodeEvent1",
    "patternOpcodeEvent2",
    "patternOpcodeEvent3",
)


# Clock Generation #
def tsm_ssc_clock_generator_abort(tsm: TSMDigital):
    _ssc_clock_generator_abort(tsm.ssc)
    return tsm


def tsm_ssc_clock_generator_generate_clock(
    tsm: TSMDigital, frequency: float, select_digital_function: bool = True
):
    _ssc_clock_generator_generate_clock(tsm.ssc, frequency, select_digital_function)
    return tsm


def tsm_ssc_modify_time_set_for_clock_generation(
    tsm: TSMDigital, frequency: float, duty_cycle: float, time_set: str
):
    _ssc_modify_time_set_for_clock_generation(tsm.ssc, frequency, duty_cycle, time_set)
    return tsm


# End of Clock Generation #


# Configuration #
def tsm_ssc_clear_start_trigger_signal(tsm: TSMDigital):
    _ssc_clear_start_trigger_signal(tsm.ssc)
    return tsm


def tsm_ssc_configure_trigger_signal(
    tsm: TSMDigital, source: str, edge: enums.DigitalEdge = enums.DigitalEdge.RISING
):
    _ssc_configure_trigger_signal(tsm.ssc, source, edge)
    return tsm


def tsm_ssc_select_function(tsm: TSMDigital, function: enums.SelectedFunction):
    _ssc_select_function(tsm.ssc, function)
    return tsm


def tsm_ssc_export_opcode_trigger_signal(
    tsm: TSMDigital, signal_id: str, output_terminal: str = ""
):
    _ssc_export_opcode_trigger_signal(tsm.ssc, signal_id, output_terminal)
    return tsm


# End of Configuration #


# Frequency Measurement #
def tsm_ssc_frequency_counter_configure_measurement_time(tsm: TSMDigital, measurement_time: float):
    _ssc_frequency_counter_configure_measurement_time(tsm.ssc, measurement_time)
    return tsm


def tsm_ssc_frequency_counter_measure_frequency(tsm: TSMDigital):
    initialized_array = [[0.0 for _ in tsm.pins] for _ in tsm.site_numbers]
    per_instrument_to_per_site_per_pin_lut = _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins
    )
    _, per_instrument_frequencies = _ssc_frequency_counter_measure_frequency(tsm.ssc)
    per_site_per_pin_frequency_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
        initialized_array,
        per_instrument_to_per_site_per_pin_lut,
        per_instrument_frequencies,
    )
    return tsm, per_site_per_pin_frequency_measurements


# End of Frequency Measurement #


# HRAM #
def tsm_ssc_configure_hram(
    tsm: TSMDigital, hram_configuration: HRAM_Configuration = HRAM_Configuration()
):
    number_of_samples_is_finite = hram_configuration.finite_samples
    cycles_to_acquire = hram_configuration.cycles_to_acquire
    pretrigger_samples = hram_configuration.pretrigger_samples
    buffer_size_per_site = hram_configuration.buffer_size_per_site
    max_samples_to_acquire_per_site = hram_configuration.max_samples_to_acquire_per_site
    triggers_type = hram_configuration.trigger_type
    cycle_number = hram_configuration.cycle_number
    pattern_label = hram_configuration.pattern_label
    cycle_offset = hram_configuration.cycle_offset
    vector_offset = hram_configuration.vector_offset
    _ssc_configure_hram_settings(
        tsm.ssc,
        cycles_to_acquire,
        pretrigger_samples,
        max_samples_to_acquire_per_site,
        number_of_samples_is_finite,
        buffer_size_per_site,
    )
    _ssc_configure_hram_trigger(
        tsm.ssc, triggers_type, cycle_number, pattern_label, cycle_offset, vector_offset
    )
    return tsm


def tsm_ssc_get_hram_configuration(tsm: TSMDigital):
    (
        _,
        per_instrument_cycles_to_acquire,
        per_instrument_pretrigger_samples,
        per_instrument_max_samples_to_acquire_per_site,
        per_instrument_number_of_samples_is_finite,
        per_instrument_buffer_size_per_site,
    ) = _ssc_get_hram_settings(tsm.ssc)
    (
        _,
        per_instrument_triggers_type,
        per_instrument_cycle_number,
        per_instrument_pattern_label,
        per_instrument_cycle_offset,
        per_instrument_vector_offset,
    ) = _ssc_get_hram_trigger_settings(tsm.ssc)
    # Assumes all instruments have the same settings
    hram_configuration: HRAM_Configuration = HRAM_Configuration()
    hram_configuration.finite_samples = per_instrument_number_of_samples_is_finite[-1]
    hram_configuration.trigger_type = per_instrument_triggers_type[-1]
    hram_configuration.cycle_number = per_instrument_cycle_number[-1]
    hram_configuration.pattern_label = per_instrument_pattern_label[-1]
    hram_configuration.vector_offset = per_instrument_vector_offset[-1]
    hram_configuration.cycle_offset = per_instrument_cycle_offset[-1]
    hram_configuration.cycles_to_acquire = per_instrument_cycles_to_acquire[-1]
    hram_configuration.pretrigger_samples = per_instrument_pretrigger_samples[-1]
    hram_configuration.buffer_size_per_site = per_instrument_buffer_size_per_site[-1]
    hram_configuration.max_samples_to_acquire_per_site = (
        per_instrument_max_samples_to_acquire_per_site[-1]
    )
    return tsm, hram_configuration


def tsm_ssc_log_hram_results(
    tsm: TSMDigital,
    per_site_cycle_information: typing.List[typing.List[HistoryRAMCycleInformation]],
    pattern_name: str,
    destination_dir: str,
):
    if not os.path.exists(destination_dir):
        os.mkdir(destination_dir)
    os.chdir(destination_dir)
    files_generated: typing.List[str] = []
    for cycle_informations, site_number in zip(per_site_cycle_information, tsm.site_numbers):
        results: typing.List[typing.List[typing.Any]] = []
        if not cycle_informations or all(
            [not cycle_information.per_pin_pass_fail for cycle_information in cycle_informations]
        ):
            results.append(["PATTERN PASSED - NO FAILURES"])
        else:
            for cycle_information in cycle_informations:
                results.append(
                    [
                        str(cycle_information.vector_number),
                        cycle_information.time_set_name,
                        str(cycle_information.cycle_number),
                        str(cycle_information.scan_cycle_number),
                        str(
                            (lambda x: "P" if x else "F")(
                                all(cycle_information.per_pin_pass_fail)
                            )
                        ),
                        "{" + ",".join(tsm.pins) + "}",
                        "{"
                        + ",".join(
                            [
                                (lambda x: "P" if x is True else "F")(value)
                                for value in cycle_information.per_pin_pass_fail
                            ]
                        )
                        + "}",
                        "{"
                        + ",".join([str(value) for value in cycle_information.expected_pin_states])
                        + "}",
                        "{"
                        + ",".join([str(value) for value in cycle_information.actual_pin_states])
                        + "}",
                    ]
                )
            results.insert(
                0,
                [
                    "Vector",
                    "Timeset",
                    "Cycle",
                    "Scan Cycle",
                    "Pass/Fail",
                    "Pin List",
                    "Per Pin Pass/Fail",
                    "Expected Pin States",
                    "Actual Pin States",
                ],
            )
        filename = (
            "HRAM_Results_site"
            + str(site_number)
            + "_"
            + datetime.now().strftime("%d-%b-%Y-%H-%M-%S")
            + ".csv"
        )
        files_generated.append(filename)
        filehandle = open(filename, "w")
        for row in results:
            for col in row:
                filehandle.write("%s\t" % col)
            filehandle.write("\n")
        filehandle.close()
    return tsm, files_generated


def tsm_ssc_stream_hram_results(tsm: TSMDigital):
    (
        _,
        per_instrument_per_site_cycle_information,
        number_of_samples,
    ) = _ssc_stream_hram_results(tsm.ssc)
    per_instrument_per_site_to_per_site_lut = (
        _ssc_calculate_per_instrument_per_site_to_per_site_lut(tsm.ssc, tsm.site_numbers)
    )
    per_site_cycle_information = [
        [HistoryRAMCycleInformation() for _ in range(number_of_samples)] for _ in tsm.site_numbers
    ]
    for lut, cycle_information in zip(
        per_instrument_per_site_to_per_site_lut,
        per_instrument_per_site_cycle_information,
    ):
        for index in lut.location_1d_array:
            per_site_cycle_information[index] = cycle_information
    return tsm, per_site_cycle_information


# End of HRAM #


# Pattern Actions #
def tsm_ssc_abort(tsm: TSMDigital):
    _ssc_abort(tsm.ssc)
    return tsm


def tsm_ssc_burst_pattern_pass_fail(
    tsm: TSMDigital,
    start_label: str,
    select_digital_function: bool = True,
    timeout: float = 10,
):
    initialized_array = [False for _ in tsm.site_numbers]
    per_instrument_to_per_site_lut = _ssc_calculate_per_instrument_to_per_site_lut(
        tsm.ssc, tsm.site_numbers
    )
    _, per_instrument_pass = _ssc_burst_pattern_pass_fail(
        tsm.ssc, start_label, select_digital_function, timeout
    )
    per_site_pass = _apply_lut_per_instrument_to_per_site(
        initialized_array, per_instrument_to_per_site_lut, per_instrument_pass
    )
    return tsm, per_site_pass


def tsm_ssc_burst_pattern(
    tsm: TSMDigital,
    start_label: str,
    select_digital_function: bool = True,
    timeout: float = 10,
    wait_until_done: bool = True,
):
    _ssc_burst_pattern(tsm.ssc, start_label, select_digital_function, timeout, wait_until_done)
    return tsm


def tsm_ssc_get_fail_count(tsm: TSMDigital):
    initialized_array = [[0 for _ in tsm.pins] for _ in tsm.site_numbers]
    per_instrument_to_per_site_per_pin_lut = _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins
    )
    _, per_instrument_failure_counts = _ssc_get_fail_count(tsm.ssc)
    per_site_per_pin_fail_counts = _apply_lut_per_instrument_to_per_site_per_pin(
        initialized_array,
        per_instrument_to_per_site_per_pin_lut,
        per_instrument_failure_counts,
    )
    return tsm, per_site_per_pin_fail_counts


def tsm_ssc_get_site_pass_fail(tsm: TSMDigital):
    initialized_array = [False for _ in tsm.site_numbers]
    per_instrument_to_per_site_lut = _ssc_calculate_per_instrument_to_per_site_lut(
        tsm.ssc, tsm.site_numbers
    )
    _, per_instrument_pass = _ssc_get_site_pass_fail(tsm.ssc)
    per_site_pass = _apply_lut_per_instrument_to_per_site(
        initialized_array, per_instrument_to_per_site_lut, per_instrument_pass
    )
    return tsm, per_site_pass


def tsm_ssc_wait_until_done(tsm: TSMDigital, timeout: float = 10):
    _ssc_wait_until_done(tsm.ssc, timeout)
    return tsm


# End of Pattern Actions #


# Pin Levels and Timing #
def tsm_ssc_apply_levels_and_timing(tsm: TSMDigital, levels_sheet: str, timing_sheet: str):
    _ssc_apply_levels_and_timing(tsm.ssc, levels_sheet, timing_sheet)
    return tsm


def tsm_ssc_apply_tdr_offsets_per_site_per_pin(
    tsm: TSMDigital, per_site_per_pin_tdr_values: typing.List[typing.List[float]]
):
    (
        per_site_per_pin_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_per_pin_to_per_instrument_lut(tsm.ssc, tsm.site_numbers, tsm.pins)
    initialized_array = [
        [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_tdr_values = _apply_lut_per_site_per_pin_to_per_instrument(
        initialized_array,
        per_site_per_pin_to_per_instrument_lut,
        per_site_per_pin_tdr_values,
    )
    _ssc_apply_tdr_offsets(tsm.ssc, per_instrument_tdr_values)


def tsm_ssc_apply_tdr_offsets(
    tsm: TSMDigital, per_instrument_offsets: typing.List[typing.List[float]]
):
    _ssc_apply_tdr_offsets(tsm.ssc, per_instrument_offsets)
    return tsm


def tsm_ssc_configure_active_load(tsm: TSMDigital, vcom: float, iol: float, ioh: float):
    _ssc_configure_active_load(tsm.ssc, vcom, iol, ioh)
    return tsm


def tsm_ssc_configure_single_level_per_site(
    tsm: TSMDigital,
    level_type_to_set: LevelTypeToSet,
    per_site_value: typing.List[float],
):
    (
        per_site_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    initialized_array = [
        [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_value = _apply_lut_per_site_to_per_instrument(
        initialized_array, per_site_to_per_instrument_lut, per_site_value
    )
    _ssc_configure_single_level_per_site(tsm.ssc, level_type_to_set, per_instrument_value)
    return tsm


def tsm_ssc_configure_single_level(
    tsm: TSMDigital, level_type_to_set: LevelTypeToSet, setting: float
):
    _ssc_configure_single_level(tsm.ssc, level_type_to_set, setting)
    return tsm


def tsm_ssc_configure_termination_mode(tsm: TSMDigital, termination_mode: enums.TerminationMode):
    _ssc_configure_termination_mode(tsm.ssc, termination_mode)
    return tsm


def tsm_ssc_configure_time_set_compare_edge_per_site_per_pin(
    tsm: TSMDigital,
    time_set: str,
    per_site_per_pin_compare_strobe: typing.List[typing.List[float]],
):
    (
        per_site_per_pin_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_per_pin_to_per_instrument_lut(tsm.ssc, tsm.site_numbers, tsm.pins)
    initialized_array = [
        [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_compare_strobe = _apply_lut_per_site_per_pin_to_per_instrument(
        initialized_array,
        per_site_per_pin_to_per_instrument_lut,
        per_site_per_pin_compare_strobe,
    )
    _ssc_configure_time_set_compare_edge_per_site_per_pin(
        tsm.ssc, time_set, per_instrument_compare_strobe
    )
    return tsm


def tsm_ssc_configure_time_set_compare_edge_per_site(
    tsm: TSMDigital, time_set: str, per_site_compare_strobe: typing.List[float]
):
    (
        per_site_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    initialized_array = [
        [0.0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_compare_strobe = _apply_lut_per_site_to_per_instrument(
        initialized_array, per_site_to_per_instrument_lut, per_site_compare_strobe
    )
    _ssc_configure_time_set_compare_edge_per_site(tsm.ssc, time_set, per_instrument_compare_strobe)
    return tsm


def tsm_ssc_configure_time_set_compare_edge(tsm: TSMDigital, time_set: str, compare_strobe: float):
    _ssc_configure_time_set_compare_edge(tsm.ssc, time_set, compare_strobe)
    return tsm


def tsm_ssc_configure_time_set_period(tsm: TSMDigital, time_set: str, period: float):
    _, configured_period = _ssc_configure_time_set_period(tsm.ssc, time_set, period)
    return tsm, configured_period


def tsm_ssc_configure_voltage_levels(
    tsm: TSMDigital, vil: float, vih: float, vol: float, voh: float, vterm: float
):
    _ssc_configure_voltage_levels(tsm.ssc, vil, vih, vol, voh, vterm)
    return tsm


# End of Pin Levels and Timing #


# PPMU #
def tsm_ssc_ppmu_configure_aperture_time(tsm: TSMDigital, aperture_time: float):
    _ssc_ppmu_configure_aperture_time(tsm.ssc, aperture_time)
    return tsm


def tsm_ssc_ppmu_configure_current_limit_range(tsm: TSMDigital, current_limit_range: float):
    _ssc_ppmu_configure_current_limit_range(tsm.ssc, current_limit_range)
    return tsm


def tsm_ssc_ppmu_configure_voltage_limits(
    tsm: TSMDigital, voltage_limit_high: float, voltage_limit_low: float
):
    _ssc_ppmu_configure_voltage_limits(tsm.ssc, voltage_limit_high, voltage_limit_low)
    return tsm


def tsm_ssc_ppmu_measure_current(tsm: TSMDigital):
    initialized_array = [[0.0 for _ in tsm.pins] for _ in tsm.site_numbers]
    per_instrument_to_per_site_per_pin_lut = _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins
    )
    _, per_instrument_measurements = _ssc_ppmu_measure(tsm.ssc, enums.PPMUMeasurementType.CURRENT)
    per_site_per_pin_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
        initialized_array,
        per_instrument_to_per_site_per_pin_lut,
        per_instrument_measurements,
    )
    return tsm, per_site_per_pin_measurements


def tsm_ssc_ppmu_measure_voltage(tsm: TSMDigital):
    initialized_array = [[0.0 for _ in tsm.pins] for _ in tsm.site_numbers]
    per_instrument_to_per_site_per_pin_lut = _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins
    )
    _, per_instrument_measurements = _ssc_ppmu_measure(tsm.ssc, enums.PPMUMeasurementType.VOLTAGE)
    per_site_per_pin_measurements = _apply_lut_per_instrument_to_per_site_per_pin(
        initialized_array,
        per_instrument_to_per_site_per_pin_lut,
        per_instrument_measurements,
    )
    return tsm, per_site_per_pin_measurements


def tsm_ssc_ppmu_source_current(
    tsm: TSMDigital, current_level: float, current_level_range: float = 0
):
    _ssc_ppmu_source_current(tsm.ssc, current_level, current_level_range)
    return tsm


def tsm_ssc_ppmu_source_voltage_per_site_per_pin(
    tsm: TSMDigital,
    current_limit_range: float,
    per_site_per_pin_source_voltages: typing.List[typing.List[float]],
):
    (
        per_site_per_pin_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_per_pin_to_per_instrument_lut(tsm.ssc, tsm.site_numbers, tsm.pins)
    initialized_array = [
        [0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_source_voltages = _apply_lut_per_site_per_pin_to_per_instrument(
        initialized_array,
        per_site_per_pin_to_per_instrument_lut,
        per_site_per_pin_source_voltages,
    )
    _ssc_ppmu_source_voltage_per_site_per_pin(
        tsm.ssc, current_limit_range, per_instrument_source_voltages
    )
    return tsm


def tsm_ssc_ppmu_source_voltage_per_site(
    tsm: TSMDigital,
    current_limit_range: float,
    per_site_source_voltages: typing.List[float],
):
    (
        per_site_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    initialized_array = [
        [0 for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
    ]
    per_instrument_source_voltages = _apply_lut_per_site_to_per_instrument(
        initialized_array, per_site_to_per_instrument_lut, per_site_source_voltages
    )
    _ssc_ppmu_source_voltage_per_site(tsm.ssc, current_limit_range, per_instrument_source_voltages)
    return tsm


def tsm_ssc_ppmu_source_voltage(tsm: TSMDigital, voltage_level: float, current_limit_range: float):
    _ssc_ppmu_source_voltage(tsm.ssc, voltage_level, current_limit_range)
    return tsm


def tsm_ssc_ppmu_source(tsm: TSMDigital):
    _ssc_ppmu_source(tsm.ssc)
    return tsm


# End of PPMU #


# Sequencer Flags and Registers #
def tsm_ssc_read_sequencer_flag(tsm: TSMDigital, sequencer_flag: enums.SequencerFlag):
    _, per_instrument_state = _ssc_read_sequencer_flag(tsm.ssc, sequencer_flag)
    return tsm, per_instrument_state


def tsm_ssc_read_sequencer_register(tsm: TSMDigital, sequencer_register: enums.SequencerRegister):
    _, per_instrument_register_values = _ssc_read_sequencer_register(tsm.ssc, sequencer_register)
    return tsm, per_instrument_register_values


def tsm_ssc_write_sequencer_flag(
    tsm: TSMDigital, sequencer_flag: enums.SequencerFlag, state: bool = True
):
    _ssc_write_sequencer_flag(tsm.ssc, sequencer_flag, state)
    return tsm


def tsm_ssc_write_sequencer_register(
    tsm: TSMDigital, sequencer_register: enums.SequencerRegister, value: int = 0
):
    _ssc_write_sequencer_register(tsm.ssc, sequencer_register, value)
    return tsm


# End of Sequencer Flags and Registers #


# Session Properties #
def tsm_ssc_get_properties(tsm: TSMDigital):  # checked _
    session_properties: typing.List[Session_Properties] = []
    for _ssc in tsm.ssc:
        instrument_name = ""
        match = re.search(r"[A-Za-z]+[1-9]+", str(_ssc.session))
        if match:
            instrument_name = match.group()
        session_properties.append(
            Session_Properties(
                instrument_name,
                _ssc.session.channels[_ssc.channel_list].voh,
                _ssc.session.channels[_ssc.channel_list].vol,
                _ssc.session.channels[_ssc.channel_list].vih,
                _ssc.session.channels[_ssc.channel_list].vil,
                _ssc.session.channels[_ssc.channel_list].vterm,
                _ssc.session.channels[_ssc.channel_list].frequency_counter_measurement_time,
            )
        )
    return tsm, session_properties


# End of Session Properties #


# Source and Capture Waveforms #
def tsm_ssc_fetch_capture_waveform(
    tsm: TSMDigital, waveform_name: str, samples_to_read: int, timeout: float = 10
):
    initialized_array = [[0 for _ in range(samples_to_read)] for _ in range(len(tsm.site_numbers))]
    per_instrument_to_per_site_lut = _ssc_calculate_per_instrument_to_per_site_lut(
        tsm.ssc, tsm.site_numbers
    )
    _, per_instrument_capture = _ssc_fetch_capture_waveform(
        tsm.ssc, waveform_name, samples_to_read, timeout
    )
    per_site_waveforms = _apply_lut_per_instrument_to_per_site(
        initialized_array, per_instrument_to_per_site_lut, per_instrument_capture
    )
    return tsm, per_site_waveforms


def tsm_ssc_write_source_waveform_broadcast(
    tsm: TSMDigital,
    waveform_name: str,
    waveform_data: typing.List[int],
    expand_to_minimum_size: bool = False,
    minimum_size: int = 128,
):
    _ssc_write_source_waveform_broadcast(
        tsm.ssc, waveform_name, waveform_data, expand_to_minimum_size, minimum_size
    )
    return tsm


def tsm_ssc_write_source_waveform_site_unique(
    tsm: TSMDigital,
    waveform_name: str,
    per_site_waveforms: typing.List[typing.List[int]],
    expand_to_minimum_size: bool = False,
    minimum_size: int = 128,
):  # checked _
    _, cols = numpy.shape(per_site_waveforms)
    (
        per_site_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    initialized_array = [
        [[0 for _ in range(cols)] for _ in range(max_sites_on_instrument)]
        for _ in range(instrument_count)
    ]
    per_instrument_waveforms = _apply_lut_per_site_to_per_instrument(
        initialized_array, per_site_to_per_instrument_lut, per_site_waveforms
    )
    _ssc_write_source_waveform_site_unique(
        tsm.ssc,
        waveform_name,
        per_instrument_waveforms,
        expand_to_minimum_size,
        minimum_size,
    )
    return tsm


# End of Source and Capture Waveforms #


# SSC Digital #
# Clock Generation #
def _ssc_clock_generator_abort(ssc: typing.List[SSCDigital]):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].clock_generator_abort()
    return ssc


def _ssc_clock_generator_generate_clock(
    ssc: typing.List[SSCDigital], frequency: float, select_digital_function: bool = True
):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].clock_generator_generate_clock(
            frequency, select_digital_function
        )
    return ssc


def _ssc_modify_time_set_for_clock_generation(
    ssc: typing.List[SSCDigital], frequency: float, duty_cycle: float, time_set: str
):
    period = 1 / frequency
    for _ssc in ssc:
        _ssc.session.configure_time_set_period(time_set, period)
        _ssc.session.channels[_ssc.channel_list].configure_time_set_drive_edges(
            time_set,
            enums.DriveFormat.RL,
            0,
            0,
            period * duty_cycle,
            period * duty_cycle,
        )
    return ssc
    # End of Clock Generation #

    # Configuration #


def _ssc_select_function(ssc: typing.List[SSCDigital], function: enums.SelectedFunction):
    for _ssc in ssc:
        _ssc.session.abort()
        _ssc.session.channels[_ssc.channel_list].selected_function = function
    return ssc
    # End of Configuration #

    # Frequency Measurement #


def _ssc_frequency_counter_configure_measurement_time(
    ssc: typing.List[SSCDigital], measurement_time: float
):
    for _ssc in ssc:
        _ssc.session.channels[
            _ssc.channel_list
        ].frequency_counter_measurement_time = measurement_time
    return ssc


def _ssc_frequency_counter_measure_frequency(ssc: typing.List[SSCDigital]):
    per_instrument_frequencies: typing.List[typing.List[float]] = []
    for _ssc in ssc:
        per_instrument_frequencies.append(
            _ssc.session.channels[_ssc.channel_list].frequency_counter_measure_frequency()
        )
    return ssc, per_instrument_frequencies
    # End of Frequency Measurement #

    # HRAM #


def _ssc_configure_hram_settings(
    ssc: typing.List[SSCDigital],
    cycles_to_acquire: enums.HistoryRAMCyclesToAcquire = enums.HistoryRAMCyclesToAcquire.FAILED,
    pretrigger_samples: int = 0,
    max_samples_to_acquire_per_site: int = 8191,
    number_of_samples_is_finite: bool = True,
    buffer_size_per_site: int = 32000,
):
    for _ssc in ssc:
        _ssc.session.history_ram_cycles_to_acquire = cycles_to_acquire
        _ssc.session.history_ram_pretrigger_samples = pretrigger_samples
        _ssc.session.history_ram_max_samples_to_acquire_per_site = max_samples_to_acquire_per_site
        _ssc.session.history_ram_number_of_samples_is_finite = number_of_samples_is_finite
        _ssc.session.history_ram_buffer_size_per_site = buffer_size_per_site
    return ssc


def _ssc_configure_hram_trigger(
    ssc: typing.List[SSCDigital],
    triggers_type: enums.HistoryRAMTriggerType,
    cycle_number: int = 0,
    pattern_label: str = "",
    cycle_offset: int = 0,
    vector_offset: int = 0,
):
    for _ssc in ssc:
        if triggers_type == enums.HistoryRAMTriggerType.FIRST_FAILURE:
            _ssc.session.history_ram_trigger_type = triggers_type
        elif triggers_type == enums.HistoryRAMTriggerType.CYCLE_NUMBER:
            _ssc.session.history_ram_trigger_type = triggers_type
            _ssc.session.cycle_number_history_ram_trigger_cycle_number = cycle_number
        elif triggers_type == enums.HistoryRAMTriggerType.PATTERN_LABEL:
            _ssc.session.history_ram_trigger_type = triggers_type
            _ssc.session.pattern_label_history_ram_trigger_label = pattern_label
            _ssc.session.pattern_label_history_ram_trigger_cycle_offset = cycle_offset
            _ssc.session.pattern_label_history_ram_trigger_vector_offset = vector_offset
    return ssc


def _ssc_get_hram_settings(ssc: typing.List[SSCDigital]):
    per_instrument_cycles_to_acquire: typing.List[enums.HistoryRAMCyclesToAcquire] = []
    per_instrument_pretrigger_samples: typing.List[int] = []
    per_instrument_max_samples_to_acquire_per_site: typing.List[int] = []
    per_instrument_number_of_samples_is_finite: typing.List[bool] = []
    per_instrument_buffer_size_per_site: typing.List[int] = []
    for _ssc in ssc:
        per_instrument_cycles_to_acquire.append(_ssc.session.history_ram_cycles_to_acquire)
        per_instrument_pretrigger_samples.append(_ssc.session.history_ram_pretrigger_samples)
        per_instrument_max_samples_to_acquire_per_site.append(
            _ssc.session.history_ram_max_samples_to_acquire_per_site
        )
        per_instrument_number_of_samples_is_finite.append(
            _ssc.session.history_ram_number_of_samples_is_finite
        )
        per_instrument_buffer_size_per_site.append(_ssc.session.history_ram_buffer_size_per_site)
    return (
        ssc,
        per_instrument_cycles_to_acquire,
        per_instrument_pretrigger_samples,
        per_instrument_max_samples_to_acquire_per_site,
        per_instrument_number_of_samples_is_finite,
        per_instrument_buffer_size_per_site,
    )


def _ssc_get_hram_trigger_settings(ssc: typing.List[SSCDigital]):
    per_instrument_triggers_type: typing.List[enums.HistoryRAMTriggerType] = []
    per_instrument_cycle_number: typing.List[int] = []
    per_instrument_pattern_label: typing.List[str] = []
    per_instrument_cycle_offset: typing.List[int] = []
    per_instrument_vector_offset: typing.List[int] = []
    for _ssc in ssc:
        per_instrument_triggers_type.append(_ssc.session.history_ram_trigger_type)
        per_instrument_cycle_number.append(
            _ssc.session.cycle_number_history_ram_trigger_cycle_number
        )
        per_instrument_pattern_label.append(_ssc.session.pattern_label_history_ram_trigger_label)
        per_instrument_cycle_offset.append(
            _ssc.session.pattern_label_history_ram_trigger_cycle_offset
        )
        per_instrument_vector_offset.append(
            _ssc.session.pattern_label_history_ram_trigger_vector_offset
        )
    return (
        ssc,
        per_instrument_triggers_type,
        per_instrument_cycle_number,
        per_instrument_pattern_label,
        per_instrument_cycle_offset,
        per_instrument_vector_offset,
    )


def _ssc_stream_hram_results(ssc: typing.List[SSCDigital]):
    per_instrument_per_site_array: typing.List[SSCDigital] = []
    for _ssc in ssc:
        channel_list_array, site_list_array, _ = _arrange_channels_per_site(
            _ssc.channel_list, _ssc.site_list
        )
        for channel, site in zip(channel_list_array, site_list_array):
            per_instrument_per_site_array.append(SSCDigital(_ssc.session, channel, site))
    per_instrument_per_site_cycle_information: typing.List[
        typing.List[HistoryRAMCycleInformation]
    ] = []
    number_of_samples = 0
    for _ssc in per_instrument_per_site_array:
        cycle_information: typing.List[HistoryRAMCycleInformation] = []
        read_position = 0
        sum_of_samples_to_read = 0
        stop = False
        while not stop:
            done = _ssc.session.is_done()
            _, pins, _ = _channel_list_to_pins(_ssc.channel_list)
            sample_count = _ssc.session.sites[_ssc.site_list].get_history_ram_sample_count()
            samples_to_read = sample_count - read_position
            cycle_information += (
                _ssc.session.sites[_ssc.site_list]
                .pins_info[pins]
                .fetch_history_ram_cycle_information(read_position, samples_to_read)
            )
            read_position = sample_count
            sum_of_samples_to_read += samples_to_read
            if not samples_to_read and done:
                stop = True
        per_instrument_per_site_cycle_information.append(cycle_information)
        number_of_samples = max(number_of_samples, sum_of_samples_to_read)
    return ssc, per_instrument_per_site_cycle_information, number_of_samples
    # End of HRAM #

    # Pattern Actions #


def _ssc_abort(ssc: typing.List[SSCDigital]):
    for _ssc in ssc:
        _ssc.session.abort()
    return ssc


def _ssc_burst_pattern_pass_fail(
    ssc: typing.List[SSCDigital],
    start_label: str,
    select_digital_function: bool = True,
    timeout: float = 10,
):
    per_instrument_pass: typing.List[typing.List[bool]] = []
    for _ssc in ssc:
        per_instrument_pass.append(
            list(
                _ssc.session.sites[_ssc.site_list]
                .burst_pattern(start_label, select_digital_function, True, timeout)
                .values()
            )
        )
    return ssc, per_instrument_pass


def _ssc_burst_pattern(
    ssc: typing.List[SSCDigital],
    start_label: str,
    select_digital_function: bool = True,
    timeout: float = 10,
    wait_until_done: bool = True,
):
    for _ssc in ssc:
        _ssc.session.sites[_ssc.site_list].burst_pattern(
            start_label, select_digital_function, wait_until_done, timeout
        )
    return ssc


def _ssc_get_fail_count(ssc: typing.List[SSCDigital]):
    per_instrument_failure_counts: typing.List[typing.List[int]] = []
    for _ssc in ssc:
        per_instrument_failure_counts.append(
            _ssc.session.channels[_ssc.channel_list].get_fail_count()
        )
    return ssc, per_instrument_failure_counts


def _ssc_get_site_pass_fail(ssc: typing.List[SSCDigital]):
    per_instrument_pass: typing.List[typing.List[bool]] = []
    for _ssc in ssc:
        per_instrument_pass.append(
            list(_ssc.session.sites[_ssc.site_list].get_site_pass_fail().values())
        )
    return ssc, per_instrument_pass


def _ssc_wait_until_done(ssc: typing.List[SSCDigital], timeout: float = 10):
    for _ssc in ssc:
        _ssc.session.wait_until_done(timeout)
    return ssc
    # End of Pattern Actions #

    # Pin Levels and Timing #


def _ssc_apply_levels_and_timing(
    ssc: typing.List[SSCDigital], levels_sheet: str, timing_sheet: str
):
    for _ssc in ssc:
        _ssc.session.sites[_ssc.site_list].apply_levels_and_timing(levels_sheet, timing_sheet)
    return ssc


def _ssc_apply_tdr_offsets(
    ssc: typing.List[SSCDigital],
    per_instrument_offsets: typing.List[typing.List[float]],
):
    for _ssc, per_instrument_offset in zip(ssc, per_instrument_offsets):
        _ssc.session.channels[_ssc.channel_list].apply_tdr_offsets(per_instrument_offset)
    return ssc


def _ssc_configure_active_load(ssc: typing.List[SSCDigital], vcom: float, iol: float, ioh: float):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].configure_active_load_levels(iol, ioh, vcom)
    return ssc


def _ssc_configure_single_level_per_site(
    ssc: typing.List[SSCDigital],
    level_type_to_set: LevelTypeToSet,
    per_site_value: typing.List[typing.List[float]],
):
    for _ssc, settings in zip(ssc, per_site_value):
        channel_list_array, _, _ = _arrange_channels_per_site(_ssc.channel_list, _ssc.site_list)
        for channel, setting in zip(channel_list_array, settings):
            if level_type_to_set == LevelTypeToSet.VIL:
                _ssc.session.channels[channel].vil = setting
            elif level_type_to_set == LevelTypeToSet.VIH:
                _ssc.session.channels[channel].vih = setting
            elif level_type_to_set == LevelTypeToSet.VOL:
                _ssc.session.channels[channel].vol = setting
            elif level_type_to_set == LevelTypeToSet.VOH:
                _ssc.session.channels[channel].voh = setting
            elif level_type_to_set == LevelTypeToSet.VTERM:
                _ssc.session.channels[channel].vterm = setting
            elif level_type_to_set == LevelTypeToSet.LOL:
                _ssc.session.channels[channel].lol = setting
            elif level_type_to_set == LevelTypeToSet.LOH:
                _ssc.session.channels[channel].loh = setting
            elif level_type_to_set == LevelTypeToSet.VCOM:
                _ssc.session.channels[channel].vcom = setting
            _ssc.session.commit()
    return ssc


def _ssc_configure_single_level(
    ssc: typing.List[SSCDigital], level_type_to_set: LevelTypeToSet, setting: float
):
    for _ssc in ssc:
        if level_type_to_set == LevelTypeToSet.VIL:
            _ssc.session.channels[_ssc.channel_list].vil = setting
        elif level_type_to_set == LevelTypeToSet.VIH:
            _ssc.session.channels[_ssc.channel_list].vih = setting
        elif level_type_to_set == LevelTypeToSet.VOL:
            _ssc.session.channels[_ssc.channel_list].vol = setting
        elif level_type_to_set == LevelTypeToSet.VOH:
            _ssc.session.channels[_ssc.channel_list].voh = setting
        elif level_type_to_set == LevelTypeToSet.VTERM:
            _ssc.session.channels[_ssc.channel_list].vterm = setting
        elif level_type_to_set == LevelTypeToSet.LOL:
            _ssc.session.channels[_ssc.channel_list].lol = setting
        elif level_type_to_set == LevelTypeToSet.LOH:
            _ssc.session.channels[_ssc.channel_list].loh = setting
        elif level_type_to_set == LevelTypeToSet.VCOM:
            _ssc.session.channels[_ssc.channel_list].vcom = setting
        _ssc.session.commit()
    return ssc


def _ssc_configure_termination_mode(
    ssc: typing.List[SSCDigital], termination_mode: enums.TerminationMode
):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].termination_mode = termination_mode
    return ssc


def _ssc_configure_time_set_compare_edge_per_site_per_pin(
    ssc: typing.List[SSCDigital],
    time_set: str,
    per_site_per_pin_compare_strobe: typing.List[typing.List[float]],
):
    for _ssc, compare_strobes in zip(ssc, per_site_per_pin_compare_strobe):
        channels, _, _ = _channel_list_to_pins(_ssc.channel_list)
        for channel, compare_strobe in zip(channels, compare_strobes):
            _ssc.session.channels[channel].configure_time_set_compare_edges_strobe(
                time_set, compare_strobe
            )
    return ssc


def _ssc_configure_time_set_compare_edge_per_site(
    ssc: typing.List[SSCDigital],
    time_set: str,
    per_site_compare_strobe: typing.List[typing.List[float]],
):
    for _ssc, compare_strobes in zip(ssc, per_site_compare_strobe):
        channel_list_array, _, _ = _arrange_channels_per_site(_ssc.channel_list, _ssc.site_list)
        for channel, compare_strobe in zip(channel_list_array, compare_strobes):
            _ssc.session.channels[channel].configure_time_set_compare_edges_strobe(
                time_set, compare_strobe
            )
    return ssc


def _ssc_configure_time_set_compare_edge(
    ssc: typing.List[SSCDigital], time_set: str, compare_strobe: float
):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].configure_time_set_compare_edges_strobe(
            time_set, compare_strobe
        )
    return ssc


def _ssc_configure_time_set_period(ssc: typing.List[SSCDigital], time_set: str, period: float):
    configured_period = period
    if configured_period > 40e-6:
        configured_period = 40e-6
    elif configured_period < 10e-9:
        configured_period = 10e-9
    for _ssc in ssc:
        _ssc.session.configure_time_set_period(time_set, configured_period)
    return ssc, configured_period


def _ssc_configure_voltage_levels(
    ssc: typing.List[SSCDigital],
    vil: float,
    vih: float,
    vol: float,
    voh: float,
    vterm: float,
):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].configure_voltage_levels(vil, vih, vol, voh, vterm)
    return ssc
    # End of Pin Levels and Timing #

    # PPMU #


def _ssc_ppmu_configure_aperture_time(ssc: typing.List[SSCDigital], aperture_time: float):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].ppmu_aperture_time = aperture_time
    return ssc


def _ssc_ppmu_configure_current_limit_range(
    ssc: typing.List[SSCDigital], current_limit_range: float
):
    current_limit_range = abs(current_limit_range)
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].ppmu_current_limit_range = current_limit_range
    return ssc


def _ssc_ppmu_configure_voltage_limits(
    ssc: typing.List[SSCDigital], voltage_limit_high: float, voltage_limit_low: float
):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].ppmu_voltage_limit_high = voltage_limit_high
        _ssc.session.channels[_ssc.channel_list].ppmu_voltage_limit_low = voltage_limit_low
    return ssc


def _ssc_ppmu_measure(ssc: typing.List[SSCDigital], measurement_type: enums.PPMUMeasurementType):
    per_instrument_measurements: typing.List[typing.List[float]] = []
    for _ssc in ssc:
        per_instrument_measurements.append(
            _ssc.session.channels[_ssc.channel_list].ppmu_measure(measurement_type)
        )
    return ssc, per_instrument_measurements


def _ssc_ppmu_source_current(
    ssc: typing.List[SSCDigital], current_level: float, current_level_range: float = 0
):
    if current_level_range == 0:
        current_level_range = abs(current_level)
        if current_level_range > 32e-3:
            current_level_range = 32e-3
        elif current_level_range < 2e-6:
            current_level_range = 2e-6
    for _ssc in ssc:
        _ssc.session.channels[
            _ssc.channel_list
        ].ppmu_output_function = enums.PPMUOutputFunction.CURRENT
        _ssc.session.channels[_ssc.channel_list].ppmu_current_level_range = current_level_range
        _ssc.session.channels[_ssc.channel_list].ppmu_current_level = current_level
        _ssc.session.channels[_ssc.channel_list].ppmu_source()
    return ssc


def _ssc_ppmu_source_voltage_per_site_per_pin(
    ssc: typing.List[SSCDigital],
    current_limit_range: float,
    per_site_per_pin_source_voltages: typing.List[typing.List[float]],
):
    current_limit_range = abs(current_limit_range)
    for _ssc, source_voltages in zip(ssc, per_site_per_pin_source_voltages):
        _ssc.session.channels[
            _ssc.channel_list
        ].ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
        _ssc.session.channels[_ssc.channel_list].ppmu_current_limit_range = current_limit_range
        channels, _, _ = _channel_list_to_pins(_ssc.channel_list)
        for channel, source_voltage in zip(channels, source_voltages):
            _ssc.session.channels[channel].ppmu_voltage_level = source_voltage
        _ssc.session.channels[_ssc.channel_list].ppmu_source()
    return ssc


def _ssc_ppmu_source_voltage_per_site(
    ssc: typing.List[SSCDigital],
    current_limit_range: float,
    per_site_source_voltages: typing.List[typing.List[float]],
):
    current_limit_range = abs(current_limit_range)
    for _ssc, source_voltages in zip(ssc, per_site_source_voltages):
        _ssc.session.channels[
            _ssc.channel_list
        ].ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
        _ssc.session.channels[_ssc.channel_list].ppmu_current_limit_range = current_limit_range
        channel_list_array, _, _ = _arrange_channels_per_site(_ssc.channel_list, _ssc.site_list)
        for channel, source_voltage in zip(channel_list_array, source_voltages):
            _ssc.session.channels[channel].ppmu_voltage_level = source_voltage
        _ssc.session.channels[_ssc.channel_list].ppmu_source()
    return ssc


def _ssc_ppmu_source_voltage(
    ssc: typing.List[SSCDigital], voltage_level: float, current_limit_range: float
):
    """
    Current limit is not configured here
    The PXIe-6570 and PXIe-6571 do not support current limits in PPMU voltage mode:
    http://zone.ni.com/reference/en-XX/help/375145e/nidigitalpropref/pnidigital_ppmucurrentlimit/
    """

    current_limit_range = abs(current_limit_range)
    for _ssc in ssc:
        _ssc.session.channels[
            _ssc.channel_list
        ].ppmu_output_function = enums.PPMUOutputFunction.VOLTAGE
        _ssc.session.channels[_ssc.channel_list].ppmu_current_limit_range = current_limit_range
        _ssc.session.channels[_ssc.channel_list].ppmu_voltage_level = voltage_level
        _ssc.session.channels[_ssc.channel_list].ppmu_source()
    return ssc


def _ssc_ppmu_source(ssc: typing.List[SSCDigital]):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].ppmu_source()
    return ssc
    # End of PPMU #

    # Sequencer Flags and Registers #


def _ssc_read_sequencer_flag(ssc: typing.List[SSCDigital], sequencer_flag: enums.SequencerFlag):
    per_instrument_state: typing.List[bool] = []
    for _ssc in ssc:
        per_instrument_state.append(_ssc.session.read_sequencer_flag(sequencer_flag))
    return ssc, per_instrument_state


def _ssc_read_sequencer_register(
    ssc: typing.List[SSCDigital], sequencer_register: enums.SequencerRegister
):
    per_instrument_register_values: typing.List[int] = []
    for _ssc in ssc:
        per_instrument_register_values.append(
            _ssc.session.read_sequencer_register(sequencer_register)
        )
    return ssc, per_instrument_register_values


def _ssc_write_sequencer_flag(
    ssc: typing.List[SSCDigital],
    sequencer_flag: enums.SequencerFlag,
    state: bool = True,
):
    for _ssc in ssc:
        _ssc.session.write_sequencer_flag(sequencer_flag, state)
    return ssc


def _ssc_write_sequencer_register(
    ssc: typing.List[SSCDigital],
    sequencer_register: enums.SequencerRegister,
    value: int = 0,
):
    for _ssc in ssc:
        _ssc.session.write_sequencer_register(sequencer_register, value)
    return ssc
    # End of Sequencer Flags and Registers #

    # Source and Capture Waveforms #


def _ssc_fetch_capture_waveform(
    ssc: typing.List[SSCDigital],
    waveform_name: str,
    samples_to_read: int,
    timeout: float = 10,
):
    per_instrument_capture: typing.List[typing.List[typing.List[int]]] = []
    for _ssc in ssc:
        waveforms = _ssc.session.sites[_ssc.site_list].fetch_capture_waveform(
            waveform_name, samples_to_read, timeout
        )
        per_instrument_capture.append([list(waveforms[i]) for i in waveforms.keys()])
    return ssc, per_instrument_capture


def _ssc_write_source_waveform_broadcast(
    ssc: typing.List[SSCDigital],
    waveform_name: str,
    waveform_data: typing.List[int],
    expand_to_minimum_size: bool = False,
    minimum_size: int = 128,
):
    if minimum_size > len(waveform_data) and expand_to_minimum_size:
        initialized_array = [0 for _ in range(minimum_size)]
        for i in range(len(waveform_data)):
            initialized_array[i] = waveform_data[i]
        waveform_data = initialized_array
    for _ssc in ssc:
        _ssc.session.write_source_waveform_broadcast(waveform_name, waveform_data)
    return ssc


def _ssc_write_source_waveform_site_unique(
    ssc: typing.List[SSCDigital],
    waveform_name: str,
    per_instrument_waveforms: typing.List[typing.List[typing.List[int]]],
    expand_to_minimum_size: bool = False,
    minimum_size: int = 128,
):
    for _ssc, per_instrument_waveform in zip(ssc, per_instrument_waveforms):
        rows, cols = numpy.shape(per_instrument_waveform)
        site_numbers, _ = _site_list_to_site_numbers(_ssc.site_list)
        if minimum_size > cols and expand_to_minimum_size:
            initialized_array = [[0 for _ in range(minimum_size)] for _ in range(len(site_numbers))]
            for row in range(rows):
                for col in range(cols):
                    initialized_array[row][col] = per_instrument_waveform[row][col]
            per_instrument_waveform = initialized_array
        waveform_data = {}
        for site_number, waveform in zip(site_numbers, per_instrument_waveform):
            waveform_data[site_number] = waveform
        _ssc.session.write_source_waveform_site_unique(waveform_name, waveform_data)
    return ssc
    # End of Source and Capture Waveforms #

    # Static #


def _ssc_read_static(ssc: typing.List[SSCDigital]):
    per_instrument_data: typing.List[typing.List[enums.PinState]] = []
    for _ssc in ssc:
        per_instrument_data.append(_ssc.session.channels[_ssc.channel_list].read_static())
    return ssc, per_instrument_data


def _ssc_write_static(ssc: typing.List[SSCDigital], state: enums.WriteStaticPinState):
    for _ssc in ssc:
        _ssc.session.channels[_ssc.channel_list].write_static(state)
    return ssc


def _ssc_write_static_per_site_per_pin(
    ssc: typing.List[SSCDigital],
    per_site_per_pin_state: typing.List[typing.List[enums.WriteStaticPinState]],
):
    for _ssc, states in zip(ssc, per_site_per_pin_state):
        channels, _, _ = _channel_list_to_pins(_ssc.channel_list)
        for channel, state in zip(channels, states):
            _ssc.session.channels[channel].write_static(state)
    return ssc


def _ssc_write_static_per_site(
    ssc: typing.List[SSCDigital],
    per_site_state: typing.List[typing.List[enums.WriteStaticPinState]],
):
    for _ssc, states in zip(ssc, per_site_state):
        channel_list_array, _, _ = _arrange_channels_per_site(_ssc.channel_list, _ssc.site_list)
        for channel, state in zip(channel_list_array, states):
            _ssc.session.channels[channel].write_static(state)
    return ssc
    # End of Static #

    # Trigger #


def _ssc_clear_start_trigger_signal(ssc: typing.List[SSCDigital]):
    for _ssc in ssc:
        _ssc.session.start_trigger_type = enums.TriggerType.NONE
    return ssc


def _ssc_configure_trigger_signal(
    ssc: typing.List[SSCDigital],
    source: str,
    edge: enums.DigitalEdge = enums.DigitalEdge.RISING,
):
    for _ssc in ssc:
        _ssc.session.digital_edge_start_trigger_source = source
        _ssc.session.digital_edge_start_trigger_edge = edge
    return ssc


def _ssc_export_opcode_trigger_signal(
    ssc: typing.List[SSCDigital], signal_id: str, output_terminal: str = ""
):
    for _ssc in ssc:
        _ssc.session.pattern_opcode_events[
            signal_id
        ].exported_pattern_opcode_event_output_terminal = output_terminal
    return ssc
    # End of Trigger #


def _ssc_filter_sites(ssc: typing.List[SSCDigital], desired_sites: typing.List[int]):
    ssc_with_requested_sites: typing.List[SSCDigital] = []
    for _ssc in ssc:
        channel_list_array, site_list_array, site_numbers = _arrange_channels_per_site(
            _ssc.channel_list, _ssc.site_list
        )
        channel_list: typing.List[str] = []
        site_list: typing.List[str] = []
        for _channel_list, _site_list, site_number in zip(
            channel_list_array, site_list_array, site_numbers
        ):
            if site_number in desired_sites:
                channel_list.append(_channel_list)
                site_list.append(_site_list)
        if site_list:
            ssc_with_requested_sites.append(
                SSCDigital(_ssc.session, ",".join(channel_list), ",".join(site_list))
            )
    return ssc_with_requested_sites


def _ssc_initiate(ssc: typing.List[SSCDigital]):
    for _ssc in ssc:
        _ssc.session.initiate()
    return ssc


# End of SSC Digital #


# Static #
def tsm_ssc_read_static(tsm: TSMDigital):
    initialized_array = [[enums.PinState.ZERO for _ in tsm.pins] for _ in tsm.site_numbers]
    per_instrument_to_per_site_per_pin_lut = _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
        tsm.ssc, tsm.site_numbers, tsm.pins
    )
    _, per_instrument_data = _ssc_read_static(tsm.ssc)
    per_site_per_pin_data = _apply_lut_per_instrument_to_per_site_per_pin(
        initialized_array, per_instrument_to_per_site_per_pin_lut, per_instrument_data
    )
    return tsm, per_site_per_pin_data


def tsm_ssc_write_static_per_site_per_pin(
    tsm: TSMDigital,
    per_site_per_pin_state: typing.List[typing.List[enums.WriteStaticPinState]],
):
    (
        per_site_per_pin_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_per_pin_to_per_instrument_lut(tsm.ssc, tsm.site_numbers, tsm.pins)
    initialized_array = [
        [enums.WriteStaticPinState.ZERO for _ in range(max_sites_on_instrument)]
        for _ in range(instrument_count)
    ]
    per_instrument_state = _apply_lut_per_site_per_pin_to_per_instrument(
        initialized_array,
        per_site_per_pin_to_per_instrument_lut,
        per_site_per_pin_state,
    )
    _ssc_write_static_per_site_per_pin(tsm.ssc, per_instrument_state)
    return tsm


def tsm_ssc_write_static_per_site(
    tsm: TSMDigital, per_site_state: typing.List[enums.WriteStaticPinState]
):
    (
        per_site_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
    initialized_array = [
        [enums.WriteStaticPinState.X for _ in range(max_sites_on_instrument)]
        for _ in range(instrument_count)
    ]
    per_instrument_state = _apply_lut_per_site_to_per_instrument(
        initialized_array, per_site_to_per_instrument_lut, per_site_state
    )
    _ssc_write_static_per_site(tsm.ssc, per_instrument_state)
    return tsm


def tsm_ssc_write_static(tsm: TSMDigital, state: enums.WriteStaticPinState):
    _ssc_write_static(tsm.ssc, state)
    return tsm


# End of Static #


# Subroutines #
def _apply_lut_per_instrument_to_per_site_per_pin(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[Location_2D_Array],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for location, result in zip(_lut.location_2d_array, _results_to_apply_lut_to):
            array_out[location.row][location.col] = result
    return array_out


def _apply_lut_per_instrument_to_per_site(
    initialized_array: typing.List[typing.Any],
    lut: typing.List[Location_1D_Array],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for index, result in zip(_lut.location_1d_array, _results_to_apply_lut_to):
            array_out[index] = result
    return array_out


def _apply_lut_per_site_per_pin_to_per_instrument(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[typing.List[Location_2D]],
    results_to_apply_lut_to: typing.List[typing.List[typing.Any]],
):
    array_out = copy.deepcopy(initialized_array)
    for _lut, _results_to_apply_lut_to in zip(lut, results_to_apply_lut_to):
        for location, result in zip(_lut, _results_to_apply_lut_to):
            array_out[location.row][location.col] = result
    return array_out


def _apply_lut_per_site_to_per_instrument(
    initialized_array: typing.List[typing.List[typing.Any]],
    lut: typing.List[Location_2D],
    results_to_apply_lut_to: typing.List[typing.Any],
):
    array_out = copy.deepcopy(initialized_array)
    for location, result in zip(lut, results_to_apply_lut_to):
        array_out[location.row][location.col] = result
    return array_out


def _arrange_channels_per_site(channel_list_string: str, site_list_string: str):
    site_numbers, site_list_array = _site_list_to_site_numbers(site_list_string)
    channels, _, sites = _channel_list_to_pins(channel_list_string)
    channel_list_array: typing.List[str] = []
    for site_number in site_numbers:
        channel_list: typing.List[str] = []
        for channel, site in zip(channels, sites):
            if site_number == site:
                channel_list.append(channel)
        channel_list_array.append(",".join(channel_list))
    return channel_list_array, site_list_array, site_numbers


def _site_list_to_site_numbers(site_list: str):
    sites = re.split(r"\s*,\s*", site_list)
    site_numbers = [int(re.match(r"site(\d+)", site).group(1)) for site in sites]
    return site_numbers, sites


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
            sites[i] = int(re.match(r"site(\d+)", site).group(1))
    return channels, pins, sites


def _ssc_calculate_per_instrument_per_site_to_per_site_lut(
    ssc: typing.List[SSCDigital], sites: typing.List[int]
):
    per_instrument_per_site_to_per_site_lut: typing.List[Location_1D_Array] = []
    for _ssc in ssc:
        site_numbers, _ = _site_list_to_site_numbers(_ssc.site_list)
        array: typing.List[Location_1D_Array] = []
        for site_number in site_numbers:
            array.append(Location_1D_Array([sites.index(site_number)]))
        per_instrument_per_site_to_per_site_lut += array
    return per_instrument_per_site_to_per_site_lut


def _ssc_calculate_per_instrument_to_per_site_lut(
    ssc: typing.List[SSCDigital], sites: typing.List[int]
):
    per_instrument_to_per_site_lut: typing.List[Location_1D_Array] = []
    for _ssc in ssc:
        site_numbers, _ = _site_list_to_site_numbers(_ssc.site_list)
        array: typing.List[int] = []
        for site_number in site_numbers:
            array.append(sites.index(site_number))
        per_instrument_to_per_site_lut.append(Location_1D_Array(array))
    return per_instrument_to_per_site_lut


def _ssc_calculate_per_instrument_to_per_site_per_pin_lut(
    ssc: typing.List[SSCDigital], sites: typing.List[int], pins: typing.List[str]
):
    per_instrument_to_per_site_per_pin_lut: typing.List[Location_2D_Array] = []
    for _ssc in ssc:
        _, _pins, _sites = _channel_list_to_pins(_ssc.channel_list)
        array: typing.List[Location_2D] = []
        for pin, site in zip(_pins, _sites):
            array.append(Location_2D(sites.index(site), pins.index(pin)))
        per_instrument_to_per_site_per_pin_lut.append(Location_2D_Array(array))
    return per_instrument_to_per_site_per_pin_lut


def _ssc_calculate_per_site_per_pin_to_per_instrument_lut(
    ssc: typing.List[SSCDigital], sites: typing.List[int], pins: typing.List[str]
):
    max_sites_on_instrument = 0
    instrument_count = len(ssc)
    i = 0
    location_2d_array: typing.List[Location_2D] = []
    pins_sites_array: typing.List[typing.Any] = []
    per_site_per_pin_to_per_instrument_lut: typing.List[typing.List[Location_2D]] = []
    for _ssc in ssc:
        _, _pins, _sites = _channel_list_to_pins(_ssc.channel_list)
        pins_sites_array += list(map(list, zip(_pins, _sites)))
        max_sites_on_instrument = max(max_sites_on_instrument, len(_pins))
        location_2d_array += [Location_2D(i, j) for j in range(len(_pins))]
        i += 1
    for site in sites:
        array: typing.List[Location_2D] = []
        for pin in pins:
            index = pins_sites_array.index([pin, site])
            array.append(location_2d_array[index])
        per_site_per_pin_to_per_instrument_lut.append(array)
    return (
        per_site_per_pin_to_per_instrument_lut,
        instrument_count,
        max_sites_on_instrument,
    )


def _ssc_calculate_per_site_to_per_instrument_lut(
    ssc: typing.List[SSCDigital], sites: typing.List[int]
):
    max_sites_on_instrument = 0
    instrument_count = len(ssc)
    i = 0
    location_2d_array: typing.List[Location_2D] = []
    sites_array: typing.List[int] = []
    per_site_to_per_instrument_lut: typing.List[Location_2D] = []
    for _ssc in ssc:
        site_numbers, _ = _site_list_to_site_numbers(_ssc.site_list)
        sites_array += site_numbers
        max_sites_on_instrument = max(max_sites_on_instrument, len(site_numbers))
        location_2d_array += [Location_2D(i, j) for j in range(len(site_numbers))]
        i += 1
    for site in sites:
        index = sites_array.index(site)
        per_site_to_per_instrument_lut.append(location_2d_array[index])
    return per_site_to_per_instrument_lut, instrument_count, max_sites_on_instrument


# End of Subroutines #


# TSM #
def tsm_close_sessions(tsm_context: SemiconductorModuleContext):
    sessions = tsm_context.get_all_nidigital_sessions()
    for session in sessions:
        session.reset()
        session.close()


def tsm_initialize_sessions(tsm_context: SemiconductorModuleContext, options: dict = {}):
    instrument_names = tsm_context.get_all_nidigital_instrument_names()
    if instrument_names:
        pin_map_file_path = tsm_context.pin_map_file_path
        # specifications_file_paths = tsm_context.nidigital_project_specifications_file_paths
        # levels_file_paths = tsm_context.nidigital_project_levels_file_paths
        # timing_file_paths = tsm_context.nidigital_project_timing_file_paths
        # pattern_file_paths = tsm_context.nidigital_project_pattern_file_paths
        # source_waveform_file_paths = tsm_context.nidigital_project_source_waveform_file_paths
        # capture_waveform_file_paths = tsm_context.nidigital_project_capture_waveform_file_paths
        for instrument_name in instrument_names:
            session = nidigital.Session(instrument_name, options=options)
            tsm_context.set_nidigital_session(instrument_name, session)
            session.load_pin_map(pin_map_file_path)
            # session.load_specifications_levels_and_timing(
            #     specifications_file_paths, levels_file_paths, timing_file_paths
            # )
            session.unload_all_patterns()
            # for pattern_file_path in pattern_file_paths:
            #     session.load_pattern(pattern_file_path)
            # for capture_waveform_file_path in capture_waveform_file_paths:
            #     filename = os.path.basename(capture_waveform_file_path)
            #     waveform_name, _ = filename.split(".")
            #     session.create_capture_waveform_from_file_digicapture(
            #         waveform_name, capture_waveform_file_path
            #     )
            # for source_waveform_file_path in source_waveform_file_paths:
            #     filename = os.path.basename(source_waveform_file_path)
            #     waveform_name, _ = filename.split(".")
            #     session.create_source_waveform_from_file_tdms(
            #         waveform_name, source_waveform_file_path, False
            #     )
        return session


def tsm_ssc_1_pin_to_n_sessions(tsm_context: SemiconductorModuleContext, pin: str):
    tsm = tsm_ssc_n_pins_to_m_sessions(tsm_context, [pin])
    return tsm


def tsm_ssc_n_pins_to_m_sessions(
    tsm_context: SemiconductorModuleContext,
    pins: typing.List[str],
    site_numbers: typing.List[int] = [],
    turn_pin_groups_to_pins: bool = True,
):
    if len(site_numbers) == 0:
        site_numbers = list(tsm_context.site_numbers)
    if turn_pin_groups_to_pins:
        pins = list(tsm_context.get_pins_in_pin_groups(pins))
    ssc: typing.List[SSCDigital] = []
    (
        pin_query_context,
        sessions,
        pin_set_strings,
    ) = tsm_context.pins_to_nidigital_sessions_for_ppmu(pins)
    _, _, site_lists = tsm_context.pins_to_nidigital_sessions_for_pattern(pins)
    for session, pin_set_string, site_list in zip(sessions, pin_set_strings, site_lists):
        ssc.append(SSCDigital(session, pin_set_string, site_list))
    tsm = TSMDigital(pin_query_context, ssc, site_numbers, pins)
    return tsm


def tsm_ssc_filter_sites(tsm: TSMDigital, desired_sites: typing.List[int]):
    ssc = _ssc_filter_sites(tsm.ssc, desired_sites)
    tsm = TSMDigital(tsm.pin_query_context, ssc, tsm.site_numbers, tsm.pins)
    return tsm


def tsm_ssc_initiate(tsm: TSMDigital):
    _ssc_initiate(tsm.ssc)
    return tsm


def tsm_ssc_publish(
    tsm: TSMDigital,
    data_to_publish: typing.List[typing.Any],
    published_data_id: str = "",
):
    if len(numpy.shape(data_to_publish)) == 1:
        (
            per_site_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = _ssc_calculate_per_site_to_per_instrument_lut(tsm.ssc, tsm.site_numbers)
        default = {bool: False, float: 0.0}[type(data_to_publish[0])]
        initialized_array = [
            [default for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_data = _apply_lut_per_site_to_per_instrument(
            initialized_array, per_site_to_per_instrument_lut, data_to_publish
        )
        tsm.pin_query_context.publish(per_instrument_data, published_data_id)
    elif len(numpy.shape(data_to_publish)) == 2:
        (
            per_site_per_pin_to_per_instrument_lut,
            instrument_count,
            max_sites_on_instrument,
        ) = _ssc_calculate_per_site_per_pin_to_per_instrument_lut(
            tsm.ssc, tsm.site_numbers, tsm.pins
        )
        default = {bool: False, float: 0.0}[type(data_to_publish[0][0])]
        initialized_array = [
            [default for _ in range(max_sites_on_instrument)] for _ in range(instrument_count)
        ]
        per_instrument_data = _apply_lut_per_site_per_pin_to_per_instrument(
            initialized_array, per_site_per_pin_to_per_instrument_lut, data_to_publish
        )
        tsm.pin_query_context.publish(per_instrument_data, published_data_id)
    else:
        raise TypeError("Unexpected data_to_publish array dimension.")


# End of TSM #
