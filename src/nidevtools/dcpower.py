import datetime
import re
import math
import typing
import nidcpower
from nidcpower.enums import *
import nidcpower.errors
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidevtools.common as ni_dt_common
from datetime import datetime


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


class MeasurementMode(Enum):
    AUTO = 0
    r'''
    Enables the automatic selection of the best measurement mode for the instrument.
    '''
    SOFTWARE_TRIGGER = 1
    r'''
    Performs measurements by sending a software trigger to the instrument. Typically yields fastest test times.
    '''
    MEASURE_MULTIPLE = 2
    r'''
    Performs measurements on demand. Typically allows for easier debugging but takes longer to fetch measurements.
    '''


class CustomTransientResponse:
    def __init__(self, gain_bandwidth: float, compensation_frequency: float, pole_zero_ratio: float):
        self._gain_bandwidth = gain_bandwidth
        self._compensation_frequency = compensation_frequency
        self._pole_zero_ratio = pole_zero_ratio

    @property
    def gain_bandwidth(self):
        return self._gain_bandwidth

    @property
    def compensation_frequency(self):
        return self._compensation_frequency

    @property
    def pole_zero_ratio(self):
        return self._pole_zero_ratio


def model_to_ranges(model, channel):
    r_v = []
    r_i = []
    current_ranges = []
    voltage_ranges = []

    if model == 4135:
        r_v = [500000000, 5000000, 50000, 5000, 500, 50, 5]
        r_i = r_v
    elif model == 4137:
        r_v = [5000000, 500000, 50000, 5000, 500, 50, 5]
        r_i = r_v
    elif model == 4139:
        r_v = [5000000, 500000, 50000, 5000, 500, 50, 5, 0.5]
        r_i = r_v
    elif model == 4141:
        r_v = [100000, 10000, 1000, 100, 10]
    elif model == 4143:
        r_v = [100000, 10000, 1000, 100, 6.66]
    elif model == 4145:
        r_v = [50000, 5000, 500, 50, 5, 1]
    elif model == 4147:
        r_v = [4000000, 400000, 40000, 4000, 400, 40, 1.25]
        r_i = [2500000, 250000, 25000, 2500, 250, 25, 750]

    if model == 4110 or model == 4112:
        current_ranges = [1]
    elif model == 4113:
        current_ranges = [6]
    elif model == 4132:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    elif model == 4135:
        current_ranges = [10e-9, 1e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
    elif model == 4136 or model == 4137:
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
    elif model == 4138 or model == 4139:
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1, 3]
    elif model == 4140 or model == 4141:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    elif model == 4142 or model == 4143:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.15]
    elif model == 4144 or model == 4145:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1, 0.5]
    elif model == 4147:
        current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 3]
    elif model == 4162:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    elif model == 4163:
        current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.05]

    if model == 4110:
        if channel == 0:
            voltage_ranges = [6]
        elif channel == 1:
            voltage_ranges = [20]
        elif channel == 2:
            voltage_ranges = [-20]
    elif model == 4112:
        voltage_ranges = [60]
    elif model == 4113:
        voltage_ranges = [10]
    elif model == 4132:
        voltage_ranges = [10, 100]
    elif model == 4135 or model == 4136 or model == 4137:
        voltage_ranges = [.6, 6, 20, 200]
    elif model == 4138 or model == 4139:
        voltage_ranges = [.6, 6, 60]
    elif model == 4140 or model == 4141:
        voltage_ranges = [10]
    elif model == 4142 or model == 4143 or model == 4162 or model == 4163:
        voltage_ranges = [24]
    elif model == 4144 or model == 4145:
        voltage_ranges = [6]
    elif model == 4147:
        voltage_ranges = [1, 8]

    return r_v, r_i, current_ranges, voltage_ranges


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

    def configure_aperture_time_with_abort_and_initiate(self, aperture_time=16.667,
                                                        aperture_time_units=ApertureTimeUnits.SECONDS):
        self._channels_session.abort()
        self._channels_session.aperture_time(aperture_time, aperture_time_units)
        self._channels_session.initiate()

    def configure_aperture_time(self, aperture_time=16.667, aperture_time_units=ApertureTimeUnits.SECONDS):
        return self._channels_session.configure_aperture_time(aperture_time, aperture_time_units)

    def configure_power_line_frequency(self, power_line_frequency=60.0):
        self.power_line_frequency = power_line_frequency  # To Do - confirm global replaced with object attributes.
        self._channels_session.power_line_frequency = power_line_frequency

    def configure_sense(self, sense=Sense.LOCAL):
        self._channels_session.sense = sense

    def configure_settings(self, aperture_time=16.667, source_delay=0.0, sense=Sense.LOCAL,
                           aperture_time_unit=ApertureTimeUnits.SECONDS,
                           transient_response=TransientResponse.NORMAL):
        self._channels_session.abort()
        match = re.search("\d\d\d\d", self._session.instrument_model, re.RegexFlag.ASCII)[0]
        temp = aperture_time
        if aperture_time_unit == ApertureTimeUnits.POWER_LINE_CYCLES:
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
            self._channels_session.aperture_time_units = aperture_time_unit
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
            self._channels_session.sense = sense
            self._channels_session.sense = sense
        elif (match == "4112") or (match == "4112"):
            self._channels_session.aperture_time_units = aperture_time_unit
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
        else:  # All properties supported
            self._channels_session.transient_response = transient_response
            self._channels_session.aperture_time_units = aperture_time_unit
            self._channels_session.aperture_time = aperture_time
            self._channels_session.source_delay = source_delay
            self._channels_session.sense = sense

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
            if self._channels_session.aperture_time_units == ApertureTimeUnits.POWER_LINE_CYCLES:
                actual_aperture_time = self._channels_session.aperture_time_units / \
                                       self._channels_session.power_line_frequency

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

    def query_in_compliance(self):
        return self._channels_session.query_in_compliance()

    def query_output_state(self, output_state: nidcpower.OutputStates):
        return self._channels_session.query_output_state(output_state)

    def configure_current_level_range(self, current_level_range=0.0):
        self._channels_session.current_level_range = current_level_range  # To Do method or property

    def configure_current_level(self, current_level=0.0):
        self._channels_session.current_level = current_level

    def configure_single_point_force_dc_current_asymmetric_limits(self, current_level=0.0, current_level_range=0.0,
                                                                  voltage_limit_high=0.0, voltage_limit_low=0.0,
                                                                  voltage_limit_range=0.0):
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

    def configure_single_point_force_dc_current_symmetric_limits(self, current_level=0.0, current_level_range=0.0,
                                                                 voltage_limit=0.0, voltage_limit_range=0.0):
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
        self._channels_session.voltage_limit_range = voltage_limit_range

    def configure_voltage_limit(self, voltage_limit=0.0):
        self._channels_session.voltage_limit = voltage_limit

    def force_current_asymmetric_limits(self, current_level=0.0, current_level_range=0.0, voltage_limit_high=0.0,
                                        voltage_limit_low=0.0, voltage_limit_range=0.0):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_current_asymmetric_limits(
            current_level,
            current_level_range, voltage_limit_high, voltage_limit_low, voltage_limit_range)
        self._channels_session.commit()

    def force_current_symmetric_limits(self, current_level=0.0, current_level_range=0.0, voltage_limit=0.0,
                                       voltage_limit_range=0.0):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_current_symmetric_limits(current_level,
                                                                                        current_level_range,
                                                                                        voltage_limit,
                                                                                        voltage_limit_range)
        self._channels_session.commit()

    def configure_current_limit_range(self, current_limit_range=0.0):
        self._channels_session.current_limit_range = current_limit_range

    def configure_current_limit(self, current_limit=0.0):
        self._channels_session.current_limit = current_limit

    def configure_single_point_force_dc_voltage_asymmetric_limits(self, voltage_level=0.0, voltage_level_range=0.0,
                                                                  current_limit_high=0.0, current_limit_low=0.0,
                                                                  current_limit_range=0.0):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._channels_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self._channels_session.voltage_level = voltage_level
        self._channels_session.current_limit_high = current_limit_high
        self._channels_session.current_limit_low = current_limit_low
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._channels_session.voltage_level_range = v_value
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = max(abs(current_limit_high), abs(current_limit_low))
        self._channels_session.current_limit_range = c_value
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.ASYMMETRIC

    def configure_single_point_force_dc_voltage_symmetric_limits(self, voltage_level=0.0, voltage_level_range=0.0,
                                                                 current_limit=0.0, current_limit_range=0.0):
        self._channels_session.source_mode = nidcpower.SourceMode.SINGLE_POINT
        self._channels_session.output_function = nidcpower.OutputFunction.DC_VOLTAGE
        self._channels_session.voltage_level = voltage_level
        self._channels_session.current_limit = current_limit
        v_value = voltage_level_range
        if v_value == 0.0:
            v_value = abs(voltage_level)
        self._channels_session.voltage_level_range = v_value
        c_value = current_limit_range
        if c_value == 0.0:
            c_value = abs(current_limit)
        self._channels_session.current_limit_range = c_value
        self._channels_session.compliance_limit_symmetry = nidcpower.ComplianceLimitSymmetry.SYMMETRIC  # To Do method?

    def configure_voltage_level_range(self, voltage_level_range=0.0):
        self._channels_session.voltage_level_range = voltage_level_range

    def configure_voltage_level(self, voltage_level=0.0):
        self._channels_session.voltage_level = voltage_level

    def force_voltage_asymmetric_limits(self, voltage_level=0.0, voltage_level_range=0.0, current_limit_high=0.0,
                                        current_limit_low=0.0, current_limit_range=0.0):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_voltage_asymmetric_limits(voltage_level,
                                                                                         voltage_level_range,
                                                                                         current_limit_high,
                                                                                         current_limit_low,
                                                                                         current_limit_range)
        self._channels_session.commit()

    def force_voltage_symmetric_limits(self, voltage_level=0.0, voltage_level_range=0.0, current_limit=0.0,
                                       current_limit_range=0.0):
        self._channels_session.abort()
        self._channels_session.configure_single_point_force_dc_voltage_symmetric_limits(voltage_level,
                                                                                        voltage_level_range,
                                                                                        current_limit,
                                                                                        current_limit_range)
        self._channels_session.commit()

    def configure_source_adapt(self, voltage_ctr: CustomTransientResponse, current_ctr: CustomTransientResponse):
        self._channels_session.transient_response = TransientResponse.CUSTOM
        self._channels_session.voltage_gain_bandwidth = voltage_ctr.gain_bandwidth
        self._channels_session.voltage_compensation_frequency = voltage_ctr.compensation_frequency
        self._channels_session.voltage_pole_zero_ratio = voltage_ctr.pole_zero_ratio
        self._channels_session.current_gain_bandwidth = current_ctr.gain_bandwidth
        self._channels_session.current_compensation_frequency = current_ctr.compensation_frequency
        self._channels_session.current_pole_zero_ratio = current_ctr.pole_zero_ratio

    def configure_transient_response(self, transient_response=TransientResponse.NORMAL):
        self._channels_session.transient_response = transient_response

    def get_source_adapt_settings(self):
        transient_response = self._channels_session.transient_response
        v_gain_bw = self._channels_session.voltage_gain_bandwidth
        v_comp_fr = self._channels_session.voltage_compensation_frequency
        v_pole_0_ratio = self._channels_session.voltage_pole_zero_ratio
        i_gain_bw = self._channels_session.current_gain_bandwidth
        i_comp_fr = self._channels_session.current_compensation_frequency
        i_pole_0_ratio = self._channels_session.current_pole_zero_ratio
        voltage_ctr = CustomTransientResponse(v_gain_bw, v_comp_fr, v_pole_0_ratio)
        current_ctr = CustomTransientResponse(i_gain_bw, i_comp_fr, i_pole_0_ratio)
        return transient_response, voltage_ctr, current_ctr

    def configure_output_connected(self, output_connected=False):
        self._channels_session.output_connected = output_connected

    def configure_output_enabled(self, output_enabled=False):
        self._channels_session.output_enabled = output_enabled

    def configure_output_function(self, output_function=nidcpower.OutputFunction.DC_VOLTAGE):
        self._channels_session.output_function = output_function

    def configure_output_resistance(self, output_resistance=0.0):
        self._channels_session.output_resistance = output_resistance

    def configure_source_delay(self, source_delay=0.0):
        self._channels_session.source_delay = source_delay

    def configure_source_mode(self, source_mode=nidcpower.SourceMode.SINGLE_POINT):
        self._channels_session.source_mode = source_mode

    def get_smu_model(self):
        smu_model = re.search("\d\d\d\d", self._channels_session.instrument_model, re.RegexFlag.ASCII)[0]
        return smu_model

    def get_max_current(self):
        smu_model = self.get_smu_model()
        c_r = model_to_ranges(smu_model, self.channels)
        return c_r[-1]

    def configure_measurements(self, mode=MeasurementMode.AUTO):
        self._channels_session.abort()
        if self.measure_multiple_only:
            mode = MeasurementMode.MEASURE_MULTIPLE
        if mode == MeasurementMode.AUTO:
            model = self.get_smu_model()
            if model == 4110 or model == 4130:
                mode = MeasurementMode.MEASURE_MULTIPLE
            else:
                mode = MeasurementMode.SOFTWARE_TRIGGER
        if mode == MeasurementMode.SOFTWARE_TRIGGER:
            self._channels_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
            self._channels_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
            self._channels_session.measure_record_length = 1
        else:
            self._channels_session.measure_when = nidcpower.MeasureWhen.ON_DEMAND

    def configure_export_signal(self, signal, output_terminal):
        # self._channels_session.export_signal () method not found.
        pass

    def send_software_edge_trigger(self, trigger_to_send=SendSoftwareEdgeTriggerType.MEASURE):
        return self._channels_session.send_software_edge_trigger(trigger_to_send)

    def wait_for_event(self, event=nidcpower.Event.SOURCE_COMPLETE, timeout=10.0):
        return self._channels_session.wait_for_event(event, timeout)

    def configure_and_commit_waveform_acquisition(self, sample_rate, buffer_length=1.0):
        settings = self.get_measurement_settings()
        self._channels_session.aperture_time_units = ApertureTimeUnits.SECONDS
        self._channels_session.aperture_time = 1/sample_rate
        self._channels_session.measure_record_length_is_finite = False
        self._channels_session.measure_when = nidcpower.MeasureWhen.ON_MEASURE_TRIGGER
        self._channels_session.measure_trigger_type = nidcpower.TriggerType.SOFTWARE_EDGE
        self._channels_session.commit()
        num_samples = int(math.ceil(buffer_length/self._channels_session.measure_record_delta_time))
        # coerce num_samples to be between 1 and max value of I32 (2147483647)
        if num_samples < 1:
            num_samples = 1
        elif num_samples > 2147483647:
            num_samples = 2147483647
        if self._channels_session.measure_buffer_size < num_samples:
            self._channels_session.measure_buffer_size = num_samples
        return settings

    def get_measurement_settings(self):
        settings = {'aperture_time_units': self._channels_session.aperture_time_units,
                    'aperture_time': self._channels_session.aperture_time,
                    'measure_when': self._channels_session.measure_when,
                    'measure_trigger_type': self._channels_session.measure_trigger_type,
                    'measure_record_length': self._channels_session.measure_record_length,
                    'measure_record_length_is_finite': self._channels_session.measure_record_length_is_finite}
        return settings

    def set_measurement_settings(self, settings):
        self._channels_session.aperture_time = settings['aperture_time']
        self._channels_session.aperture_time_units = settings['aperture_time_units']
        self._channels_session.measure_when = settings['measure_when']
        self._channels_session.measure_trigger_type = settings['measure_trigger_type']
        self._channels_session.measure_record_length = settings['measure_record_length']
        self._channels_session.measure_record_length_is_finite = settings['measure_record_length_is_finite']

    def measure_setup(self, measurement_mode: MeasurementMode):
        if measurement_mode == MeasurementMode.MEASURE_MULTIPLE:
            fetch_or_measure = False
        elif measurement_mode == MeasurementMode.SOFTWARE_TRIGGER:
            fetch_or_measure = not self.measure_multiple_only
        else:
            fetch_or_measure = (self._channels_session.measure_when == MeasureWhen.ON_MEASURE_TRIGGER)

        if fetch_or_measure:
            self._channels_session.send_software_edge_trigger(SendSoftwareEdgeTriggerType.MEASURE)
        return fetch_or_measure

    def measure_execute(self, fetch_or_measure: bool):
        if fetch_or_measure:
            samples = self._channels_session.channels[self.channels].fetch_multiple(1, 1.0)
        else:
            samples = self._channels_session.channels[self.channels].measure_multiple()
        voltages = []
        currents = []
        in_compliance = []
        for s in samples:
            voltages.append(s[0])
            currents.append(s[1])
            in_compliance.append(s[2])
        voltage = voltages[0]
        current = currents[0]
        return voltage, current


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

    @staticmethod
    def _expand_to_requested_array_size(generic_in, size: int):
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
        return self._sessions_sites_channels

    def _configure_settings_array(self, aperture_times, source_delays, senses, aperture_time_units,
                                  transient_responses):
        for (ssc, aperture_time, source_delay, sense, aperture_time_unit,
             transient_response) in zip(self._sessions_sites_channels, aperture_times, source_delays, senses,
                                        aperture_time_units, transient_responses):
            ssc.configure_settings(aperture_time, source_delay, sense, aperture_time_unit, transient_response)

    def _force_current_asymmetric_limits_array(self, current_levels, current_level_ranges, voltage_limit_highs,
                                               voltage_limit_lows, voltage_limit_ranges):
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.force_current_asymmetric_limits(current_levels[i], current_level_ranges[i], voltage_limit_highs[i],
                                                voltage_limit_lows[i], voltage_limit_ranges[i])
            i += 1
        self.initiate()

    def _force_current_symmetric_limits_array(self, current_levels, current_level_ranges, voltage_limits,
                                              voltage_limit_ranges):
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.force_current_symmetric_limits(current_levels[i], current_level_ranges[i], voltage_limits[i],
                                               voltage_limit_ranges[i])
            i += 1
        self.initiate()

    def _force_voltage_asymmetric_limits_array(self, voltage_levels, voltage_level_ranges, current_limit_highs,
                                               current_limit_lows, current_limit_ranges):
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.force_voltage_asymmetric_limits(voltage_levels[i], voltage_level_ranges[i], current_limit_highs[i],
                                                current_limit_lows[i], current_limit_ranges[i])
            i += 1
        self.initiate()

    def _force_voltage_symmetric_limits_array(self, voltage_levels, voltage_level_ranges, current_limits,
                                              current_limit_ranges):
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.force_voltage_symmetric_limits(voltage_levels[i], voltage_level_ranges[i], current_limits[i],
                                               current_limit_ranges[i])
            i += 1
        self.initiate()

    def _expand_array_to_sessions(self, generic_in):
        if hasattr(generic_in, "__iter__"):
            generic_array = generic_in
            # Need to revisit this code for all cases as per reference LabVIEW code
        else:
            generic_array = []
            for ssc in self._sessions_sites_channels:
                generic_array.append(generic_in)
        return generic_array

    def _force_current_asymmetric_limits(self, current_level, current_level_range, voltage_limit_high,
                                         voltage_limit_low, voltage_limit_range):
        size = 0
        for scc in self._sessions_sites_channels:
            size += 1
        current_levels = self._expand_to_requested_array_size(current_level, size)
        current_level_ranges = self._expand_to_requested_array_size(current_level_range, size)
        voltage_limit_highs = self._expand_to_requested_array_size(voltage_limit_high, size)
        voltage_limit_lows = self._expand_to_requested_array_size(voltage_limit_low, size)
        voltage_limit_ranges = self._expand_to_requested_array_size(voltage_limit_range, size)
        self._force_current_asymmetric_limits_array(current_levels, current_level_ranges, voltage_limit_highs,
                                                    voltage_limit_lows, voltage_limit_ranges)

    def _force_current_symmetric_limits(self, current_level, current_level_range, voltage_limit, voltage_limit_range):
        size = 0
        for scc in self._sessions_sites_channels:
            size += 1
        current_levels = self._expand_to_requested_array_size(current_level, size)
        current_level_ranges = self._expand_to_requested_array_size(current_level_range, size)
        voltage_limits = self._expand_to_requested_array_size(voltage_limit, size)
        voltage_limit_ranges = self._expand_to_requested_array_size(voltage_limit_range, size)
        self._force_current_symmetric_limits_array(current_levels, current_level_ranges, voltage_limits,
                                                   voltage_limit_ranges)

    def _force_voltage_asymmetric_limits(self, voltage_level, voltage_level_range, current_limit_high,
                                         current_limit_low, current_limit_range):
        size = 0
        for scc in self._sessions_sites_channels:
            size += 1
        voltage_levels = self._expand_to_requested_array_size(voltage_level, size)
        voltage_level_ranges = self._expand_to_requested_array_size(voltage_level_range, size)
        current_limit_highs = self._expand_to_requested_array_size(current_limit_high, size)
        current_limit_lows = self._expand_to_requested_array_size(current_limit_low, size)
        current_limit_ranges = self._expand_to_requested_array_size(current_limit_range, size)
        self._force_current_asymmetric_limits_array(voltage_levels, voltage_level_ranges, current_limit_highs,
                                                    current_limit_lows, current_limit_ranges)

    def _force_voltage_symmetric_limits(self, voltage_level, voltage_level_range, current_limit, current_limit_range):
        size = 0
        for scc in self._sessions_sites_channels:
            size += 1
        voltage_levels = self._expand_to_requested_array_size(voltage_level, size)
        voltage_level_ranges = self._expand_to_requested_array_size(voltage_level_range, size)
        current_limits = self._expand_to_requested_array_size(current_limit, size)
        current_limit_ranges = self._expand_to_requested_array_size(current_limit_range, size)
        self._force_current_symmetric_limits_array(voltage_levels, voltage_level_ranges, current_limits,
                                                   current_limit_ranges)

    def abort(self):
        for ssc in self._sessions_sites_channels:
            ssc.abort()

    def commit(self):
        for ssc in self._sessions_sites_channels:
            ssc.commit()

    def initiate(self):
        for ssc in self._sessions_sites_channels:
            ssc.initiate()

    def reset(self):
        for ssc in self._sessions_sites_channels:
            ssc.reset()

    def configure_aperture_time_with_abort_and_initiate(self, aperture_time=16.667,
                                                        aperture_time_units=ApertureTimeUnits.SECONDS):
        for ssc in self._sessions_sites_channels:
            ssc.configure_aperture_time_with_abort_and_initiate(aperture_time, aperture_time_units)
        return

    def configure_power_line_frequency(self, power_line_frequency=60.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_power_line_frequency(power_line_frequency)
        return

    def configure_sense(self, sense=Sense.LOCAL):
        for ssc in self._sessions_sites_channels:
            ssc.configure_sense(sense)
        return

    def get_aperture_times_in_seconds(self):
        return [ssc.get_aperture_time_in_seconds() for ssc in self._sessions_sites_channels]

    def get_power_line_frequencies(self):
        return [ssc.get_power_line_frequency() for ssc in self._sessions_sites_channels]

    def query_in_compliance(self):
        return [ssc.query_in_compliance() for ssc in self._sessions_sites_channels]

    def query_output_state(self, output_state: nidcpower.OutputStates):
        return [ssc.query_output_state(output_state) for ssc in self._sessions_sites_channels]

    def configure_transient_response(self, transient_response=TransientResponse.NORMAL):
        for ssc in self._sessions_sites_channels:
            ssc.configure_transient_response(transient_response)
        return

    def configure_output_connected(self, output_connected=False):
        for ssc in self._sessions_sites_channels:
            ssc.configure_output_connected(output_connected)
        return

    def configure_output_enabled(self, output_enabled=False):
        for ssc in self._sessions_sites_channels:
            ssc.configure_output_enabled(output_enabled)
        return

    def configure_output_enabled_and_connected(self, output_enabled_and_connected=False):
        if output_enabled_and_connected:
            self.configure_output_enabled(output_enabled_and_connected)
            self.configure_output_connected(output_enabled_and_connected)
        else:
            self.configure_output_connected(output_enabled_and_connected)
            self.configure_output_enabled(output_enabled_and_connected)

    def configure_output_resistance(self, output_resistance=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_output_resistance(output_resistance)
        return

    def configure_output_resistance_array(self, output_resistance):
        output_resistances = self._expand_array_to_sessions(output_resistance)
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.configure_output_resistance(output_resistances[i])
            i += 1

    def configure_source_delay(self, source_delay=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_source_delay(source_delay)

    def configure_source_mode(self, source_mode=nidcpower.SourceMode.SINGLE_POINT):
        for ssc in self._sessions_sites_channels:
            ssc.configure_source_mode(source_mode)

    def get_max_current(self):
        return [ssc.get_max_current() for ssc in self._sessions_sites_channels]

    def wait_for_event(self, event=nidcpower.Event.SOURCE_COMPLETE, timeout=10.0):
        for ssc in self._sessions_sites_channels:
            ssc.wait_for_event(event, timeout)
        return

    def configure_and_start_waveform_acquisition(self, sample_rate=0.0, buffer_length=0.0):
        self.abort()
        previous_settings = []
        for ssc in self._sessions_sites_channels:
            settings = ssc.configure_and_commit_waveform_acquisition(sample_rate, buffer_length)
            previous_settings.append(settings)
        self.initiate()
        self.send_software_edge_trigger(nidcpower.SendSoftwareEdgeTriggerType.MEASURE)
        start_time = datetime.now()
        settings = [previous_settings, start_time]
        return settings

    def send_software_edge_trigger(self, trigger_to_send=nidcpower.SendSoftwareEdgeTriggerType.MEASURE):
        for ssc in self._sessions_sites_channels:
            ssc.send_software_edge_trigger(trigger_to_send)

    def finish_waveform_acquisition(self, settings, fetch_waveform_length_s=0.0):
        voltage_waveforms, current_waveforms = self.fetch_waveform(settings['start_time'], fetch_waveform_length_s)
        self.abort()
        self.set_measurement_settings(settings['previous_settings'])
        self.initiate()
        return voltage_waveforms, current_waveforms

    def fetch_waveform(self, waveform_t0, waveform_length_s=0.0):
        voltage_waveforms = []
        current_waveforms = []
        for ssc in self._sessions_sites_channels:
            record_dt = ssc.session.measure_record_delta_time.total_seconds()
            fetch_backlog = ssc.session.fetch_backlog
            if waveform_length_s == 0.0:
                fetch_samples = fetch_backlog
            else:
                fetch_samples = int(waveform_length_s / record_dt)
            samples = ssc.session.channels[ssc.channels].fetch_multiple(fetch_samples, timeout=waveform_length_s + 1)
            voltages = []
            currents = []
            in_compliance = []
            for s in samples:
                voltages.append(s[0])
                currents.append(s[1])
                in_compliance.append(s[2])
            voltage_waveform = {
                'channel': ssc.channels + "(V)",
                'samples': voltages,
                'x_increment': record_dt,
                'absolute_initial_x': waveform_t0
            }
            current_waveform = {
                'channel': ssc.channels + "(A)",
                'samples': currents,
                'x_increment': record_dt,
                'absolute_initial_x': waveform_t0
            }
            voltage_waveforms.append(voltage_waveform)
            current_waveforms.append(current_waveform)
        return voltage_waveforms, current_waveforms

    def get_measurement_settings(self):
        meas_settings = []
        for ssc in self._sessions_sites_channels:
            settings = ssc.get_measurement_settings()
            meas_settings.append(settings)
        return meas_settings

    def set_measurement_settings(self, meas_settings):
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.set_measurement_settings(meas_settings[i])
            i += 1

    def configure_measurements(self, mode=MeasurementMode.AUTO):
        for ssc in self._sessions_sites_channels:
            ssc.configure_measurements(mode)

    def configure_settings(self, aperture_time=16.667, source_delay=0.0, sense=Sense.LOCAL,
                           aperture_time_unit=ApertureTimeUnits.SECONDS,
                           transient_response=TransientResponse.NORMAL):
        transient_responses = self._expand_array_to_sessions(transient_response)
        aperture_time_units = self._expand_array_to_sessions(aperture_time_unit)
        aperture_times = self._expand_array_to_sessions(aperture_time)
        source_delays = self._expand_array_to_sessions(source_delay)
        senses = self._expand_array_to_sessions(sense)
        self._configure_settings_array(aperture_times, source_delays, senses, aperture_time_units, transient_responses)

    def configure_current_level_range(self, current_level_range=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_level_range(current_level_range)

    def configure_current_level(self, current_level=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_level(current_level)

    def configure_current_level_array(self, current_levels_array):
        current_levels = self._expand_array_to_sessions(current_levels_array)
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_level(current_levels[i])
            i += 1

    def configure_voltage_limit_range(self, voltage_limit_range=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_limit_range(voltage_limit_range)

    def configure_voltage_limit(self, voltage_limit=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_limit(voltage_limit)

    def configure_voltage_limit_array(self, voltage_limits_array):
        voltage_limits = self._expand_array_to_sessions(voltage_limits_array)
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_limit(voltage_limits[i])
            i += 1

    def configure_voltage_level_range(self, voltage_level_range=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_level_range(voltage_level_range)

    def configure_voltage_level(self, voltage_level=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_level(voltage_level)

    def configure_voltage_level_array(self, voltage_levels_array):
        voltage_levels = self._expand_array_to_sessions(voltage_levels_array)
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.configure_voltage_level(voltage_levels[i])
            i += 1

    def configure_current_limit_range(self, current_limit_range=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_limit_range(current_limit_range)

    def configure_current_limit(self, current_limit=0.0):
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_limit(current_limit)

    def configure_current_limit_array(self, current_limits_array):
        current_limits = self._expand_array_to_sessions(current_limits_array)
        i = 0
        for ssc in self._sessions_sites_channels:
            ssc.configure_current_limit(current_limits[i])
            i += 1

    def force_current_asymmetric_limits(self, current_level, current_level_range, voltage_limit_high,
                                        voltage_limit_low, voltage_limit_range):
        current_levels = self._expand_array_to_sessions(current_level)
        current_level_ranges = self._expand_array_to_sessions(current_level_range)
        voltage_limit_highs = self._expand_array_to_sessions(voltage_limit_high)
        voltage_limit_lows = self._expand_array_to_sessions(voltage_limit_low)
        voltage_limit_ranges = self._expand_array_to_sessions(voltage_limit_range)
        self._force_current_asymmetric_limits_array(current_levels, current_level_ranges, voltage_limit_highs,
                                                    voltage_limit_lows, voltage_limit_ranges)

    def force_current_symmetric_limits(self, current_level, current_level_range, voltage_limit, voltage_limit_range):
        current_levels = self._expand_array_to_sessions(current_level)
        current_level_ranges = self._expand_array_to_sessions(current_level_range)
        voltage_limits = self._expand_array_to_sessions(voltage_limit)
        voltage_limit_ranges = self._expand_array_to_sessions(voltage_limit_range)
        self._force_current_symmetric_limits_array(current_levels, current_level_ranges, voltage_limits,
                                                   voltage_limit_ranges)

    def force_voltage_asymmetric_limits(self, voltage_level, voltage_level_range, current_limit_high,
                                        current_limit_low, current_limit_range):
        voltage_levels = self._expand_array_to_sessions(voltage_level)
        voltage_level_ranges = self._expand_array_to_sessions(voltage_level_range)
        current_limit_highs = self._expand_array_to_sessions(current_limit_high)
        current_limit_lows = self._expand_array_to_sessions(current_limit_low)
        current_limit_ranges = self._expand_array_to_sessions(current_limit_range)
        self._force_current_asymmetric_limits_array(voltage_levels, voltage_level_ranges, current_limit_highs,
                                                    current_limit_lows, current_limit_ranges)

    def force_voltage_symmetric_limits(self, voltage_level, voltage_level_range, current_limit, current_limit_range):
        voltage_levels = self._expand_array_to_sessions(voltage_level)
        voltage_level_ranges = self._expand_array_to_sessions(voltage_level_range)
        current_limits = self._expand_array_to_sessions(current_limit)
        current_limit_ranges = self._expand_array_to_sessions(current_limit_range)
        self._force_current_symmetric_limits_array(voltage_levels, voltage_level_ranges, current_limits,
                                                   current_limit_ranges)

    def measure(self, measurement_mode: MeasurementMode):
        fetch_or_measure_array = []
        voltages = []
        currents = []
        for ssc in self._sessions_sites_channels:
            fetch_or_measure_array.append(ssc.measure_setup(measurement_mode))
        i = 0
        for ssc in self._sessions_sites_channels:
            voltage, current = ssc.measure_execute(fetch_or_measure_array[i])
            voltages.append(voltage)
            currents.append(current)
            i += 1
        return voltages, currents

    def configure_source_adapt(self, voltage_ctr: CustomTransientResponse, current_ctr: CustomTransientResponse):
        for ssc in self._sessions_sites_channels:
            ssc.configure_source_adapt(voltage_ctr, current_ctr)

    def get_source_adapt_settings(self):
        return [ssc.get_source_adapt_settings() for ssc in self._sessions_sites_channels]

    def filter_sites(self, requested_sites):
        filtered_ssc = []
        for ssc in self._sessions_sites_channels:
            found = False
            sites = ni_dt_common.channel_list_to_pins(ssc.channels)[2]
            for s in sites:
                found = (s in requested_sites) or found
            if found:
                filtered_ssc.append(ssc)
        return filtered_ssc

    def filter_pins(self, requested_pins):
        temp1 = []
        temp2 = []
        for ssc in self._sessions_sites_channels:
            sites_pins, pins, sites = ni_dt_common.channel_list_to_pins(ssc.channels)
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
    pin_query_context: typing.Any
    ssc: _NIDCPowerTSM
    site_numbers: typing.List[int]
    pins_info: typing.List[ni_dt_common.PinInformation]
    pins_expanded: typing.List[ni_dt_common.ExpandedPinInformation]


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: SemiconductorModuleContext, power_line_frequency=60.0, **kwargs):
    """Creates the sessions for all the nidcpower resource string
    available in the tsm_context"""
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


@nitsm.codemoduleapi.code_module
def pins_to_sessions(tsm_context: SemiconductorModuleContext,
                     pins: typing.List[str],
                     site_numbers: typing.List[int] = [],
                     fill_pin_site_info=True):
    if len(site_numbers) == 0:
        site_numbers = list(tsm_context.site_numbers)
    pins_expanded = []
    pins_info = []
    pin_query_context, sessions, channels = tsm_context.pins_to_nidcpower_sessions(pins)
    if fill_pin_site_info:
        pins_info, pins_expanded = ni_dt_common.expand_pin_groups_and_identify_pin_types(tsm_context, pins)
    else:
        for pin in pins:
            a = ni_dt_common.PinInformation  # create instance of class
            a.pin = pin
            pins_info.append(a)
    session_channel_list = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, pins_expanded, site_numbers)
    sscs = [_NIDCPowerSSC(session, channel) for session, channel in zip(sessions, session_channel_list)]
    dc_power_tsm = _NIDCPowerTSM(sscs)
    return TSMDCPower(pin_query_context, dc_power_tsm, site_numbers, pins_info, pins_expanded)


def filter_pins(dc_power_tsm: TSMDCPower, desired_pins):
    dc_power_tsm.ssc.filter_pins(desired_pins)
    all_pins = ni_dt_common.get_pin_names_from_expanded_pin_information(dc_power_tsm.pins_expanded)
    i = 0
    pins_expand_new = []
    for d_pin in desired_pins:
        index_d = all_pins.index(d_pin)
        data = dc_power_tsm.pins_expanded[index_d]
        output = ni_dt_common.PinInformation(data.pin, data.type, 1)
        data.index = i
        dc_power_tsm.pins_info.append(output)
        if index_d >= 0:
            pins_expand_new.append(data)
        i += 1
    dut_pins, system_pins = ni_dt_common.get_dut_pins_and_system_pins_from_expanded_pin_list(pins_expand_new)
    pins_to_query_ctx = ni_dt_common.get_pin_names_from_expanded_pin_information(dut_pins + system_pins)
    dc_power_tsm.pin_query_context.Pins = pins_to_query_ctx
    return dc_power_tsm


def filter_sites(dc_power_tsm: TSMDCPower, sites):
    dc_power_tsm.ssc = dc_power_tsm.ssc.filter_sites(sites)
    dc_power_tsm.site_numbers = sites
    return dc_power_tsm


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: SemiconductorModuleContext):
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
