import pytest
import nidcpower
import nidevtools.dcpower as ni_dt_dc_power
# import os.path
# import os

OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4162"}}

@pytest.fixture
def tsm_context_nidcpower(standalone_tsm_context):
    ni_dt_dc_power.initialize_sessions(standalone_tsm_context)
    yield standalone_tsm_context
    ni_dt_dc_power.close_sessions(standalone_tsm_context)

@pytest.fixture
def tsm_ssc_nidcpower_pins(tsm_context_nidcpower, pins):
    # ni_dt_dc_power.initialize_sessions(
    #    standalone_tsm_context, options=OPTIONS
    # )
    # ni_dt_tsm=ni_dt_dc_power.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"], site_numbers=[],
    #                                       fill_pin_site_info=True)
    # yield ni_dt_tsm
    # ni_dt_dc_power.close_sessions(standalone_tsm_context)
    return tsm_context_nidcpower


@pytest.mark.pin_map("nidcpower.pinmap")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:

    def test_initialize_session(self, tsm_context_nidcpower):
        queried_sessions = list(tsm_context_nidcpower.get_all_nidcpower_sessions())
        for session in queried_sessions:
            assert isinstance(session, nidcpower.Session)
        assert len(queried_sessions) == len(tsm_context_nidcpower.get_all_nidcpower_resource_strings())

    @pytest.mark.skip
    def test_pin_to_sessions(self, tsm_context_nidcpower):
        for session in tsm_context_nidcpower:
            assert isinstance(session, nidcpower.Session)

    @pytest.mark.skip
    def test_initiate(self, tsm_ssc_nidcpower_pins):
        tsm_ssc_nidcpower_pins.initiate()

    @pytest.mark.skip
    def test_commit(self, tsm_ssc_nidcpower_pins):
        tsm_ssc_nidcpower_pins.commit()

    @pytest.mark.skip
    def test_reset(self, tsm_ssc_nidcpower_pins):
        tsm_ssc_nidcpower_pins.reset()

    @pytest.mark.skip
    def test_abort(self, tsm_ssc_nidcpower_pins):
        tsm_ssc_nidcpower_pins.abort()

    @pytest.mark.skip
    def test_query_in_compliance(self, tsm_ssc_nidcpower_pins):
        tsm_ssc_nidcpower_pins.query_in_compliance()




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
