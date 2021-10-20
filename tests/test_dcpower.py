import pytest
import nidcpower
import nidevtools.ni_dt_dcpower as ni_dt_dcpower


@pytest.fixture
def nidcpower_tsm(standalone_tsm_context):
    ni_dt_dcpower.initialize_sessions(
        standalone_tsm_context, options={"Simulate": True, "DriverSetup": {"Model": "4162"}}
    )
    yield ni_dt_dcpower.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"])
    ni_dt_dcpower.close_sessions(standalone_tsm_context)


@pytest.mark.pin_map("nidcpower.pinmap")
class TestDCPower:
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
