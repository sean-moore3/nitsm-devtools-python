import nifpga
import nitsm
import typing
import pytest
import os
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
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
def tsm(standalone_tsm):
    """
    This TSM context is on simulated hardware or on real hardware based on OPTIONS defined below.
    This TSM context uses standalone_tsm context fixture created by the conftest.py
    """
    print("\nSimulated driver?", SIMULATE)
    print("LLL", ni_fpga.initialize_sessions(standalone_tsm))
    yield standalone_tsm
    ni_fpga.close_sessions(standalone_tsm)


@pytest.fixture
def fpga_tsm_s(tsm, tests_pins):
    """Returns LabVIEW Cluster equivalent data"""
    fpga_tsms = []
    sessions = []
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
        print(len(sessions))
    yield tsm, fpga_tsms


@pytest.mark.pin_map(pin_file_name)
@pytest.mark.filterwarnings("ignore::DeprecationWarning")
class TestFPGA:
    def test_initialize_sessions(self, tsm):
        print(tsm.pin_map_file_path)
        queried_sessions = tsm.get_all_custom_sessions("782xFPGA")
        assert isinstance(queried_sessions[0], tuple)  # Type verification
        for session in queried_sessions[0]:
            print("\nTest_Init/Clear_Sessions\n", session)
            assert isinstance(session, nifpga.session.Session)  # Type verification
            assert len(queried_sessions[0]) != 0  # not void
            assert len(queried_sessions[0]) == 2  # Matching quantity

    def test_pin_to_sessions(self, fpga_tsm_s):
        list_fpga_tsm = fpga_tsm_s[1]
        for fpga_tsm in list_fpga_tsm:
            print("\nTest_pin_to_sessions\n", fpga_tsm)
            assert isinstance(fpga_tsm, ni_fpga.TSMFPGA)
            assert isinstance(fpga_tsm.pin_query_context, ni_fpga.PinQuery)
            assert isinstance(fpga_tsm.SSC, typing.List)

    def test_get_i2c_master_session(self, tsm):
        print(
            ni_fpga.get_i2c_master_session(tsm, ni_fpga.I2CMaster.I2C_3V3_7822_LINT, True)
        )

    def test_update_line_on_connectors(self):
        for i in range(8):
            dioline = ni_fpga.DIOLines(i)
            state = ni_fpga.StaticStates(1)
            result = ni_fpga.update_line_on_connector(0, 0, dioline, state)
            assert result[1] == 2**i

    def test_wr(self, fpga_tsm_s):
        fpga_session7821 = fpga_tsm_s[1][0].SSC[1]
        fpga_session7820 = fpga_tsm_s[1][0].SSC[0]
        for i in range(4):
            con_enable = fpga_session7820.Session.registers["Connector%d Output Enable" % i]
            con_data = fpga_session7820.Session.registers["Connector%d Output Data" % i]
            con_enable.write(0)
            con_data.write(0)
            print("READ_CON", con_enable.read(), con_data.read())
            print("READ", fpga_session7821.Session.registers["Connector%d Read Data" % i].read())

    def test_wr_and_rd(self, fpga_tsm_s):
        fpga_session7821 = fpga_tsm_s[1][0].SSC[1]
        fpga_session7820 = fpga_tsm_s[1][0].SSC[0]
        print("Start", fpga_session7821.read_all_lines())
        for i in range(8):
            fpga_session7820.write_single_dio_line(
                ni_fpga.Connectors.Connector0, ni_fpga.DIOLines(i), ni_fpga.StaticStates.Zero
            )
        print("Mid", fpga_session7821.read_all_lines())
        fpga_session7820.write_single_dio_line(
            ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.One
        )
        print("End", fpga_session7821.read_all_lines())
        assert fpga_session7821.read_all_lines().Connector0 == 128
        fpga_session7820.write_single_dio_line(
            ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.Zero
        )
        assert fpga_session7821.read_all_lines().Connector0 == 0
        wr1 = ni_fpga.DIOLineLocationAndStaticState(
            ni_fpga.DIOLines(7), ni_fpga.Connectors(0), ni_fpga.StaticStates(0)
        )
        wr2 = ni_fpga.DIOLineLocationAndStaticState(
            ni_fpga.DIOLines(6), ni_fpga.Connectors(0), ni_fpga.StaticStates(1)
        )
        fpga_session7820.write_multiple_dio_lines([wr2, wr1])
        assert (
            fpga_session7821.read_single_dio_line(
                ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO6
            )
            == "1"
        )
        assert (
            fpga_session7821.read_single_dio_line(
                ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7
            )
            == "0"
        )
        assert fpga_session7821.read_single_connector(ni_fpga.Connectors(0)) == 64
        data = fpga_session7821.read_multiple_lines(
            [
                ni_fpga.LineLocation(ni_fpga.DIOLines(7), ni_fpga.Connectors(0)),
                ni_fpga.LineLocation(ni_fpga.DIOLines(6), ni_fpga.Connectors(0)),
            ]
        )
        assert data[0].state == "0"
        assert data[1].state == "1"
        data = fpga_session7821.read_multiple_dio_commanded_states(
            [
                ni_fpga.LineLocation(ni_fpga.DIOLines(7), ni_fpga.Connectors(0)),
                ni_fpga.LineLocation(ni_fpga.DIOLines(6), ni_fpga.Connectors(0)),
            ]
        )
        assert data[0].channel == ni_fpga.DIOLines.DIO7
        assert data[1].channel == ni_fpga.DIOLines.DIO6
        assert data[0].connector == data[0].connector

    def test_rd_wr_static(self, fpga_tsm_s):
        fpga_tsm_s[1][0].write_static(
            [ni_fpga.StaticStates.Zero] * 128
        )  # TODO Check why Loosing LSB
        list_s = fpga_tsm_s[1][0].read_static()
        for data in list_s[0][0]:
            assert data.state == "0"
        fpga_tsm_s[1][0].write_static([ni_fpga.StaticStates.One] * 128)
        list_s = fpga_tsm_s[1][0].read_static()
        for data in list_s[0][0]:
            print(data.state)
        fpga_tsm_s[1][0].write_static([ni_fpga.StaticStates.Zero] * 128)
        list_s = fpga_tsm_s[1][0].read_static()
        for data in list_s[0][0]:
            assert data.state == "0"

    def test_rd_commanded(self, fpga_tsm_s):
        print(fpga_tsm_s[1][0].read_commanded_line_states())


