"""
This is nidcpower wrapper for use with STS test codes
"""
import math
import re
import typing
from cmath import nan
from datetime import datetime
import nidcpower
import nidcpower.enums as enums
import nidcpower.errors
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
from . import common


class _ModelSupport:
    """
    supported models of ni dc power driver
    """

    ALL_MODELS = {
        "NI PXI-4110",
        "NI PXIe-4112",
        "NI PXIe-4113",
        "NI PXI-4130",
        "NI PXI-4132",
        "NI PXIe-4135",
        "NI PXIe-4136",
        "NI PXIe-4137",
        "NI PXIe-4138",
        "NI PXIe-4139",
        "NI PXIe-4140",
        "NI PXIe-4141",
        "NI PXIe-4142",
        "NI PXIe-4143",
        "NI PXIe-4144",
        "NI PXIe-4145",
        "NI PXIe-4147",
        "NI PXIe-4154",
        "NI PXIe-4162",
        "NI PXIe-4163",
    }

    DEFAULT_OUTPUT_STATE_0V = ALL_MODELS - {"NI PXIe-4112", "NI PXIe-4113"}
    POWER_LINE_FREQUENCY = ALL_MODELS - {"NI PXI-4110", "NI PXI-4130", "NI PXIe-4154"}


class ResourceMap:
    """Maps resources to channels."""

    def __init__(self, resource_string):
        self._map = {}
        resource_string = resource_string.replace(" ", "")
        channels = resource_string.split(",")
        for channel in channels:
            resource_name = channel.split("/")[0]
            if resource_name in self._map.keys():
                self._map[resource_name].add(channel)
            else:
                self._map[resource_name] = {channel}
        for instrument_name, channel_set in self._map.items():
            self._map[instrument_name] = ", ".join(channel_set)

    def __getitem__(self, item):
        return self._map[item]

    def __iter__(self):
        return self._map.values()  # iterate over the channels for each resource


class MeasurementMode(enums.Enum):
    """
    ni dcpower measurement mode
    """

    AUTO = 0
    """
    Enables the automatic selection of the best measurement mode for the instrument.
    """
    SOFTWARE_TRIGGER = 1
    """
    Performs measurements by sending a software trigger to the instrument. Typically yields fastest
    test times.
    """
    MEASURE_MULTIPLE = 2
    """
    Performs measurements on demand. Typically allows for easier debugging but takes longer to fetch
     measurements.
    """


# class SignalTypes(enums.SendSoftwareEdgeTriggerType, enums.Events):
#    pass


class CustomTransientResponse:
    """
    class to store and access the custom transient response settings
    """

    def __init__(
        self, gain_bandwidth: float, compensation_frequency: float, pole_zero_ratio: float
    ):
        """
        constructor for storing custom transient response

        Args:
            gain_bandwidth (float): gain bandwidth is stored as floating point number
            compensation_frequency (float): compensation frequency is stored as floating point
                number
            pole_zero_ratio (float): pole zero ration is stored as floating point number
        """
        self._gain_bandwidth = gain_bandwidth
        self._compensation_frequency = compensation_frequency
        self._pole_zero_ratio = pole_zero_ratio

    @property
    def gain_bandwidth(self):
        """To read and write gain bandwidth

        Returns:
            float: returns the gain stored in object
        """
        return self._gain_bandwidth

    @property
    def compensation_frequency(self):
        """To read and write compensation frequency

        Returns:
            float: returns the compensation frequency stored in object
        """
        return self._compensation_frequency

    @property
    def pole_zero_ratio(self):
        """To read and write pole zero ratio

        Returns:
            float: returns the pole zero ratio stored in object
        """
        return self._pole_zero_ratio


class ChannelProperties(typing.NamedTuple):
    """
    for storing several the channel properties in a single object
    """

    instrument_name: str
    model: str
    channel: str
    pin: str
    output_function: str
    level: float
    limit: float
    voltage_range: float
    current_range: float
    sense: str
    aperture_time: float
    transient_response: str
    output_enabled: str
    output_connected: str


def model_to_ranges(model: int, channel: int):
    """Returns current, voltage and resistance (for voltage and current) ranges"""
    current_ranges = []
    voltage_ranges = []
    resistor_v_ranges = []
    resistor_i_ranges = []
    if model == 4110:
        current_ranges = [1]
        if channel == 0:
            voltage_ranges = [6]
        elif channel == 1:
            voltage_ranges = [20]
        elif channel == 2:
            voltage_ranges = [-20]
    elif model == 4112:
        current_ranges = [1]
        voltage_ranges = [60]
    elif model == 4113:
        current_ranges = [6]
        voltage_ranges = [10]
    elif model == 4132:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
        voltage_ranges = [10, 100]
    elif model == 4135:
        resistor_v_ranges = [500000000, 5000000, 50000, 5000, 500, 50, 5]
        resistor_i_ranges = resistor_v_ranges
        current_ranges = [10e-9, 1e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
        voltage_ranges = [0.6, 6, 20, 200]
    elif model == 4136:
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
        voltage_ranges = [0.6, 6, 20, 200]
    elif model == 4137:
        resistor_v_ranges = [5000000, 500000, 50000, 5000, 500, 50, 5]
        resistor_i_ranges = resistor_v_ranges
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
        voltage_ranges = [0.6, 6, 20, 200]
    elif model == 4138:
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1, 3]
        voltage_ranges = [0.6, 6, 60]
    elif model == 4139:
        resistor_v_ranges = [5000000, 500000, 50000, 5000, 500, 50, 5, 0.5]
        resistor_i_ranges = resistor_v_ranges
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1, 3]
        voltage_ranges = [0.6, 6, 60]
    elif model == 4140:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
        voltage_ranges = [10]
    elif model == 4141:
        resistor_v_ranges = [100000, 10000, 1000, 100, 10]
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
        voltage_ranges = [10]
    elif model == 4142:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.15]
        voltage_ranges = [24]
    elif model == 4143:
        resistor_v_ranges = [100000, 10000, 1000, 100, 6.66]
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.15]
        voltage_ranges = [24]
    elif model == 4144:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1, 0.5]
        voltage_ranges = [6]
    elif model == 4145:
        resistor_v_ranges = [50000, 5000, 500, 50, 5, 1]
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1, 0.5]
        voltage_ranges = [6]
    elif model == 4147:
        resistor_v_ranges = [4000000, 400000, 40000, 4000, 400, 40, 1.25]
        resistor_i_ranges = [2500000, 250000, 25000, 2500, 250, 25, 750]
        voltage_ranges = [1, 8]
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 3]
    elif model == 4162:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
        voltage_ranges = [24]
    elif model == 4163:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.05]
        voltage_ranges = [24]
    return [voltage_ranges, current_ranges, resistor_v_ranges, resistor_i_ranges]


