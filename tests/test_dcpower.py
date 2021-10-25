import pytest
import nidcpower
import nidevtools.dcpower as ni_dt_dc_power
from nitsm.codemoduleapi import SemiconductorModuleContext
import os.path
# import os

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))

pin_file_names = ["I2C.pinmap",  "I2C_Logic.pinmap", "Logic.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[0]


@pytest.fixture
def tsm_context(standalone_tsm_context: SemiconductorModuleContext):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("")
    print("entering tsm_context fixture")
    print("Test is running on Simulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        options = {"Simulate": True, "DriverSetup": {"Model": "4162"}}
    else:
        options = {}  # empty options to run on real hardware.

    ni_dt_dc_power.initialize_sessions(standalone_tsm_context, options=options)
    yield standalone_tsm_context
    ni_dt_dc_power.close_sessions(standalone_tsm_context)
    print("")
    print("exiting tsm_context fixture")


@pytest.fixture
def test_pin_s():
    """Need to improve this logic for supplying test pins
    using @pytest.mark.parametrize"""
    # pin_map_instruments = ["SMU1", "SMU2"]
    test_pins = ["SCL", "SDA"]
    read_pins = ["R_SCL", "R_SDA"]
    all_pins = test_pins+read_pins
    resistor_pin = ["SMD"]
    power_pins = ["VDD", "VDDIO"]
    return [resistor_pin]


@pytest.fixture
def dcpower_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data"""
    dcpower_tsms = []
    for test_pin in test_pin_s:
        dcpower_tsms.append(ni_dt_dc_power.pins_to_sessions(tsm_context, test_pin))
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
        """ This Api is used in the Init routine"""
        queried_sessions = list(tsm_context.get_all_nidcpower_sessions())
        print("")
        print("The number of sessions opened is ", len(queried_sessions))
        for session in queried_sessions:
            print(session)
            assert isinstance(session, nidcpower.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_nidcpower_resource_strings())

    def test_pin_to_sessions(self, dcpower_tsm_s, test_pin_s):
        """ TSM SSC DCPower Pins to Sessions.vi """
        print(test_pin_s)
        for session in dcpower_tsm_s:
            assert isinstance(session, nidcpower.Session)

    def test_get_max_current(self, dcpower_tsm_s):
        """TSM DC Power Get Max Current.vi"""
        assert dcpower_tsm_s.get_max_current()

    def test_configure_settings(self, dcpower_tsm_s):
        """  TSM SSC DCPower Configure Settings.vim"""
        assert dcpower_tsm_s.configure_settings()

    def test_measure(self, dcpower_tsm_s):
        """# TSM SSC DCPower Measure.vi"""
        assert dcpower_tsm_s.measure()

    @pytest.mark.skip
    def test_tsm_source_current(self, dcpower_tsm_s):
        """# TSM SSC DCPower Source Current.vim"""
        dcpower_tsm_s.abort()

    @pytest.mark.skip
    def test_tsm_source_voltage(self, dcpower_tsm_s):
        """# TSM SSC DCPower Source Voltage.vim"""
        dcpower_tsm_s.abort()

    def test_reset(self, dcpower_tsm_s):
        """# SSC DCPower Reset Channels.vi"""
        dcpower_tsm_s.reset()

    @pytest.mark.skip
    def test_ssc_source_current(self, dcpower_tsm_s):
        """# SSC DCPower Source Current.vim"""
        dcpower_tsm_s.abort()

    def test_query_in_compliance(self, dcpower_tsm_s):
        assert dcpower_tsm_s.query_in_compliance()

    def test_initiate(self, dcpower_tsm_s):
        assert dcpower_tsm_s.initiate()

    def test_commit(self, dcpower_tsm_s):
        assert dcpower_tsm_s.commit()

    @pytest.mark.skip
    def test_reset(self, dcpower_tsm_s):
        dcpower_tsm_s.reset()

    def test_abort(self, dcpower_tsm_s):
        dcpower_tsm_s.abort()
