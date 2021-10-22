import pytest
import nidcpower
import nidevtools.dcpower as ni_dt_dc_power
# import os.path
# import os

OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4162"}}


@pytest.fixture
def tsm_context(standalone_tsm_context):
    """This TSM context is simulated one ref the conftest.py for the standalone_tsm_context fixture"""
    ni_dt_dc_power.initialize_sessions(standalone_tsm_context)
    yield standalone_tsm_context
    ni_dt_dc_power.close_sessions(standalone_tsm_context)


@pytest.fixture
def dcpower_tsm(tsm_context, pins):
    # ni_dt_dc_power.initialize_sessions(
    #    standalone_tsm_context, options=OPTIONS
    # )
    # ni_dt_tsm=ni_dt_dc_power.pins_to_sessions(standalone_tsm_context, ["DUTPin1", "DUTPin2"], site_numbers=[],
    #                                       fill_pin_site_info=True)
    # yield ni_dt_tsm
    # ni_dt_dc_power.close_sessions(standalone_tsm_context)
    return tsm_context


@pytest.fixture
def dcpower_ssc(dcpower_tsm):
    return dcpower_tsm


@pytest.mark.pin_map("nidcpower.pinmap")
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDCPower:
    """
    The Following APIs/VIs are used in the DUT Power on sequence.
    So these functions needs to be test first.
    """

    def test_initialize_session(self, tsm_context):
        """ This Api is used in the Init routine"""
        queried_sessions = list(tsm_context.get_all_nidcpower_sessions())
        for session in queried_sessions:
            assert isinstance(session, nidcpower.Session)
        assert len(queried_sessions) == len(tsm_context.get_all_nidcpower_resource_strings())

    @pytest.mark.skip
    def test_pin_to_sessions(self, dcpower_tsm):
        """ TSM SSC DCPower Pins to Sessions.vi """
        for session in dcpower_tsm:
            assert isinstance(session, nidcpower.Session)

    @pytest.mark.skip
    def test_get_max_current(self, dcpower_tsm):
        """TSM DC Power Get Max Current.vi"""
        dcpower_tsm.get_max_current()

    @pytest.mark.skip
    def test_configure_settings(self, dcpower_tsm):
        """  TSM SSC DCPower Configure Settings.vim"""
        dcpower_tsm.configure_settings()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        """# TSM SSC DCPower Measure.vi"""
        dcpower_tsm.abort()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        """# TSM SSC DCPower Source Current.vim"""
        dcpower_tsm.abort()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        """# TSM SSC DCPower Source Voltage.vim"""
        dcpower_tsm.abort()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        """# SSC DCPower Reset Channels.vi"""
        dcpower_tsm.abort()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        """# SSC DCPower Source Current.vim"""
        dcpower_tsm.abort()

    @pytest.mark.skip
    def test_query_in_compliance(self, dcpower_tsm):
        dcpower_tsm.query_in_compliance()

    @pytest.mark.skip
    def test_initiate(self, dcpower_tsm):
        dcpower_tsm.initiate()

    @pytest.mark.skip
    def test_commit(self, dcpower_tsm):
        dcpower_tsm.commit()

    @pytest.mark.skip
    def test_reset(self, dcpower_tsm):
        dcpower_tsm.reset()

    @pytest.mark.skip
    def test_abort(self, dcpower_tsm):
        dcpower_tsm.abort()


# pin_map_instruments = ["DCPower1", "DCPower2"]
# pin_map_dut_pins = ["DUTPin1", "DUTPin2"]
# pin_map_system_pins = ["SystemPin1"]
# pin_map_file_path = "C://G//nitsm-devtools-python//tests//supporting_materials//nidcpower.pinmap"
# pin_map_file_path = os.path.join(os.path.dirname(__file__), "nidcpower.pinmap")
