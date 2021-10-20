import pytest
# import os
import os.path
import nidcpower
import nidevtools.ni_dt_dcpower as ni_dt_dcpower

"""The Following APIs/VIs are used in the DUT Power on sequence. 
So these functions needs to be test first.

# TSM SSC DCPower Abort.vi
# TSM SSC DCPower Initiate.vi
# SSC DCPower Reset Channels.vi
# SSC DCPower Source Current.vim
# TSM SSC DCPower Get Max Current.vi
# TSM SSC DCPower Configure Settings.vim
# TSM SSC DCPower Measure.vi
# TSM SSC DCPower Source Current.vim
# TSM SSC DCPower Source Voltage.vim
# TSM SSC DCPower Pins to Sessions.vi

"""

OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4162"}}


@pytest.fixture
def simulated_tsm_nidcpower_sessions(standalone_tsm_context):
    # ni_dt_dcpower.initialize_sessions(
    #    standalone_tsm_context, options={"Simulate": True, "DriverSetup": {"Model": "4162"}}
    # )
    # yield ni_dt_dcpower.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"])
    # ni_dt_dcpower.close_sessions(standalone_tsm_context)
    resource_strings = standalone_tsm_context.get_all_nidcpower_resource_strings()
    sessions = [
        nidcpower.Session(resource_string, options=OPTIONS)
        for resource_string in resource_strings
    ]
    for resource_string, session in zip(resource_strings, sessions):
        standalone_tsm_context.set_nidcpower_session(resource_string, session)
    yield sessions
    for session in sessions:
        session.close()


@pytest.mark.pin_map("nidcpower.pinmap")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:
    pin_map_instruments = ["DCPower1", "DCPower2"]
    pin_map_dut_pins = ["DUTPin1", "DUTPin2"]
    pin_map_system_pins = ["SystemPin1"]
    # pin_map_file_path = "C://G//nitsm-devtools-python//tests//supporting_materials//nidcpower.pinmap"
    pin_map_file_path = os.path.join(os.path.dirname(__file__), "nidcpower.pinmap")

    def test_open_sessions(self, standalone_tsm_context):
        queried_sessions = ni_dt_dcpower.initialize_sessions(standalone_tsm_context)
        assert isinstance(queried_sessions, nidcpower.Session)

    def test_dummy(self, simulated_tsm_nidcpower_sessions):
        pass

    def test_abort(self, simulated_tsm_nidcpower_sessions):
        simulated_tsm_nidcpower_sessions.abort()

    #
    # def test_commit(tsm):
    #     tsm.commit()
    #
    #
    # def test_initiate(tsm):
    #     tsm.initiate()
    #
    #
    # def test_reset(tsm):
    #     tsm.reset()

    def test_query_in_compliance(self, simulated_tsm_nidcpower_sessions):
        simulated_tsm_nidcpower_sessions.query_in_compliance()
