import os
import nifpga
from enum import Enum
from time import time
import nitsm.codemoduleapi
from nitsm.enums import Capability
from nidaqmx.constants import TerminalConfiguration
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.enums import InstrumentTypeIdConstants
from nitsm.pinquerycontexts import PinQueryContext
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


class Channel():
    channel: DIOLines
    connector: Connector

class CurrentCommandedStates(Channel):
    State:

class I2CMasterLineConfiguration(typing.NamedTuple):
    SDA: Channel
    SCL: Channel


class WorldControllerSetting:
    Device_Address: int
    Read: bool
    Number_of_Bytes: int
    ten_bit_addressing: bool
    Divide: int


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
        if i2c_master == 0:
            master = self.Session.registers['I2C Master0 Line Configuration']
            master.write(cluster)
        elif i2c_master == 1:
            master = self.Session.registers['I2C Master1 Line Configuration']
            master.write(cluster)
        elif i2c_master == 2:
            master = self.Session.registers['I2C Master2 Line Configuration']
            master.write(cluster)
        elif i2c_master == 3:
            master = self.Session.registers['I2C Master3 Line Configuration']
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
        cluster = WorldControllerSetting(Divide=divide, ten_bit_addressing=ten_bit_addressing)
        if i2c_master == 0:
            master = self.Session.registers['I2C Master0 Configuration']
            clock = self.Session.registers['I2C Master0 Enable Clock Stretching?']
            clock.write(clock_stretching)
            master.write(cluster)
        elif i2c_master == 1:
            master = self.Session.registers['I2C Master1 Configuration']
            clock = self.Session.registers['I2C Master1 Enable Clock Stretching?']
            clock.write(clock_stretching)
            master.write(cluster)
        elif i2c_master == 2:
            master = self.Session.registers['I2C Master2 Configuration']
            clock = self.Session.registers['I2C Master2 Enable Clock Stretching?']
            clock.write(clock_stretching)
            master.write(cluster)
        elif i2c_master == 3:
            master = self.Session.registers['I2C Master3 Configuration']
            clock = self.Session.registers['I2C Master3 Enable Clock Stretching?']
            clock.write(clock_stretching)
            master.write(cluster)
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
        if i2c_master == 0:
            master_ready = self.Session.registers['I2C Master0 ready for input']
        elif i2c_master == 1:
            master_ready = self.Session.registers['I2C Master1 ready for input']
        elif i2c_master == 2:
            master_ready = self.Session.registers['I2C Master2 ready for input']
        elif i2c_master == 3:
            master_ready = self.Session.registers['I2C Master3 ready for input']
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        stop = False
        while not stop:
            data = master_ready.read()
            time_count = time() - start_time
            stop = data and time_count > timeout
        if data:
            pass
        else:
            raise nifpga.ErrorStatus(5000,
                                     ("I2C %s not ready for input", I2CMaster),
                                     "i2c_master_poll_until_ready()",
                                     ["i2c_master", "timeout"],
                                     (i2c_master, timeout))
    def i2c_master_read(self,
                        i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                        device_address: int = 0,
                        timeout:float = 1,
                        number_of_bytes:int = 1
                        ):
        start_time=time()
        if timeout>30:
            timeout=30
        elif timeout<0:
            timeout=0
        else:
            pass
        if i2c_master == 0:
            master_config = self.Session.registers['I2C Master0 Configuration']
            master_go = self.Session.registers['I2C Master0 Go']
            master_data = self.Session.registers['I2C Master0 Read Data']
        elif i2c_master == 1:
            master_config = self.Session.registers['I2C Master1 Configuration']
            master_go = self.Session.registers['I2C Master1 Go']
            master_data = self.Session.registers['I2C Master1 Read Data']
        elif i2c_master == 2:
            master_config = self.Session.registers['I2C Master2 Configuration']
            master_go = self.Session.registers['I2C Master2 Go']
            master_data = self.Session.registers['I2C Master2 Read Data']
        elif i2c_master == 3:
            master_config = self.Session.registers['I2C Master3 Configuration']
            master_go = self.Session.registers['I2C Master3 Go']
            master_data = self.Session.registers['I2C Master3 Read Data']
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        config: WorldControllerSetting
        config = master_config.read()
        config.Device_Address = device_address
        config.Number_of_Bytes = number_of_bytes
        config.Read = True
        self.i2c_master_poll_until_ready(i2c_master,start_time,timeout)
        master_config.write(config)
        master_go.write(True)
        self.i2c_master_poll_until_ready(i2c_master, start_time, timeout)
        data = master_data.read()
        data = data[0:number_of_bytes+1]
        return data


    def i2c_master_write(self,
                         i2c_master: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                         timeout:float = 1,
                         device_address:int = 0,
                         data_to_write: typing.List[int] = []):
        start_time=time()
        if i2c_master == 0:
            master_config = self.Session.registers['I2C Master0 Configuration']
            master_go = self.Session.registers['I2C Master0 Go']
            master_data = self.Session.registers['I2C Master0 Write Data']
        elif i2c_master == 1:
            master_config = self.Session.registers['I2C Master1 Configuration']
            master_go = self.Session.registers['I2C Master1 Go']
            master_data = self.Session.registers['I2C Master1 Write Data']
        elif i2c_master == 2:
            master_config = self.Session.registers['I2C Master2 Configuration']
            master_go = self.Session.registers['I2C Master2 Go']
            master_data = self.Session.registers['I2C Master2 Write Data']
        elif i2c_master == 3:
            master_config = self.Session.registers['I2C Master3 Configuration']
            master_go = self.Session.registers['I2C Master3 Go']
            master_data = self.Session.registers['I2C Master3 Write Data']
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
        con0 = self.Session.registers['Connector0 Read Data']
        con1 = self.Session.registers['Connector1 Read Data']
        con2 = self.Session.registers['Connector2 Read Data']
        con3 = self.Session.registers['Connector3 Read Data']
        con0_data = con0.read()
        con1_data = con1.read()
        con2_data = con2.read()
        con3_data = con3.read()
        data = ReadData(con0_data, con1_data,con2_data,con3_data)
        return data

    def serch_line(self, line: Channel, list:typing.List[Channel]):
        index=0
        for element in list:
            if element.channel==line.channel and element.connector==line.connector:
                return index
            else:
                index+=1
        return -1

    def read_multiple_dio_commanded_states(self, lines_to_read: typing.List[Channel]):
        connector_enable0 = self.Session.registers["Connector0 Output Enable"]
        connector_enable1 = self.Session.registers["Connector1 Output Enable"]
        connector_enable2 = self.Session.registers["Connector2 Output Enable"]
        connector_enable3 = self.Session.registers["Connector3 Output Enable"]
        connector_data0 = self.Session.registers["Connector0 Output Data"]
        connector_data1 = self.Session.registers["Connector1 Output Data"]
        connector_data2 = self.Session.registers["Connector2 Output Data"]
        connector_data3 = self.Session.registers["Connector3 Output Data"]
        master0:I2CMasterLineConfiguration = self.Session.registers["I2C_Master0_Line_Configuration"]
        master1:I2CMasterLineConfiguration = self.Session.registers["I2C_Master1_Line_Configuration"]
        master2:I2CMasterLineConfiguration = self.Session.registers["I2C_Master2_Line_Configuration"]
        master3:I2CMasterLineConfiguration = self.Session.registers["I2C_Master3_Line_Configuration"]
        out_list = [(connector_enable0, connector_data0),
                    (connector_enable1, connector_data1),
                    (connector_enable2, connector_data2),
                    (connector_enable3, connector_data3)]
        config_list=[master0.SDA, master0.SCL,
                     master1.SDA, master1.SCL,
                     master2.SDA, master2.SCL,
                     master3.SDA, master3.SCL]
        states_list=[]
        for element in lines_to_read:
            index = self.serch_line(element, config_list)
            connector = element.connector
            line = element.channel
            out = out_list[connector]
            enable = list("{:032b}".format(out[0],"b"))[::-1]
            data = list("{:032b}".format(out[1],"b"))[::-1]
            if data[line]:
                line_state = States.One
            else:
                line_state = States.Zero
            if enable[line]:
                pass
            else:
                line_state = States.X
            if index>0:
                pass
            else:
                line_state = States.I2C
            state = CurrentCommandedStates()
            state.State = line_state
            state.connector = connector
            state.channel = line
            states_list.append(state)
        return states_list



    def read_multiple_lines(self):
        pass  # TODO finish


    def read_single_connector(self):
        pass  # TODO finish


    def read_single_dio_line(self):
        pass  # TODO finish


    def write_multiple_dio_lines(self):
        pass  # TODO finish


    def write_single_dio_line(self):
        pass  # TODO finish

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
        traget_list = ["PXIe-7822R", "PXIe-7821R", "PXIe-7820R"]
        for target in traget_list:
            ref_out = open_reference(instrument, target, ldb_type)
        tsm_context.set_custom_session(InstrumentTypeId, instrument, group, ref_out)
        dut_pins, system_pins = tsm_context.get_pin_names(InstrumentTypeId)
        debug = tsm_context.pins_to_custom_sessions(InstrumentTypeId, dut_pins+system_pins)
        return debug
