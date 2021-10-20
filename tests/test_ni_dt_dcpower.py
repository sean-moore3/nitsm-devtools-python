import pytest
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

OPTIONS = "Simulate = True, DriverSetup = Model : 4162"


@pytest.fixture
def nidcpower_tsm(standalone_tsm_context):
    ni_dt_dcpower.initialize_sessions(
        standalone_tsm_context, options={"Simulate": True, "DriverSetup": {"Model": "4162"}}
    )
    yield ni_dt_dcpower.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"])
    ni_dt_dcpower.close_sessions(standalone_tsm_context)


@pytest.mark.pin_map("nidcpower.pinmap")
class TestDCPower:

    def test_open_sessions(self, standalone_tsm_context):
        queried_sessions = ni_dt_dcpower.initialize_sessions(standalone_tsm_context)
        assert isinstance(queried_sessions, nidcpower.Session)

    def test_dummy(self, nidcpower_tsm):
        pass

    def test_abort(self, nidcpower_tsm):
        nidcpower_tsm.abort()

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

    def test_query_in_compliance(self, nidcpower_tsm):
        nidcpower_tsm.query_in_compliance()
