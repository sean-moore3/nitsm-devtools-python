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
    ni_fpga.close_sessions(standalone_tsm)


@pytest.fixture
def fpga_tsm_s(tsm_context, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    fpga_tsms = []
    sessions = []
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm_context, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
        print(len(sessions))
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
            assert len(queried_sessions[0]) == 2  # Matching quantity

    def test_pin_to_sessions(self, fpga_tsm_s):
        tsm_context = fpga_tsm_s[0]
        list_fpga_tsm = fpga_tsm_s[1]
        for fpga_tsm in list_fpga_tsm:
            print("\nTest_pin_to_sessions\n", fpga_tsm)
            assert isinstance(fpga_tsm, ni_fpga.TSMFPGA)
            assert isinstance(fpga_tsm.pin_query_context, ni_fpga.PinQuery)
            assert isinstance(fpga_tsm.SSC, typing.List)

    def test_parse_header(self):
        for data in range(254):
            print('Test Address/Read/Valid')
            for addr in range(256):
                result = ni_fpga.parse_header(ni_fpga.I2CHeaderWord(addr, True, False), addr, True)
                assert (result[0].Address == ((addr << 8) | addr))
                assert (result[0].Read is True)
                assert (result[0].Valid is True)
                result = ni_fpga.parse_header(ni_fpga.I2CHeaderWord(addr, False, False), addr, False)
                if (addr & 248) == 240:
                    assert (result[0].Address == ((addr >> 1) & 3))
                else:
                    assert (result[0].Address == (addr >> 1))
                assert (result[0].Read == bool(addr % 2))
                assert (result[0].Valid != result[1])
        print('Value test completed: Pass')

    def test_create_header(self):
        print('Test Create Header')
        result = ni_fpga.create_header(False, 15, False)
        assert (result == (30, 15))
        result = ni_fpga.create_header(False, 25, True)
        assert (result == (51, 25))
        result = ni_fpga.create_header(True, 35, False)
        assert (result == (240, 35))
        result = ni_fpga.create_header(True, 45, True)
        assert (result == (241, 45))

    def test_get_i2c_master_session(self, tsm_context):
        print(ni_fpga.get_i2c_master_session(tsm_context, ni_fpga.I2CMaster.I2C_3V3_7822_LINT, True))

    def test_write_and_read(self, tsm_context):
        data = ni_fpga.get_i2c_master_session(tsm_context, ni_fpga.I2CMaster.I2C_3V3_7822_LINT, True)
        print('Read: ', data.read_i2c_data(number_of_bytes=8, slave_address=23, timeout=100))
        array = [1, 0, 1, 0, 1, 0, 1, 0]
        data.write_i2c_data(data_to_write=array, slave_address=23, timeout=100)
        print('Read: ', data.read_i2c_data(number_of_bytes=8, slave_address=23, timeout=100))

    def test_update_line_on_connectors(self):
        for i in range(8):
            dioline = ni_fpga.DIOLines(i)
            state = ni_fpga.StaticStates(1)
            result = ni_fpga.update_line_on_connector(0,0,dioline,state)
            assert(result[1] == 2**i)

    def test_wr_and_rd(self, fpga_tsm_s):
        fpga_session7821 = fpga_tsm_s[1][0].SSC[0]
        fpga_session7820 = fpga_tsm_s[1][0].SSC[1]
        for i in range(8):
            fpga_session7820.write_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines(i),
                                                   ni_fpga.StaticStates.Zero)
        fpga_session7820.write_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.One)
        assert(fpga_session7821.read_all_lines().Connector0==128)
        fpga_session7820.write_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.Zero)
        assert (fpga_session7821.read_all_lines().Connector0 == 0)
        wr1 = ni_fpga.DIOLineLocationandStaticState(ni_fpga.DIOLines(7),ni_fpga.Connectors(0),ni_fpga.StaticStates(0))
        wr2 = ni_fpga.DIOLineLocationandStaticState(ni_fpga.DIOLines(6), ni_fpga.Connectors(0), ni_fpga.StaticStates(1))
        fpga_session7820.write_multiple_dio_lines([wr2,wr1])
        assert (fpga_session7821.read_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO6) == '1')
        assert (fpga_session7821.read_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7) == '0')
        assert(fpga_session7821.read_single_connector(ni_fpga.Connectors(0))==64)
        data = fpga_session7821.read_multiple_lines([ni_fpga.LineLocation(ni_fpga.DIOLines(7),ni_fpga.Connectors(0)),
                                                     ni_fpga.LineLocation(ni_fpga.DIOLines(6),ni_fpga.Connectors(0))])
        assert(data[0].state == '0')
        assert (data[1].state == '1')
        data = fpga_session7821.read_multiple_dio_commanded_states(
            [ni_fpga.LineLocation(ni_fpga.DIOLines(7),ni_fpga.Connectors(0)),
            ni_fpga.LineLocation(ni_fpga.DIOLines(6),ni_fpga.Connectors(0))]
        )
        assert(data[0].channel==ni_fpga.DIOLines.DIO7)
        assert (data[1].channel == ni_fpga.DIOLines.DIO6)
        assert (data[0].connector == data[0].connector)

    def test_rd_wr_static(self, fpga_tsm_s):
        fpga_tsm_s[1][0].write_static([ni_fpga.StaticStates.One]*128) #TODO Check why Loosing LSB
        print(fpga_tsm_s[1][0].read_static())
        #fpga_tsm_s[1][0].write_static([ni_fpga.StaticStates.One] * 128)
        #print(fpga_tsm_s[1][0].read_static())
        #fpga_tsm_s[1][0].write_static([ni_fpga.StaticStates.Zero] * 128)


