import re
import math
import typing
import nidcpower
import nidcpower.errors
import nitsm.codemoduleapi
# import nidevtools.common
import common

_SemiconductorModuleContext = nitsm.codemoduleapi.SemiconductorModuleContext


class _ModelSupport:
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


class _NIDCPowerSSC:
    """Session, sites, and channels."""

    def __init__(self, session: nidcpower.Session, channels: str):
        self._session = session
        self._channels = channels
        self._channels_session = session.channels[channels]
        self.power_line_frequency = 60.0  # To Do confirm global replaced with object attributes.
        self.measure_multiple_only = False  # To Do confirm global replaced with object attributes.

    @property
    def session(self):
        return self._session

    @property
    def channels(self):
        return self._channels

    def abort(self):
        return self._channels_session.abort()

    def commit(self):
        return self._channels_session.commit()

    def initiate(self):
        return self._channels_session.initiate()

    def reset(self):
        return self._channels_session.reset()

    def configure_settings(
            self,
            aperture_time=16.667,
            source_delay=0.0,
            sense=nidcpower.Sense.LOCAL,
            aperture_time_units=nidcpower.ApertureTimeUnits.SECONDS,
            transient_response=nidcpower.TransientResponse.NORMAL,
    ):
        self._channels_session.abort()
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        temp = aperture_time
        if aperture_time_units == nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES:
            temp = temp / self.power_line_frequency

        if match == "4110":
            self._channels_session.source_delay = source_delay
            self._channels_session.samples_to_average = 3000 * temp
        elif match == "4130":
            self._channels_session.source_delay = source_delay
            self._channels_session.samples_to_average = 3000 * temp
            # To do - validate and enable below code
            # if self._channels_session.channels == "1":
            # self._channels_session.sense = sense
        elif match == "4154":
            self._channels_session.source_delay = source_delay
            self._channels_session.samples_to_average = 300000 * temp
            self._channels_session.sense = sense
            # To do - validate and enable below code
            # if self._channels_session.channels == "0":
            # self._channels_session.transient_response =transient_response
        elif match == "4132":
            self._channels_session.aperture_time_units = aperture_time_units
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
            self._channels_session.sense = sense
        elif (match == "4112") or (match == "4112"):
            self._channels_session.aperture_time_units = aperture_time_units
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
        else:  # All properties supported
            self._channels_session.transient_response = transient_response
            self._channels_session.aperture_time_units = aperture_time_units
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
            self._channels_session.sense = sense

    def query_in_compliance(self):
        return self._channels_session.query_in_compliance()

    def query_output_state(self, output_state: nidcpower.OutputStates):
        return self._channels_session.query_output_state(output_state)

    def configure_aperture_time_with_abort_and_initiate(
            self,
            aperture_time=16.667,
            aperture_time_units=nidcpower.ApertureTimeUnits.SECONDS,
    ):
        self._channels_session.abort()
        self._channels_session.aperture_time(aperture_time, aperture_time_units)
        self._channels_session.initiate()

    def configure_aperture_time(self, aperture_time=16.667, aperture_time_units=nidcpower.ApertureTimeUnits.SECONDS):
        return self._channels_session.configure_aperture_time(aperture_time, aperture_time_units)

    def configure_power_line_frequency(self, power_line_frequency=60.0):
        self.power_line_frequency = power_line_frequency  # To Do confirm global replaced with object attributes.
        self._channels_session.power_line_frequency = power_line_frequency  # To Do method or property

    def configure_sense(self, sense=nidcpower.Sense.LOCAL):
        self._channels_session.sense = sense  # To Do method or property

    def get_aperture_time_in_seconds(self):
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
        actual_aperture_time = self._channels_session.aperture_time_units
        if match in all_supported_models + ["4112", "4113", "4132"]:
            if self._channels_session.aperture_time_units == nidcpower.ApertureTimeUnits.POWER_LINE_CYCLES:
                actual_aperture_time = self._channels_session.aperture_time_units / self._channels_session.power_line_frequency

        if match in ["4110", "4130"]:
            actual_aperture_time = self._channels_session.samples_to_average / 3000
        elif match == "4154":
            actual_aperture_time = self._channels_session.samples_to_average / 300000
        return actual_aperture_time

    def get_power_line_frequency(self):
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        configured_power_line_frequency = self._channels_session.power_line_frequency
        if match in ["4110", "4130"]:
            configured_power_line_frequency = self.power_line_frequency
        elif match == "4154":
            configured_power_line_frequency = self.power_line_frequency
        return configured_power_line_frequency

    def configure_current_level_range(self, current_level_range=0.0):
        self._channels_session.current_level_range = current_level_range  # To Do method or property

    def configure_current_level(self, current_level=0.0):
        self._channels_session.current_level = current_level  # To Do method or property

    def configure_single_point_force_dc_current_asymmetric_limits(
            self,
            current_level=0.0,
            current_level_range=0.0,
            voltage_limit_high=0.0,
            voltage_limit_low=0.0,
            voltage_limit_range=0.0
    ):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT  # To Do method or property
        self._channels_session.output_function = nidcpower.OutputFunction.DC_CURRENT  # To Do method or property
        self._channels_session.current_level = current_level  # To Do method or property
        self._channels_session.voltage_limit_high = voltage_limit_high  # To Do method or property
        self._channels_session.voltage_limit_low = voltage_limit_low  # To Do method or property
        c_value = current_level_range
        if c_value == 0.0:
            c_value = abs(current_level)
        self._channels_session.current_level_range = c_value  # To Do method or property
        v_value = voltage_limit_range
        if v_value == 0.0:
            v_value = max(abs(voltage_limit_high), abs(voltage_limit_low))
        self._channels_session.voltage_limit_range = v_value  # To Do method or property
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.ASYMMETRIC  # To Do method?

    def configure_single_point_force_dc_current_symmetric_limits(
            self,
            current_level=0.0,
            current_level_range=0.0,
            voltage_limit=0.0,
            voltage_limit_range=0.0
    ):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT  # To Do method or property
        self._channels_session.output_function = nidcpower.OutputFunction.DC_CURRENT  # To Do method or property
        self._channels_session.current_level = current_level  # To Do method or property
        self._channels_session.voltage_limit = voltage_limit  # To Do method or property
        c_value = current_level_range
        if c_value == 0.0:
            c_value = abs(current_level)
        self._channels_session.current_level_range = c_value  # To Do method or property
        v_value = voltage_limit_range
        if v_value == 0.0:
            v_value = abs(voltage_limit)
        self._channels_session.voltage_limit_range = v_value  # To Do method or property
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.SYMMETRIC  # To Do method?

    def configure_voltage_limit_range(self, voltage_limit_range=0.0):
        self._channels_session.voltage_limit_range = voltage_limit_range  # To Do method or property

    def configure_voltage_limit(self, voltage_limit=0.0):
        self._channels_session.voltage_limit = voltage_limit  # To Do method or property

    def force_current_asymmetric_limits(
            self,
            current_level=0.0,
            current_level_range=0.0,
            voltage_limit_high=0.0,
            voltage_limit_low=0.0,
            voltage_limit_range=0.0
    ):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_current_asymmetric_limits(
            current_level,
            current_level_range, voltage_limit_high, voltage_limit_low, voltage_limit_range)
        self._channels_session.commit()

    def force_current_symmetric_limits(
            self,
            current_level=0.0,
            current_level_range=0.0,
            voltage_limit=0.0,
            voltage_limit_range=0.0
    ):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_current_symmetric_limits(current_level,
                                                                                        current_level_range,
                                                                                        voltage_limit,
                                                                                        voltage_limit_range)
        self._channels_session.commit()

    def configure_voltage_level_range(self, voltage_level_range=0.0):
        self._channels_session.voltage_level_range = voltage_level_range  # To Do method or property

    def configure_voltage_level(self, voltage_level=0.0):
        self._channels_session.voltage_level = voltage_level  # To Do method or property

    def configure_single_point_force_dc_voltage_asymmetric_limits(
            self,
            voltage_level=0.0,
            voltage_level_range=0.0,
            current_limit_high=0.0,
            current_limit_low=0.0,
            current_limit_range=0.0
    ):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT  # To Do method or property
        self._channels_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE  # To Do method or property
        self._channels_session.voltage_level = voltage_level  # To Do method or property
        self._channels_session.current_limit_high = current_limit_high  # To Do method or property
        self._channels_session.current_limit_low = current_limit_low  # To Do method or property
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._channels_session.voltage_level_range = v_value  # To Do method or property
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = max(abs(current_limit_high), abs(current_limit_low))
        self._channels_session.current_limit_range = c_value  # To Do method or property
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.ASYMMETRIC  # To Do method?

    def configure_single_point_force_dc_voltage_symmetric_limits(
            self,
            voltage_level=0.0,
            voltage_level_range=0.0,
            current_limit=0.0,
            current_limit_range=0.0
    ):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT  # To Do method or property
        self._channels_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE  # To Do method or property
        self._channels_session.voltage_level = voltage_level  # To Do method or property
        self._channels_session.current_limit = current_limit  # To Do method or property
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._channels_session.voltage_level_range = v_value  # To Do method or property
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = abs(current_limit)
        self._channels_session.current_limit_range = c_value  # To Do method or property
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.SYMMETRIC  # To Do method?

    def configure_current_limit_range(self, current_limit_range=0.0):
        self._channels_session.current_limit_range = current_limit_range  # To Do method or property

    def configure_current_limit(self, current_limit=0.0):
        self._channels_session.current_limit = current_limit  # To Do method or property

    def force_voltage_asymmetric_limits(
            self,
            voltage_level=0.0,
            voltage_level_range=0.0,
            current_limit_high=0.0,
            current_limit_low=0.0,
            current_limit_range=0.0
    ):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_voltage_asymmetric_limits(voltage_level,
                                                                                         voltage_level_range,
                                                                                         current_limit_high,
                                                                                         current_limit_low,
                                                                                         current_limit_range)
        self._channels_session.commit()

    def force_voltage_symmetric_limits(
            self,
            voltage_level=0.0,
            voltage_level_range=0.0,
            current_limit=0.0,
            current_limit_range=0.0
    ):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_voltage_symmetric_limits(voltage_level,
                                                                                        voltage_level_range,
                                                                                        current_limit,
                                                                                        current_limit_range)
        self._channels_session.commit()

    def configure_source_adapt(
            self,
            voltage_gain_bandwidth,
            voltage_compensation_frequency,
            voltage_pole_zero_ratio,
            current_gain_bandwidth,
            current_compensation_frequency,
            current_pole_zero_ratio
    ):
        self._channels_session.transient_response = nidcpower.TransientResponse.CUSTOM
        self._channels_session.voltage_gain_bandwidth = voltage_gain_bandwidth
        self._channels_session.voltage_compensation_frequency = voltage_compensation_frequency
        self._channels_session.voltage_pole_zero_ratio = voltage_pole_zero_ratio
        self._channels_session.current_gain_bandwidth = current_gain_bandwidth
        self._channels_session.current_compensation_frequency = current_compensation_frequency
        self._channels_session.current_pole_zero_ratio = current_pole_zero_ratio

    def configure_transient_response(self, transient_response=nidcpower.TransientResponse.NORMAL):
        self._channels_session.transient_response = transient_response

    def get_source_adapt_settings(self):
        transient_response = self._channels_session.transient_response
        voltage_gain_bandwidth = self._channels_session.voltage_gain_bandwidth
        voltage_compensation_frequency = self._channels_session.voltage_compensation_frequency
        voltage_pole_zero_ratio = self._channels_session.voltage_pole_zero_ratio
        current_gain_bandwidth = self._channels_session.current_gain_bandwidth
        current_compensation_frequency = self._channels_session.current_compensation_frequency
        current_pole_zero_ratio = self._channels_session.current_pole_zero_ratio
        voltage = (voltage_gain_bandwidth, voltage_compensation_frequency, voltage_pole_zero_ratio)
        current = (current_gain_bandwidth, current_compensation_frequency, current_pole_zero_ratio)
        return transient_response, voltage, current

    def configure_output_connected(self, output_connected=False):
        self._channels_session.output_connected = output_connected  # To Do method or property

    def configure_output_enabled(self, output_enabled=False):
        self._channels_session.output_enabled = output_enabled  # To Do method or property

    def configure_output_function(self, output_function=nidcpower.OutputFunction.DC_VOLTAGE):
        self._channels_session.output_function = output_function  # To Do method or property

    def configure_output_resistance(self, output_resistance=0.0):
        self._channels_session.output_resistance = output_resistance  # To Do method or property

    def configure_source_delay(self, source_delay=0.0):
        self._channels_session.source_delay = source_delay  # To Do method or property

    def configure_source_mode(self, source_mode=nidcpower.SourceMode.SINGLE_POINT):
        self._channels_session.source_mode = source_mode  # To Do method or property

    def get_smu_model(self):
        smu_model = re.search("\d\d\d\d", self._channels_session.instrument_model, re.RegexFlag.ASCII)[0]
        return smu_model

    def get_max_current(self):
        pass

    def configure_export_signal(self, signal, output_terminal):
        pass

    def send_software_edge_trigger(self, trigger_to_send=nidcpower.SendSoftwareEdgeTriggerType.MEASURE):
        return self._channels_session.send_software_edge_trigger(trigger_to_send)

    def wait_for_event(self, event=nidcpower.Event.SOURCE_COMPLETE):
        return self._channels_session.wait_for_event(event)

    def configure_and_commit_waveform_acquisition(self, sample_rate, buffer_length):
        aperture_time_units = self._channels_session.aperture_time_units
        aperture_time = self._channels_session.aperture_time
        measure_when = self._channels_session.measure_when
        measure_trigger_type = self._channels_session.measure_trigger_type
        self._channels_session.aperture_time_units = nidcpower.ApertureTimeUnits.SECONDS
        self._channels_session.aperture_time = 1/sample_rate
        self._channels_session.measure_record_length_is_finite = False
        self._channels_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
        self._channels_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
        self._channels_session.commit()
        temp = math.ceil(buffer_length/self._channels_session.measure_record_delta_time)
        if self._channels_session.measure_buffer_size < temp:
            self._channels_session.measure_buffer_size = temp
        return aperture_time_units, aperture_time, measure_when, measure_trigger_type

    def reassign_post_acquisition(self, aperture_time_units, aperture_time, measure_when, measure_trigger_type):
        self._channels_session.aperture_time_units = aperture_time_units
        self._channels_session.aperture_time = aperture_time
        self._channels_session.measure_when = measure_when
        self._channels_session.measure_trigger_type = measure_trigger_type
        self._channels_session.measure_record_length_is_finite = True

    def configure_measurements(self,measurement_mode="Auto"):
        temp = measurement_mode
        if self.measure_multiple_only:
            temp = "Measure_Multiple"
        self._channels_session.abort()
        if temp == "Auto":
            model = self.get_smu_model()
            if model == 4110 or model == 4130:
                temp = "Measure_Multiple"
            else:
                temp = "Software_Triggers"
        if temp == "Software_Triggers":
            self._channels_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            self._channels_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
            self._channels_session.measure_record_length = 1
        else:
            self._channels_session.measure_when = nidcpower.MeasureWhen.ON_DEMAND




