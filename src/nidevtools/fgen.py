import typing
import math
import nifgen
import nitsm.codemoduleapi
import nitsm.enums
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
import nidevtools.common as ni_dt_common


class _NIFGenSSC:
    """
    _Site specific _Session and _Channel.
    Each object of this class is used to store info for a specified pin under specific Site.
    To store a _Session and _Channel(s) for different _Site(s) you need an array of this class object.
    """

    """
    Prefix cs is used in all methods that operates on a given channels in a session. 
    These are for internal use only and can be changed any time. 
    External module should not use these methods with prefix 'cs_' directly.  
    """

    def __init__(self, session: nifgen.Session, channels: str, pin_list: str):
        self._session = session  # mostly shared session  (very rarely unique session) depends on pinmap file.
        self._channels = channels  # specific channel(s) of that session
        self._pin_list = pin_list  # pin names mapped to the channels

    @property
    def session(self):
        return self._session  # This session may contain other pin's channels

    @property
    def cs_channels(self):
        return self._channels

    def cs_generate_sine_wave(self, waveform_data, gain: float, offset: float = 0.0):
        self.session.abort()
        self.session.clear_arb_memory()
        self.session.output_mode = nifgen.OutputMode.ARB
        waveform = self.session.create_waveform(waveform_data_array=waveform_data)
        self.session.configure_arb_waveform(waveform_handle=waveform, gain=gain, offset=offset)
        self.session.digital_filter_enabled = True
        self.session.initiate()
        return


class _NIFGenTSM:
    def __init__(self, sessions_sites_channels: typing.Iterable[_NIFGenSSC]):
        self._sessions_sites_channels = sessions_sites_channels

    @staticmethod
    def create_waveform_data(number_of_samples):
        waveform_data = []
        angle_per_sample = (2 * math.pi) / number_of_samples
        for i in range(number_of_samples):
            waveform_data.append(math.sin(i * angle_per_sample) * math.sin(i * angle_per_sample * 20))
        return waveform_data

    def generate_sine_wave(
        self,
        frequency: float,
        amplitude: float,
        offset: float,
        wfm_len_min: int,
        wfm_len_inc: int,
        generation_rate: float,
    ):
        # generate waveform here
        f_inv = 1 / frequency
        pts = int(math.ceil(f_inv * generation_rate))
        if pts < 2:
            pts = 2
        elif pts >= 4096:
            pts = 4095
        else:
            pass
        calc_samples = wfm_len_inc * pts
        min_wav_samples = int(wfm_len_min / (2 * wfm_len_inc)) * calc_samples
        if calc_samples >= wfm_len_min:
            samples = calc_samples
        else:
            samples = min_wav_samples
        waveform_data = self.create_waveform_data(samples)
        waveform_data *= amplitude
        waveform_data += offset
        gain = max([abs(data) for data in waveform_data])
        normalised_waveform = [data / gain for data in waveform_data]
        for ssc in self._sessions_sites_channels:
            ssc.cs_generate_sine_wave(normalised_waveform, gain)
        return waveform_data


class TSMFgen(typing.NamedTuple):
    pin_query_context: typing.Any
    ssc: _NIFGenTSM
    sites: typing.List[int]


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: TSMContext, pins: typing.List[str], sites: typing.List[int]):
    pin_query_context, sessions, channels = tsm_context.pins_to_nifgen_sessions(pins)
    sites_out, pin_list_per_session = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], sites)
    sscs: typing.List[_NIFGenSSC] = []
    for session, channel, pin_list in zip(sessions, channels, pin_list_per_session):
        sscs.append(_NIFGenSSC(session=session, channels=channel, pin_list=pin_list))
    fgen_tsm = _NIFGenTSM(sscs)
    return TSMFgen(pin_query_context, fgen_tsm, sites_out)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: TSMContext, options: dict = {}):
    """Opens sessions for all instrument channels that are associated with the tsm context"""
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
def close_sessions(tsm_context: TSMContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm_context.get_all_nifgen_sessions()
    for session in sessions:
        session.reset()
        session.close()


if __name__ == "__main__":
    pass
