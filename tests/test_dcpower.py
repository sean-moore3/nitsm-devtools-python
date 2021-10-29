import pytest
import nidcpower
import nidevtools.dcpower as ni_dt_dc_power
from nitsm.codemoduleapi import SemiconductorModuleContext
import os.path

# import os

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))

pin_file_names = ["I2C.pinmap", "I2C_Logic_SingleSite.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
if SIMULATE_HARDWARE:
    pin_file_name = pin_file_names[0]


@pytest.fixture
def tsm_context(standalone_tsm_context: SemiconductorModuleContext):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        options = {"Simulate": True, "DriverSetup": {"Model": "4162"}}
    else:
        options = {}  # empty options to run on real hardware.

    ni_dt_dc_power.initialize_sessions(standalone_tsm_context, options=options)
    yield standalone_tsm_context
    ni_dt_dc_power.close_sessions(standalone_tsm_context)


@pytest.fixture
def dcpower_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data"""
    dcpower_tsms = []
    for test_pin in test_pin_s:
        dcpower_tsms.append(
            ni_dt_dc_power.pins_to_sessions(tsm_context, test_pin, fill_pin_site_info=True)
        )
        # print(dcpower_tsms)
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

    def test_initialize_session(self, tsm_context):
        """This Api is used in the Init routine"""
        queried_sessions = tsm_context.get_all_nidcpower_sessions()
        assert isinstance(queried_sessions, tuple)
        for session in queried_sessions:
            # print("\nTest_session\n", session)
            assert isinstance(session, nidcpower.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_nidcpower_resource_strings())

    def test_pin_to_sessions(self, dcpower_tsm_s, test_pin_s):
        """TSM SSC DCPower Pins to Sessions.vi"""
        # print("\nTest_pin_s\n", test_pin_s)
        for dcpower_tsm in dcpower_tsm_s:
            # print("\nTest_dcpower_tsm\n", dcpower_tsm)
            assert isinstance(dcpower_tsm, ni_dt_dc_power.TSMDCPower)

    def test_get_max_current(self, dcpower_tsm_s):
        """TSM DC Power Get Max Current.vi"""
        expected_currents = [3.0, 0.1, 0.1]
        index = 0
        for dcpower_tsm in dcpower_tsm_s:
            max_currents = dcpower_tsm.ssc.get_max_current()
            print("\nmax_current\n", max_currents)
            assert max(max_currents) == expected_currents[index]
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
        custom_settings = {"aperture_time": 20e-03, "source_delay": 1.0, "sense": nidcpower.Sense.LOCAL}
        for dcpower_tsm in dcpower_tsm_s:
            # print("\ndcpower_tsm\n", dcpower_tsm)
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


    def test_configure_settings(self, dcpower_tsm_s):
        """
        TSM SSC DCPower Configure Settings.vim
        dcpower_tsm.query_in_compliance()
        """
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.configure_settings(aperture_time=40e-03)
            dcpower_tsm.ssc.force_voltage_symmetric_limits(1.0, 1.0, 0.1, 0.1)
            compliance = dcpower_tsm.ssc.query_in_compliance()
            print(compliance)
            voltages, currents = dcpower_tsm.ssc.measure()
            print(voltages, currents)
            dcpower_tsm.ssc.abort()
        # custom_settings = {"aperture_time": 20e-03, "source_delay": 1.0, "sense": Sense.LOCAL}
        # dcpower_tsm_s.configure_settings(custom_settings)
        # default_settings = dcpower_tsm_s.get_measurement_settings()
        # assert custom_settings == default_settings

    def test_tsm_source_voltage(self, dcpower_tsm_s):
        """
        # TSM SSC DCPower Source Voltage.vim
        Force_voltage_symmetric_limits is the python function name
        """
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.force_voltage_symmetric_limits(1.0, 1.0, 0.1, 0.1)
            compliance = dcpower_tsm.ssc.query_in_compliance()
            print(compliance)
            voltages, currents = dcpower_tsm.ssc.measure()
            print(voltages, currents)
            dcpower_tsm.ssc.abort()


    def test_tsm_source_current(self, dcpower_tsm_s):
        """
        # TSM SSC DCPower Source Current.vim
        # SSC DCPower Source Current.vim
        """
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.configure_settings(aperture_time=20e-03)
            dcpower_tsm.ssc.force_current_symmetric_limits(0.1e-03, 0.1e-03, 3.0, 5.0)
            compliance = dcpower_tsm.ssc.query_in_compliance()
            print(compliance)
            voltages, currents = dcpower_tsm.ssc.measure()
            print(voltages, currents)
            dcpower_tsm.ssc.abort()
        # c_Level = 0.5
        # # Do not call configure meas since the default is auto
        # ni_dt_dc_power.tsm_source_current(c_level)  # Where is the function to source? it force voltage?
        # assert dcpower_tsm_s.measure()[1] == c_Level

    @pytest.mark.skip
    def test_measure(self, dcpower_tsm_s):
        """# TSM SSC DCPower Measure.vi"""
        # # Do not call configure meas since the default is auto
        v_Level = 2.0
        for dcpower_tsm in dcpower_tsm_s:
            dcpower_tsm.ssc.source_voltage(v_Level)
            measurements = dcpower_tsm.ssc.measure()[0]
            assert measurements == v_Level

    @pytest.mark.skip
    def test_query_in_compliance(self, dcpower_tsm_s):
        for dcpower_tsm in dcpower_tsm_s:
            print("\ndcpower_tsm\n", dcpower_tsm)
            # dcpower_tsm.ssc.
            dcpower_tsm.query_in_compliance()