class _NIDCPowerTSM:
    def __init__(self, sessions_sites_channels: typing.Iterable[_NIDCPowerSSC]):
        self._sessions_sites_channels = sessions_sites_channels

    @staticmethod
    def _parse_instrument_names(resource_string: str) -> typing.Set[str]:
        channels = resource_string.split(",")
        instrument_names = set()
        for channel in channels:
            instrument_name = channel.split("/")[0]
            instrument_names += instrument_name.strip()
        return instrument_names

    @property
    def sessions_sites_channels(self):
        return self._sessions_sites_channels

    def abort(self):
        for ssc in self._sessions_sites_channels:
            ssc.abort()
        return

    def commit(self):
        for ssc in self._sessions_sites_channels:
            ssc.commit()
        return

    def initiate(self):
        for ssc in self._sessions_sites_channels:
            ssc.initiate()
        return

    def reset(self):
        for ssc in self._sessions_sites_channels:
            ssc.reset()
        return

    def configure_settings(self):
        pass

    def query_in_compliance(self):
        return [ssc.query_in_compliance() for ssc in self._sessions_sites_channels]

    def query_output_state(self, output_state: nidcpower.OutputStates):
        return [ssc.query_output_state(output_state) for ssc in self._sessions_sites_channels]


@nitsm.codemoduleapi.code_module
def initialize_sessions(
        tsm_context: _SemiconductorModuleContext, power_line_frequency=60.0, **kwargs
):
    """Todo(smooresni): Future docstring."""
    # cache kwargs
    reset = kwargs["reset"] if "reset" in kwargs.keys() else False
    options = kwargs["options"] if "options" in kwargs.keys() else {}

    # initialize and reset sessions
    resource_strings = tsm_context.get_all_nidcpower_resource_strings()
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
        tsm_context.set_nidcpower_session(resource_string, session)
    return


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: _SemiconductorModuleContext, pins):
    pin_query_context, sessions, channels = tsm_context.pins_to_nidcpower_sessions(pins)
    # pins = nidevtools.common.get_all_pins(tsm_context)
    pins = common.get_all_pins(tsm_context)
    # sscs = [_NIDCPowerSSC(session, channel) for session, channel in zip(sessions, channel_lists)]
    return


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: _SemiconductorModuleContext):
    """Todo(smooresni): Future docstring."""
    sessions = tsm_context.get_all_nidcpower_sessions()
    for session in sessions:
        session.abort()
        try:
            session.reset()
        except nidcpower.errors.DriverError:
            session.reset_device()
        session.close()
    return


if __name__ == "__main__":
    nidcpower.Session("Dev1", options={"Simulate": True, "DriverSetup": {"Model": "4162"}})
    # with nidcpower.Session("Dev1/0", options={"Simulate": True, "DriverSetup": {"Model": "4162"}}) as session:
    #     ssc = NIDCPowerSSC(session, "Dev1/0")
    #     tsm = NIDCPowerTSM([ssc])
    #     tsm.abort()