class _NIDCPowerSSC:
    """
    _Site specific _Session and _Channel.
    Each object of this class is used to store info for a specified pin under specific Site.
    To store a _Session and _Channel(s) for different _Site(s) we need an array of this class
    object.
    Prefix cs is used in all methods that operates on a given channels in a session.
    These are for internal use only and can be changed any time.
    External module should not use these methods with prefix 'cs_' directly.
    """

    def __init__(self, session: nidcpower.Session, channels: str, pins: str):
        """
        NI DC power SSC class initialisation for session related operations.

        Args:
            session (nidcpower.Session): This is a shared session. Need to use this with channel
                subset notation.
            channels (str): List of channels that are part of this session.
            pins (str): List of pins that are part of this session.
        """
        self._session = session  # mostly shared session depends on pinmap file.
        self._channels = channels  # specific channel(s) of that session
        self._pins = pins  # pin names mapped to the channels
        self._ch_session = session.channels[channels]
        # To operate on session on very specific channel(s)
        self._ch_list = channels.split(",")  # channels in a list for internal operations
        self.power_line_frequency = 60.0
        self.measure_multiple_only = False

    @property
    def session(self):
        """
        get the stored nidcpower session in which the channels are mapped for the selected pins

        Returns:
            session: This session contains the selected pin's channels and may contain other pin's
            channels
        """
        return self._session  #

    @property
    def cs_channels(self):
        """
        get the stored channel list

        Returns:
            str: channels
        """
        return self._channels

    @property
    def cs_session(self):
        """
        returns the sessions specific to the channels of the pins specified

        Returns:
            session: subset of session
        """
        return self._ch_session  # This session will operate only on subset of channels

    def cs_abort(self):
        """
        Transitions the specified channel(s) from the Running state to the
        Uncommitted state. If a sequence is running, it is stopped. Any
        configuration methods called after this method are not applied until
        the initiate method is called. If power output is enabled
        when you call the abort method, the output channels remain
        in their current state and continue providing power.

        Use the ConfigureOutputEnabled method to disable power
        output on a per-channel basis. Use the reset method to
        disable output on all channels.

        Returns:
            none: when aborted otherwise exception
        """
        return self._ch_session.abort()

    def cs_commit(self):
        """
        Applies previously configured settings to the specified channel(s) under current session.
        Calling this method moves the NI-DCPower session from the Uncommitted state into
        the Committed state. After calling this method, modifying any
        property reverts the NI-DCPower session to the Uncommitted state. Use
        the initiate method to transition to the Running state.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        return self._ch_session.commit()

    def cs_initiate(self):
        """
        Starts generation or acquisition, causing the specified channel(s) to
        leave the Uncommitted state or Committed state and enter the Running
        state. To return to the Uncommitted state call the abort
        method.

        Returns:
            context manager: This method will return a Python context manager that will
            initiate on entering and abort on exit.
        """
        return self._ch_session.initiate()

    def cs_reset(self):
        """
        Resets the specified channel(s) to a known state. This method disables power
        generation, resets session properties to their default values, commits
        the session properties, and leaves the session in the Uncommitted state.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        return self._ch_session.reset()

    def cs_configure_aperture_time_with_abort_and_initiate(
        self, aperture_time=16.667e-03, aperture_time_units=enums.ApertureTimeUnits.SECONDS
    ):
        """
        Aborts current operation and configures the measurement aperture time for the
        current channel configuration. Later initiates the session.
        Aperture time is specified in the units set by the aperture_time_units property.
        for information about supported devices.Refer to the Aperture Time topic in the
        NI DC Power Supplies and SMUs Help for more information about how to configure your
        measurements and for information about valid values.

        Args:
            aperture_time (float, optional): in seconds by default. Defaults to 16.667e-03.
            aperture_time_units (enum, optional): seconds. Defaults to
                enums.ApertureTimeUnits.SECONDS.
        """
        self._ch_session.abort()
        self._ch_session.aperture_time = aperture_time
        self._ch_session.aperture_time_units = aperture_time_units
        self._ch_session.initiate()

    def cs_configure_aperture_time(
        self, aperture_time=16.667e-03, aperture_time_units=enums.ApertureTimeUnits.SECONDS
    ):
        """
        Configures the measurement aperture time for the channel configuration.
        Aperture time is specified in the units set by the aperture_time_units property.
        for information about supported devices.
        Refer to the Aperture Time topic in the NI DC Power Supplies and SMUs Help for
        more information about how to configure your measurements and for information about valid
        values.

        Args:
            aperture_time (float, optional): in seconds by default. Defaults to 16.667e-03.
            aperture_time_units (enum, optional): seconds. Defaults to
                enums.ApertureTimeUnits.SECONDS.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        return self._ch_session.configure_aperture_time(aperture_time, aperture_time_units)

    def cs_configure_power_line_frequency(self, power_line_frequency=60.0):
        """
        Stores the session object variable power line frequency for other operations
        that uses power line frequency.

        Args:
            power_line_frequency (float, optional): in hertz. Defaults to 60.0.
        """
        self.power_line_frequency = power_line_frequency
        self._ch_session.power_line_frequency = power_line_frequency

    def cs_configure_sense(self, sense=enums.Sense.REMOTE):
        """
        configures the sense for all channels in the session that are part to pin-query context

        Args:
            sense (enum, optional): sensing at local or remote. Defaults to enums.Sense.REMOTE.
        """
        self._ch_session.sense = sense

    def cs_configure_settings(
        self,
        aperture_time=16.667e-03,
        source_delay=0.0,
        sense=enums.Sense.REMOTE,
        aperture_time_unit=enums.ApertureTimeUnits.SECONDS,
        transient_response=enums.TransientResponse.NORMAL,
    ):
        """
        Configures the measurement settings for the current session

        Args:
            aperture_time (float or int, optional): depends on the unit specified in the argument.
                Defaults to 16.667e-03.
            source_delay (float, optional): in seconds. Defaults to 0.0.
            sense (enum, optional): measurement to use Hi and Lo sense lines or not.
                Defaults to enums.Sense.REMOTE.
            aperture_time_unit (enum, optional): based on model this value needs to be set.
                Defaults to enums.ApertureTimeUnits.SECONDS.
            transient_response (enum, optional): Controls how to control the response based on load.
                Defaults to enums.TransientResponse.NORMAL.
        """
        self._ch_session.abort()
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        temp = aperture_time
        if aperture_time_unit == enums.ApertureTimeUnits.POWER_LINE_CYCLES:
            temp = temp / self.power_line_frequency

        if match == "4110":
            self._ch_session.source_delay = source_delay
            self._ch_session.samples_to_average = 3000 * temp
        elif match == "4130":
            self._ch_session.source_delay = source_delay
            self._ch_session.samples_to_average = 3000 * temp
            if self._ch_session.channels == "1":
                self._ch_session.sense = sense
        elif match == "4154":
            self._ch_session.source_delay = source_delay
            self._ch_session.samples_to_average = 300000 * temp
            self._ch_session.sense = sense
            if self._ch_session.channels == "0":
                self._ch_session.transient_response = transient_response
        elif match == "4132":
            self._ch_session.aperture_time_units = aperture_time_unit
            self._ch_session.aperture_time = aperture_time
            self._ch_session.source_delay = source_delay
            self._ch_session.sense = sense
            self._ch_session.sense = sense
        elif (match == "4112") or (match == "4112"):
            self._ch_session.aperture_time_units = aperture_time_unit
            self._ch_session.aperture_time = aperture_time
            self._ch_session.source_delay = source_delay
        else:  # All properties supported
            self._ch_session.transient_response = transient_response
            self._ch_session.aperture_time_units = aperture_time_unit
            self._ch_session.aperture_time = aperture_time
            self._ch_session.source_delay = source_delay
            self._ch_session.sense = sense

    def cs_get_aperture_time_in_seconds(self):
        """
        get the aperture time in seconds for all channels in the session. if the model has different
        units convert them into seconds.

        Returns:
            float: aperture time in seconds
        """
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        all_supported_models = [
            "4135",
            "4136",
            "4137",
            "4138",
            "4139",
            "4140",
            "4141",
            "4142",
            "4143",
            "4144",
            "4162",
            "4163",
        ]
        actual_aperture_time = self._ch_session.aperture_time_units
        if match in all_supported_models + ["4112", "4113", "4132"]:
            if self._ch_session.aperture_time_units == enums.ApertureTimeUnits.POWER_LINE_CYCLES:
                actual_aperture_time = (
                    self._ch_session.aperture_time_units / self._ch_session.power_line_frequency
                )

        if match in ["4110", "4130"]:
            actual_aperture_time = self._ch_session.samples_to_average / 3000
        elif match == "4154":
            actual_aperture_time = self._ch_session.samples_to_average / 300000
        return actual_aperture_time

    def cs_get_power_line_frequency(self):
        """
        get the power line frequency stored in the object or from the instrument based on the
        supported model

        Returns:
            float: power line frequency in hertz
        """
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        configured_power_line_frequency = self._ch_session.power_line_frequency
        if match in ["4110", "4130"]:
            configured_power_line_frequency = self.power_line_frequency
        elif match == "4154":
            configured_power_line_frequency = self.power_line_frequency
        return configured_power_line_frequency

    def cs_query_in_compliance(self):
        """
        get the in compliance status of each channel under the current session.

        Returns:
            bool list: list of status one for each channel
        """
        compliance_states = []
        for ch in self._ch_list:
            comp = self.session.channels[ch].query_in_compliance()  # access one channel at a time.
            compliance_states.append(comp)
        return compliance_states

    def cs_query_output_state(self, output_state: nidcpower.OutputStates):
        """
        compares the state of the output against the desired state

        Args:
            output_state (nidcpower.OutputStates): desired output state

        Returns:
            bool list: indicates output state is same as desired state or not.
        """
        output_states = []
        for ch in self._ch_list:
            state = self.session.channels[ch].query_output_state(
                output_state
            )  # access one channel at a time.
            output_states.append(state)
        return output_states

    def cs_configure_current_level_range(self, current_level_range=0.0):
        """
        updates the property

        Args:
            current_level_range (float, optional): updates the range property. Defaults to 0.0.
        """
        self._ch_session.current_level_range = current_level_range

    def cs_configure_current_level(self, current_level=0.0):
        """
        updates the current level property.

        Args:
            current_level (float, optional): updates the level property. Defaults to 0.0.
        """
        self._ch_session.current_level = current_level

    def cs_configure_single_pt_force_current_asymmetric_limits(
        self,
        current_level=0.0,
        current_level_range=0.0,
        voltage_limit_high=0.0,
        voltage_limit_low=0.0,
        voltage_limit_range=0.0,
    ):
        """
        configure single point force dc current with asymmetric voltage limits

        Args:
            current_level (float, optional): current in amps to set. Defaults to 0.0.
            current_level_range (float, optional): current level range to set in amps. Defaults to
                0.0.
            voltage_limit_high (float, optional): voltage limit high in volts. Defaults to 0.0.
            voltage_limit_low (float, optional): voltage limit low in volts. Defaults to 0.0.
            voltage_limit_range (float, optional): voltage limit range in volts. Defaults to 0.0.
        """
        self._ch_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._ch_session.output_function = nidcpower.OutputFunction.DC_CURRENT
        self._ch_session.current_level = current_level
        self._ch_session.voltage_limit_high = voltage_limit_high
        self._ch_session.voltage_limit_low = voltage_limit_low
        c_value = current_level_range
        if c_value == 0.0:
            c_value = abs(current_level)
        self._ch_session.current_level_range = c_value
        v_value = voltage_limit_range
        if v_value == 0.0:
            v_value = max(abs(voltage_limit_high), abs(voltage_limit_low))
        self._ch_session.voltage_limit_range = v_value
        self._ch_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.ASYMMETRIC

    def cs_configure_single_pt_force_current_symmetric_limits(
        self, current_level=0.0, current_level_range=0.0, voltage_limit=0.0, voltage_limit_range=0.0
    ):
        """
         configure single point force dc current with symmetric voltage limits

        Args:
            current_level (float, optional): current in amps to set. Defaults to 0.0.
            current_level_range (float, optional): current level range to set in amps. Defaults to
                0.0.
            voltage_limit (float, optional): voltage limit in volts. Defaults to 0.0.
            voltage_limit_range (float, optional): voltage limit range in volts. Defaults to 0.0.
        """
        self._ch_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._ch_session.output_function = nidcpower.OutputFunction.DC_CURRENT
        self._ch_session.current_level = current_level
        self._ch_session.voltage_limit = voltage_limit
        c_value = current_level_range
        if c_value == 0.0:
            c_value = abs(current_level)
        self._ch_session.current_level_range = c_value
        v_value = voltage_limit_range
        if v_value == 0.0:
            v_value = abs(voltage_limit)
        self._ch_session.voltage_limit_range = v_value
        self._ch_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.SYMMETRIC

    def cs_configure_voltage_limit_range(self, voltage_limit_range=0.0):
        """
        Specifies the voltage limit range, in volts, for the specified pins(s). The range defines
        the valid values to which the voltage limit can be set. Use the voltage_limit_autorange
        property to enable automatic selection of the voltage limit range. The voltage_limit_range
        property is applicable only if the output_function property is set to
        OutputFunction.DC_CURRENT.

        Args:
            voltage_limit_range (float, optional): voltage limit range to set in volts. Defaults to
                0.0.
        """
        self._ch_session.voltage_limit_range = voltage_limit_range

    def cs_configure_voltage_limit(self, voltage_limit=0.0):
        """
        Specifies the voltage limit, in volts, that the output cannot exceed when generating the
        desired current level on the specified channels. This property is applicable only if the
        output_function property is set to OutputFunction.DC_CURRENT and the
        compliance_limit_symmetry property is set to ComplianceLimitSymmetry.SYMMETRIC.
        The valid values for this property are defined by the values to which the
        voltage_limit_range property is set.


        Args:
            voltage_limit (float, optional): _description_. Defaults to 0.0.
        """
        self._ch_session.voltage_limit = voltage_limit

    def cs_force_current_asymmetric_limits(
        self,
        current_level=0.0,
        current_level_range=0.0,
        voltage_limit_high=0.0,
        voltage_limit_low=0.0,
        voltage_limit_range=0.0,
    ):
        """
        configure and commit session for forcing current with asymmetric voltage limits

        Args:
            current_level (float, optional): current level in amps. Defaults to 0.0.
            current_level_range (float, optional): current level range in amps. Defaults to 0.0.
            voltage_limit_high (float, optional): voltage high limit in volts. Defaults to 0.0.
            voltage_limit_low (float, optional): voltage low limit in volts. Defaults to 0.0.
            voltage_limit_range (float, optional): voltage range to set in volts. Defaults to 0.0.
        """
        self._ch_session.abort()
        self.cs_configure_single_pt_force_current_asymmetric_limits(
            current_level,
            current_level_range,
            voltage_limit_high,
            voltage_limit_low,
            voltage_limit_range,
        )
        self._ch_session.commit()

    def cs_force_current_symmetric_limits(
        self, current_level=0.0, current_level_range=0.0, voltage_limit=0.0, voltage_limit_range=0.0
    ):
        """
        configure and commit session for forcing current with symmetric voltage limits

        Args:
            current_level (float, optional): current level in amps. Defaults to 0.0.
            current_level_range (float, optional): current level range in amps. Defaults to 0.0.
            voltage_limit (float, optional): voltage high limit in volts. Defaults to 0.0.
            voltage_limit_range (float, optional): voltage range to set in volts. Defaults to 0.0.
        """
        self._ch_session.abort()
        self.cs_configure_single_pt_force_current_symmetric_limits(
            current_level, current_level_range, voltage_limit, voltage_limit_range
        )
        self._ch_session.commit()

    def cs_configure_current_limit_range(self, current_limit_range=0.0):
        """
        Specifies the current limit range, in amps, for the specified pin(s). The range defines the
        valid value to which the current limit can be set. Use the current_limit_autorange property
        to enable automatic selection of the current limit range.The current_limit_range property
        is applicable only if the output_function property is set to OutputFunction.DC_VOLTAGE.
        output_enabled property for more information about enabling the output channel.

        Args:
            current_limit_range (float, optional): _description_. Defaults to 0.0.
        """
        self._ch_session.current_limit_range = current_limit_range

    def cs_configure_current_limit(self, current_limit=0.0):
        """
        Specifies the current limit, in amps, that the output cannot exceed when generating the
        desired voltage level on the specified pin(s). This property is applicable only if the
        output_function property is set to OutputFunction.DC_VOLTAGE and the
        compliance_limit_symmetry property is set to ComplianceLimitSymmetry.SYMMETRIC.
        output_enabled property for more information about enabling the output channel.
        The valid values for this property are defined by the values to which current_limit_range
        property is set.The channel must be enabled for the specified current limit to take effect.

        Args:
            current_limit (float, optional): _description_. Defaults to 0.0.
        """
        self._ch_session.current_limit = current_limit

    def cs_configure_single_point_force_dc_voltage_asymmetric_limits(
        self,
        voltage_level=0.0,
        voltage_level_range=0.0,
        current_limit_high=0.0,
        current_limit_low=0.0,
        current_limit_range=0.0,
    ):
        """
        configure and commit for single point dc voltage with asymmetric current limits

        Args:
            voltage_level (float, optional): voltage level in volts. Defaults to 0.0.
            voltage_level_range (float, optional): voltage level range in volts. Defaults to 0.0.
            current_limit_high (float, optional): current high limits in amps. Defaults to 0.0.
            current_limit_low (float, optional): current low limits in amps. Defaults to 0.0.
            current_limit_range (float, optional): current limit range in amps. Defaults to 0.0.
        """
        self._ch_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._ch_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self._ch_session.voltage_level = voltage_level
        self._ch_session.current_limit_high = current_limit_high
        self._ch_session.current_limit_low = current_limit_low
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._ch_session.voltage_level_range = v_value
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = max(abs(current_limit_high), abs(current_limit_low))
        self._ch_session.current_limit_range = c_value
        self._ch_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.ASYMMETRIC

    def cs_configure_single_point_force_dc_voltage_symmetric_limits(
        self, voltage_level=0.0, voltage_level_range=0.0, current_limit=0.0, current_limit_range=0.0
    ):
        """
        configure dc power supply pins to force single point voltage with symmetric current limits

        Args:
            voltage_level (float, optional): voltage level in volts. Defaults to 0.0.
            voltage_level_range (float, optional): voltage level range in volts. Defaults to 0.0.
            current_limit (float, optional): current limit in amps. Defaults to 0.0.
            current_limit_range (float, optional): current limit range in amps. Defaults to 0.0.
        """
        self._ch_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._ch_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self._ch_session.voltage_level = voltage_level
        self._ch_session.current_limit = current_limit
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._ch_session.voltage_level_range = v_value
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = abs(current_limit)
        self._ch_session.current_limit_range = c_value
        self._ch_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.SYMMETRIC

    def cs_configure_voltage_level_range(self, voltage_level_range=0.0):
        """
        Specifies the voltage level range, in volts, for the specified pin(s).The range defines the
        valid values to which the voltage level can be set. Use the voltage_level_autorange
        property to enable automatic selection of the voltage level range. The voltage_level_range
        property is applicable only if the output_function property is set to
        OutputFunction.DC_VOLTAGE.output_enabled property for more information about enabling the
        output channel.

        Args:
            voltage_level_range (float, optional): voltage level range volts. Defaults to 0.0.
        """
        self._ch_session.voltage_level_range = voltage_level_range

    def cs_configure_voltage_level(self, voltage_level=0.0):
        """
        Specifies the voltage level, in volts, that the device attempts to generate on the
        specified pin(s). This property is applicable only if the output_function property is set
        to OutputFunction.DC_VOLTAGE. output_enabled property for more information about enabling
        the output channel.The valid values for this property are defined by the values you specify
        for the voltage_level_range property.The pin must be enabled for the specified voltage
        level to take effect.

        Args:
            voltage_level (float, optional): voltage level in volts . Defaults to 0.0.
        """
        self._ch_session.voltage_level = voltage_level

    def cs_force_voltage_asymmetric_limits(
        self,
        voltage_level=0.0,
        voltage_level_range=0.0,
        current_limit_high=0.0,
        current_limit_low=0.0,
        current_limit_range=0.0,
    ):
        """
        configures and commits to force single point dc voltage with asymmetric current limits

        Args:
            voltage_level (float, optional): voltage level in volts. Defaults to 0.0.
            voltage_level_range (float, optional): voltage level range in volts. Defaults to 0.0.
            current_limit_high (float, optional): current high limits in amps. Defaults to 0.0.
            current_limit_low (float, optional): current low limits in amps. Defaults to 0.0.
            current_limit_range (float, optional): current limit range in amps. Defaults to 0.0.
        """
        self._ch_session.abort()
        self.cs_configure_single_point_force_dc_voltage_asymmetric_limits(
            voltage_level,
            voltage_level_range,
            current_limit_high,
            current_limit_low,
            current_limit_range,
        )
        self._ch_session.commit()

    def cs_force_voltage_symmetric_limits(
        self, voltage_level=0.0, voltage_level_range=0.0, current_limit=0.0, current_limit_range=0.0
    ):
        """
        configures and commits to force single point dc voltage with symmetric current limits

        Args:
            voltage_level (float, optional): voltage level in volts. Defaults to 0.0.
            voltage_level_range (float, optional): voltage level range in volts. Defaults to 0.0.
            current_limit (float, optional): current limit in amps. Defaults to 0.0.
            current_limit_range (float, optional): current limit range in amps. Defaults to 0.0.
        """
        self._ch_session.abort()
        self.cs_configure_single_point_force_dc_voltage_symmetric_limits(
            voltage_level, voltage_level_range, current_limit, current_limit_range
        )
        self._ch_session.commit()

    def cs_configure_source_adapt(
        self, voltage_ctr: CustomTransientResponse, current_ctr: CustomTransientResponse
    ):
        """
        configure the source adapt settings for custom transient response for voltage current

        Args:
            voltage_ctr (CustomTransientResponse): transient response settings for voltage
            current_ctr (CustomTransientResponse): transient response settings for current
        """
        self._ch_session.transient_response = enums.TransientResponse.CUSTOM
        self._ch_session.voltage_gain_bandwidth = voltage_ctr.gain_bandwidth
        self._ch_session.voltage_compensation_frequency = voltage_ctr.compensation_frequency
        self._ch_session.voltage_pole_zero_ratio = voltage_ctr.pole_zero_ratio
        self._ch_session.current_gain_bandwidth = current_ctr.gain_bandwidth
        self._ch_session.current_compensation_frequency = current_ctr.compensation_frequency
        self._ch_session.current_pole_zero_ratio = current_ctr.pole_zero_ratio

    def cs_configure_transient_response(self, transient_response=enums.TransientResponse.NORMAL):
        """
        Specifies the transient response.Default Value: TransientResponse.NORMAL. This property is
        not supported by all devices.

        Args:
            transient_response (TransientResponse, optional): specifies custom response settings or
            normal. Defaults to enums.TransientResponse.NORMAL.
        """
        self._ch_session.transient_response = transient_response

    def cs_get_source_adapt_settings(self):
        """
        get the transient response settings for one session

        Returns:
            tuple: transient response type, Voltage T.R settings, Current T.R. settings
        """
        transient_response = self._ch_session.transient_response
        v_gain_bw = self._ch_session.voltage_gain_bandwidth
        v_comp_fr = self._ch_session.voltage_compensation_frequency
        v_pole_0_ratio = self._ch_session.voltage_pole_zero_ratio
        i_gain_bw = self._ch_session.current_gain_bandwidth
        i_comp_fr = self._ch_session.current_compensation_frequency
        i_pole_0_ratio = self._ch_session.current_pole_zero_ratio
        voltage_ctr = CustomTransientResponse(v_gain_bw, v_comp_fr, v_pole_0_ratio)
        current_ctr = CustomTransientResponse(i_gain_bw, i_comp_fr, i_pole_0_ratio)
        return transient_response, voltage_ctr, current_ctr

    def cs_configure_output_connected(self, output_connected=False):
        """
        Specifies whether the output relay is connected (closed) or disconnected (open). The
        output_enabled property does not change based on this property; they are independent of
        each other.Set this property to False inorder to disconnect the output terminal from the
        output. to the output terminal might discharge unless the relay is disconnected. Excessive
        connecting and disconnecting of the output can cause premature wear on the relay.

        Note: Only disconnect the output when disconnecting is necessary for your application. For
        example, a battery connected

        Args:
            output_connected (bool, optional): controls the output relay. Defaults to False.
        """
        self._ch_session.output_connected = output_connected

    def cs_configure_output_enabled(self, output_enabled=False):
        """
        Specifies whether the output is enabled (True) or disabled (False).
        Depending on the value you specify for the output_function property, you also must set the
        voltage level or current level in addition to enabling the output the initiate method.
        Refer to the Programming States topic in the NI DC Power Supplies and SMUs Help for more
        information about NI-DCPower programming states. Default Value: The default value is True
        if you use the __init__ method to open the session. Otherwise, the default value is False,
        including when you use a calibration session or the deprecated programming model.

        Note: If the session is in the Committed or Uncommitted states, enabling the output does
        not take effect until you call the Init session

        Args:
            output_enabled (bool, optional): selects the output to be enabled or not. Defaults to
            False.
        """
        self._ch_session.output_enabled = output_enabled

    def cs_configure_output_function(self, output_function=nidcpower.OutputFunction.DC_VOLTAGE):
        """
        Configures the method to generate on the specified channel(s).
        When OutputFunction.DC_VOLTAGE is selected, the device generates the desired voltage level
        on the output as long as the output current is below the current limit. You can use the
        following properties to configure the channel when OutputFunction.DC_VOLTAGE is selected:
        voltage_level
        current_limit
        current_limit_high
        current_limit_low
        voltage_level_range
        current_limit_range
        compliance_limit_symmetry
        When OutputFunction.DC_CURRENT is selected, the device generates the desired current level
        on the output as long as the output voltage is below the voltage limit. You can use the
        following properties to configure the channel when OutputFunction.DC_CURRENT is selected:
        current_level
        voltage_limit
        voltage_limit_high
        voltage_limit_low
        current_level_range
        voltage_limit_range
        compliance_limit_symmetry


        Args:
            output_function (nidcpower.OutputFunction, optional): selects the output function to be
            dc_voltage or dc_current. Defaults to nidcpower.OutputFunction.DC_VOLTAGE.
        """
        self._ch_session.output_function = output_function

    def cs_configure_output_resistance(self, output_resistance=0.0):
        """
        Specifies the output resistance for the selected pin(s).This property is available only
        when you set the output_function property on a support device. Default Value: 0.0

        Args:
            output_resistance (float, optional): resistance value in ohms. Defaults to 0.0.
        """
        self._ch_session.output_resistance = output_resistance

    def cs_configure_source_delay(self, source_delay=0.01667):
        """
        Determines when, in seconds, the device generates the Source Complete event, potentially
        starting a measurement if the measure_when property is set to
        MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE.
        Refer to the Single Point Source Mode and Sequence Source Mode topics for more information.

        Note:
        Refer to Supported Properties by Device for information about supported devices.


        Args:
            source_delay (float, optional): hightime.timedelta, datetime.timedelta, or float in
            seconds. Defaults to 0.01667.Valid Values: 0 to 167 seconds.
        """
        self._ch_session.source_delay = source_delay

    def cs_configure_source_mode(self, source_mode=nidcpower.SourceMode.SINGLE_POINT):
        """
        Specifies whether to run a single output point or a sequence. Refer to the Single Point
        Source Mode and Sequence Source Mode topics in the NI DC Power Supplies and SMUs Help for
        more information about source modes.
        Default value: SourceMode.SINGLE_POINT

        Args:
            source_mode (nidcpower.SourceMode, optional): configures the single point or sequence.
            Defaults to nidcpower.SourceMode.SINGLE_POINT.
        """
        self._ch_session.source_mode = source_mode

    def cs_get_smu_model(self):
        """
        get the smu model of the pin

        Returns:
            model_number (str): pxi model number of the instrument to which the pin is connected.
        """
        smu_model_str = re.search("\d\d\d\d", self.session.instrument_model, re.RegexFlag.ASCII)[0]
        # This will throw error if different types / models of instruments are under same session.
        smu_model_number = int(smu_model_str)
        return smu_model_number

    def cs_get_max_current(self):
        """
        gets the maximum current that can be supplied to the selected pin

        Returns:
            current_in_amps (float): maximum current that can be drawn in amps
        """
        smu_model_number = self.cs_get_smu_model()
        # channel_number = int(self.channels)
        channel_number = 0
        all_ranges = model_to_ranges(smu_model_number, channel_number)
        current_ranges = all_ranges[1]  # V_ranges, current_ranges, R_v, R_i
        max_current = current_ranges[-1]  # this throws exception if ranges is empty list
        return max_current

    def cs_configure_measurements(self, mode=MeasurementMode.AUTO):
        """
        configure the measurement mode to be auto by default, otherwise the value specified by the
        parameter passed. Then configures additional settings that are required by the measurement
        mode.

        Args:
            mode (MeasurementMode, optional): . Defaults to MeasurementMode.AUTO.
        """
        self._ch_session.abort()
        if self.measure_multiple_only:
            mode = MeasurementMode.MEASURE_MULTIPLE
        if mode == MeasurementMode.AUTO:
            model = self.cs_get_smu_model()
            if model == 4110 or model == 4130:
                mode = MeasurementMode.MEASURE_MULTIPLE
            else:
                mode = MeasurementMode.SOFTWARE_TRIGGER
        if mode == MeasurementMode.SOFTWARE_TRIGGER:
            self._ch_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            self._ch_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
            self._ch_session.measure_record_length = 1
        else:
            self._ch_session.measure_when = nidcpower.MeasureWhen.ON_DEMAND

    def cs_configure_export_signal(self, signal: enums.SendSoftwareEdgeTriggerType, terminal):
        """
        configures the signal to be exported on the specified output terminal. when the output
        terminal is assigned and read back we will get fully qualified name.

        Args:
            signal (Signal): signal to be exported
            terminal (str): output terminal on which the signal is exported.

        Returns:
            terminal_name (str) : fully qualified output terminal name
        """

        if signal == enums.SendSoftwareEdgeTriggerType.START:
            self._ch_session.exported_start_trigger_output_terminal = terminal
            terminal_name = self._ch_session.exported_start_trigger_output_terminal
        elif signal == enums.SendSoftwareEdgeTriggerType.SOURCE:
            self._ch_session.exported_source_trigger_output_terminal = terminal
            terminal_name = self._ch_session.exported_source_trigger_output_terminal
        elif signal == enums.SendSoftwareEdgeTriggerType.MEASURE:
            self._ch_session.exported_measure_trigger_output_terminal = terminal
            terminal_name = self._ch_session.exported_measure_trigger_output_terminal
        elif signal == enums.SendSoftwareEdgeTriggerType.SEQUENCE_ADVANCE:
            self._ch_session.exported_sequence_advance_trigger_output_terminal = terminal
            terminal_name = self._ch_session.exported_sequence_advance_trigger_output_terminal
        elif signal == enums.SendSoftwareEdgeTriggerType.PULSE:
            self._ch_session.exported_pulse_trigger_output_terminal = terminal
            terminal_name = self._ch_session.exported_pulse_trigger_output_terminal
        else:
            terminal_name = terminal
        return terminal_name

    def cs_send_software_edge_trigger(
        self, trigger_to_send=enums.SendSoftwareEdgeTriggerType.MEASURE
    ):
        """
        Asserts the specified trigger. This method can override an external edge trigger.

        Args:
            trigger_to_send (enums.SendSoftwareEdgeTriggerType): Specifies which trigger to assert.
            Defaults to enums.SendSoftwareEdgeTriggerType.MEASURE.
            **Defined Values:**
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_START_TRIGGER            | Asserts the Start trigger.            |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SOURCE_TRIGGER           | Asserts the Source trigger.           |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_MEASURE_TRIGGER          | Asserts the Measure trigger.          |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SEQUENCE_ADVANCE_TRIGGER | Asserts the Sequence Advance trigger. |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_PULSE_TRIGGER            | Asserts the Pulse trigger.            |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SHUTDOWN_TRIGGER         | Asserts the Shutdown trigger.         |
            +----------------------------------------+---------------------------------------+
        """
        return self._ch_session.send_software_edge_trigger(trigger_to_send)

    def cs_wait_for_event(self, event=nidcpower.Event.SOURCE_COMPLETE, timeout=10.0):
        """
        Waits until the specified pin(s) have generated the specified event.

        The session monitors whether each type of event has occurred at least
        once since the last time this method or the initiate
        method were called. If an event has only been generated once, and you
        call this method successively, the method times out. Individual
        events must be generated between separate calls of this method.

        Args:
            event (enums.Event): Specifies which event to wait for.Defaults to
            nidcpower.Event.SOURCE_COMPLETE.
                **Defined Values:**
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_SOURCE_COMPLETE_EVENT    | Waits for the Source Complete event.  |
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_MEASURE_COMPLETE_EVENT   | Waits for the Measure Complete event. |
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_SEQUENCE_ITERATION_COMPLETE_EVENT | Waits for Specified event.   |
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_SEQUENCE_ENGINE_DONE_EVENT| Waits for the Seq Engine Done event. |
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_PULSE_COMPLETE_EVENT     | Waits for the Pulse Complete event.   |
                +----------------------------------------+---------------------------------------+
                | NIDCPOWER_VAL_READY_FOR_PULSE_TRIGGER_EVENT| Waits for Specified event.        |
                +----------------------------------------+---------------------------------------+

            timeout (float in seconds): Specifies the maximum time allowed for this method to
                complete, in seconds. If the method does not complete within this time interval,
                NI-DCPower returns an error. Defaults to 10.0.

            Note:
            When setting the timeout interval, ensure you take into account any triggers so that the
            timeout interval is long enough for your application.
        """
        return self._ch_session.wait_for_event(event, timeout)

    def cs_configure_and_commit_waveform_acquisition(self, sample_rate, buffer_length=1.0):
        """
        configures measurement settings and commits the changes

        Args:
            sample_rate (hertz in float): samples per second for data acquisition
            buffer_length (float, optional): Number of samples to hold in memory. Defaults to 1.0.

        Returns:
            settings: previous settings before configuration for reverting purpose.
        """
        settings = self.cs_get_measurement_settings()
        self._ch_session.aperture_time_units = enums.ApertureTimeUnits.SECONDS
        self._ch_session.aperture_time = 1 / sample_rate
        self._ch_session.measure_record_length_is_finite = False
        self._ch_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
        self._ch_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
        self._ch_session.commit()
        num_samples = int(
            math.ceil(buffer_length / self._ch_session.measure_record_delta_time.total_seconds())
        )
        # coerce num_samples to be between 1 and max value of I32 (2147483647)
        if num_samples < 1:
            num_samples = 1
        elif num_samples > 2147483647:
            num_samples = 2147483647
        if self._ch_session.measure_buffer_size < num_samples:
            self._ch_session.measure_buffer_size = num_samples
        return settings

    def cs_get_measurement_settings(self):
        """
        reads the measurement settings like aperture time, measure trigger and record length

        Returns:
            settings(dict): measurement settings in the dictionary format
        """
        settings = {
            "aperture_time_units": self._ch_session.aperture_time_units,
            "aperture_time": self._ch_session.aperture_time,
            "measure_when": self._ch_session.measure_when,
            "measure_trigger_type": self._ch_session.measure_trigger_type,
            "measure_record_length": self._ch_session.measure_record_length,
            "measure_record_length_is_finite": self._ch_session.measure_record_length_is_finite,
        }
        return settings

    def cs_set_measurement_settings(self, settings):
        """
        sets several measurement related settings from the dictionary input

        Args:
            settings (dict): aperture, trigger and record related properties in a dictionary format
        """
        self._ch_session.aperture_time = settings["aperture_time"]
        self._ch_session.aperture_time_units = settings["aperture_time_units"]
        self._ch_session.measure_when = settings["measure_when"]
        self._ch_session.measure_trigger_type = settings["measure_trigger_type"]
        self._ch_session.measure_record_length = settings["measure_record_length"]
        self._ch_session.measure_record_length_is_finite = settings[
            "measure_record_length_is_finite"
        ]

    def cs_measure_setup(self, measurement_mode: MeasurementMode):
        """
        measurement setup mode and get a boolean for fetching or measuring.

        Args:
            measurement_mode (MeasurementMode): measure_multiple or software triggered or default

        Returns:
            fetch_measure (bool): This can be used to decide between to use fetch or measure
            operation to perform.
        """
        if measurement_mode == MeasurementMode.MEASURE_MULTIPLE:
            fetch_or_measure = False
        elif measurement_mode == MeasurementMode.SOFTWARE_TRIGGER:
            fetch_or_measure = not self.measure_multiple_only
        else:
            fetch_or_measure = self._ch_session.measure_when == enums.MeasureWhen.ON_MEASURE_TRIGGER

        if fetch_or_measure:
            self._ch_session.send_software_edge_trigger(enums.SendSoftwareEdgeTriggerType.MEASURE)
        return fetch_or_measure

    def cs_measure_execute(self, fetch_or_measure: bool):
        """
        fetches or measures based on the boolean parameter passed

        Args:
            fetch_or_measure (bool): decides the operation between fetch and measure

        Returns:
            tuple of voltages and currents: lists of voltages and current in tuple format
        """
        if fetch_or_measure:
            samples = self._ch_session.fetch_multiple(1, 1.0)
        else:
            samples = self._ch_session.measure_multiple()
        voltages = []
        currents = []
        in_compliance = []
        for s in samples:
            voltages.append(s[0])
            currents.append(s[1])
            in_compliance.append(s[2])
        return voltages, currents

    def cs_get_properties(self):
        """
        for each channel find its properties like level, limit, voltage range, current range

        Returns:
            list of channel properties: list of channel properties of all channels in the session
        """
        channel_properties = []
        # ap_times = list(self.cs_get_aperture_time_in_seconds())
        channels = self.cs_channels.split(",")
        pns = self._pins.split(",")
        for pin, channel in zip(pns, channels):
            ss = self.session.channels[channel]
            output_fn = ss.output_function
            if output_fn == enums.OutputFunction.DC_VOLTAGE:
                level = ss.voltage_level
                limit = ss.current_limit
                v_range = ss.voltage_level_range
                i_range = ss.current_limit_range
                output_function = "DC Voltage"
            elif output_fn == enums.OutputFunction.DC_CURRENT:
                level = ss.current_level
                limit = ss.voltage_limit
                v_range = ss.voltage_limit_range
                i_range = ss.current_level_range
                output_function = "DC Current"
            elif output_fn == enums.OutputFunction.PULSE_VOLTAGE:
                level = ss.pulse_voltage_level
                limit = ss.pulse_current_limit
                v_range = ss.pulse_voltage_level_range
                i_range = ss.pulse_current_limit_range
                output_function = "Pulse Voltage"
            elif output_fn == enums.OutputFunction.PULSE_CURRENT:
                level = ss.pulse_current_level
                limit = ss.pulse_voltage_limit
                v_range = ss.pulse_voltage_limit_range
                i_range = ss.pulse_current_level_range
                output_function = "Pulse Current"
            else:
                level = nan
                limit = nan
                v_range = nan
                i_range = nan
                output_function = "un defined"
            max_instr_name = channel.split("/")[0]
            print(max_instr_name, max_instr_name)
            model = self.session.instruments[max_instr_name].instrument_model
            match = re.search("\d\d\d\d", model, re.RegexFlag.ASCII)[0]
            if match in [4110, 4112, 4113, 4130, 4132]:
                tr_response = "N/A"
            elif match == 4154 and channel == "1":
                tr_response = "N/A"
            else:
                tr_response = str(ss.transient_response)
            if match in [4110, 4130, 4140, 4141, 4142, 4143, 4144, 4145]:
                output_connected = "N/A"
            else:
                output_connected = str(ss.output_connected)
            sense = str(ss.sense)
            ap_time = ss.aperture_time
            output_en = ss.output_enabled
            instr_name = self.session.instruments[max_instr_name].instrument_manufacturer
            ch_prop = ChannelProperties(
                instr_name,
                model,
                channel,
                pin,
                output_function,
                level,
                limit,
                v_range,
                i_range,
                sense,
                ap_time,
                tr_response,
                output_en,
                output_connected,
            )
            channel_properties.append(ch_prop)
        return channel_properties


class _NIDCPowerTSM:
    """
    Class to store the sessions for each context of pins.
    """

    def __init__(self, sessions_sites_channels: typing.Iterable[_NIDCPowerSSC]):
        """
        constructor function for NIDCPowerTSM private class

        Args:
            sessions_sites_channels (typing.Iterable[_NIDCPowerSSC]): list of sessions for the
            context pins
        """
        self._sscs = sessions_sites_channels

    @staticmethod
    def _parse_instrument_names(resource_string: str) -> typing.Set[str]:
        """
        returns a set of instrument names from the channels of resource string

        Args:
            resource_string (str): comma separated list of channels from different cards

        Returns:
            typing.Set[str]: set of instruments names
        """
        channels = resource_string.split(",")
        instrument_names = set()
        for channel in channels:
            instrument_name = channel.split("/")[0]
            instrument_names += instrument_name.strip()
        return instrument_names

    @staticmethod
    def _expand_to_requested_array_size(generic_in, size: int):
        """
        private function to compute the size and expand the given list to the size specified

        Args:
            generic_in (any): any python datatype for expanding
            size (int):  desired number of elements

        Returns:
            _type_: _description_
        """
        if hasattr(generic_in, "__iter__"):
            generic_array = []
            length = len(generic_in)
            reminder = size % length
            if (size == 0 or length == 0) and reminder != 0:
                pass
                # need to raise exception
            else:
                i = 0
                for j in range(length):
                    generic_array.append(generic_in[i])
                    i += 1
                    if i == length:
                        i = 0
        else:
            generic_array = []
            for index in range(size):
                generic_array.append(generic_in)
        return generic_array

    @property
    def sessions_sites_channels(self):
        """
        get the sessions stored in for the context pins

        Returns:
            sessions: list of sessions for various pins in the context
        """
        return self._sscs

    def _configure_settings_array(
        self, aperture_times, source_delays, senses, aperture_time_units, transient_responses
    ):
        """
        Configures the measurement settings for all the sessions

        Args:
            aperture_times (list of float or int): depends on the unit specified in the argument.
                Defaults to 16.667e-03.
            source_delays (list of float): in seconds. Defaults to 0.0.
            senses (list of enum): measurement to use Hi and Lo sense lines or not.
                Defaults to enums.Sense.REMOTE.
            aperture_time_units (list of enum): based on model this value needs to be set.
                Defaults to enums.ApertureTimeUnits.SECONDS.
            transient_responses (list of enum): Controls how to control the response based on load.
                Defaults to enums.TransientResponse.NORMAL.
        """
        for (
            ssc,
            aperture_time,
            source_delay,
            sense,
            aperture_time_unit,
            transient_response,
        ) in zip(
            self._sscs,
            aperture_times,
            source_delays,
            senses,
            aperture_time_units,
            transient_responses,
        ):
            ssc.cs_configure_settings(
                aperture_time, source_delay, sense, aperture_time_unit, transient_response
            )

    def _force_current_asymmetric_limits_array(
        self,
        current_levels,
        current_level_ranges,
        voltage_limit_highs,
        voltage_limit_lows,
        voltage_limit_ranges,
    ):
        """
        configures and commits to force single point dc current with asymmetric voltage limits

        Args:
            current_levels (list of float): current levels in amps.
            current_level_ranges (list of float): current level ranges in amps.
            voltage_limit_highs (list of float): voltage higher limits in volts.
            voltage_limit_lows (list of float): voltage lower limits in volts.
            voltage_limit_ranges (list of float): voltage limit range in volts.
        """
        i = 0
        for ssc in self._sscs:
            ssc.cs_force_current_asymmetric_limits(
                current_levels[i],
                current_level_ranges[i],
                voltage_limit_highs[i],
                voltage_limit_lows[i],
                voltage_limit_ranges[i],
            )
            i += 1
        self.initiate()

    def _force_current_symmetric_limits_array(
        self, current_levels, current_level_ranges, voltage_limits, voltage_limit_ranges
    ):
        """
        configures and commits to force single point dc current with symmetric voltage limits

        Args:
            current_levels (list of float): current levels in amps.
            current_level_ranges (list of float): current level ranges in amps.
            voltage_limits (list of float): voltage limits in volts.
            voltage_limit_ranges (list of float): voltage limit range in volts.
        """
        i = 0
        for ssc in self._sscs:
            ssc.cs_force_current_symmetric_limits(
                current_levels[i],
                current_level_ranges[i],
                voltage_limits[i],
                voltage_limit_ranges[i],
            )
            i += 1
        self.initiate()

    def _force_voltage_asymmetric_limits_array(
        self,
        voltage_levels,
        voltage_level_ranges,
        current_limit_highs,
        current_limit_lows,
        current_limit_ranges,
    ):
        """
        configures and commits to force single point dc voltage with asymmetric current limits

        Args:
            voltage_levels (list of float): voltage levels in volts.
            voltage_level_ranges (list of float): voltage level ranges in volts.
            current_limit_highs (list of float): current higher limits in amps.
            current_limit_lows (list of float): current lower limits in amps.
            current_limit_ranges (list of float): current limit range in amps.
        """
        i = 0
        for ssc in self._sscs:
            ssc.cs_force_voltage_asymmetric_limits(
                voltage_levels[i],
                voltage_level_ranges[i],
                current_limit_highs[i],
                current_limit_lows[i],
                current_limit_ranges[i],
            )
            i += 1
        self.initiate()

    def _force_voltage_symmetric_limits_array(
        self, voltage_levels, voltage_level_ranges, current_limits, current_limit_ranges
    ):
        """
        configures and commits to force single point dc voltage with symmetric current limits

        Args:
            voltage_levels (list of float): voltage levels in volts.
            voltage_level_ranges (list of float): voltage level ranges in volts.
            current_limits (list of float): current limits in amps.
            current_limit_ranges (list of float): current limit range in amps.
        """
        i = 0
        for ssc in self._sscs:
            ssc.cs_force_voltage_symmetric_limits(
                voltage_levels[i],
                voltage_level_ranges[i],
                current_limits[i],
                current_limit_ranges[i],
            )
            i += 1
        self.initiate()

    def _expand_array_to_sessions(self, generic_in):
        """
        private function for expanding the given array to the requested array size

        Args:
            generic_in (any): if the data is a list already it will be passed as such

        Returns:
            list of any type: creates the list of given generic input argument
        """
        if hasattr(generic_in, "__iter__"):
            generic_array = generic_in
            # Need to revisit this code for all cases as per reference LabVIEW code
        else:
            generic_array = []
            for _ in self._sscs:
                generic_array.append(generic_in)
        return generic_array

    def _force_current_asymmetric_limits(
        self,
        current_level,
        current_level_range,
        voltage_limit_high,
        voltage_limit_low,
        voltage_limit_range,
    ):
        """
        private function which performs sourcing of current with symmetric voltage limit settings

        Args:
            current_level (float list): in amps
            current_level_range (float list): in amps
            voltage_limit_high (float list): in volts
            voltage_limit_low (float list): in volts
            voltage_limit_range (float list): in volts
        """
        size = 0
        for _ in self._sscs:
            size += 1
        current_levels = self._expand_to_requested_array_size(current_level, size)
        current_level_ranges = self._expand_to_requested_array_size(current_level_range, size)
        voltage_limit_highs = self._expand_to_requested_array_size(voltage_limit_high, size)
        voltage_limit_lows = self._expand_to_requested_array_size(voltage_limit_low, size)
        voltage_limit_ranges = self._expand_to_requested_array_size(voltage_limit_range, size)
        self._force_current_asymmetric_limits_array(
            current_levels,
            current_level_ranges,
            voltage_limit_highs,
            voltage_limit_lows,
            voltage_limit_ranges,
        )

    def _force_current_symmetric_limits(
        self, current_level, current_level_range, voltage_limit, voltage_limit_range
    ):
        """
        private function which performs sourcing of current with symmetric voltage limit settings

        Args:
            current_level (float list): in amps
            current_level_range (float list): in amps
            voltage_limit (float list): in volts
            voltage_limit_range (float list): in volts
        """
        size = 0
        for _ in self._sscs:
            size += 1
        current_levels = self._expand_to_requested_array_size(current_level, size)
        current_level_ranges = self._expand_to_requested_array_size(current_level_range, size)
        voltage_limits = self._expand_to_requested_array_size(voltage_limit, size)
        voltage_limit_ranges = self._expand_to_requested_array_size(voltage_limit_range, size)
        self._force_current_symmetric_limits_array(
            current_levels, current_level_ranges, voltage_limits, voltage_limit_ranges
        )

    def _force_voltage_asymmetric_limits(
        self,
        voltage_level,
        voltage_level_range,
        current_limit_high,
        current_limit_low,
        current_limit_range,
    ):
        """
        private function which performs sourcing of voltage with asymmetric current limit settings

        Args:
            voltage_level (float list): in volts
            voltage_level_range (float list): in volts
            current_limit_high (float list): in amps
            current_limit_low (float list): in amps
            current_limit_range (float list): in amps
        """
        size = 0
        for _ in self._sscs:
            size += 1
        voltage_levels = self._expand_to_requested_array_size(voltage_level, size)
        voltage_level_ranges = self._expand_to_requested_array_size(voltage_level_range, size)
        current_limit_highs = self._expand_to_requested_array_size(current_limit_high, size)
        current_limit_lows = self._expand_to_requested_array_size(current_limit_low, size)
        current_limit_ranges = self._expand_to_requested_array_size(current_limit_range, size)
        self._force_current_asymmetric_limits_array(
            voltage_levels,
            voltage_level_ranges,
            current_limit_highs,
            current_limit_lows,
            current_limit_ranges,
        )

    def _force_voltage_symmetric_limits(
        self, voltage_level, voltage_level_range, current_limit, current_limit_range
    ):
        """
        private function which performs sourcing of voltage with symmetric current limit settings

        Args:
            voltage_level (float list): in volts
            voltage_level_range (float list): in volts
            current_limit (float list): in amps
            current_limit_range (float list): in amps
        """
        size = 0
        for _ in self._sscs:
            size += 1
        voltage_levels = self._expand_to_requested_array_size(voltage_level, size)
        voltage_level_ranges = self._expand_to_requested_array_size(voltage_level_range, size)
        current_limits = self._expand_to_requested_array_size(current_limit, size)
        current_limit_ranges = self._expand_to_requested_array_size(current_limit_range, size)
        self._force_voltage_symmetric_limits_array(
            voltage_levels, voltage_level_ranges, current_limits, current_limit_ranges
        )

    def abort(self):
        """
        Transitions the specified channel(s) from the Running state to the
        Uncommitted state. If a sequence is running, it is stopped. Any
        configuration methods called after this method are not applied until
        the initiate method is called. If power output is enabled
        when you call the abort method, the output channels remain
        in their current state and continue providing power.

        Use the ConfigureOutputEnabled method to disable power
        output on a per-channel basis. Use the reset method to
        disable output on all channels.

        Returns:
            none: when aborted otherwise exception
        """
        for ssc in self._sscs:
            ssc.cs_abort()

    def commit(self):
        """
        Applies previously configured settings to the specified channel(s) under current session.
        Calling this method moves the NI-DCPower session from the Uncommitted state into
        the Committed state. After calling this method, modifying any
        property reverts the NI-DCPower session to the Uncommitted state. Use
        the initiate method to transition to the Running state.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        for ssc in self._sscs:
            ssc.cs_commit()

    def initiate(self):
        """
        Starts generation or acquisition, causing the specified channel(s) to
        leave the Uncommitted state or Committed state and enter the Running
        state. To return to the Uncommitted state call the abort
        method.

        Returns:
            context manager: This method will return a Python context manager that will
            initiate on entering and abort on exit.
        """
        for ssc in self._sscs:
            ssc.cs_initiate()

    def reset(self):
        """
        Resets the specified pin(s) to a known state. This method disables power
        generation, resets session properties to their default values, commits
        the session properties, and leaves the session in the Uncommitted state.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        for ssc in self._sscs:
            ssc.cs_reset()

    def configure_aperture_time_with_abort_and_initiate(
        self, aperture_time=16.667e-03, aperture_time_units=enums.ApertureTimeUnits.SECONDS
    ):
        """
        Configures the measurement aperture time for the channel configuration.
        Aperture time is specified in the units set by the aperture_time_units property.
        for information about supported devices.

        Args:
            aperture_time (float, optional): in seconds by default. Defaults to 16.667e-03.
            aperture_time_units (enum, optional): seconds. Defaults to
                enums.ApertureTimeUnits.SECONDS.

        Returns:
            None: when this operation is completed successfully, i.e. no error.
        """
        for ssc in self._sscs:
            ssc.cs_configure_aperture_time_with_abort_and_initiate(
                aperture_time, aperture_time_units
            )
        return

    def configure_power_line_frequency(self, power_line_frequency=60.0):
        """
        Stores the session object variable power line frequency for other operations
        that uses power line frequency.

        Args:
            power_line_frequency (float, optional): in hertz. Defaults to 60.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_power_line_frequency(power_line_frequency)
        return

    def configure_sense(self, sense=enums.Sense.LOCAL):
        """
        configures the sense for all channels in the session that are part to pin-query context

        Args:
            sense (enum, optional): sensing at local or remote. Defaults to enums.Sense.LOCAL.
        """
        for ssc in self._sscs:
            ssc.cs_configure_sense(sense)
        return

    def get_aperture_times_in_seconds(self):
        """
        get the aperture time in seconds for all channels in the session. if the model has
        different units convert them into seconds.

        Returns:
            list of float: aperture times in seconds
        """
        temp_list = []
        for ssc in self._sscs:
            temp_list.append(ssc.cs_get_aperture_time_in_seconds())
        return temp_list

    def get_power_line_frequencies(self):
        """
        get the power line frequencies stored in the object or from the instrument based on the
        supported model

        Returns:
            list of float: power line frequency in hertz
        """
        temp_list = []
        for ssc in self._sscs:
            temp_list.append(ssc.cs_get_power_line_frequency())
        return temp_list

    def query_in_compliance(self):
        """
        get the in compliance status of each channel under the current session.

        Returns:
            bool list: list of status one for each channel
        """
        temp_list = []
        for ssc in self._sscs:
            temp_list += ssc.cs_query_in_compliance()
        return temp_list

    def query_output_state(self, output_state: nidcpower.OutputStates):
        """
        compares the states of the output against the desired state

        Args:
            output_state (nidcpower.OutputStates): desired output state

        Returns:
            bool list: indicates output state is same as desired state or not.
        """
        temp_list = []
        for ssc in self._sscs:
            temp_list += ssc.cs_query_output_state(output_state)
        return temp_list

    def configure_transient_response(self, transient_response=enums.TransientResponse.NORMAL):
        """
        Specifies the transient response.Default Value: TransientResponse.NORMAL. This property is
        not supported by all devices.

        Args:
            transient_response (TransientResponse, optional): specifies custom response settings or
            normal. Defaults to enums.TransientResponse.NORMAL.
        """
        for ssc in self._sscs:
            ssc.cs_configure_transient_response(transient_response)
        return

    def configure_output_connected(self, output_connected=False):
        """
        Specifies whether the output relay is connected (closed) or disconnected (open). The
        output_enabled property does not change based on this property; they are independent of
        each other. Set this property to False inorder to disconnect the output terminal from the
        output. to the output terminal might discharge unless the relay is disconnected. Excessive
        connecting and disconnecting of the output can cause premature wear on the relay.

        Args:
            output_connected (bool, optional): controls the output relay. Defaults to False.
        """
        for ssc in self._sscs:
            ssc.cs_configure_output_connected(output_connected)
        return

    def configure_output_enabled(self, output_enabled=False):
        """
        Specifies whether the output is enabled (True) or disabled (False).Depending on the value
        you specify for the output_function property, you also must set the voltage level or
        current level in addition to enabling the output the initiate method.

        Args:
            output_enabled (bool, optional): selects the output to be enabled or not. Defaults to
            False.
        """
        for ssc in self._sscs:
            ssc.cs_configure_output_enabled(output_enabled)
        return

    def configure_output_enabled_and_connected(self, output_enabled_and_connected=False):
        """
        Specifies whether the output relay is connected (closed) or disconnected (open).
        The output_enabled property also changes based on this property;

        Args:
            output_enabled_and_connected (bool, optional):controls the output relay and enables the
            output. Defaults to False.
        """
        if output_enabled_and_connected:
            self.configure_output_enabled(output_enabled_and_connected)
            self.configure_output_connected(output_enabled_and_connected)
        else:
            self.configure_output_connected(output_enabled_and_connected)
            self.configure_output_enabled(output_enabled_and_connected)

    def configure_output_resistance(self, output_resistance=0.0):
        """
        Specifies the output resistance that the device attempts to generate for the specified
        pin(s). This property is available only when you set the output_function property on a
        supported device.

        Args:
            output_resistance (float, optional): resistance value in ohms. Defaults to 0.0.
        """

        for ssc in self._sscs:
            ssc.cs_configure_output_resistance(output_resistance)
        return

    def configure_output_resistance_array(self, output_resistance):
        """
        Specifies the output resistance that the device attempts to generate for the specified
        pin(s). This property is available only when you set the output_function property on a
        supported device.

        Args:
            output_resistance (List of float): resistance values in ohms.
        """
        output_resistances = self._expand_array_to_sessions(output_resistance)
        i = 0
        for ssc in self._sscs:
            ssc.cs_configure_output_resistance(output_resistances[i])
            i += 1

    def configure_source_delay(self, source_delay=0.01667):
        """
        Determines when, in seconds, the device generates the Source Complete event, potentially
        starting a measurement if the measure_when property is set to
        MeasureWhen.AUTOMATICALLY_AFTER_SOURCE_COMPLETE.

        Args:
            source_delay (float, optional): hightime.timedelta, datetime.timedelta, or float in
            seconds. Defaults to 0.01667.Valid Values: 0 to 167 seconds.
        """
        for ssc in self._sscs:
            ssc.cs_configure_source_delay(source_delay)

    def configure_source_mode(self, source_mode=nidcpower.SourceMode.SINGLE_POINT):
        """
        Specifies whether to run a single output point or a sequence. Refer to the Single Point
        Source Mode and Sequence Source Mode topics in the NI DC Power Supplies and SMUs Help for
        more information about source modes.Default value: SourceMode.SINGLE_POINT

        Args:
            source_mode (nidcpower.SourceMode, optional): configures the single point or sequence.
            Defaults to nidcpower.SourceMode.SINGLE_POINT.
        """
        for ssc in self._sscs:
            ssc.cs_configure_source_mode(source_mode)

    def get_max_current(self):
        """
        gets the maximum current that can be supplied to one of the selected pins

        Returns:
            current_in_amps (float): maximum current that can be drawn in amps
        """
        return max([ssc.cs_get_max_current() for ssc in self._sscs])

    def wait_for_event(self, event=nidcpower.Event.SOURCE_COMPLETE, timeout=10.0):
        """
        Waits until the specified pin(s) have generated the specified event.

        The session monitors whether each type of event has occurred at least
        once since the last time this method or the initiate
        method were called. If an event has only been generated once, and you
        call this method successively, the method times out. Individual
        events must be generated between separate calls of this method.

        Args:
            event (enums.Event): Specifies which event to wait for.Defaults to
            nidcpower.Event.SOURCE_COMPLETE.
            **Defined Values:**
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SOURCE_COMPLETE_EVENT    | Waits for the Source Complete event.  |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_MEASURE_COMPLETE_EVENT   | Waits for the Measure Complete event. |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SEQUENCE_ITERATION_COMPLETE_EVENT | Waits for Specified event.   |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SEQUENCE_ENGINE_DONE_EVENT| Waits for the Seq Engine Done event. |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_PULSE_COMPLETE_EVENT     | Waits for the Pulse Complete event.   |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_READY_FOR_PULSE_TRIGGER_EVENT| Waits for Specified event.        |
            +----------------------------------------+---------------------------------------+

            timeout (hightime.timedelta, datetime.timedelta, or float in seconds): Specifies the
                maximum time allowed for this method to complete, in seconds. If the method does
                not complete within this time interval, NI-DCPower returns an error. Defaults to
                10.0.

        Note:
        When setting the timeout interval, ensure you take into account any triggers so that the
        timeout interval is long enough for your application.
        """
        for ssc in self._sscs:
            ssc.cs_wait_for_event(event, timeout)
        return

    def configure_and_start_waveform_acquisition(self, sample_rate=0.0, buffer_length=0.0):
        """
        configures and records previous settings and start the waveform acquisition

        Args:
            sample_rate (float, optional): sampling rate for acquisition. Defaults to 0.0.
            buffer_length (float, optional): length of measurement to be stored in memory. Defaults
            to 0.0.

        Returns:
            settings: list of settings and start time
        """
        self.abort()
        previous_settings = []
        for ssc in self._sscs:
            settings = ssc.cs_configure_and_commit_waveform_acquisition(sample_rate, buffer_length)
            previous_settings.append(settings)
        self.initiate()
        self.send_software_edge_trigger(nidcpower.SendSoftwareEdgeTriggerType.MEASURE)
        start_time = datetime.now()
        settings = [previous_settings, start_time]
        return settings

    def configure_export_signal(self, signal: enums.SendSoftwareEdgeTriggerType, output_terminal):
        """
        configures the signal to be exported on the specified output terminal.

        Args:
            signal (enums.SendSoftwareEdgeTriggerType): signal to be exported
            output_terminal (str): output terminal on which the signal is exported.

        Returns:
            terminal_name (str) : fully qualified output terminal name
        """

        terminal_name = output_terminal
        for ssc in self._sscs:
            terminal_name = ssc.cs_configure_export_signal(signal, output_terminal)
            break
        return terminal_name

    def send_software_edge_trigger(
        self, trigger_to_send=nidcpower.SendSoftwareEdgeTriggerType.MEASURE
    ):
        """
        Asserts the specified trigger. This method can override an external edge trigger.

        Args:
            trigger_to_send (enums.SendSoftwareEdgeTriggerType, optional): Specifies which trigger
            to assert. Defaults to enums.SendSoftwareEdgeTriggerType.MEASURE.
            **Defined Values:**
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_START_TRIGGER            | Asserts the Start trigger.            |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SOURCE_TRIGGER           | Asserts the Source trigger.           |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_MEASURE_TRIGGER          | Asserts the Measure trigger.          |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SEQUENCE_ADVANCE_TRIGGER | Asserts the Sequence Advance trigger. |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_PULSE_TRIGGER            | Asserts the Pulse trigger.            |
            +----------------------------------------+---------------------------------------+
            | NIDCPOWER_VAL_SHUTDOWN_TRIGGER         | Asserts the Shutdown trigger.         |
            +----------------------------------------+---------------------------------------+
        """
        for ssc in self._sscs:
            ssc.cs_send_software_edge_trigger(trigger_to_send)

    def finish_waveform_acquisition(self, settings, fetch_waveform_length_s=0.0):
        """
        finish waveform acquisition by aborting and applying previous settings and initiating
        session

        Args:
            settings (dict): previous settings to apply on the sessions
            fetch_waveform_length_s (float, optional): length of waveform to acquire. Defaults to
                0.0.

        Returns:
            voltage and current waveforms: tuple of voltage and current waveforms
        """
        voltage_waveforms, current_waveforms = self.fetch_waveform(
            settings["start_time"], fetch_waveform_length_s
        )
        self.abort()
        self.set_measurement_settings(settings["previous_settings"])
        self.initiate()
        return voltage_waveforms, current_waveforms

    def fetch_waveform(self, waveform_t0, waveform_length_s=0.0):
        """
        Returns a voltage and current waveform tuples (Measurement) that were
        previously taken and are stored in the NI-DCPower buffer. This method
        should not be used when the measure_when property is
        set to MeasureWhen.ON_DEMAND. You must first call
        initiate before calling this method.

        Args:
            waveform_t0 (time stamp): waveform time stamp
            waveform_length_s (float, optional): duration of waveform to measure. Defaults to 0.0.

        Returns:
            voltage and current waveforms: tuple of voltage and current waveforms
        """
        voltage_waveforms = []
        current_waveforms = []
        for ssc in self._sscs:
            record_dt = ssc._ch_session.measure_record_delta_time.total_seconds()
            fetch_backlog = ssc._ch_session.fetch_backlog
            if waveform_length_s == 0.0:
                fetch_samples = fetch_backlog
            else:
                fetch_samples = int(waveform_length_s / record_dt)
            samples = ssc._ch_session.fetch_multiple(fetch_samples, timeout=waveform_length_s + 1)
            voltages = []
            currents = []
            in_compliance = []
            for s in samples:
                voltages.append(s[0])
                currents.append(s[1])
                in_compliance.append(s[2])
            voltage_waveform = {
                "channel": ssc.cs_channels + "(V)",
                "samples": voltages,
                "x_increment": record_dt,
                "absolute_initial_x": waveform_t0,
            }
            current_waveform = {
                "channel": ssc.cs_channels + "(A)",
                "samples": currents,
                "x_increment": record_dt,
                "absolute_initial_x": waveform_t0,
            }
            voltage_waveforms.append(voltage_waveform)
            current_waveforms.append(current_waveform)
        return voltage_waveforms, current_waveforms

    def get_measurement_settings(self):
        """
        reads the measurement settings like aperture time, measure trigger and record length

        Returns:
            list of settings(dict): measurement settings in list of dictionary format

        """
        meas_settings = []
        for ssc in self._sscs:
            settings = ssc.cs_get_measurement_settings()
            meas_settings.append(settings)
        return meas_settings

    def get_properties(self):
        """
        for each channel find its properties like level, limit, voltage range, current range

        Returns:
            list of channel properties: list of channel properties of all channels in the session
        """
        all_ch_prop = []
        for ssc in self._sscs:
            prop = ssc.cs_get_properties()
            all_ch_prop.append(prop)
        return all_ch_prop

    def set_measurement_settings(self, meas_settings):
        """
        sets several measurement related settings from the list of dictionary input

        Args:
            meas_settings (list of dict): list of dictionary of aperture, trigger and record related
                properties
        """
        i = 0
        for ssc in self._sscs:
            ssc.cs_set_measurement_settings(meas_settings[i])
            i += 1

    def configure_measurements(self, mode=MeasurementMode.AUTO):
        """
        configure the measurement mode to be auto by default, otherwise the value specified by the
        parameter passed. Then configures additional settings that are required by the measurement
        mode

        Args:
            mode (MeasurementMode, optional): measurement mode to configure. Defaults to
            MeasurementMode.AUTO.
        """
        for ssc in self._sscs:
            ssc.cs_configure_measurements(mode)

    def configure_settings(
        self,
        aperture_time=16.667e-03,
        source_delay=0.0,
        sense=enums.Sense.REMOTE,
        aperture_time_unit=enums.ApertureTimeUnits.SECONDS,
        transient_response=enums.TransientResponse.NORMAL,
    ):
        """
        Configures the measurement settings for all the sessions

        Args:
            aperture_time (float or int, optional): depends on the unit specified in the argument.
                Defaults to 16.667e-03.
            source_delay (float, optional): in seconds. Defaults to 0.0.
            sense (enum, optional): measurement to use Hi and Lo sense lines or not.
                Defaults to enums.Sense.REMOTE.
            aperture_time_unit (enum, optional): based on model this value needs to be set.
                Defaults to enums.ApertureTimeUnits.SECONDS.
            transient_response (enum, optional): Controls how to control the response based on load.
                Defaults to enums.TransientResponse.NORMAL.
        """
        transient_responses = self._expand_array_to_sessions(transient_response)
        aperture_time_units = self._expand_array_to_sessions(aperture_time_unit)
        aperture_times = self._expand_array_to_sessions(aperture_time)
        source_delays = self._expand_array_to_sessions(source_delay)
        senses = self._expand_array_to_sessions(sense)
        self._configure_settings_array(
            aperture_times, source_delays, senses, aperture_time_units, transient_responses
        )

    def configure_current_level_range(self, current_level_range=0.0):
        """
        updates the current level range property for all sessions in the context.

        Args:
            current_level_range (float, optional): updates the current level range property.
            Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_current_level_range(current_level_range)

    def configure_current_level(self, current_level=0.0):
        """
        updates the current level property.

        Args:
            current_level (float, optional): updates the level property. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_current_level(current_level)

    def configure_current_level_array(self, current_levels_array):
        """
        updates the current level property with the expanded array of current levels.

        Args:
            current_levels_array (list of floats): updates the current level property.
        """
        current_levels = self._expand_array_to_sessions(current_levels_array)
        for ssc, current_level in zip(self._sscs, current_levels):
            ssc.cs_configure_current_level(current_level)

    def configure_voltage_limit_range(self, voltage_limit_range=0.0):
        """
        configure same voltage limit for all channels in each session.

        Args:
            voltage_limit_range (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_voltage_limit_range(voltage_limit_range)

    def configure_voltage_limit(self, voltage_limit=0.0):
        """
        configure the same voltage limit for all channels in each session.

        Args:
            voltage_limit (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_voltage_limit(voltage_limit)

    def configure_voltage_limit_array(self, voltage_limits_array):
        """
        configure different the voltage limit for all channels in each session.

        Args:
            voltage_limits_array (List of float): one voltage limit for each channel
        """
        voltage_limits = self._expand_array_to_sessions(voltage_limits_array)
        i = 0
        for ssc in self._sscs:
            ssc.cs_configure_voltage_limit(voltage_limits[i])
            i += 1

    def configure_voltage_level_range(self, voltage_level_range=0.0):
        """
        configures the same voltage level range for all channels in the sessions

        Args:
            voltage_level_range (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_voltage_level_range(voltage_level_range)

    def configure_voltage_level(self, voltage_level=0.0):
        """
        configure the same voltage level for all channels in the session

        Args:
            voltage_level (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_voltage_level(voltage_level)

    def configure_voltage_level_array(self, voltage_levels_array):
        """
        Configures different voltage level for each channel in the sessions

        Args:
            voltage_levels_array (float): for each channel
        """
        voltage_levels = self._expand_array_to_sessions(voltage_levels_array)
        i = 0
        for ssc in self._sscs:
            ssc.cs_configure_voltage_level(voltage_levels[i])
            i += 1

    def configure_current_limit_range(self, current_limit_range=0.0):
        """
        configures same current limit range for all channels in the sessions

        Args:
            current_limit_range (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_current_limit_range(current_limit_range)

    def configure_current_limit(self, current_limit=0.0):
        """
        configures same current limit for all channels in the sessions

        Args:
            current_limit (float, optional): for all channels. Defaults to 0.0.
        """
        for ssc in self._sscs:
            ssc.cs_configure_current_limit(current_limit)

    def configure_current_limit_array(self, current_limits_array):
        """
        configures the current limit for each channel in the sessions

        Args:
            current_limits_array (float): one for each channel in the session
        """
        current_limits = self._expand_array_to_sessions(current_limits_array)
        i = 0
        for ssc in self._sscs:
            ssc.cs_configure_current_limit(current_limits[i])
            i += 1

    def force_current_asymmetric_limits(
        self,
        current_level,
        current_level_range,
        voltage_limit_high,
        voltage_limit_low,
        voltage_limit_range,
    ):
        """
                Source different voltage limits on both sides (positive and negative)

        Args:
            current_level (float): to be applied on the channels.
            current_level_range (float): for the desired current level.
            voltage_limit_high (float): maximum allowed positive side voltage.
            voltage_limit_low (float): maximum allowed negative side voltage.
            voltage_limit_range (float): range selection for voltage limit.
        """
        current_levels = self._expand_array_to_sessions(current_level)
        current_level_ranges = self._expand_array_to_sessions(current_level_range)
        voltage_limit_highs = self._expand_array_to_sessions(voltage_limit_high)
        voltage_limit_lows = self._expand_array_to_sessions(voltage_limit_low)
        voltage_limit_ranges = self._expand_array_to_sessions(voltage_limit_range)
        self._force_current_asymmetric_limits_array(
            current_levels,
            current_level_ranges,
            voltage_limit_highs,
            voltage_limit_lows,
            voltage_limit_ranges,
        )

    def force_current_symmetric_limits(
        self, current_level, current_level_range, voltage_limit, voltage_limit_range
    ):
        """
               Source same voltage limit on both sides (positive and negative)

        Args:
            current_level (float): to be applied on the channels
            current_level_range (float): for the desired current level
            voltage_limit (float): maximum allowed voltage
            voltage_limit_range (float): range selection for voltage limit
        """
        current_levels = self._expand_array_to_sessions(current_level)
        current_level_ranges = self._expand_array_to_sessions(current_level_range)
        voltage_limits = self._expand_array_to_sessions(voltage_limit)
        voltage_limit_ranges = self._expand_array_to_sessions(voltage_limit_range)
        self._force_current_symmetric_limits_array(
            current_levels, current_level_ranges, voltage_limits, voltage_limit_ranges
        )

    def force_voltage_asymmetric_limits(
        self,
        voltage_level,
        voltage_level_range,
        current_limit_high,
        current_limit_low,
        current_limit_range,
    ):
        """
         Source different current limits on both sides (positive and negative)

        Args:
            voltage_level (float): to be applied on the channels.
            voltage_level_range (float): for the desired voltage level.
            current_limit_high (float): maximum allowed positive side current.
            current_limit_low (float): maximum allowed negative side current.
            current_limit_range (float): range selection for current limit.
        """
        voltage_levels = self._expand_array_to_sessions(voltage_level)
        voltage_level_ranges = self._expand_array_to_sessions(voltage_level_range)
        current_limit_highs = self._expand_array_to_sessions(current_limit_high)
        current_limit_lows = self._expand_array_to_sessions(current_limit_low)
        current_limit_ranges = self._expand_array_to_sessions(current_limit_range)
        self._force_current_asymmetric_limits_array(
            voltage_levels,
            voltage_level_ranges,
            current_limit_highs,
            current_limit_lows,
            current_limit_ranges,
        )

    def force_voltage_symmetric_limits(
        self, voltage_level=0.0, voltage_level_range=0.0, current_limit=0.0, current_limit_range=0.0
    ):
        """
        Source same current limit on both sides (positive and negative)

        Args:
            voltage_level (float, optional): to be applied on the channels. Defaults to 0.0.
            voltage_level_range (float, optional): for the desired voltage level. Defaults to 0.0.
            current_limit (float, optional): maximum allowed current . Defaults to 0.0.
            current_limit_range (float, optional): range selection for current limit. Defaults to
            0.0.
        """
        voltage_levels = self._expand_array_to_sessions(voltage_level)
        voltage_level_ranges = self._expand_array_to_sessions(voltage_level_range)
        current_limits = self._expand_array_to_sessions(current_limit)
        current_limit_ranges = self._expand_array_to_sessions(current_limit_range)
        self._force_voltage_symmetric_limits_array(
            voltage_levels, voltage_level_ranges, current_limits, current_limit_ranges
        )

    def measure(self, measurement_mode=MeasurementMode.AUTO):
        """
        measure the data by setting uo the measurement mode
        reads all data from all the sessions.

        Args:
            measurement_mode (enum, optional): specifies the desired measurement mode. Defaults to
            MeasurementMode.AUTO.

        Returns:
            voltages, current: tuple of list of voltages and currents
        """
        fetch_or_measure_array = []
        voltages = []
        currents = []
        for ssc in self._sscs:
            fetch_or_measure_array.append(ssc.cs_measure_setup(measurement_mode))
        i = 0
        for ssc in self._sscs:
            voltages_new, currents_new = ssc.cs_measure_execute(fetch_or_measure_array[i])
            voltages += voltages_new
            currents += currents_new
            i += 1
        return voltages, currents

    def configure_source_adapt(
        self, voltage_ctr: CustomTransientResponse, current_ctr: CustomTransientResponse
    ):
        """configures the transient responses for both voltage and current

        Args:
            voltage_ctr (CustomTransientResponse): for voltage control
            current_ctr (CustomTransientResponse): for current control
        """
        for ssc in self._sscs:
            ssc.cs_configure_source_adapt(voltage_ctr, current_ctr)

    def get_source_adapt_settings(self):
        """source adapt settings from all sessions

        Returns:
            list of tuple: transient response type, Voltage T.R settings, Current T.R. settings
        """
        return [ssc.cs_get_source_adapt_settings() for ssc in self._sscs]

    def filter_sites(self, requested_sites):
        """filter  the sites specified in the current TSMObject

        Args:
            requested_sites (list of int): sites

        Returns:
            SSC: list of sessions sites and channels
        """
        filtered_ssc = []
        for ssc in self._sscs:
            found = False
            sites = common.channel_list_to_pins(ssc.cs_channels)[2]
            for s in sites:
                found = (s in requested_sites) or found
            if found:
                filtered_ssc.append(ssc)
        return filtered_ssc

    def filter_pins(self, requested_pins):
        """filter the pins specified in the current TSMObject

        Args:
            requested_pins (str): pin names

        Returns:
            SSC: list of sessions sites and channels
        """
        temp1 = []
        temp2 = []
        for ssc in self._sscs:
            sites_pins, pins, sites = common.channel_list_to_pins(ssc.cs_channels)
            try:
                search_pos = int(requested_pins.index(pins[0]))
            except ValueError:
                search_pos = -1
            if sites[0] >= 0 and search_pos >= 0:
                temp1.append((sites[0], search_pos, ssc))
            elif (sites[0] < 0) and (search_pos >= 0):
                temp2.append((sites[0], search_pos, ssc))
        temp1 = sorted(temp1)
        temp2 = sorted(temp2)
        dut_pins_ssc = [i[2] for i in temp1]
        sys_pins_ssc = [i[2] for i in temp2]
        filtered_ssc = dut_pins_ssc + sys_pins_ssc
        return filtered_ssc


class TSMDCPower(typing.NamedTuple):
    """
    data type of the DCPower_Tsm objects

    Args:
        TSM objects (tuple): 5 entities for storing them togather.
    """

    pin_query_context: typing.Any
    ssc: _NIDCPowerTSM
    sites: typing.List[int]
    pins_info: typing.List[common.PinInformation]
    pins_expanded: typing.List[common.ExpandedPinInformation]


def filter_pins(dc_power_tsm: TSMDCPower, desired_pins):
    """From the tsm context select only desired pins

    Args:
        dc_power_tsm (TSMDCPower): tsm context for nidcpower
        desired_pins (_type_): pin names list

    Returns:
        TSMDCPower: tsm context with only desired pins
    """
    dc_power_tsm.ssc.filter_pins(desired_pins)
    all_pins = common.get_pin_names_from_expanded_pin_information(dc_power_tsm.pins_expanded)
    i = 0
    pins_expand_new = []
    for d_pin in desired_pins:
        index_d = all_pins.index(d_pin)
        data = dc_power_tsm.pins_expanded[index_d]
        output = common.PinInformation(data.pin, data.type, 1)
        data.index = i
        dc_power_tsm.pins_info.append(output)
        if index_d >= 0:
            pins_expand_new.append(data)
        i += 1
    dut_pins, system_pins = common.get_dut_pins_and_system_pins_from_expanded_pin_list(
        pins_expand_new
    )
    pins_to_query_ctx = common.get_pin_names_from_expanded_pin_information(dut_pins + system_pins)
    dc_power_tsm.pin_query_context.Pins = pins_to_query_ctx
    return dc_power_tsm


def filter_sites(tsm: TSMDCPower, sites):
    """from tsm context select only desired sites

    Args:
        tsm (TSMDCPower): pin query context
        sites (int list): desired site numbers

    Returns:
        dc power tsm: same as input but with desired sites only
    """
    tsm.ssc = tsm.ssc.filter_sites(sites)
    tsm.site_numbers = sites
    return tsm


@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm: SMContext,
    pins: typing.List[str],
    sites: typing.List[int] = [],
    fill_pin_site_info=True,
):
    """
    get the sessions for the selected pins

    Args:
        tsm (SMContext): tsm context for nidcpower
        pins (typing.List[str]): desired pins for which the TSMDCPower object is created
        sites (typing.List[int], optional): list of desired sites. Defaults to [].
        fill_pin_site_info (bool, optional): if true updates the sites. Defaults to True.

    Returns:
        dcpower_tsm: pin-query context variable
    """
    if len(sites) == 0:
        sites = list(tsm.site_numbers)  # This is tested and works
    pins_expanded = []
    pins_info = []
    pin_query_context, sessions, channels = tsm.pins_to_nidcpower_sessions(pins)
    if fill_pin_site_info:
        pins_info, pins_expanded = common.expand_pin_groups_and_identify_pin_types(
            tsm, pins
        )  # This is tested and working fine.
    else:
        for pin in pins:
            a = common.PinInformation  # create instance of class
            a.pin = pin
            pins_info.append(a)
    _, pin_lists = common.pin_query_context_to_channel_list(pin_query_context, pins_expanded, sites)
    sscs = [
        _NIDCPowerSSC(session, channel, pin_list)
        for session, channel, pin_list in zip(sessions, channels, pin_lists)
    ]
    dc_power_tsm = _NIDCPowerTSM(sscs)
    return TSMDCPower(pin_query_context, dc_power_tsm, sites, pins_info, pins_expanded)


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm: SMContext, power_line_frequency=60.0, **kwargs):
    """
    Creates the sessions for all the nidcpower resource string available in the tsm context for
    instruments

    Args:
        tsm (SMContext): TestStand semiconductor module context
        power_line_frequency(float, Optional): power line frequency of the power supply. Defaults to
        60 Hz.
    """
    # cache kwargs
    reset = kwargs["reset"] if "reset" in kwargs.keys() else False
    options = kwargs["options"] if "options" in kwargs.keys() else {}

    # initialize and reset sessions
    resource_strings = tsm.get_all_nidcpower_resource_strings()
    for resource_string in resource_strings:
        session = nidcpower.Session(resource_string, reset=reset, options=options)
        try:
            session.reset()
        except nidcpower.errors.DriverError as error:
            if error.code == -1074118575:
                session.reset_device()
            else:
                raise

        # set start up state on each channel
        for i in range(session.channel_count):
            channel_name = session.get_channel_name(i + 1)
            resource_name = channel_name.split("/")[0]
            instrument_model = session.instruments[resource_name].instrument_model
            if instrument_model in _ModelSupport.POWER_LINE_FREQUENCY:
                session.channels[channel_name].power_line_frequency = power_line_frequency
            if instrument_model not in _ModelSupport.DEFAULT_OUTPUT_STATE_0V:
                session.channels[channel_name].initiate()

        # set session in the tsm context
        tsm.set_nidcpower_session(resource_string, session)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    """
    Closes the sessions associated with the tsm context

    Args:
        tsm (SMContext): TestStand semiconductor module context
    """
    sessions = tsm.get_all_nidcpower_sessions()
    for session in sessions:
        session.abort()
        try:
            session.reset()
        except nidcpower.errors.DriverError:
            session.reset_device()
        session.close()
    return


if __name__ == "__main__":
    pass
