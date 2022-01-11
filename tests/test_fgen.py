import time

import pytest
import os.path
import nifgen
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
import nidevtools.fgen as ni_dt_fgen

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["Rainbow.pinmap", "MonoLithic.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
OPTIONS = {}
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "5451", "BoardType": "PXIe"}}

@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_dt_fgen.initialize_sessions(standalone_tsm, options=OPTIONS)
    yield standalone_tsm
    ni_dt_fgen.close_sessions(standalone_tsm)


@pytest.fixture
def fgen_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    fgen_tsms = []
    for test_pin in tests_pins:
        fgen_tsms.append(ni_dt_fgen.pins_to_sessions(tsm_context, test_pin, sites=[]))
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

    def test_pin_to_sessions(self, fgen_tsm_s, tests_pins):
        """TSM SSC fgen Pins to Sessions"""
        # print("\nTest_pin_s\n", test_pin_s)
        for fgen_tsm in fgen_tsm_s:
            # print("\nTest_fgen_tsm\n", fgen_tsm)
            assert isinstance(fgen_tsm, ni_dt_fgen.TSMFGen)

    def test_generate_sine_wave(self, fgen_tsm_s):
        """Generate the sin wave on the hardware"""
        for fgen_tsm in fgen_tsm_s:
            fgen_tsm.ssc.generate_sine_wave()
            # fgen_tsm.ssc.generate_sine_wave(10e6, enable_filter=False)
            # fgen_tsm.ssc.generate_sine_wave(10e6, 1, 0, 5, 1, 100e6, enable_filter=True)
        time.sleep(10.0)


