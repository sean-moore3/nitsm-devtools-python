import math
import typing

import nifgen
import nitsm.codemoduleapi
import nitsm.enums
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

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
        """
        Updates the sessions in the class object for pin name based operations

        Args:
            session (nifgen.Session): stores the session of the fgen card
            channels (str): comma separated list of channels in the session
            pin_list (str): pin names from the pinmap corresponding to the channels
        """
        self._session = (
            session  # mostly shared session  (very rarely unique session) depends on pinmap file.
        )
        self._channels = channels  # specific channel(s) of that session
        self._pin_list = pin_list  # pin names mapped to the channels

    @property
    def session(self):
        return self._session  # This session may contain other pin's channels

    @property
    def cs_channels(self):
        return self._channels

    def cs_generate_sine_wave(
        self, waveform_data, sample_rate=1.0, gain=1.0, offset=0.0, enable_filter=True
    ):
        """
        generates the sine waveform of desired sampling rate, gain and offset using the waveform data

        Args:
            waveform_data (_type_): this is the data reference in memory for signal generation
            sample_rate (float, optional): number of samples per second. Defaults to 1.0.
            gain (float, optional): gain to be applied on the signal during generation. Defaults to 1.0.
            offset (float, optional): any dc offset to add on the generated signal. Defaults to 0.0.
            enable_filter (bool, optional): enable filter for smooth signal generation so the higher order signals are
                removed in the output. Defaults to True.
        """
        self.session.abort()
        self.session.clear_arb_memory()
        self.session.output_mode = nifgen.OutputMode.ARB
        waveform = self.session.create_waveform(waveform_data_array=waveform_data)
        self.session.configure_arb_waveform(waveform_handle=waveform, gain=gain, offset=offset)
        self.session.arb_sample_rate = sample_rate
        self.session.digital_filter_enabled = enable_filter
        self.session.initiate()
        return


class _NIFGenTSM:
    def __init__(self, sessions_sites_channels: typing.Iterable[_NIFGenSSC]):
        self._sessions_sites_channels = sessions_sites_channels

    @staticmethod
    def create_waveform_data(samples=128, frequency=7.8125e-3, phase_degree=0):
        """
        generate the samples on the waveform so that it is stored and played back

        Args:
            samples (int, optional): number of points to generate. Defaults to 128.
            frequency (_type_, optional): frequency of the sine signal generated. Defaults to 7.8125e-3.
            phase_degree (int, optional): phase of the sine wave. Defaults to 0.

        Returns:
            waveform list: list of samples in the waveform
        """
        waveform_data = []
        angle_offset = phase_degree * math.pi / 180  # in radians
        angle_per_sample = 2 * math.pi * frequency
        for i in range(samples):
            angle = angle_offset + angle_per_sample * i
            waveform_data.append(math.sin(angle))
        print("waveform length", len(waveform_data))
        return waveform_data

    def generate_sine_wave(
        self,
        frequency: float = 100e3,
        amplitude: float = 1.0,
        offset: float = 0.0,
        wfm_len_min: int = 4,
        wfm_len_inc: int = 16,
        generation_rate: float = 100e6,
        enable_filter: bool = True,
    ):
        """
        generate the sine signal on the current pins.

        Args:
            frequency (float, optional): of the sine waveform. Defaults to 100e3.
            amplitude (float, optional): of the sine waveform. Defaults to 1.0.
            offset (float, optional): dc signal added to the sine waveform. Defaults to 0.0.
            wfm_len_min (int, optional): minimum number of points to be there in the waveform. Defaults to 4.
            wfm_len_inc (int, optional): step size for length. Defaults to 16.
            generation_rate (float, optional): determines the speed of waveform driven out. Defaults to 100e6.
            enable_filter (bool, optional): for filtering high frequency signals. Defaults to True.

        Returns:
            waveform data: sine waveform data to be loaded in memory.
        """
        f_inv = 1 / frequency
        pts = int(math.ceil(f_inv * generation_rate))
        if pts < 2:
            pts = 2
        elif pts >= 4096:
            pts = 4096
        else:
            pass
        calc_samples = wfm_len_inc * pts
        min_wav_samples = int(wfm_len_min / (2 * wfm_len_inc)) * calc_samples
        if calc_samples >= wfm_len_min:
            samples = calc_samples
        else:
            samples = min_wav_samples
        sine_fr = 1 / (2 * pts)
        waveform_data = self.create_waveform_data(samples, sine_fr, phase_degree=90)
        waveform_data = [amplitude * data for data in waveform_data]
        waveform_data = [offset + data for data in waveform_data]
        sample_rate = pts * frequency  # waveform_dt = 1 / (sample_rate)
        gain = max([abs(data) for data in waveform_data])
        normalised_waveform = [data / gain for data in waveform_data]
        for ssc in self._sessions_sites_channels:
            ssc.cs_generate_sine_wave(
                normalised_waveform, sample_rate, gain, 0, enable_filter=enable_filter
            )
        return waveform_data


class TSMFGen(typing.NamedTuple):
    pin_query_context: typing.Any
    ssc: _NIFGenTSM
    sites: typing.List[int]


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: SMContext, pins: typing.List[str], sites: typing.List[int]):
    """
    Returns the pin-query context object for the given pins at given sites.

    Args:
        tsm_context (TSMContext): Semiconductor module Reference from the TestStand.
        pins (typing.List[str]): Pins names defined in the current the pinmap.
        sites (typing.List[int]): if you need to control only on specific sites,
        then provide site numbers. Defaults to [].

    Returns:
        TSMScope object :  for the selected pins. All instrument specific operations
        are available as properties and methods of this object.
    """
    pin_query_context, sessions, channels = tsm_context.pins_to_nifgen_sessions(pins)
    sites_out, pin_list_per_session = ni_dt_common.pin_query_context_to_channel_list(
        pin_query_context, [], sites
    )
    sscs: typing.List[_NIFGenSSC] = []
    for session, channel, pin_list in zip(sessions, channels, pin_list_per_session):
        sscs.append(_NIFGenSSC(session=session, channels=channel, pin_list=pin_list))
    fgen_tsm = _NIFGenTSM(sscs)
    return TSMFGen(pin_query_context, fgen_tsm, sites_out)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SMContext, options: dict = {}):
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
def close_sessions(tsm_context: SMContext):
    """Closes the sessions associated with the tsm context"""
    sessions = tsm_context.get_all_nifgen_sessions()
    for session in sessions:
        session.reset()
        session.close()


if __name__ == "__main__":
    pass
