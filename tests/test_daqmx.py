import typing
import nidaqmx
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.daqmx as ni_daqmx

# To run the code on real hardware create a dummy file named "Hardware.exists" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = not os.path.exists(os.path.join(os.path.dirname(__file__), "Hardware.exists"))
# SIMULATE_HARDWARE = True

pin_file_names = ["7DUT.pinmap", "daqmx.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
message = "With DAQmx Pinmap"
if SIMULATE_HARDWARE:
    pin_file_name = pin_file_names[0]
    message = "With 7DUT Pinmap"
print( message)

OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6224"}}


@pytest.fixture
def tsm_context(standalone_tsm_context: TSM_Context):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE_HARDWARE)
    if SIMULATE_HARDWARE:
        options = OPTIONS
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
        data = ni_daqmx.pins_to_session_sessions_info(tsm_context, test_pin)
        daqmx_tsms.append(data)
    yield tsm_context, daqmx_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDaqmx:
    def test_set_task(self, tsm_context):
        queried_tasks = tsm_context.get_all_nidaqmx_tasks("AI")
        assert isinstance(queried_tasks, tuple)  # Type verification
        for task in queried_tasks:
            print("\nTest_set/clear_task\n", task)
            assert isinstance(task, nidaqmx.Task)  # Type verification
            assert len(queried_tasks) != 0  # not void
            assert len(queried_tasks) >= 1  # Matching quantity

    def test_pin_to_sessions_info(self, daqmx_tsm_s):
        """TSM SSC DCPower Pins to Sessions.vi"""
        # print("\nTest_pin_s\n", test_pin_s)
        tsm_context = daqmx_tsm_s[0]
        list_daqmx_tsm = daqmx_tsm_s[1]
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest_pin_to_sessions\n", daqmx_tsm)
            assert isinstance(daqmx_tsm, ni_daqmx.MultipleSessions)
            assert isinstance(daqmx_tsm.pin_query_contex, ni_daqmx.PinQueryContext)
            assert isinstance(daqmx_tsm.sessions, typing.List)
            assert len(daqmx_tsm.sessions) == len(tsm_context.site_numbers)

    def test_get_all_instrument_names(self, tsm_context):
        data = ni_daqmx.get_all_instrument_names(tsm_context)
        print("\nInstrument Names: \n", data)
        assert type(data) == tuple
        for element in data:
            assert type(element) == tuple
            assert len(element) != 0

    def test_get_all_sessions(self, tsm_context):
        data = ni_daqmx.get_all_sessions(tsm_context)
        print("\nSessions: \n", data)
        assert type(data) == tuple
        assert len(data) != 0
        for element in data:
            assert isinstance(element, nidaqmx.Task)

    def test_properties(self, daqmx_tsm_s):
        list_daqmx_tsm = daqmx_tsm_s[1]
        print("\nTest Start All\n")
        # for daqmx_tsm in list_daqmx_tsm: TODO Check why it is having conflicts with the names (Maybe the task that start in fixture causes some issues)
        #     daqmx_tsm.start_task()
        print("\nTest Stop All\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.stop_task()
        print("\nTest Timing Configuration\n")
        samp_cha = 500
        samp_rate = 500
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.timing(samp_cha, samp_rate)
        print("\nTest Trigger Configuration\n")
        # for daqmx_tsm in list_daqmx_tsm: #TODO similar conflict with names
        #     daqmx_tsm.reference_analog_edge("/PXI1Slot3/ai/StartTrigger")
        print("\nTest Configure Read Channels\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.configure_channels()
        print("\nTest Read\n")
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest Read Single Channel\n")
            daqmx_tsm.read_waveform()
            print("\nTest Read Multiple Channels\n")
            daqmx_tsm.read_waveform_multichannel()
        print("\nVerify Properties\n")
        for daqmx_tsm in list_daqmx_tsm:
            data = daqmx_tsm.get_task_properties()
            assert isinstance(data, typing.List)
            for task_property in data:
                assert isinstance(task_property, ni_daqmx.TaskProperties)
                assert task_property.SamplingRate == samp_rate
