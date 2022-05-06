"""
This is nifpga wrapper for use with STS test codes
"""
import collections
import os
import shutil
import typing
from enum import Enum
from time import time
import nifpga
import nitsm.pinquerycontexts
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nidevtools.common as ni_dt_common

# Types Definition

PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]
InstrumentTypeId = "782xFPGA"
CurrentPath = os.getcwd()
PinQuery = nitsm.pinquerycontexts.PinQueryContext


class ReadData(typing.NamedTuple):  # AllConnector Data
    """
    Class that describes list of connectors of FPGA to support read functions
    """

    Connector0: int
    Connector1: int
    Connector2: int
    Connector3: int


class I2CMaster(Enum):
    """
    Class that describes supported types of FPGAs
    """

    I2C_3V3_7822_SINK = 0
    I2C_3V3_7822_LINT = 1
    DIB_I2C = 2
    I2C_3V3_7822_TLOAD = 3


class BoardType(Enum):
    """
    Class that describes supported hardware
    """

    PXIe_7822R = 0
    PXIe_7821R = 1
    PXIe_7820R = 2


class DIOLines(Enum):
    """
    Class that describes DIO pins from connectors
    """

    DIO0 = 0
    DIO1 = 1
    DIO2 = 2
    DIO3 = 3
    DIO4 = 4
    DIO5 = 5
    DIO6 = 6
    DIO7 = 7
    DIO8 = 8
    DIO9 = 9
    DIO10 = 10
    DIO11 = 11
    DIO12 = 12
    DIO13 = 13
    DIO14 = 14
    DIO15 = 15
    DIO16 = 16
    DIO17 = 17
    DIO18 = 18
    DIO19 = 19
    DIO20 = 20
    DIO21 = 21
    DIO22 = 22
    DIO23 = 23
    DIO24 = 24
    DIO25 = 25
    DIO26 = 26
    DIO27 = 27
    DIO28 = 28
    DIO29 = 29
    DIO30 = 30
    DIO31 = 31
    DIO_None = 32


class Connectors(Enum):
    """
    Class that describes FPGA connectors
    """

    Connector0 = 0
    Connector1 = 1
    Connector2 = 2
    Connector3 = 3
    Con_None = 4


class StaticStates(Enum):
    """
    Class that describes bits status that supports the reading functions
    """

    Zero = 0
    One = 1
    X = 2


class States(Enum):  # DIO Line State with I2C
    """
    Class that describes bits status that supports the reading and writing functions
    """

    Zero = 0
    One = 1
    X = 2
    I2C = 3


class LineLocation(typing.NamedTuple):  # Channel
    """
    Class that contains channel and connector data to support write and read functions
    """

    channel: DIOLines
    connector: Connectors


class DIOLineLocationAndStaticState(typing.NamedTuple):  # Channel
    """
    Class that contains channel, connector and state data to support write and read functions
    """

    channel: DIOLines
    connector: Connectors
    state: StaticStates


class LineLocationAndStates(typing.NamedTuple):  # Channel
    """
    Class that contains channel, connector and states data to support write and read functions
    """

    channel: DIOLines
    connector: Connectors
    state: States


class DIOLineLocationAndReadState(typing.NamedTuple):  # Channel
    """
    Class that contains channel, connector and state data to support write and read functions
    """

    channel: DIOLines
    connector: Connectors
    state: bool


class I2CMasterLineConfiguration(typing.NamedTuple):  # I2C Channel Mapping
    """
    Class that contains SDA and SCL data to support write and read functions
    """

    SDA: LineLocation
    SCL: LineLocation


