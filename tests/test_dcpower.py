import pytest
import nidcpower
import nidevtools.dcpower as ni_dt_dc_power
# import os.path
# import os

OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4162"}}


@pytest.fixture
def nidcpower_tsm(standalone_tsm_context):
    ni_dt_dc_power.initialize_sessions(
       standalone_tsm_context, options=OPTIONS
    )
    yield ni_dt_dc_power.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"])
    ni_dt_dc_power.close_sessions(standalone_tsm_context)


@pytest.fixture
def simulated_tsm_nidcpower_sessions(standalone_tsm_context):
    instrument_names = standalone_tsm_context.get_all_nidcpower_instrument_names()
    sessions = [
        nidcpower.Session(instrument_name, options=OPTIONS)
        for instrument_name in instrument_names
    ]
    for instrument_name, session in zip(instrument_names, sessions):
        standalone_tsm_context.set_nidcpower_session(instrument_name, session)
    yield sessions
    for session in sessions:
        session.close()


@pytest.mark.pin_map("nidcpower.pinmap")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:

    def test_initiate(self, tsm):
        tsm.initiate()

    def test_commit(self, tsm):
        tsm.commit()

    def test_reset(self, tsm):
        tsm.reset()

    def test_abort(self, nidcpower_tsm):
        nidcpower_tsm.abort()

    def test_query_in_compliance(self, nidcpower_tsm):
        nidcpower_tsm.query_in_compliance()

    def test_dummy(self):
        pass

    def test_open_sessions(self, standalone_tsm_context):
        queried_sessions = ni_dt_dc_power.initialize_sessions(standalone_tsm_context)
        assert isinstance(queried_sessions, nidcpower.Session)


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
# pin_map_instruments = ["DCPower1", "DCPower2"]
# pin_map_dut_pins = ["DUTPin1", "DUTPin2"]
# pin_map_system_pins = ["SystemPin1"]
# pin_map_file_path = "C://G//nitsm-devtools-python//tests//supporting_materials//nidcpower.pinmap"
# pin_map_file_path = os.path.join(os.path.dirname(__file__), "nidcpower.pinmap")
