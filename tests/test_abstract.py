import pytest
import os
import nitsm.codemoduleapi
import nidevtools.abstract_switch as ni_abstract
import nidevtools.daqmx as ni_daqmx
import nidevtools.fpga as ni_fpga

import nidevtools.digital as ni_dt_digital
import nidevtools.switch as ni_switch


# To simulate hardware create a dummy file named "Simulate.driver" in the current folder.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["AbstInst.pinmap", "C:\\Users\\ni\\Desktop\\Baku_uSTS.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]
message = "With" + pin_file_name + "Pinmap"
print(message)
OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6368"}}


@pytest.fixture
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_daqmx.set_task(standalone_tsm)
    ni_fpga.initialize_sessions(standalone_tsm)
    ni_switch.initialize_sessions(standalone_tsm)
#    ni_dt_digital.initialize_sessions(standalone_tsm)
    print("INIT DONE")
    yield standalone_tsm
#    ni_dt_digital.close_sessions(standalone_tsm)
    ni_switch.close_sessions(standalone_tsm)
    ni_fpga.close_sessions(standalone_tsm)
    ni_daqmx.clear_task(standalone_tsm)


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestAbstract:
    def test_initialize_and_close(self, tsm):
        """
        tests init and close feature

        Args:
            tsm (_type_): _description_
        """
        ni_abstract.initialize(tsm)
        assert 4 == len(ni_abstract.get_all_sessions(tsm).enable_pins)
        assert ni_abstract.get_all_instruments_names(tsm)[0] == "Masterconnect"
        ni_abstract.close_sessions(tsm)

    def test_check_debug(self):
        ni_abstract.check_debug_ui_tool("")  # TODO add path

    def test_pins_to_session_sessions_info(self, tsm):
        ni_abstract.initialize(tsm)
        pins = ["EN_FPGA"]
        enabled = ni_abstract.enable_pins_to_sessions(tsm, pins)
        assert enabled.enable_pins[0].enable_pin == pins[0]
        enabled.connect_sessions_info(tsm)
        t = ni_daqmx.get_all_sessions(tsm)[0]
        t.stop()
        enabled.disconnect_sessions_info(tsm)
        # ni_abstract.disconnect_all(tsm)
        abst_session = ni_abstract.pins_to_sessions_sessions_info(tsm, "BuckSGL_1_DUT")
        print(abst_session)
        enabled.read_state(tsm)
        ni_abstract.pins_to_task_and_connect(tsm, ["En_Daq"], ["BuckSGL_3_DUT", "BuckSGL_4_DUT"])
        # ni_abstract.disconnect_all(tsm)
        ni_abstract.disconnect_pin(tsm, "BuckSGL_1_DUT")

    def test_pin_name_to_instrument(self, tsm):
        # ni_abstract.pin_name_to_instrument(pinmap_path='C:\\Users\\ni\\Desktop\\Baku_uSTS.pinmap')
        print(tsm.pin_map_file_path)
        print("INIT")
        ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.init)
        print("GET CONNECTIONS")
        ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.get_connections)
        print("DISCONNECT ALL")
        ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.disconnect_all)


@nitsm.codemoduleapi.code_module
def ts_open_session(tsm):
    ni_daqmx.set_task(tsm)
    ni_fpga.initialize_sessions(tsm)
    # ni_dt_digital.tsm_initialize_sessions(tsm)


@nitsm.codemoduleapi.code_module
def ts_close_session(tsm):
    # ni_dt_digital.tsm_close_sessions(tsm)
    ni_fpga.close_sessions(tsm)
    ni_daqmx.clear_task(tsm)


@nitsm.codemoduleapi.code_module
def ts_initialize_and_close(tsm):
    ni_abstract.initialize(tsm)
    assert 4 == len(ni_abstract.get_all_sessions(tsm).enable_pins)
    assert ni_abstract.get_all_instruments_names(tsm)[0] == "Masterconnect"
    ni_abstract.close_sessions(tsm)


@nitsm.codemoduleapi.code_module
def ts_check_debug():
    ni_abstract.check_debug_ui_tool("")  # TODO add path


@nitsm.codemoduleapi.code_module
def ts_pins_to_session_sessions_info(tsm):
    ni_abstract.initialize(tsm)
    pins = ["En_Daq"]
    enabled = ni_abstract.enable_pins_to_sessions(tsm, pins)
    assert enabled.enable_pins[0].enable_pin == pins[0]
    enabled.connect_sessions_info(tsm)
    t = ni_daqmx.get_all_sessions(tsm)[0]
    t.stop()
    enabled.disconnect_sessions_info(tsm)
    ni_abstract.disconnect_all(tsm)
    abst_session = ni_abstract.pins_to_sessions_sessions_info(tsm, "BuckSGL_1")
    print(abst_session)
    enabled.read_state(tsm)
    ni_abstract.pins_to_task_and_connect(tsm, ["En_Daq"], ["BuckSGL_3", "BuckSGL_4"])
    ni_abstract.disconnect_all(tsm)
    ni_abstract.disconnect_pin(tsm, "BuckSGL_1")


@nitsm.codemoduleapi.code_module
def ts_pin_name_to_instrument(tsm):
    # ni_abstract.pin_name_to_instrument(pinmap_path='C:\\Users\\ni\\Desktop\\Baku_uSTS.pinmap')
    # print(tsm.pin_map_file_path)
    print("INIT")
    ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.init)
    print("GET CONNECTIONS")
    ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.get_connections)
    print("DISCONNECT ALL")
    ni_abstract.pin_fgv(tsm, "", ni_abstract.Control.disconnect_all)
