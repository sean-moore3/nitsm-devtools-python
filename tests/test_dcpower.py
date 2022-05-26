import nitsm.codemoduleapi
import pytest
import os.path
import nidcpower
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nidevtools.dcpower as dcpower
import time
import os
import ctypes

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["YinYang.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]
OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4162"}}


@pytest.fixture
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    dcpower.initialize_sessions(standalone_tsm, options=OPTIONS)
    yield standalone_tsm
    dcpower.close_sessions(standalone_tsm)


@pytest.fixture
def dcpower_tsm_s(tsm, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    dcpower_tsms = []
    for test_pin in tests_pins:
        dcpower_tsms.append(dcpower.pins_to_sessions(tsm, test_pin, fill_pin_site_info=True))
    return dcpower_tsms


@pytest.fixture
def dcpower_ssc_s(dcpower_tsm_s):
    """Returns LabVIEW Array equivalent data"""
    # func needs to be defined.
    dcpower_ssc = []
    for dcpower_tsm in dcpower_tsm_s:
        dcpower_ssc.extend(dcpower_tsm.ssc)
    return dcpower_ssc


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:
    """
    The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_initialize_session(self, tsm):
        """This Api is used in the Init routine"""
        queried_sessions = tsm.get_all_nidcpower_sessions()
        assert isinstance(queried_sessions, tuple)
        for session in queried_sessions:
            # print("\nTest_session\n", session)
            assert isinstance(session, nidcpower.Session)
        assert len(queried_sessions) == len(tsm.get_all_nidcpower_resource_strings())

    def test_pin_to_sessions(self, dcpower_tsm_s, tests_pins):
        """TSM SSC DCPower Pins to Sessions vi"""
        # print("\nTest_pin_s\n", test_pin_s)
        for dcpower_tsm in dcpower_tsm_s:
            # print("\nTest_dcpower_tsm\n", dcpower_tsm)
            assert isinstance(dcpower_tsm, dcpower.TSMDCPower)

    def test_get_max_current(self, dcpower_tsm_s):
        """TSM DC Power Get Max Current.vi"""
        expected_currents = [3.0, 0.1, 0.1, 0.1, 0.1]
        if SIMULATE:
            expected_currents = [0.1, 0.1, 0.1, 0.1, 0.1]
        index = 0
        for dcpower_tsm in dcpower_tsm_s:
            max_current = dcpower_tsm.ssc.get_max_current()
            print("\nmax_current\n", max_current)
            assert max_current == expected_currents[index]
            index += 1

    # model = dcpower_tsm_s.get_smu_model() #not sure what object to call to get this property
    # if model == 4110 or model == 4112:
    #     current_ranges = [1]
    # elif model == 4113:
    #     current_ranges = [6]
    # elif model == 4132:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    # elif model == 4135:
    #     current_ranges = [10e-9, 1e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
    # elif model == 4136 or model == 4137:
    #     current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1]
    # elif model == 4138 or model == 4139:
    #     current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 1, 3]
    # elif model == 4140 or model == 4141:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    # elif model == 4142 or model == 4143:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.15]
    # elif model == 4144 or model == 4145:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1, 0.5]
    # elif model == 4147:
    #     current_ranges = [1e-6, 10e-6, 100e-6, 1e-3, 10e-3, 0.1, 3]
    # elif model == 4162:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.1]
    # elif model == 4163:
    #     current_ranges = [10e-6, 100e-6, 1e-3, 10e-3, 0.05]
    # max_current = max(current_ranges)
    # assert dcpower_tsm_s.get_max_current() == max_current

    def test_reset(self, dcpower_tsm_s):
        """# SSC DCPower Reset Channels.vi"""
        # the below code needs refactoring after changes from driver.
        print("\ndcpower_tsm_s\n", dcpower_tsm_s)
        custom_settings = {
            "aperture_time": 20e-03,
            "source_delay": 1.0,
            "sense": nidcpower.Sense.LOCAL,
        }
        for dcpower_tsm in dcpower_tsm_s:
            # print("\n dcpower_tsm\n", dcpower_tsm)
            # default_settings = dcpower_tsm.ssc.get_measurement_settings()
            # dcpower_tsm.ssc.configure_settings(custom_settings)
            # # assert custom_settings != default_settings
            dcpower_tsm.ssc.reset()  # resetting for all pins in all sites

    def test_initiate_commit_abort(self, dcpower_tsm_s):
        """Test initiate commit and abort"""
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.initiate()
            dcpower_tsm.ssc.commit()
            dcpower_tsm.ssc.abort()

    def test_source_voltage(self, dcpower_tsm_s):
        """
        # TSM SSC DCPower Source Voltage vim
        Force_voltage_symmetric_limits is the python function name
        """
        voltage_set_point = 1.0  # we measured current consumed for this voltage.
        for dcpower_tsm in dcpower_tsm_s:
            # Where is the function to source voltage? is it force voltage?
            # Yes, this is the standard name for it.
            dcpower_tsm.ssc.force_voltage_symmetric_limits(voltage_set_point, 1.0, 0.1, 0.1)
            compliance = dcpower_tsm.ssc.query_in_compliance()
            print("compliance\n", compliance)
            voltages, currents = dcpower_tsm.ssc.measure()
            print("voltages\n", voltages)
            print("currents\n", currents)
            dcpower_tsm.ssc.abort()
            for voltage in voltages:
                assert voltage_set_point - 0.1 <= voltage <= voltage_set_point + 0.1

    def test_source_current(self, dcpower_tsm_s):
        """
        # TSM SSC DCPower Source Current vim
        # SSC DCPower Source Current vim
        """
        current_set_point = 0.1e-03  # This value is measured for a know voltage
        for dcpower_tsm in dcpower_tsm_s:
            # # Do not call configure meas since the default is auto
            # dcpower_tsm.ssc.configure_settings(aperture_time=20e-03)
            # Where is the function to source current? is it force current?
            # Yes, this is the standard name for it.
            dcpower_tsm.ssc.force_current_symmetric_limits(current_set_point, 0.1e-03, 3.0, 5.0)
            compliance = dcpower_tsm.ssc.query_in_compliance()
            print("compliance\n", compliance)
            voltages, currents = dcpower_tsm.ssc.measure()
            print("voltages\n", voltages)
            dcpower_tsm.ssc.abort()
            for current in currents:
                print(current_set_point, current)
                # assert current_set_point - 0.1e-04 <= current <= current_set_point + 0.1e-04

    def test_queries_status(self, dcpower_tsm_s):
        voltage_set_point = 1.0  # we measured current consumed for this voltage.
        i = 0
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.configure_output_connected(output_connected=True)
            dcpower_tsm.ssc.force_voltage_symmetric_limits(voltage_set_point, 1.0, 0.1, 0.1)

            compliance = dcpower_tsm.ssc.query_in_compliance()
            print("compliance\n", compliance)

            power_line_frequencies = dcpower_tsm.ssc.get_power_line_frequencies()
            print("power_line_frequencies\n", power_line_frequencies)

            output_state = dcpower_tsm.ssc.query_output_state(nidcpower.OutputStates.VOLTAGE)
            print("output_state\n", output_state)

            aperture_times_in_seconds = dcpower_tsm.ssc.get_aperture_times_in_seconds()
            print("aperture_times_in_seconds\n", aperture_times_in_seconds)

            voltages, currents = dcpower_tsm.ssc.measure()
            print("voltages\n", voltages)
            print("currents\n", currents)
            dcpower_tsm.ssc.abort()
            dcpower_tsm.ssc.reset()
            print("Iteration number", i)
            dcpower_tsm.ssc.configure_output_connected(output_connected=True)
            # dcpower_tsm.ssc.configure_output_enabled_and_connected(output_enabled_and_connected=False)
            i += 1

    def test_get_properties(self, dcpower_tsm_s):
        voltage_set_point = 1.0  # we measured current consumed for this voltage.
        i = 0
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.configure_output_connected(output_connected=True)
            dcpower_tsm.ssc.force_voltage_symmetric_limits(voltage_set_point, 1.0, 0.1, 0.1)
            aperture_times_in_seconds = dcpower_tsm.ssc.get_aperture_times_in_seconds()
            print("aperture_times_in_seconds\n", aperture_times_in_seconds)
            dcpower_tsm.ssc.abort()
            dcpower_tsm.ssc.reset()
            print("Iteration number", i)
            dcpower_tsm.ssc.configure_output_connected(output_connected=True)
            # dcpower_tsm.ssc.configure_output_enabled_and_connected(output_enabled_and_connected=False)
            all_props = dcpower_tsm.ssc.get_properties()
            print(all_props)
            i += 1

    def test_configure_settings(self, dcpower_tsm_s):
        """
        TSM SSC DCPower Configure Settings vim
        dcpower_tsm.query_in_compliance()
        """
        # custom_settings = {"aperture_time": 20e-03, "source_delay": 1.0, "sense": Sense.LOCAL}
        for dcpower_tsm in dcpower_tsm_s:
            # dcpower_tsm.ssc.configure_settings(aperture_time=40e-03)
            dcpower_tsm.ssc.force_voltage_symmetric_limits(1.0, 1.0, 0.1, 0.1)
            time.sleep(1)
            voltages, currents = dcpower_tsm.ssc.measure()
            print(voltages, currents)
            dcpower_tsm.ssc.abort()
        # dcpower_tsm_s.configure_settings(custom_settings)
        # default_settings = dcpower_tsm_s.get_measurement_settings()
        # assert custom_settings == default_settings


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm: SMContext):
    # ctypes.windll.user32.MessageBoxW(None, "Process ID:" + str(os.getpid()), "Attach debugger", 0)
    dcpower.initialize_sessions(tsm, options=OPTIONS)
    dcpower_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2", "SMU_VI_ANA1"])
    dcpower_tsm[1].reset()
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def configure_measurements(tsm: SMContext):
    # ctypes.windll.user32.MessageBoxW(None, "Process ID: " + str(os.getpid()),"Attach debugger", 0)
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2"])
    dc_tsm.ssc.abort()
    dc_tsm.ssc.configure_aperture_time_with_abort_and_initiate()

    # dc_tsm.ssc.configure_settings(20e-3, 0.0, ni_dt_dcpower.enums.Sense.LOCAL)
    # ap_time = dc_tsm.ssc.get_aperture_times_in_seconds()
    # output_state = dc_tsm.ssc.query_output_state
    # max_curr = dc_tsm.ssc.get_max_current
    # print(ap_time)
    # print(output_state)
    # print(max_curr)


@nitsm.codemoduleapi.code_module
def configure_measurements_waveform(tsm: SMContext):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2", "SMU_VI_ANA1"])
    dc_tsm.ssc.abort()
    dc_tsm.ssc.configure_settings(20e-3, 0.0, dcpower.enums.Sense.LOCAL)
    dc_tsm.ssc.configure_and_start_waveform_acquisition(sample_rate=10e3, buffer_length=1.0)
    wf_settings = dc_tsm.ssc.get_measurement_settings()
    dc_tsm.ssc.configure_output_connected(output_connected=True)
    return wf_settings


@nitsm.codemoduleapi.code_module
def fetch_waveform(tsm: SMContext):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2", "SMU_VI_ANA1"])
    volt_wf, curr_wf = dc_tsm.ssc.fetch_waveform(0, waveform_length_s=1e-3)
    print(volt_wf, curr_wf)
    return volt_wf


@nitsm.codemoduleapi.code_module
def source_current(tsm: SMContext):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2"])
    dc_tsm.ssc.force_current_symmetric_limits(
        current_level=10e-3, current_level_range=10e-3, voltage_limit=6, voltage_limit_range=6
    )
    time.sleep(0.5)


@nitsm.codemoduleapi.code_module
def source_voltage(tsm: SMContext):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2"])
    dc_tsm.ssc.force_voltage_symmetric_limits(
        voltage_level=3.8, voltage_level_range=6.0, current_limit=10e-3, current_limit_range=100e-3
    )
    time.sleep(0.5)

    # output_terminal_name =dc_tsm.ssc.cs_session.exported_source_trigger_output_terminal # something like this "/Dev1/PXI_Trig0" will be returned
    # session2 = dc_tsm.ssc.cs_session
    # session2.source_trigger_type = nidcpower.Enum.TriggerType.DIGITAL_EDGE
    # session2.digital_edge_source_trigger_input_terminal = output_terminal_name
    # dc_tsm.ssc.cs_send_software_edge_trigger()


@nitsm.codemoduleapi.code_module
def measure(tsm: SMContext):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2"])
    volt_meas, curr_meas = dc_tsm.ssc.measure()
    compliance = dc_tsm.ssc.query_in_compliance()
    print(compliance)
    time.sleep(0.5)
    return volt_meas, curr_meas


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext, settings):
    dc_tsm = dcpower.pins_to_sessions(tsm, ["SMU_VI_ANA2", "SMU_VI_ANA1"])
    dc_tsm.ssc.abort()
    dc_tsm.ssc.configure_output_connected(output_connected=True)
    # dc_tsm.ssc.set_measurement_settings(settings)
    dcpower.close_sessions(tsm)