class _SSCFPGA(typing.NamedTuple):
    """
    Private class that contains data of the individual session, including Session, Channel Group
    ID, Channels, Channel List
    """

    Session: nifpga.Session
    ChannelGroupID: str
    Channels: str
    ChannelList: str

    def ss_wr_static_array(self, states: typing.Union[StaticStates, typing.List[StaticStates]]):
        """
        This function allows to write a static array of States for the specific single session

        Args:
            static_states: Array of objects class StaticStates to be written on the single session
        """
        if isinstance(states, StaticStates):
            states = [states]
        ch_list = self.ChannelList.split(",")
        iq_list = []
        r_list = []
        for ch in ch_list[0]:
            iq_list.append(int(ch) // 32)
            r_list.append(int(ch) % 32)
        lines_to_write = []
        for s_s, iq, r in zip(states, iq_list, r_list):
            element = DIOLineLocationAndStaticState(DIOLines(r), Connectors(iq), s_s)
            lines_to_write.append(element)
        self.write_multiple_dio_lines(lines_to_write)

    def ss_wr_static(self, static_states: typing.Union[StaticStates, typing.List[StaticStates]]):
        """
        This function allows to write a static array of StaticStates for the specific single session

        Args:
            static_states: Single or array of objects class StaticStates to be written on the
            single session
        """
        if isinstance(static_states, StaticStates):
            static_states = [static_states]
        ch_list = self.Channels.split(",")
        iq_list = []
        r_list = []
        for ch in ch_list:
            iq_list.append(int(ch) // 32)
            r_list.append(int(ch) % 32)
        lines_to_write = []
        # print("test", iq_list)
        for s_s, iq, r in zip(static_states, iq_list, r_list):
            element = DIOLineLocationAndStaticState(DIOLines(r), Connectors(iq), s_s)
            lines_to_write.append(element)
        self.write_multiple_dio_lines(lines_to_write)
        # TODO Check difference with ss_wr_static_array

    def ss_read_static(self):
        """
        This function allows to write a static array of StaticStates for the specific single session
        """
        line_states = []
        ch_list = self.Channels.split(",")
        channels = []
        for ch in ch_list:
            iq = int(ch) // 32
            r = int(ch) % 32
            channels.append(LineLocation(DIOLines(r), Connectors(iq)))
        data = self.read_multiple_lines(channels)
        for bit in data:
            line_states.append(bit.state)
        return data, line_states

    def ss_read_c_states(self):  # TODO CHECK
        """
        This function reads from FPGA the States of each pin and returns two arreys states and
        commanded_states
        Returns:
            states: Array of current states read from FPGA
            commanded_states: Array of current commanded_states read from FPGA
        """
        commanded_states = []
        ch_list = self.Channels.split(",")
        channels = []
        for ch in ch_list:
            iq = int(ch) // 32
            r = int(ch) % 32
            channels.append(LineLocation(DIOLines(r), Connectors(iq)))
        states = self.read_multiple_dio_commanded_states(channels)
        for state in states:
            commanded_states.append(state.state)
        return states, commanded_states

    def close_session(self, reset_if_last_session: bool = True):
        """
        Closes the reference to the FPGA session and, optionally, resets execution of the session.
        By default, the Close FPGA session Reference function closes the reference to the FPGA
        session and resets the FPGA session.To configure this function only to close the reference,
        change the value of the argument when calling the function. The Close FPGA session reference
        function also stops all DMA FIFOs on the FPGA.

        Args:
            reset_if_last_session: configuration variable should be a boolean, it is True by default
        """
        self.Session.close(reset_if_last_session)

    def w_master_lc(self, control_label: str, cluster: I2CMasterLineConfiguration):
        """
        Write on the regiter name "control_label" the cluster with the line configuration
        Args:
            control_label: Defines the register to be written
            cluster: Includes the data to be written on the register
        """
        control = self.Session.registers[control_label]
        sda = collections.OrderedDict()
        sda["Channel"] = cluster.SDA.channel.value
        sda["Connector"] = cluster.SDA.connector.value
        scl = collections.OrderedDict()
        scl["Channel"] = cluster.SCL.channel.value
        scl["Connector"] = cluster.SCL.connector.value
        data = collections.OrderedDict()
        data["SDA"] = sda
        data["SCL"] = scl
        control.write(data)

    def configure_master_sda_scl_lines(
        self,
        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
        sda_channel: LineLocation = LineLocation(DIOLines.DIO0, Connectors.Connector0),
        scl_channel: LineLocation = LineLocation(DIOLines.DIO0, Connectors.Connector0),
    ):
        """
        Configures the provided SDA and SCL channels with the indicated I2C master configuration.
        Args:
            i2c_master_in: Objet of class I2CMaster that indicates the configuration to configure.
                It should Match with the physical hardware.
            sda_channel: Location of the SDA channel given by DioLine and Connector.
                Line location type of object is expected
            scl_channel: Location of the SCL channel given by DioLine and Connector.
                Line location type of object is expected
        """
        cluster = I2CMasterLineConfiguration(sda_channel, scl_channel)
        if 0 <= i2c_master_in.value <= 3:
            control = "I2C Master%d Line Configuration" % i2c_master_in.value
            self.w_master_lc(control, cluster)
        else:
            # print("Requested I2C_master is not defined")
            raise Exception

    def configure_i2c_master_settings(
        self,
        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
        divide: int = 8,
        ten_bit_addressing: bool = False,
        clock_stretching: bool = True,
    ):
        """
        Allows to configure the host setting in the master device. Data provided should be
        supported by the FPGA and match HW configuration
        Args:
            i2c_master_in: Objet of class I2CMaster that indicates the configuration to configure.
                It should Match with the physical hardware.
            divide: int value
            ten_bit_addressing: configuration variable should be a bool
            clock_stretching: configuration variable should be a bool
        """
        # cluster = WorldControllerSetting(divide=divide, ten_bit_addressing=ten_bit_addressing)
        if 0 <= i2c_master_in.value <= 3:
            master = self.Session.registers["I2C Master%d Configuration" % i2c_master_in.value]
            clock = self.Session.registers[
                "I2C Master%d Enable Clock Stretching?" % i2c_master_in.value
            ]
            cluster = master.read()
            cluster["10-bit Addressing"] = ten_bit_addressing
            cluster["Divide"] = divide
            clock.write(clock_stretching)
            master.write(cluster)  # without all info?
        else:
            # print("Requested I2C_master is not defined")
            raise Exception

    def i2c_master_poll_until_ready(
        self,
        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
        start_time: float = 0.0,
        timeout: float = 0.0,
    ):
        """
        Waits slave ready signal until configured timeout has passed. After the signal has been
        received it releases the resources to write or read. If the timeout expires it will rise an
        error 5000
        Args:
            i2c_master_in: Objet of class I2CMaster that indicates the configuration to configure.
                It should Match with the physical hardware.
            start_time: Float variable that indicates the function start time
            timeout: Time until timeout. After it passes the function will raise an exception
        """
        if timeout == 0:
            timeout = start_time
        if 0 <= i2c_master_in.value <= 3:
            master_ready = self.Session.registers[
                "I2C Master%d ready for input" % i2c_master_in.value
            ]
        else:
            # print("Requested I2C_master is not defined")
            raise Exception
        stop = False
        data = False
        while not stop:
            data = master_ready.read()
            time_count = time() - start_time
            stop = data or (time_count > timeout)
        if data:
            pass
        else:
            raise nifpga.ErrorStatus(
                5000,
                ("I2C %s not ready for input" % i2c_master_in.name),
                "i2c_master_poll_until_ready()",
                ["i2c_master", "timeout"],
                (i2c_master_in, timeout),
            )

    def i2c_master_read(
        self,
        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
        device_address: int = 0,
        timeout: float = 1,
        number_of_bytes: int = 1,
    ):
        """
        Reads from the FPGA a deterministic number of bytes.
        Args:
            i2c_master_in: This indicates the bitfile to be used. It should match HW being utilized
            device_address: Address of the device to read from
            timeout: After it passes the function will raise an exception
            number_of_bytes: expected number of bytes to be read
        """
        start_time = time()
        if timeout > 30:
            timeout = 30
        elif timeout < 0:
            timeout = 0
        else:
            pass
        if 0 <= i2c_master_in.value <= 3:
            master_config = self.Session.registers[
                "I2C Master%d Configuration" % i2c_master_in.value
            ]
            master_go = self.Session.registers["I2C Master%d Go" % i2c_master_in.value]
            master_data = self.Session.registers["I2C Master%d Read Data" % i2c_master_in.value]
        else:
            # print("Requested I2C_master is not defined")
            raise Exception
        # config: WorldControllerSetting
        config = master_config.read()
        config["Device Address"] = device_address
        config["Number of Bytes"] = number_of_bytes
        config["Read"] = True
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
        master_config.write(config)
        master_go.write(True)
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
        data = master_data.read()
        data = data[0 : number_of_bytes + 1]
        return data

    def i2c_master_write(
        self,
        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
        timeout: float = 1,
        device_address: int = 0,
        data_to_write: typing.List[int] = [],
    ):
        """
        Writes to the FPGA an array of int.
        Args:
            i2c_master_in: This indicates the bitfile to be used. It should match HW being utilized
            device_address: Address of the device to write to
            timeout: After it passes the function will raise an exception
            data_to_write: list of information to be written to the FPGA
        """
        start_time = time()
        if 0 <= i2c_master_in.value <= 3:
            master_config = self.Session.registers[
                "I2C Master%d Configuration" % i2c_master_in.value
            ]
            master_go = self.Session.registers["I2C Master%d Go" % i2c_master_in.value]
            master_data = self.Session.registers["I2C Master%d Write Data" % i2c_master_in.value]
        else:
            # print("Requested I2C_master is not defined")
            raise Exception
        master_read = master_config.read()
        master_read.Device_Address = device_address
        master_read.Number_of_Bytes = len(data_to_write)
        master_read.Read = False
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
        master_config.write(master_read)
        master_data.write(data_to_write)
        master_go.write(True)

    def read_all_lines(self):
        """
        Read all the lines from the FPGA and returns their value
        Returns:
            data: Object that contains data obtained from FPGA
        """
        data_rd = []
        for i in range(4):
            con = self.Session.registers["Connector%d Read Data" % i]
            data_rd.append(con.read())
        data = ReadData(data_rd[0], data_rd[1], data_rd[2], data_rd[3])
        return data

    def read_multiple_dio_commanded_states(
        self, lines_to_read: typing.Union[LineLocation, typing.Sequence[LineLocation]]
    ):
        """
        Reads the commanded states (0, 1, X, I2C) from the provided list of FPGA Lines and returns
        an array with their value
        Args:
            lines_to_read: List of line locations to be read
        Returns:
            states_list: Returns a list of states read from the specified lines.
        """
        if isinstance(lines_to_read, LineLocation):
            lines_to_read = [lines_to_read]
        out_list = []
        config_list = []
        for i in range(4):
            connector_enable = self.Session.registers["Connector%d Output Enable" % i]
            connector_data = self.Session.registers["Connector%d Output Data" % i]
            merge = (connector_enable.read(), connector_data.read())
            out_list.append(merge)
            master = self.Session.registers["I2C Master%d Line Configuration" % i]
            master_data = master.read()
            sda = master_data["SDA"]
            scl = master_data["SCL"]
            line_sda = LineLocation(sda["Channel"], sda["Connector"])
            line_scl = LineLocation(scl["Channel"], scl["Connector"])
            config_list.append(line_sda)
            config_list.append(line_scl)
        states_list = []
        for element in lines_to_read:
            index = search_line(element, config_list)
            connector = element.connector
            line = element.channel
            out = out_list[connector.value]
            enable = list("{:032b}".format(out[0], "b"))[::-1]
            data = list("{:032b}".format(out[1], "b"))[::-1]
            if data[line.value]:
                line_state = States.One
            else:
                line_state = States.Zero
            if enable[line.value]:
                pass
            else:
                line_state = States.X
            if index > 0:
                pass
            else:
                line_state = States.I2C
            state = LineLocationAndStates(line, connector, line_state)
            states_list.append(state)
        return states_list

    def read_multiple_lines(
        self, lines_to_read: typing.Union[LineLocation, typing.Sequence[LineLocation]]
    ):
        """
        Reads a provided list of lines from the FPGA
        Args:
            lines_to_read: list of Line location objects.
        Returns:
            Readings: Array of data readed
        """
        if isinstance(lines_to_read, LineLocation):
            lines_to_read = [lines_to_read]
        ch_data_list = []
        for ch in range(4):
            con_rd = self.Session.registers["Connector%d Read Data" % ch]
            ch_data_list.append(con_rd.read())
        readings = []
        for lines in lines_to_read:
            connector = lines.connector
            line = lines.channel
            data = ch_data_list[connector.value]
            state_list = list("{:032b}".format(data, "b"))[::-1]
            line_state = state_list[line.value]
            state = DIOLineLocationAndReadState(line, connector, line_state)
            readings.append(state)
        return readings

    def read_single_connector(self, connector: Connectors):
        """
        Reads the FPGA connector and return its value
        Args:
            connector: Specifies connector to be read
        Returns:
            Data read in one array
        """
        data: int = 0
        if 0 <= connector.value <= 3:
            read_control = self.Session.registers["Connector%d Read Data" % connector.value]
            data = read_control.read()
        return data

    def read_single_dio_line(
        self, connector: Connectors = Connectors.Connector0, line: DIOLines = DIOLines.DIO0
    ):
        """
        Reads the specific DIO line and return its value
        Args:
            connector: Defines the connector from the list provided in the class Connectors
            line: Defines the line from the list provided in the class DIOLines
        Returns:
            Line State: Object that contains the current state of the line
        """
        data = self.read_single_connector(connector)
        state_list = list("{:032b}".format(data, "b"))[::-1]
        line_state = state_list[line.value]
        return line_state

    def write_multiple_dio_lines(
        self,
        lines_to_write: typing.Union[
            DIOLineLocationAndStaticState, typing.Sequence[DIOLineLocationAndStaticState]
        ],
    ):
        """
        Writes the provided list of DIOLineLocationAndStaticState objects into the FPGA using the
        address provided in each element
        Args:
            lines_to_write: List of DIOLineLocationAndStaticState objects to be written
        """
        if isinstance(lines_to_write, DIOLineLocationAndStaticState):
            lines_to_write = [lines_to_write]
        con_list = []
        data_list = []
        for i in range(4):
            con_enable = self.Session.registers["Connector%d Output Enable" % i]
            con_data = self.Session.registers["Connector%d Output Enable" % i]
            merge_con = (con_enable, con_data)
            merge_data = [con_enable.read(), con_data.read()]
            con_list.append(merge_con)
            data_list.append(merge_data)
        for lines in lines_to_write:
            if 0 <= lines.connector.value <= 3:
                self.write_single_dio_line(lines.connector, lines.channel, lines.state)
        try:
            update_state = self.Session.registers["Update State"]
            update_state.write(True)
        except KeyError:
            pass

    def write_single_dio_line(
        self,
        connector: Connectors = Connectors.Connector0,
        line: DIOLines = DIOLines.DIO0,
        state: StaticStates = StaticStates.Zero,
    ):
        """
        Writes the provided DiO Line with the given state into the FPGA
        Args:
            connector: Connector to write
            line: Line to write
            state: State to be written
        """
        if 0 <= connector.value <= 3:
            con_enable = self.Session.registers["Connector%d Output Enable" % connector.value]
            con_data = self.Session.registers["Connector%d Output Data" % connector.value]
            enable, data = update_line_on_connector(con_enable.read(), con_data.read(), line, state)
            con_enable.write(enable)
            con_data.write(data)
            try:
                update_state = self.Session.registers["Update State"]
                update_state.write(True)
            except KeyError:
                pass


class TSMFPGA(typing.NamedTuple):
    pin_query_context: Any
    SSC: typing.List[_SSCFPGA]
    site_numbers: typing.List[int]

    def configure_i2c_bus(
        self, ten_bit_addressing: bool = False, divide: int = 8, clock_stretching: bool = True
    ):
        """
        Allows to configure the host setting for the TSMFPGA session. Data provided should be
        supported by the FPGA and match HW configuration for that specific session.
        Args:
            ten_bit_addressing: Configuration variable false by default
            divide: configuration variable 8 by default
            clock_stretching: Configuration variable True by default
        """
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        session.configure_i2c_master_settings(i2c, divide, ten_bit_addressing, clock_stretching)

    def read_i2c_data(self, timeout: float = 1, slave_address: int = 0, number_of_bytes: int = 1):
        """
        Reads from the FPGA session a given number of bytes.
        Args:
            slave_address: Address of the device to read from
            timeout: After it passes the function will raise an exception
            number_of_bytes: expected number of bytes to be read
        Returns:
            Data read from FPG
        """
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        i2c_read_data = session.i2c_master_read(i2c, slave_address, timeout, number_of_bytes)
        return i2c_read_data

    def write_i2c_data(
        self, data_to_write: typing.List[int], timeout: float = 1, slave_address: int = 0
    ):
        """
        Writes to the FPGA session the provided list of integers.
        Args:
            slave_address: Address of the device to write the provided data
            timeout: If it passes the function will raise an exception
            data_to_write: list of integers to write on the FPGA session
        """
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        session.i2c_master_write(i2c, timeout, slave_address, data_to_write)

    def extract_i2c_master_from_sessions(self):
        """
        From session, it determines the right configuration to be used that Matches de FPGA HW
        Returns:
            Session handler and scan value in a string
        """
        session = self.SSC[0]  # .Session
        ch_list = self.SSC[0].ChannelList
        sites_and_pins, sites, pins = channel_list_to_pins(ch_list)
        sites_and_pins.clear()
        sites.clear()
        scan = ""
        for i2c in I2CMaster:
            if i2c.name in pins[0]:
                scan = i2c
        if type(scan) != I2CMaster:
            raise nifpga.ErrorStatus(
                5000,
                "Invalid I2C Master Session Provided",
                "extract_i2c_master_from_sessions",
                ["self"],
                self,
            )
        return session, scan

    def read_commanded_line_states(self):
        """
        Read commanded states for the specific session and returns it as an array of elements
        Returns:
            list of current commanded states and commanded states as a tuple
        """
        commanded_states = []
        current_commanded_states = []
        data = ()
        for ss in self.SSC:
            data = ss.ss_read_c_states()
        current_commanded_states.append(data[0])
        commanded_states += data[1]
        return current_commanded_states, commanded_states

    def read_static(self):
        """
        Read static values for each FPGA session in the TSMFPGA list
        Returns:
            Readings and line states as a Tuple
        """
        readings = []
        line_states = []
        for ss in self.SSC:
            data = ss.ss_read_static()
            readings.append(data[0])
            line_states.append(data[0])
        return readings, line_states

    def write_static_array(
        self, static_state: typing.Union[StaticStates, typing.List[StaticStates]]
    ):
        """
        Write a list of Static States on the FPGA session
        Args:
            static_state: List of static states to be written
        """
        for ss in self.SSC:
            ss.ss_wr_static_array(static_state)

    def write_static(self, static_state: typing.Union[StaticStates, typing.List[StaticStates]]):
        """
        Write a list of Static States on the FPGA session
        Args:
            static_state: List of static states to be written
        """
        for ss in self.SSC:
            ss.ss_wr_static(static_state)


def debug_ui_launcher(semiconductor_module_manager: nitsm.codemoduleapi.SemiconductorModuleContext):
    # print(semiconductor_module_manager)
    pass


def search_line(line: LineLocation, ch_list: typing.List[LineLocation]):
    """
    Search the a line that corresponds to the inputs provided and returns -1 in case it is not found
    Args:
        line: Line location object to be searched in the list of channels
        ch_list: list of channels to perform the search
    """
    index = 0
    for element in ch_list:
        if element.channel == line.channel and element.connector == line.connector:
            return index
        else:
            index += 1
    return -1


def update_line_on_connector(
    enable_in: int = 0,
    data_in: int = 0,
    dio_line: DIOLines = DIOLines.DIO0,
    line_state: StaticStates = StaticStates.Zero,
):
    """
    Calculates the next value to write on FPGA given its previous values and location
    Args:
        enable_in: 0 by default. Carries the last known value of enable
        data_in: 0 by default. Represents the new value of Data
        dio_line: Defines the Dio line to be updated
        line_state: Value to update
    Returns:
        Tuple with enable value and data value for the next iteration
    """
    dio_index = dio_line.value
    output_data = ((-dio_index << data_in) & 1) > 0
    data, enable = line_state_to_out(line_state, output_data)
    ch1 = ~(1 << dio_index)
    ch2 = int(enable) << dio_index
    ch3 = int(data) << dio_index
    enable_out = ch2 | (enable_in & ch1)
    data_out = (ch1 & data_in) | ch3
    return enable_out, data_out


def line_state_to_out(line: StaticStates, out_data: bool):
    """
    Calculate the data and enable values given a initial state
    Args:
        line: StaticState that represent the line
        out_data: If line value is 2 it will be returned as the next value of data
    Returns:
         Data and Enable values for the next iteration
    """
    data = False
    enable = False
    if line.value == 0:
        data = False
        enable = True
    elif line.value == 1:
        data = True
        enable = True
    elif line.value == 2:
        data = out_data
        enable = False
    return data, enable


def channel_list_to_pins(channel_list: str = ""):
    """
    Converts from a provided channel list to hardware pins
    Args:
        channel_list: List of channels to use in the function
    Returns:
        sites_and_pins, sites, pins in a tuple
    """
    ch_list = channel_list.split(",")
    sites_and_pins = []
    sites = []
    pins = []
    for ch in ch_list:
        ch = ch.lstrip()
        sites_and_pins.append(ch)
        ch_l = ch.replace("/", "\\").split("\\")
        if "\\" in ch or "/" in ch:
            site_out = ch_l[0]
            pin = ch_l[1]
        else:
            site_out = "site-1"
            pin = ch_l[0]
        site_out = site_out[4:]
        if site_out[0] == "+" or site_out[0] == "-":
            if site_out[1:].isnumeric():
                data = int(site_out)
            else:
                data = 0
        else:
            if site_out.isnumeric():
                data = int(site_out)
            else:
                data = 0
        sites.append(data)
        pins.append(pin)
    return sites_and_pins, sites, pins


def close_sessions(tsm_context: SMContext):
    """
    Clears the FPGA session.  Before clearing, this method aborts the session, if necessary, and
    releases any resources the session has reserved. You cannot use a session after you clear it
    unless you recreate the session. If you create the FPGA session object within a loop, use this
    method within the loop after you are finished with the session to avoid allocating unnecessary
    memory.
    """
    session_data, _, _ = tsm_context.get_all_custom_sessions(InstrumentTypeId)
    for session in session_data:
        session.close()


debug = []


def initialize_sessions(tsm_context: SMContext, ldb_type: str = ""):
    """
    Initialize the sessions from TSM context pinmap.
    """
    global debug
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(
        InstrumentTypeId
    )
    # when the output from a function is unused use _ instead of variables like below
    # instrument_names, channel_group_ids, _ = tsm_context.get_custom_instrument_names(
    # InstrumentTypeId)
    for instrument, group_id in zip(instrument_names, channel_group_ids):
        # target_list = ["PXIe-7822R", "PXIe-7821R", "PXIe-7820R"]
        ref_out = ""
        for target in BoardType:
            try:
                ref_out = open_reference(instrument, target, ldb_type)
            except Exception:  # TODO Check on baku since the condition seems to be up side down
                continue
            else:
                break
        tsm_context.set_custom_session(InstrumentTypeId, instrument, group_id, ref_out)
    dut_pins, system_pins = tsm_context.get_pin_names(InstrumentTypeId)
    debug = list(tsm_context.pins_to_custom_sessions(InstrumentTypeId, dut_pins + system_pins))


def pins_to_sessions(
    tsm_context: SMContext,
    pins: typing.Union[str, typing.Sequence[str]],
    site_numbers: typing.Union[int, typing.Sequence[int]] = [],
):
    """
    Returns an object that contains a list of sessions generated for the provided pins.
    """
    if type(pins) == str:
        pins = [pins]
    if type(site_numbers) == int:
        site_numbers = [site_numbers]
    (
        pin_query_context,
        session_data,
        channel_group_ids,
        channels_lists,
    ) = tsm_context.pins_to_custom_sessions(InstrumentTypeId, pins)
    session_data: typing.Tuple[nifpga.Session]
    channel_list, sites = ni_dt_common.pin_query_context_to_channel_list(
        pin_query_context, [], site_numbers
    )
    new_sessions = []
    for session, channel_id, channel, site in zip(
        session_data, channel_group_ids, channels_lists, sites
    ):
        new_sessions.append(_SSCFPGA(session, channel_id, channel, site))
    return TSMFPGA(pin_query_context, new_sessions, channel_list)


def open_reference(rio_resource: str, target: BoardType, ldb_type: str):
    """
    Creates an FPGA session for the specific RIO resource.
    Args:
        rio_resource: FPGA board name should match with NI-MAX
        target: HW type should match with the real hardware
        ldb_type:String indicating LDB type
    """
    if target == BoardType.PXIe_7820R:
        name_of_relative_path = "7820R Static IO and I2C FPGA Main 3.3V.lvbitx"
    elif target == BoardType.PXIe_7821R:
        name_of_relative_path = "7821R Static IO and I2C FPGA Main 3.3V.lvbitx"
    elif target == BoardType.PXIe_7822R:
        if "seq" in ldb_type.lower():
            name_of_relative_path = "7822R Static IO and I2C FPGA Main 3.3V.lvbitx"
        else:
            name_of_relative_path = (
                "7822R Static IO and I2C FPGA Main Conn01 3.3V Conn 23 1.2V.lvbitx"
            )
    else:
        name_of_relative_path = ""
    path = os.path.join(CurrentPath, "..\\..\\FPGA Bitfiles\\", name_of_relative_path)
    reference = nifpga.Session(path, rio_resource)
    return reference


def get_i2c_master_session(
    tsm_context: SMContext,
    i2c_master_in: I2CMaster.I2C_3V3_7822_SINK,
    apply_i2c_settings: bool = True,
):
    sda = "%s_SDA" % i2c_master_in.name
    scl = "%s_SCL" % i2c_master_in.name
    session_data = pins_to_sessions(tsm_context, [sda, scl], [])
    session = session_data.SSC[0]
    ch_list = session_data.SSC[0].Channels.split(",")
    iq_list = []
    r_list = []
    for ch in ch_list:
        iq_list.append(int(ch) // 32)
        r_list.append(int(ch) % 32)
    e0 = LineLocation(DIOLines(r_list[0]), Connectors(iq_list[0]))
    e1 = LineLocation(DIOLines(r_list[1]), Connectors(iq_list[1]))
    session.configure_master_sda_scl_lines(i2c_master_in, e0, e1)
    if apply_i2c_settings:
        session_data.configure_i2c_bus(False, 64, True)
    return session_data


def check_ui_tool(
    path_in: str,
    path_teststand="C:\\Users\\Public\\Documents\\National Instruments\\TestStand 2019 (64-bit)",
):
    path_icons = os.path.join(path_teststand, "Components\\Icons")
    path_in = os.path.join(
        path_in, "..\\Code Modules\\Common\\Instrument Control\\782x FPGA\\CustomInstrument"
    )
    path_debug = os.path.join(path_icons, "782x FPGA Debug UI.ico")
    if not os.path.exists(path_debug):
        source = os.path.join(path_in, "782x FPGA Debug UI.ico")
        target = path_icons
        shutil.copy2(source, target)
    path_panels = os.path.join(
        path_teststand, "Components\\Modules\\NI_SemiconductorModule\\CustomInstrumentPanels"
    )
    path_debug = os.path.join(path_panels, "782x FPGA Debug UI.seq")
    path_debug2 = os.path.join(path_panels, "782x FPGA Debug UI")
    condition = os.path.exists(path_debug) and os.path.exists(path_debug2)
    if not False:
        source = os.path.join(path_in, ".\\782x FPGA Debug UI\\")
        target = path_panels
        shutil.copy2(source, target)
        source = os.path.join(path_in, ".\\782x FPGA Debug UI.seq")
        shutil.copy2(source, target)