@nitsm.codemoduleapi.code_module
def ts_open_sessions(tsm: SMContext):
    ni_fpga.initialize_sessions(tsm)


@nitsm.codemoduleapi.code_module
def ts_close_sessions(tsm: SMContext):
    ni_fpga.close_sessions(tsm)


@nitsm.codemoduleapi.code_module
def ts_initialize_sessions(tsm):
    print(tsm.pin_map_file_path)
    queried_sessions = tsm.get_all_custom_sessions("782xFPGA")
    assert isinstance(queried_sessions[0], tuple)  # Type verification
    for session in queried_sessions[0]:
        print("\nTest_Init/Clear_Sessions\n", session)
        assert isinstance(session, nifpga.session.Session)  # Type verification
        assert len(queried_sessions[0]) != 0  # not void
        assert len(queried_sessions[0]) == 2  # Matching quantity


@nitsm.codemoduleapi.code_module
def ts_get_i2c_master_session(tsm):
    print(ni_fpga.get_i2c_master_session(tsm, ni_fpga.I2CMaster.I2C_3V3_7822_LINT, True))


@nitsm.codemoduleapi.code_module
def ts_wr(tsm):
    fpga_tsms = []
    sessions = []
    tests_pins = [["RIO_Pins"]]
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
    fpga_session7821 = fpga_tsms[0].SSC[1]
    fpga_session7820 = fpga_tsms[0].SSC[0]
    for i in range(4):
        con_enable = fpga_session7820.Session.registers["Connector%d Output Enable" % i]
        con_data = fpga_session7820.Session.registers["Connector%d Output Data" % i]
        con_enable.write(0)
        con_data.write(0)
        print("READ_CON", con_enable.read(), con_data.read())
        print("READ", fpga_session7821.Session.registers["Connector%d Read Data" % i].read())


