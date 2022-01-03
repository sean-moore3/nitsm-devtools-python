import os
import nifpga
from enum import Enum
from time import time
# import nitsm.codemoduleapi
# from nitsm.enums import Capability
# from nidaqmx.constants import TerminalConfiguration
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
# from nitsm.enums import InstrumentTypeIdConstants
# from nitsm.pinquerycontexts import PinQueryContext
import typing

# Types Definition

PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]
InstrumentTypeId = '782xFPGA'
CurrentPath = os.getcwd()


class ReadData(typing.NamedTuple):
    Connector0: nifpga.DataType.U32
    Connector1: nifpga.DataType.U32
    Connector2: nifpga.DataType.U32
    Connector3: nifpga.DataType.U32


class I2CMaster(Enum):
    I2C_3V3_7822_SINK = 0
    I2C_3V3_7822_LINT = 1
    DIB_I2C = 2
    I2C_3V3_7822_TLOAD = 3


class DIOLines(Enum):
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


class Connector(Enum):
    Connector0 = 0
    Connector1 = 1
    Connector2 = 2
    Connector3 = 3
    Con_None = 4


class States(Enum):
    Zero: 0
    One: 1
    X: 2
    I2C: 3


class Channel:
    def __init__(self, channel: DIOLines, connector: Connector):
        self.channel = channel
        self.connector = connector


class CurrentCommandedStates(Channel):
    state: States


class I2CMasterLineConfiguration(typing.NamedTuple):
    SDA: Channel
    SCL: Channel


class WorldControllerSetting:
    def __init__(self,
                 device_address: int = 0,
                 read: bool = False,
                 number_of_bytes: int = 0,
                 ten_bit_addressing: bool = False,
                 divide: int = 0
                 ):
        self.Device_Address = device_address
        self.Read = read
        self.Number_of_Bytes = number_of_bytes
        self.Ten_Bit_Addressing = ten_bit_addressing
        self.Divide = divide


def search_line(line: Channel, ch_list: typing.List[Channel]):
    index = 0
    for element in ch_list:
        if element.channel == line.channel and element.connector == line.connector:
            return index
        else:
            index += 1
    return -1


