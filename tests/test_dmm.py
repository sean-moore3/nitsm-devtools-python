import os
import typing

import nidmm
import nidevtools.dmm as ni_dmm
import nitsm
import pytest
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["DMM.pinmap", "Rainbow.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]

OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "4081"}}

# Types Definition
PinQuery = nitsm.pinquerycontexts.PinQueryContext
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any


@pytest.fixture
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_dmm.initialize_session(standalone_tsm)
    yield standalone_tsm
    ni_dmm.close_session(standalone_tsm)


@pytest.fixture
def dmm_tsm_s(tsm, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    print(tests_pins)
    dmm_tsms = []
    sessions = []
    for test_pin in tests_pins:
        data = ni_dmm.pins_to_sessions(tsm, test_pin)
        dmm_tsms.append(data)
        sessions += data.sessions
    print(sessions)
    test = (tsm, dmm_tsms)
    yield test


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestDMM:
    def test_set_session(self, tsm):
        print(tsm. pin_map_file_path)
        queried_sessions = tsm.get_all_nidmm_sessions()
        assert isinstance(queried_sessions, tuple)  # Type verification
        for session in queried_sessions:
            print("\nTest_set/clear_task\n", session)
            assert isinstance(session, nidmm.Session)  # Type verification
            assert len(queried_sessions) != 0  # not void
            assert len(queried_sessions) == 1  # Matching quantity

    def test_pin_to_sessions_info(self, dmm_tsm_s):
        tsm = dmm_tsm_s[0]
        list_dmm_tsm = dmm_tsm_s[1]
        print(list_dmm_tsm)
        for dmm_tsm in list_dmm_tsm:
            print("\nTest_pin_to_sessions\n", dmm_tsm)
            print(dmm_tsm.sessions)
            assert isinstance(dmm_tsm, ni_dmm.TSMDMM)
            assert isinstance(dmm_tsm.pin_query_context, ni_dmm.PinQuery)
            assert isinstance(dmm_tsm.sessions, typing.Sequence)
            assert len(dmm_tsm.sessions) == len(tsm.site_numbers)

    def test_configure(self, dmm_tsm_s):
        tsm = dmm_tsm_s[0]
        list_dmm_tsm = dmm_tsm_s[1]
        print(list_dmm_tsm)
        for dmm_tsm in list_dmm_tsm:
            print("\nTest_pin_to_sessions\n", dmm_tsm)
            print(dmm_tsm.sessions)
            dmm_tsm.configure_measurement(function=nidmm.Function.DC_VOLTS,
                                          range_raw=10,
                                          resolution_in_digits=ni_dmm.Resolution.Res_5_05,
                                          input_resistance=ni_dmm.InputResistance.IR_1_MOhm)
            dmm_tsm.configure_aperture_time(aperture_time=1,
                                            units=nidmm.ApertureTimeUnits.SECONDS)
            try:
                dmm_tsm.initiate()
                data = dmm_tsm.measure()
                print("Data", data)
            except Exception as e:
                print(e)
            finally:
                dmm_tsm.abort()

@nitsm.codemoduleapi.code_module
def open_sessions(tsm: SMContext):
    ni_dmm.initialize_session(tsm)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    ni_dmm.close_session(tsm)

@nitsm.codemoduleapi.code_module
def pins_to_sessions(
    tsm: SMContext,
    pins: typing.List[str] = ["CH0"],
):
    return ni_dmm.pins_to_sessions(tsm, pins)

@nitsm.codemoduleapi.code_module
def configure(tsm: SMContext, pins: typing.List[str]):
    tsm_sessions = ni_dmm.pins_to_sessions(tsm, pins)
    for dmm_tsm in tsm_sessions:
        dmm_tsm.configure_measurement(function=nidmm.Function.DC_VOLTS,
                                      range_raw=10,
                                      resolution_in_digits=ni_dmm.Resolution.Res_5_05,
                                      input_resistance=ni_dmm.InputResistance.IR_1_MOhm)
        dmm_tsm.configure_aperture_time(aperture_time=1,
                                        units=nidmm.ApertureTimeUnits.SECONDS)
        try:
            dmm_tsm.initiate()
            data = dmm_tsm.measure()
            print("Data", data)
        except Exception as e:
            print(e)
        finally:
            dmm_tsm.abort()