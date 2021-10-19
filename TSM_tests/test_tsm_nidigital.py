import pytest
import src.nidevtools.digital


@pytest.fixture
def test():
    pass


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