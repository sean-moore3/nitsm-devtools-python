import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
import digital as ni_dt_digital
import os.path
import typing

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))
OPTIONS = {}  # empty dict options to run on real hardware.
if SIMULATE_HARDWARE:
    OPTIONS = {"Simulate": True, "driver_setup": {"Model": "6571"}}

@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SemiconductorModuleContext):
    ni_dt_digital.tsm_initialize_sessions(tsm_context, options=OPTIONS)
    tsm_spi = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(
        tsm_context, ["CS", "SCK", "MOSI", "MISO", "SYNC"]
    )
    ni_dt_digital.tsm_ssc_apply_levels_and_timing(tsm_spi, "PinLevels", "Timing")
    ni_dt_digital.tsm_ssc_select_function(tsm_spi, ni_dt_digital.enums.SelectedFunction.DIGITAL)


@nitsm.codemoduleapi.code_module
def slave_select_via_sync(tsm_context: SemiconductorModuleContext):
    tsm_sync = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["SYNC"])
    ni_dt_digital.tsm_ssc_write_static(tsm_sync, ni_dt_digital.enums.WriteStaticPinState.ZERO)
    ni_dt_digital.tsm_ssc_write_static(tsm_sync, ni_dt_digital.enums.WriteStaticPinState.ONE)
    ni_dt_digital.tsm_ssc_write_static(tsm_sync, ni_dt_digital.enums.WriteStaticPinState.ZERO)



@nitsm.codemoduleapi.code_module
def spi_write(tsm_context: SemiconductorModuleContext, data: typing.List[int] = [12, 24, 36, 55, 96],):
    tsm = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "MOSI", "MISO"])
    ni_dt_digital.tsm_ssc_write_source_waveform_broadcast(tsm, "source_buffer", data, )
    ni_dt_digital.tsm_ssc_burst_pattern(tsm, "SPI_write")


@nitsm.codemoduleapi.code_module
def spi_read(tsm_context: SemiconductorModuleContext, data: typing.List[int] = [12, 24, 36, 55, 96],):
    tsm = ni_dt_digital.tsm_ssc_n_pins_to_m_sessions(tsm_context, ["CS", "SCK", "MOSI", "MISO"])
    ni_dt_digital.tsm_ssc_write_source_waveform_broadcast(tsm, "source_buffer", data, )
    ni_dt_digital.tsm_ssc_burst_pattern(tsm, "SPI_read")
    _, per_site_waveforms = ni_dt_digital.tsm_ssc_fetch_capture_waveform(tsm, "capture_buffer", 5)
    print(per_site_waveforms)
    return per_site_waveforms


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
    ni_dt_digital.tsm_close_sessions(tsm_context)
