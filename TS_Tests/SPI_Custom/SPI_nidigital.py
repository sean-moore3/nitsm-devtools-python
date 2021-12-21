import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
import digital as ni_dt_digital


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SemiconductorModuleContext):
    ni_dt_digital.tsm_initialize_sessions(tsm_context)
    tsm_spi = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "MOSI", "MISO", "SYNC"])
    ni_dt_digital.tsm_ssc_apply_levels_and_timing(tsm_spi, "PinLevels", "Timing")
    ni_dt_digital.tsm_ssc_select_function(tsm_spi, ni_dt_digital.enums.SelectedFunction.DIGITAL)


@nitsm.codemoduleapi.code_module
def slave_select_via_sync(tsm_context: SemiconductorModuleContext):
    tsm_sync = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "SYNC"])
    # ni_dt_digital.tsm_ssc_select_function(tsm_o, ni_dt_digital.enums.SelectedFunction.DIGITAL)
    ni_dt_digital.tsm_ssc_write_static(tsm_sync, ni_dt_digital.enums.WriteStaticPinState.ZERO)
    _, per_site_pass = ni_dt_digital.tsm_ssc_burst_pattern_pass_fail(tsm_sync, "SPI_sync_write")


@nitsm.codemoduleapi.code_module
def spi_write(tsm_context: SemiconductorModuleContext):
    tsm = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "MOSI", "MISO"])
    _, per_site_pass = ni_dt_digital.tsm_ssc_burst_pattern_pass_fail(tsm, "SPI_write")
    print(per_site_pass)
    return per_site_pass


@nitsm.codemoduleapi.code_module
def spi_read(tsm_context: SemiconductorModuleContext):
    tsm = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "MOSI", "MISO"])
    # ni_dt_digital.tsm_ssc_select_function(tsm_i, ni_dt_digital.enums.SelectedFunction.DIGITAL)
    _, data = ni_dt_digital.tsm_ssc_read_static(tsm)
    _, per_site_pass = ni_dt_digital.tsm_ssc_burst_pattern_pass_fail(tsm, "SPI_read")
    print(data)
    print(per_site_pass)
    return data


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
    ni_dt_digital.tsm_close_sessions(tsm_context)
