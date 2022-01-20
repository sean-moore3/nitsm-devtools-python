import nitsm
import typing
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.abstract_switch as ni_abstract

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["AbstInst.pinmap", "Rainbow.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]
message = "With" + pin_file_name + "Pinmap"
print(message)
OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6368"}}


@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_abstract.initialize_tsm_context(standalone_tsm)
    yield standalone_tsm
    ni_abstract.disconnect_all(standalone_tsm)


@pytest.fixture
def abstract_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    print(tests_pins)
    abstract_tsm = []
    sessions = []
    for test_pin_group in tests_pins:
        print(test_pin_group)
        data = ni_abstract.pins_to_session_sessions_info(tsm_context, test_pin_group)
        abstract_tsm.append(data)
        sessions += data
    print(sessions)
    yield tsm_context, abstract_tsm


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestAbstract:
    def test_x(self, tsm_context):
        pass