class _SSCFPGA(typing.NamedTuple):
    Session: nifpga.Session
    ChannelGroupID: str
    Channels: str
    ChannelList: str

    def close_session(self, reset_if_last_session: bool = True):
        """
        Closes the reference to the FPGA session and, optionally, resets execution of the session. By default,
        the Close FPGA session Reference function closes the reference to the FPGA session and resets the FPGA session.
        To configure this function only to close the reference, change the value of the argument when calling the
        function. The Close FPGA session reference function also stops all DMA FIFOs on the FPGA.
        """
        self.Session.close(reset_if_last_session)

    def configure_i2c_master_sda_scl_lines(self,
                                           i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                           sda_channel: Channel = Channel(DIOLines.DIO0, Connector.Connector0),
                                           scl_channel: Channel = Channel(DIOLines.DIO0, Connector.Connector0)
                                           ):
        """"""
        cluster = I2CMasterLineConfiguration(sda_channel, scl_channel)
        if 0 <= i2c_master.value <= 3:
            master = self.Session.registers['I2C Master%d Line Configuration' % i2c_master.value]
            master.write(cluster)
        else:
            print("Requested I2C_master is not defined")
            raise Exception

    def configure_i2c_master_settings(self,
                                      i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                      divide: int = 8,
                                      ten_bit_addressing: bool = False,
                                      clock_stretching: bool = True
                                      ):
        """"""
        cluster = WorldControllerSetting(divide=divide, ten_bit_addressing=ten_bit_addressing)
        if 0 <= i2c_master.value <= 3:
            master = self.Session.registers['I2C Master%d Configuration' % i2c_master.value]
            clock = self.Session.registers['I2C Master%d Enable Clock Stretching?' % i2c_master.value]
            clock.write(clock_stretching)
            master.write(cluster)  # without all info?
        else:
            print("Requested I2C_master is not defined")
            raise Exception

    def i2c_master_poll_until_ready(self,
                                    i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                    start_time: float = 0.0,
                                    timeout: float = 0.0
                                    ):
        """"""
        if timeout == 0:
            timeout = start_time
        if 0 <= i2c_master.value <= 3:
            master_ready = self.Session.registers['I2C Master%d ready for input' % i2c_master.value]
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        stop = False
        data = False
        while not stop:
            data = master_ready.read()
            time_count = time() - start_time
            stop = data and time_count > timeout
        if data:
            pass
        else:
            raise nifpga.ErrorStatus(5000,
                                     ("I2C %s not ready for input" % i2c_master.name),
                                     "i2c_master_poll_until_ready()",
                                     ["i2c_master", "timeout"],
                                     (i2c_master, timeout))

    def i2c_master_read(self,
                        i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                        device_address: int = 0,
                        timeout: float = 1,
                        number_of_bytes: int = 1
                        ):
        start_time = time()
        if timeout > 30:
            timeout = 30
        elif timeout < 0:
            timeout = 0
        else:
            pass
        if 0 <= i2c_master.value <= 3:
            master_config = self.Session.registers['I2C Master%d Configuration' % i2c_master.value]
            master_go = self.Session.registers['I2C Master%d Go' % i2c_master.value]
            master_data = self.Session.registers['I2C Master%d Read Data' % i2c_master.value]
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        config: WorldControllerSetting
        config = master_config.read()
        config.Device_Address = device_address
        config.Number_of_Bytes = number_of_bytes
        config.Read = True
        self.i2c_master_poll_until_ready(i2c_master, start_time, timeout)
        master_config.write(config)
        master_go.write(True)
        self.i2c_master_poll_until_ready(i2c_master, start_time, timeout)
        data = master_data.read()
        data = data[0:number_of_bytes+1]
        return data

    def i2c_master_write(self,
                         i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                         timeout: float = 1,
                         device_address: int = 0,
                         data_to_write: typing.List[int] = []):
        start_time = time()
        if 0 <= i2c_master.value <= 3:
            master_config = self.Session.registers['I2C Master%d Configuration' % i2c_master.value]
            master_go = self.Session.registers['I2C Master%d Go' % i2c_master.value]
            master_data = self.Session.registers['I2C Master%d Write Data' % i2c_master.value]
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        master_read: WorldControllerSetting
        master_read = master_config.read()
        master_read.Device_Address = device_address
        master_read.Number_of_Bytes = len(data_to_write)
        master_read.Read = False
        self.i2c_master_poll_until_ready(i2c_master, start_time, timeout)
        master_config.write(master_read)
        master_data.write(data_to_write)
        master_go.write(True)

    def read_all_lines(self):
        data_rd = []
        for i in range(4):
            con = self.Session.registers['Connector%d Read Data' % i]
            data_rd.append(con.read())
        data = ReadData(data_rd[0], data_rd[1], data_rd[2], data_rd[3])
        return data

    def read_multiple_dio_commanded_states(self, lines_to_read: typing.List[Channel]):
        out_list = []
        config_list = []
        for i in range(4):
            connector_enable = self.Session.registers["Connector%d Output Enable" % i]
            connector_data = self.Session.registers["Connector%d Output Data" % i]
            merge = (connector_enable.read(), connector_data.read())
            out_list.append(merge)
            master = self.Session.registers["I2C_Master%d_Line_Configuration" % i]
            master_data: I2CMasterLineConfiguration = master.read()
            config_list.append(master_data.SDA)
            config_list.append(master_data.SCL)
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
            state = CurrentCommandedStates(line, connector)
            state.State = line_state
            states_list.append(state)
        return states_list

    def read_multiple_lines(self, lines_to_read: typing.List[Channel]):
        ch_data_list = []
        for ch in range(4):
            con_rd = self.Session.registers['Connector%d Read Data' % ch]
            ch_data_list.append(con_rd.read())
        readings = []
        for lines in lines_to_read:
            connector = lines.connector
            line = lines.channel
            data = ch_data_list[connector.value]
            state_list = list("{:032b}".format(data, "b"))[::-1]
            line_state = state_list[line.value]
            state = CurrentCommandedStates(line, connector)
            state.State = line_state
            readings.append(state)
        return readings

    def read_single_connector(self, connector: Connector):
        data: nifpga.DataType.U32 = 0
        if 0 <= connector.value <= 3:
            read_control = self.Session.registers["Connector%d Read Data" % connector.value]
            data = read_control.read()
        return data

    def read_single_dio_line(self, connector: Connector = Connector.Connector0, line: DIOLines = DIOLines.DIO0):
        data = self.read_single_connector(connector)
        state_list = list("{:032b}".format(data, "b"))[::-1]
        line_state = state_list[line.value]
        return line_state

    def write_multiple_dio_lines(self, lines_to_write: typing.List[CurrentCommandedStates]):
        con_list = []
        data_list = []
        for i in range(4):
            con_enable = self.Session.registers['Connector%d Output Enable' % i]
            con_data = self.Session.registers['Connector%d Output Enable' % i]
            merge_con = (con_enable, con_data)
            merge_data = [con_enable.read(), con_data.read()]
            con_list.append(merge_con)
            data_list.append(merge_data)
        for lines in lines_to_write:
            if 0 <= lines.connector.value <= 3:
                enable, data = update_line_on_connector(data_list[lines.connector.value][0],
                                                        data_list[lines.connector.value][1],
                                                        lines.channel,
                                                        lines.state)
                data_list[lines.connector.value] = [enable, data]
            else:
                pass
        for data, con in zip(data_list, con_list):
            con[0].write(data[0])
            con[1].write(data[1])

    def write_single_dio_line(self,
                              connector: Connector = Connector.Connector0,
                              line: DIOLines = DIOLines.DIO0,
                              state: States = States.Zero):
        if 0 <= connector.value <= 3:
            con_enable = self.Session.registers['Connector%d Output Enable' % connector.value]
            con_data = self.Session.registers['Connector%d Output Data' % connector.value]
            enable, data = update_line_on_connector(con_enable.read(), con_data.read(), line, state)
            con_enable.write(enable)
            con_data.write(data)


