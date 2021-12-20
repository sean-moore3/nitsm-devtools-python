import pytest
import os.path
import nifgen
from nitsm.codemoduleapi import SemiconductorModuleContext
import nidevtools.fgen as ni_dt_fgen

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))

pin_file_names = ["7DUT.pinmap", "fgen.pinmap"]
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
        options = {"Simulate": True, "DriverSetup": {"Model": "5442", "BoardType": "PXIe"}}
    else:
        options = {}  # empty options to run on real hardware.

    ni_dt_fgen.initialize_sessions(standalone_tsm_context, options=options)
    yield standalone_tsm_context
    ni_dt_fgen.close_sessions(standalone_tsm_context)


@pytest.fixture
def fgen_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data"""
    fgen_tsms = []
    for test_pin in test_pin_s:
        fgen_tsms.append(ni_dt_fgen.pins_to_sessions(tsm_context, test_pin, fill_pin_site_info=True))
    return fgen_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestFGen:
    """
    The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_initialize_session(self, tsm_context):
        """This Api is used in the Init routine"""
        queried_sessions = tsm_context.get_all_nifgen_sessions()
        assert isinstance(queried_sessions, tuple)
        for session in queried_sessions:
            # print("\nTest_session\n", session)
            assert isinstance(session, nifgen.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_nifgen_instrument_names())

    def test_pin_to_sessions(self, fgen_tsm_s, test_pin_s):
        """TSM SSC fgen Pins to Sessions"""
        # print("\nTest_pin_s\n", test_pin_s)
        for fgen_tsm in fgen_tsm_s:
            # print("\nTest_fgen_tsm\n", fgen_tsm)
            assert isinstance(fgen_tsm, ni_dt_fgen.TSMFGen)

    def test_generate_sine_wave(self, fgen_tsm_s):
        """Test initiate commit and abort"""
        for fgen_tsm in fgen_tsm_s:
            fgen_tsm.generate_sine_wave(7.8125e-3, 1, 0, 5, 1, 6)
