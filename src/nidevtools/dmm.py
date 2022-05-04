
import typing

import nidmm
import nitsm.pinquerycontexts
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# Types Definition
PinQuery = nitsm.pinquerycontexts.PinQueryContext
PinsArg = typing.Union[str, typing.Sequence[str]]


class Resolution:
    Res_3_05 = 3.5
    Res_4_05 = 4.5
    Res_5_05 = 5.5
    Res_6_05 = 6.5
    Res_7_05 = 7.5


class InputResistance:
    IR_1_MOhm = 1e6
    IR_10_MOhm = 1e7
    IR_Greater_Than_10_GOhm = 1e10


class TSM:
    pin_query_context: PinQuery
    sessions: typing.Sequence[nidmm.session.Session]

    def __init__(self, pin_query_context: PinQuery, sessions: typing.Sequence[nidmm.session.Session]):
        self.pin_query_context = pin_query_context
        self.sessions = sessions

    def config_apperture_time(self, apperture_time: float, apperture_time_units: nidmm.ApertureTimeUnits):
        for session in self.sessions:
            session.aperture_time_units = apperture_time_units
            session.aperture_time = apperture_time

    def config_measurement(self,
                           resolution_in_digits: Resolution,
                           function: nidmm.Function,
                           range_raw: float,
                           input_resistance: InputResistance):
        for session in self.sessions:
            session.configure_measurement_digits(measurement_function=function,
                                                 range=range_raw,
                                                 resolution_digits=resolution_in_digits)
            session.input_resistance = input_resistance

    def abort(self):
        for session in self.sessions:
            session.abort()

    def initiate(self):
        for session in self.sessions:
            session.initiate()

    def measure(self):
        measurements = []
        for session in self.sessions:
            measurements.append(session.read())
        return measurements


def init_session(tsm: SMContext):
    instrument_list = tsm.get_all_nidmm_instrument_names()
    for instrument in instrument_list:
        session = nidmm.Session(resource_name=instrument, reset_device=True)
        tsm.set_nidmm_session(instrument_name=instrument, session=session)


def close_session(tsm: SMContext):
    sessions_list = tsm.get_all_nidmm_sessions()
    for session in sessions_list:
        session.reset()
        session.close()


def pins_to_sessions(tsm: SMContext, pins: PinsArg):
    pin_query_context, sessions = tsm.pins_to_nidmm_sessions(pins)
    return TSM(pin_query_context, sessions)