def update_line_on_connector(output_enable: nifpga.DataType.U32 = 0,
                             output_data: nifpga.DataType.U32 = 0,
                             dio_line: DIOLines = DIOLines.DIO0,
                             line_state: States = States.Zero):
    dio_line.value
    line_state.value
    enable: nifpga.DataType.U32 = output_enable
    data: nifpga.DataType.U32 = output_data
    return enable, data  # TODO Check


def line_state_to_out(line: States, out_data: bool):
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


class TSMFPGA(typing.NamedTuple):
    pin_query_context: Any
    SSC: typing.List[_SSCFPGA]

    def get_i2c_master(self):
        for element in self.SSC:
            session = element.Session
            ch_list = element.ChannelList

    def write_i2c_data(self, data_to_write: typing.List[int], timeout: float = 1, slave_address: int = 0):
        pass


def open_reference(rio_resource: str, target: str, ldb_type: str):
    if target == 'PXIe-7820R':
        name_of_relative_path = '7820R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target == 'PXIe-7821R':
        name_of_relative_path = '7821R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target == 'PXIe-7822R':
        if 'Seq' in ldb_type:
            name_of_relative_path = '7822R Static IO and I2C FPGA Main 3.3V.lvbitx'
        else:
            name_of_relative_path = '7822R Static IO and I2C FPGA Main Conn01 3.3V Conn 23 1.2V.lvbitx'
    else:
        name_of_relative_path = ''
    path = os.path.join(CurrentPath, '..\\..\\FPGA Bitfiles\\', name_of_relative_path)
    reference = os.path.join(rio_resource, path)
    return reference


def initialize_session(tsm_context: TSMContext, ldb_type: str):
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(InstrumentTypeId)
    for instrument, group in zip(instrument_names, channel_group_ids):
        target_list = ["PXIe-7822R", "PXIe-7821R", "PXIe-7820R"]
        for target in target_list:
            ref_out = open_reference(instrument, target, ldb_type)
        tsm_context.set_custom_session(InstrumentTypeId, instrument, group, ref_out)
        dut_pins, system_pins = tsm_context.get_pin_names(InstrumentTypeId)
        debug = tsm_context.pins_to_custom_sessions(InstrumentTypeId, dut_pins+system_pins)
        return debug
