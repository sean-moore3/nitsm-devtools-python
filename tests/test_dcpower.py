import pytest
import nidcpower
import dcpower


@pytest.fixture
def nidcpower_tsm(standalone_tsm_context):
    nidevtools.dcpower.initialize_sessions(
        standalone_tsm_context, options={"Simulate": True, "DriverSetup": {"Model": "4162"}}
    )
    yield nidevtools.dcpower.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"])
    nidevtools.dcpower.close_sessions(standalone_tsm_context)


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

    def test_query_in_compliance(tsm):
        tsm.query_in_compliance()
