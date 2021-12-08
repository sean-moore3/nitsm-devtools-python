import typing
import math
import nifgen
import nitsm.codemoduleapi
import nitsm.enums
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
import nidevtools.common as ni_dt_common


class SSCFgen(typing.NamedTuple):
    session: nifgen.Session
    channels: str
    channel_list: str


class TSMFgen(typing.NamedTuple):
    pin_query_context: typing.Any
    site_numbers: typing.List[int]
    ssc: typing.List[SSCFgen]


def _create_waveform_data(number_of_samples):
    waveform_data = []
    angle_per_sample = (2 * math.pi) / number_of_samples
    for i in range(number_of_samples):
        waveform_data.append(math.sin(i * angle_per_sample) * math.sin(i * angle_per_sample * 20))
    return waveform_data



def generate_sine_wave(tsm: TSMFgen, frequency: float, amplitude: float, offset: float,
                       wfm_len_min: int, wfm_len_inc: int, generation_rate: float):
    # generate waveform here
    f_inv = 1/frequency
    pts = int(math.ceil(f_inv * generation_rate))
    if pts<2:
        pts = 2
    elif pts>=4096:
        pts = 4095
    else:
        pass
    calc_samples = wfm_len_inc * pts
    min_wav_samples = int(wfm_len_min/(2*wfm_len_inc)) * calc_samples
    if calc_samples>=wfm_len_min :
        samples = calc_samples
    else:
        samples = min_wav_samples
    waveform_data = _create_waveform_data(samples)
    waveform_data *= amplitude
    waveform_data += offset
    gain = max([abs(data) for data in waveform_data])
    normalised_waveform = [data/gain for data in waveform_data]
    for ssc in tsm.ssc:
        ssc.session.abort()
        ssc.session.clear_arb_memory()
        ssc.session.output_mode = nifgen.OutputMode.ARB
        waveform = ssc.session.create_waveform(waveform_data_array=normalised_waveform)
        ssc.session.configure_arb_waveform(waveform_handle=waveform, gain=gain, offset=0.0)
        ssc.session.digital_filter_enabled = True
        ssc.session.initiate()
    return tsm, waveform_data


@nitsm.codemoduleapi.code_module
def tsm_ssc_pins_to_sessions(tsm_context: TSMContext, pins: typing.List[str], sites: typing.List[int]):
    pin_query_context, sessions, channels = tsm_context.pins_to_nifgen_sessions(pins)
    sites_out, channel_list_per_session = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], sites)
    ssc_s: typing.List[SSCFgen] = []
    for session, channel, channel_list in zip(sessions, channels, channel_list_per_session):
        ssc_s.append(SSCFgen(session=session, channels=channel, channel_list=channel_list))
    return TSMFgen(pin_query_context, sites_out, ssc_s)


@nitsm.codemoduleapi.code_module
def tsm_initialize_sessions(tsm_context: TSMContext, options: dict = {}):
    """ Opens sessions for all instrument channels that are associated with the tsm context"""
    instrument_names = tsm_context.get_all_nifgen_instrument_names()
    for instrument_name in instrument_names:
        session = nifgen.Session(instrument_name, reset_device=True, options=options)
        tsm_context.set_nifgen_session(instrument_name, session)
    dut_pins, system_pins = tsm_context.get_pin_names()
    all_pins = dut_pins + system_pins
    instrument_type = nitsm.enums.InstrumentTypeIdConstants.NI_FGEN
    fgen_pins = tsm_context.filter_pins_by_instrument_type(all_pins, instrument_type, "")
    pin_query_context, sessions, channels = tsm_context.pins_to_nifgen_sessions(fgen_pins)
    for fgen_session, channel_list in zip(sessions, channels):
        temp = set(channel_list)
        channels = list(temp)
        fgen_session.channels = channels  # configure channels


@nitsm.codemoduleapi.code_module
def tsm_close_sessions(tsm_context: TSMContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm_context.get_all_nifgen_sessions()
    for session in sessions:
        session.reset()
        session.close()