@nitsm.codemoduleapi.code_module
def ts_wr_and_rd(tsm):
    fpga_tsms = []
    sessions = []
    tests_pins = [["RIO_Pins"]]
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
    fpga_session7821 = fpga_tsms[0].SSC[1]
    fpga_session7820 = fpga_tsms[0].SSC[0]
    print("Start", fpga_session7821.read_all_lines())
    for i in range(8):
        fpga_session7820.write_single_dio_line(
            ni_fpga.Connectors.Connector0, ni_fpga.DIOLines(i), ni_fpga.StaticStates.Zero
        )
    print("Mid", fpga_session7821.read_all_lines())
    fpga_session7820.write_single_dio_line(
        ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.One
    )
    print("End", fpga_session7821.read_all_lines())
    # assert(fpga_session7821.read_all_lines().Connector0 == 128)
    fpga_session7820.write_single_dio_line(
        ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7, ni_fpga.StaticStates.Zero
    )
    # assert (fpga_session7821.read_all_lines().Connector0 == 0)
    wr1 = ni_fpga.DIOLineLocationAndStaticState(
        ni_fpga.DIOLines(7), ni_fpga.Connectors(0), ni_fpga.StaticStates(0)
    )
    wr2 = ni_fpga.DIOLineLocationAndStaticState(
        ni_fpga.DIOLines(6), ni_fpga.Connectors(0), ni_fpga.StaticStates(1)
    )
    fpga_session7820.write_multiple_dio_lines([wr2, wr1])
    assert (
        fpga_session7821.read_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO6)
        == "1"
    )
    assert (
        fpga_session7821.read_single_dio_line(ni_fpga.Connectors.Connector0, ni_fpga.DIOLines.DIO7)
        == "0"
    )
    assert fpga_session7821.read_single_connector(ni_fpga.Connectors(0)) == 64
    data = fpga_session7821.read_multiple_lines(
        [
            ni_fpga.LineLocation(ni_fpga.DIOLines(7), ni_fpga.Connectors(0)),
            ni_fpga.LineLocation(ni_fpga.DIOLines(6), ni_fpga.Connectors(0)),
        ]
    )
    assert data[0].state == "0"
    assert data[1].state == "1"
    data = fpga_session7821.read_multiple_dio_commanded_states(
        [
            ni_fpga.LineLocation(ni_fpga.DIOLines(7), ni_fpga.Connectors(0)),
            ni_fpga.LineLocation(ni_fpga.DIOLines(6), ni_fpga.Connectors(0)),
        ]
    )
    assert data[0].channel == ni_fpga.DIOLines.DIO7
    assert data[1].channel == ni_fpga.DIOLines.DIO6
    assert data[0].connector == data[0].connector


@nitsm.codemoduleapi.code_module
def ts_rd_wr_static(tsm):
    fpga_tsms = []
    sessions = []
    tests_pins = [["RIO_Pins"]]
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
    fpga_tsms[0].write_static([ni_fpga.StaticStates.Zero] * 128)
    list_s = fpga_tsms[0].read_static()
    for data in list_s[0][0]:
        assert data.state == "0"
    fpga_tsms[0].write_static([ni_fpga.StaticStates.One] * 128)
    list_s = fpga_tsms[0].read_static()
    for data in list_s[0][0]:
        print(data.state)
    fpga_tsms[0].write_static([ni_fpga.StaticStates.Zero] * 128)
    list_s = fpga_tsms[0].read_static()
    for data in list_s[0][0]:
        assert data.state == "0"


@nitsm.codemoduleapi.code_module
def ts_rd_commanded(tsm):
    fpga_tsms = []
    sessions = []
    tests_pins = [["RIO_Pins"]]
    for test_pin_group in tests_pins:
        data = ni_fpga.pins_to_sessions(tsm, test_pin_group)
        fpga_tsms.append(data)
        sessions += data.SSC
    print(fpga_tsms[0].read_commanded_line_states())
