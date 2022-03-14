import niswitch
import pytest
import os
import nidevtools.switch as ni_switch
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["Switch.pinmap", "Rainbow.pinmap"]
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
    ni_switch.initialize_sessions(standalone_tsm)
    yield standalone_tsm
    ni_switch.close_sessions(standalone_tsm)


@pytest.fixture
def switch_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    switch_tsm = []
    sessions = []
    for test_pin in tests_pins:
        data = ni_switch.pin_to_sessions_session_info(tsm_context, test_pin)
        switch_tsm.append(data)
        sessions.append(data)
    yield tsm_context, switch_tsm


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestSwitch:
    def test_initialize_and_close(self, tsm_context):
        session_data, channel_group_ids, channel_lists = tsm_context.get_all_custom_sessions(
            ni_switch.instrument_type_id
        )
        assert len(session_data) == len(channel_group_ids) == len(channel_lists)
        instrument_names = ni_switch.get_all_instruments_names(tsm_context)[0]
        # assert len(session_data) == len(instrument_names) # disabled by anish
        for name in instrument_names:
            assert isinstance(name, str)
        sessions = ni_switch.get_all_sessions(tsm_context)
        assert len(session_data) == len(sessions)
        for session in sessions:
            assert isinstance(session, niswitch.session.Session)

    def test_name_to_topology(self):
        assert ni_switch.name_to_topology("Matrix_2738_3") == "2738/2-Wire 8x32 Matrix"
        assert ni_switch.name_to_topology("Mux_2525_test") == "2525/2-Wire Octal 8x1 Mux"
        assert ni_switch.name_to_topology("Matrix_2503_TEST") == "2503/2-Wire 4x6 Matrix"
        assert ni_switch.name_to_topology("Other") == "Configured Topology"
        assert ni_switch.name_to_topology("TEST_Matrix_2738") == "Configured Topology"

    def test_pin_to_session(self, switch_tsm_s):
        pass  # TODO review info
        # Add Forloop once solver pin2 issue
        # switch_tsm_s[1][0].action_session_info(action=ni_switch.Action.Disconnect_All)
        # switch_tsm_s[1][0].action_session_info(action=ni_switch.Action.Connect, route_value='1')
        # switch_tsm_s[1][0].action_session_info(action=ni_switch.Action.Disconnect)
        # switch_tsm_s[1][0].action_session_info(action=ni_switch.Action.Read, route_value='1')
