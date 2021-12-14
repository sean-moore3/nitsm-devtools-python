import pytest
import typing
import os
import nidaqmx
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.daqmx as ni_daqmx

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))
SIMULATE_HARDWARE = True

pin_file_names = ["simulated.pinmap", "daqmx.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
if SIMULATE_HARDWARE:
    pin_file_name = pin_file_names[0]


@pytest.fixture
def tsm_context(standalone_tsm_context: TSM_Context):

    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        options = {"Simulate": True, "DriverSetup": {"Model": "6224"}}
    else:
        options = {}  # empty options to run on real hardware.

    ni_daqmx.set_task(standalone_tsm_context, input_voltage_range=1)
    yield standalone_tsm_context
    ni_daqmx.clear_task(standalone_tsm_context)


@pytest.fixture
def daqmx_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data"""
    daqmx_tsms = []
    for test_pin in test_pin_s:
        daqmx_tsms.append(ni_daqmx.pins_to_sessions_sessions(tsm_context, test_pin))
    return daqmx_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:
    def test_set_task(self, tsm_context):
        queried_tasks = tsm_context.get_all_nidaqmx_tasks("ALL")
        assert isinstance(queried_tasks, tuple)  # Type verification
        for task in queried_tasks:
            print("\nTest_session\n", task)
            assert isinstance(task, ni_daqmx.Task)  # Type verification
            assert len(queried_tasks) != 0  # not void
            assert len(queried_tasks) == len(ni_daqmx.get_all_instrument_names(tsm_context)[0])  # Matching quantity




