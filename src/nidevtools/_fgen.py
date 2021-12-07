import nifgen
import nitsm.codemoduleapi
import nitsm.enums
from nitsm.codemoduleapi import SemiconductorModuleContext


@nitsm.codemoduleapi.code_module
def tsm_initialize_sessions(tsm_context: SemiconductorModuleContext, options: dict = {}):
    """ Opens sessions for all instrument channels that are associated with the tsm context"""
    instrument_names = tsm_context.get_all_nifgen_instrument_names()
    for instrument_name in instrument_names:
        session = nifgen.Session(instrument_name, reset_device=True, options=options)
        tsm_context.set_nifgen_session(instrument_name, session)
    dut_pins, system_pins = tsm_context.get_pin_names()
    all_pins = dut_pins + system_pins
    instrument_type = nitsm.enums.InstrumentTypeIdConstants.NI_FGEN
    fgen_pins = tsm_context.filter_pins_by_instrument_type(all_pins, instrument_type, "")
    pin_q_c, fgen_sessions, channel_lists = tsm_context.pins_to_nifgen_sessions(fgen_pins)
    for fgen_session, channel_list in zip(fgen_sessions, channel_lists):
        temp = set(channel_list)
        channels = list(temp)
        fgen_session.channels = channels  # configure channels


@nitsm.codemoduleapi.code_module
def tsm_close_sessions(tsm_context: SemiconductorModuleContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm_context.get_all_nifgen_sessions()
    for session in sessions:
        session.reset()
        session.close()
