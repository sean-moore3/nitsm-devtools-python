"""
This is nidmm wrapper for use with STS test codes
"""
import typing

import nidmm
import nitsm.pinquerycontexts
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# Types Definition
PinQuery = nitsm.pinquerycontexts.PinQueryContext
PinsArg = typing.Union[str, typing.Sequence[str]]


class Resolution:
    """
    DMM resolutions
    """

    Res_3_05 = 3.5
    Res_4_05 = 4.5
    Res_5_05 = 5.5
    Res_6_05 = 6.5
    Res_7_05 = 7.5


class InputResistance:
    """
    DMM Input Resistance
    """

    IR_1_MOhm = 1e6
    IR_10_MOhm = 1e7
    IR_Greater_Than_10_GOhm = 1e10


class TSMDMM:
    """
    Class to store the DMM Pin to sessions and pin query context info

    Returns:
        object: TSMDMM context object
    """

    pin_query_context: PinQuery
    sessions: typing.Sequence[nidmm.Session]

    def __init__(self, pin_query_context: PinQuery, sessions: typing.Sequence[nidmm.Session]):
        """
        constructor for TSMDMM class to store Pin query and sessions

        Args:
            pin_query_context (PinQuery): pin query context object stores the pin related info
            sessions (typing.Sequence[nidmm.session.Session]): sessions to perform various actions
            on the dmm instrument associated with it.
        """
        self.pin_query_context = pin_query_context
        self.sessions = sessions

    def configure_aperture_time(self, aperture_time: float, units: nidmm.ApertureTimeUnits):
        """
        Configures the measurement aperture time for the current configuration.  Aperture time is
        specified in units set by aperture_time_units.

        Args:
            aperture_time (float): On the NI 4070/4071/4072, the minimum aperture time is 8.89
                usec,  and the maximum aperture time is 149 sec. Any number of powerline cycles
                (PLCs) within the minimum and maximum ranges is allowed on the NI 4070/4071/4072.
                On the NI 4065 the minimum aperture time is 333 µs, and the maximum aperture time
                is 78.2 s. If setting the number of averages directly, the total measurement time
                is  aperture time X the number of averages, which must be less than 72.8 s. The
                aperture  times allowed are 333 µs, 667 µs, or multiples of 1.11 ms-for example
                1.11 ms, 2.22 ms,  3.33 ms, and so on. If you set an aperture time other than 333
                µs, 667 µs, or multiples  of 1.11 ms, the value will be coerced up to the next
                supported aperture time.
            units (nidmm.ApertureTimeUnits): Specifies the units of aperture time
                for the current configuration.The NI 4060 does not support an aperture time set in
                seconds.
        """
        for session in self.sessions:
            session.aperture_time_units = units
            session.aperture_time = aperture_time

    def configure_measurement(
        self,
        function: nidmm.Function,
        range_raw: float,
        resolution_in_digits: float,
        input_resistance: float,
    ):
        """
        Configures the common properties of the measurement. These properties include method,
        range, and resolution_in_digits.

        Args:
            function (enums.Function): Specifies the **measurement_function** used to acquire the
                measurement.The driver sets method to this value.

            range_raw (float): Specifies the range for the method specified in the
                **Measurement_Function** parameter. When frequency is specified in the
                **Measurement_Function** parameter, you must supply the minimum frequency expected
                in the **range** parameter. For example, you must type in 100 Hz if you are
                measuring 101 Hz or higher.For all other methods, you must supply a range that
                exceeds the value that you are measuring. For example, you must type in 10 V if you
                are measuring 9 V. range values are coerced up to the closest input range.The
                driver sets range to this value. The default is 0.02 V.
                +---------------------------+------+----------------------------------------------+
                | NIDMM_VAL_AUTO_RANGE_ON   | -1.0 | NI-DMM performs an Auto Range before acquiring
                                                     the measurement.                             |
                +---------------------------+------+----------------------------------------------+
                | NIDMM_VAL_AUTO_RANGE_OFF  | -2.0 | NI-DMM sets the Range to the current
                                                    auto_range_value and uses this range for all
                                                    subsequent measurements until the measurement
                                                    configuration is changed.                     |
                +---------------------------+------+----------------------------------------------+
                | NIDMM_VAL_AUTO_RANGE_ONCE | -3.0 | NI-DMM performs an Auto Range before acquiring
                                                    the measurement. The auto_range_value is stored
                                                    and used for all subsequent measurements until
                                                    the measurement configuration is changed.     |
                +---------------------------+------+----------------------------------------------+
                The NI 4050, NI 4060, and NI 4065 only support Auto Range when the
                trigger and sample trigger are set to IMMEDIATE.

            resolution_in_digits (float): Specifies the resolution of the measurement in digits.
                The driver sets resolution_digits property to this value. The PXIe-4080/4081/4082
                uses the resolution you specify. The NI 4065 and NI 4070/4071/4072 ignore this
                parameter when the **Range** parameter is set to NIDMM_VAL_AUTO_RANGE_ON (-1.0) or
                NIDMM_VAL_AUTO_RANGE_ONCE (-3.0). The default is 5½.
                NI-DMM ignores this parameter for capacitance and inductance measurements on the
                NI 4072. To achieve better resolution for such measurements, use the
                lc_number_meas_to_average property.

            input_resistance (float): Specifies the input resistance of the instrument.The NI 4050
                and NI 4060 are not supported.
        """
        for session in self.sessions:
            session.configure_measurement_digits(function, range_raw, resolution_in_digits)
            session.input_resistance = input_resistance

    def abort(self):
        """
        Aborts a previously initiated measurement and returns the DMM to the
        Idle state.
        """
        for session in self.sessions:
            session.abort()

    def initiate(self):
        """
        Initiates an acquisition. After you call this method, the DMM leaves
        the Idle state and enters the Wait-for-Trigger state. If trigger is set
        to Immediate mode, the DMM begins acquiring measurement data. Use
        fetch, fetch_multi_point, or fetch_waveform to
        retrieve the measurement data.
        """
        for session in self.sessions:
            session.initiate()

    def measure(self):
        """
        Acquires a single measurement from each session and returns the measured values.

        Returns:
            readings (list of float): The measured value returned from each DMM session.
        """
        measurements = []
        for session in self.sessions:
            measurements.append(session.read())
        return measurements


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm: SMContext, pins: PinsArg):
    """
    Returns the NI-DMM instrument sessions required to access the pin(s).

    Args:
        tsm (SMContext): _description_
        pins (PinsArg): The names of the pin(s) or pin group(s) to translate to instrument sessions.

    Returns:
        TSMDMM: TSM Session Object for DMM pins
    """
    pin_query_context, sessions = tsm.pins_to_nidmm_sessions(pins)
    return TSMDMM(pin_query_context, sessions)


@nitsm.codemoduleapi.code_module
def initialize_session(tsm: SMContext):
    """
    creates the sessions for all the niDMM resource string available in the tsm context for
    instruments.

    Args:
        tsm (SMContext): TestStand semiconductor module context
    """

    instrument_list = tsm.get_all_nidmm_instrument_names()
    for instrument in instrument_list:
        session = nidmm.Session(resource_name=instrument, reset_device=True)
        tsm.set_nidmm_session(instrument_name=instrument, session=session)


@nitsm.codemoduleapi.code_module
def close_session(tsm: SMContext):
    """
    Closes the sessions associated with the tsm context

    Args:
        tsm (SMContext): TestStand semiconductor module context
    """
    sessions_list = tsm.get_all_nidmm_sessions()
    for session in sessions_list:
        session.reset()
        session.close()


if __name__ == "__main__":
    pass
