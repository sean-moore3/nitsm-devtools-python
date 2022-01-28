import nifpga
import nitsm
import typing
import nidaqmx
import nidaqmx.constants as constant
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as TSM_Context
import nidevtools.fpga as ni_fpga

# To run the code on simulated hardware create a dummy file named "Simulate.driver" to flag SIMULATE boolean.
SIMULATE = os.path.exists(os.path.join(os.path.dirname(__file__), "Simulate.driver"))

pin_file_names = ["FPGA.pinmap", "Rainbow.pinmap"]
# Change index below to change the pin map to use
pin_file_name = pin_file_names[0]

OPTIONS = {}  # empty options to run on real hardware.
if SIMULATE:
    OPTIONS = {"Simulate": True, "DriverSetup": {"Model": "6368"}}

# Types Definition
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


@pytest.fixture
def tsm_context(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm_context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    ni_fpga.initialize_sessions(standalone_tsm)
    yield standalone_tsm
    ni_fpga.close_session(standalone_tsm)


@pytest.fixture
def fpga_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    print(tests_pins)
    fpga_tsms = []
    sessions = []
    for test_pin_group in tests_pins:
        print(test_pin_group)
        data = ni_fpga.pins_to_sessions(tsm_context, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
    print(sessions)
    yield tsm_context, fpga_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestFPGA:
    def test_initialize_sessions(self, tsm_context):
        print(tsm_context.pin_map_file_path)
        queried_sessions = tsm_context.get_all_custom_sessions("782xFPGA")
        assert isinstance(queried_sessions[0], tuple)  # Type verification
        for session in queried_sessions[0]:
            print("\nTest_Init/Clear_Sessions\n", session)
            assert isinstance(session, nifpga.session.Session)  # Type verification
            assert len(queried_sessions[0]) != 0  # not void
            assert len(queried_sessions[0]) == 1  # Matching quantity

    def test_pin_to_sessions(self, fpga_tsm_s):
        tsm_context = fpga_tsm_s[0]
        list_fpga_tsm = fpga_tsm_s[1]
        print(list_fpga_tsm)
        for fpga_tsm in list_fpga_tsm:
            print("\nTest_pin_to_sessions\n", fpga_tsm)
            print(fpga_tsm.SSC)
            assert isinstance(fpga_tsm, ni_fpga.TSMFPGA)
            assert isinstance(fpga_tsm.pin_query_context, ni_fpga.PinQuery)
            print(type(fpga_tsm.SSC))
            assert isinstance(fpga_tsm.SSC, typing.List)
            assert len(fpga_tsm.SSC) == len(tsm_context.site_numbers)

    def test_parse_header(self):
        for data in range(254):
            print('Test Address/Read/Valid')
            for addr in range(256):
                result = ni_fpga.parse_header(ni_fpga.I2CHeaderWord(addr, True, False), addr, True)
                assert(result[0].Address == ((addr << 8) | addr))
                assert (result[0].Read == True)
                assert (result[0].Valid != ((addr & 248) == 240))
                result = ni_fpga.parse_header(ni_fpga.I2CHeaderWord(addr, False, False), addr, False)
                assert (result[0].Address == (addr >> 1))
                assert (result[0].Read == bool(addr % 2))
                assert (result[0].Valid == True)
            print('Value test completed: Pass')
