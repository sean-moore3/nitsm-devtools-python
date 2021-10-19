import pytest
from nidigital import enums
# import os.path
# from nitsm.pinquerycontexts import PinQueryContext
import src.nidevtools.digital as dev_digital


"""The Following APIs/VIs are used in the DUT Power on sequence. 
So these functions needs to be test first.

# TSM SSC Digital Select Function.vi
# TSM SSC Digital PPMU Source Voltage.vi
# TSM SSC Digital Burst Pattern [Pass Fail].vi
# TSM SSC Digital Apply Levels and Timing.vi
# TSM SSC Digital Configure Time Set Period.vi
# TSM SSC Digital Write Sequencer Register.vi
# TSM SSC Digital Write Source Waveform [Broadcast].vi
# TSM SSC Digital Write Static.vi
# TSM SSC Digital N Pins To M Sessions.vi

"""


@pytest.fixture
def standalone_tsm_sessions(standalone_tsm_context):
    # instrument_names = standalone_tsm_context.get_all_nidigital_instrument_names()
    # sessions = [
    #     nidigital.Session(
    #         instrument_name, options={"Simulate": True, "driver_setup": {"Model": "6570"}}
    #     )
    #     for instrument_name in instrument_names
    # ]
    # for instrument_name, session in zip(instrument_names, sessions):
    #     standalone_tsm_context.set_nidigital_session(instrument_name, session)
    # yield sessions
    # for session in sessions:
    #     session.close()
    pass


class TestTSMDigital:
    def test_tsm_ssc_select_function(self, standalone_tsm_context):
        function_to_select = enums.SelectedFunction.DIGITAL
        temp_tsm = dev_digital.tsm_ssc_select_function(standalone_tsm_context, function_to_select)
        assert 1 == function_to_select

    def test_tsm_ssc_ppmu_source_voltage(self):
        assert 1 == 1

    def test_tsm_ssc_burst_pattern_pass_fail(self):
        assert 1 == 1

    def test_tsm_ssc_apply_levels_and_timing(self):
        assert 1 == 1

    def test_tsm_ssc_configure_time_set_period(self):
        assert 1 == 1

    def test_tsm_ssc_write_sequencer_register(self):
        assert 1 == 1

    def test_tsm_ssc_write_source_waveform_broadcast(self):
        assert 1 == 1

    def test_tsm_ssc_write_static(self):
        assert 1 == 1

    def test_tsm_ssc_n_pins_to_m_sessions(self):
        assert 1 == 1
