import nitsm
import typing
import nidaqmx
import nidaqmx.constants as constant
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.daqmx as ni_daqmx

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE_HARDWARE boolean.
SIMULATE_HARDWARE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["7DUT.pinmap", "daqmx.pinmap"]
# Change index below to change the pinmap to use
pin_file_name = pin_file_names[1]
message = "With DAQmx Pinmap"
if SIMULATE_HARDWARE:
    pin_file_name = pin_file_names[0]
    message = "With 7DUT Pinmap"
print(message)

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

    ni_daqmx.set_task(standalone_tsm_context)
    yield standalone_tsm_context
    ni_daqmx.clear_task(standalone_tsm_context)


@pytest.fixture
def daqmx_tsm_s(tsm_context, test_pin_s):
    """Returns LabVIEW Cluster equivalent data"""
    print(test_pin_s)
    daqmx_tsms = []
    pins = []
    for test_pin in test_pin_s:
        pins += test_pin
    print(pins)
    data = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    daqmx_tsms.append(data)
    yield tsm_context, daqmx_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDaqmx:
    def test_set_task(self, tsm_context):
        print(tsm_context.pin_map_file_path)
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
        print(list_daqmx_tsm)
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest_pin_to_sessions\n", daqmx_tsm)
            print(daqmx_tsm.sessions)
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
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.start_task()
            daqmx_tsm.stop_task()
        print("\nTest Stop All\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.stop_task()
        print("\nTest Timing Configuration\n")
        samp_cha = 500
        samp_rate = 500
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.timing(samp_cha, samp_rate)
        print("\nTest Trigger Configuration\n")
        # for daqmx_tsm in list_daqmx_tsm:
        #     daqmx_tsm.reference_analog_edge("PXI_Trig0") #TODO find Analog Trigger Source
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.reference_digital_edge("PXI_Trig0", constant.Slope.FALLING, 10)
            print("TestTest")
        print("\nTest Configure Read Channels\n")
        for daqmx_tsm in list_daqmx_tsm:
            daqmx_tsm.configure_channels()
        print("\nTest Read\n")
        for daqmx_tsm in list_daqmx_tsm:
            print("\nTest Read Single Channel\n")
            daqmx_tsm.start_task()
            daqmx_tsm.read_waveform()
            daqmx_tsm.stop_task()
            print("\nTest Read Multiple Channels\n")
            daqmx_tsm.start_task()
            daqmx_tsm.read_waveform_multichannel()
            daqmx_tsm.stop_task()
        print("\nVerify Properties\n")
        for daqmx_tsm in list_daqmx_tsm:
            data = daqmx_tsm.get_task_properties()
            assert isinstance(data, typing.List)
            for task_property in data:
                assert isinstance(task_property, ni_daqmx.TaskProperties)
                assert task_property.SamplingRate == samp_rate


@nitsm.codemoduleapi.code_module
def open_sessions(tsm_context: TSM_Context):
    ni_daqmx.set_task(tsm_context)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: TSM_Context):
    ni_daqmx.clear_task(tsm_context)


@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm_context: TSM_Context,
    pins: typing.List[str],
):
    return ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)


@nitsm.codemoduleapi.code_module
def configure(
    tsm_context: TSM_Context,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    # Timing Configuration
    tsm_multi_session.timing(500, 500)
    # Trigger Configuration
    # tsm_multi_session.reference_analog_edge() TODO Solve trigger issue
    tsm_multi_session.reference_digital_edge("PXI_Trig0", constant.Slope.FALLING, 10)
    # Configure Read Channels
    tsm_multi_session.configure_channels()
    # Get Properties
    data = tsm_multi_session.get_task_properties()
    return data


@nitsm.codemoduleapi.code_module
def acquisition_single_ch(
    tsm_context: TSM_Context,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    tsm_multi_session.start_task()
    yield tsm_multi_session.read_waveform()
    tsm_multi_session.stop_task()


@nitsm.codemoduleapi.code_module
def acquisition_multi_ch(
    tsm_context: TSM_Context,
    pins: typing.List[str],
):
    tsm_multi_session: ni_daqmx.MultipleSessions
    tsm_multi_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, pins)
    tsm_multi_session.start_task()
    yield tsm_multi_session.read_waveform_multichannel()
    tsm_multi_session.stop_task()


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm_context: TSM_Context):
    print("opening sessions")
    ni_daqmx.set_task(tsm_context)
    tsmdaqmx = ni_daqmx.pins_to_session_sessions_info(tsm_context, ["SGL1", "SGL2"])


@nitsm.codemoduleapi.code_module
def close_sessions(tsm_context: TSM_Context):
    print(" Closing sessions")
    tsmdaqmx = ni_daqmx.pins_to_session_sessions_info(tsm_context, ["SGL1", "SGL2"])
    ni_daqmx.clear_task(tsm_context)


@nitsm.codemoduleapi.code_module
def baku_scenario(tsm_context: TSM_Context):
    #ni_daqmx.set_task(tsm_context)
    daq_pins1 = [
        "ACTIVE_READY_DAQ",
        "BUTTON1_DAQ",
        "BUTTON2_DAQ",
        "GPIO17_DAQ",
        "GPIO18_DAQ",
        "GPIO20_DAQ",
        "GPIO21_DAQ",
        "GPIO22_DAQ",
        "GPIO23_DAQ",
        "GPIO24_DAQ",
        "GPIO25_DAQ",
        "RESET_L_DAQ",
        "SHDN_DAQ",
        "SYS_ALIVE_DAQ"]
    daq_pins2 = [
        "GPIO6_DAQ",
        "GPIO7_DAQ",
        "GPIO8_DAQ",
        "GPIO9_DAQ",
        "GPIO10_DAQ",
        "GPIO11_DAQ",
        "GPIO12_DAQ",
        "GPIO13_DAQ",
        "GPIO14_DAQ",
        "GPIO15_DAQ",
        "GPIO16_DAQ",
        "GPIO19_DAQ",
        "OUT32K_DAQ",
        "SLEEP_32K_DAQ"]
    daq_sessions_1 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins1)
    daq_sessions_2 = ni_daqmx.pins_to_session_sessions_info(tsm_context, daq_pins2)
    daq_sessions_all = ni_daqmx.MultipleSessions(sessions=daq_sessions_1.sessions + daq_sessions_2.sessions)
    daq_sessions_all.stop_task()
    daq_sessions_all.timing()
    daq_sessions_all.reference_digital_edge("PXI_Trig0", constant.Slope.FALLING, 10)
    daq_sessions_all.start_task()
    daq_sessions_all.read_waveform_multichannel()
    daq_sessions_all.stop_task()


