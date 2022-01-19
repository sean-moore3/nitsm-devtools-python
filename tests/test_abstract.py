import nitsm
import typing
import nidaqmx
import nidaqmx.constants as constant
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.daqmx as ni_daqmx

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["Abstract.pinmap", "Rainbow.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]
message = "With" + pin_file_name + "Pinmap"
print(message)
OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6368"}}

# Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_daqmx.set_task(standalone_tsm)
    yield standalone_tsm
    ni_daqmx.clear_task(standalone_tsm)


@pytest.fixture
def daqmx_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    print(tests_pins)
    daqmx_tsms = []
    sessions = []
    for test_pin_group in tests_pins:
        print(test_pin_group)
        data = ni_daqmx.pins_to_session_sessions_info(tsm_context, test_pin_group)
        daqmx_tsms.append(data)
        sessions += data.sessions
    print(sessions)
    yield tsm_context, daqmx_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDaqmx:
    def test_x(self):
        pass
