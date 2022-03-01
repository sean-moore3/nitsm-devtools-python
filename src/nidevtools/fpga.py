import collections
import os
import shutil
import typing
from enum import Enum
from time import time
# from time import sleep
# import site

import nifpga
import nitsm.pinquerycontexts
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
# import nitsm.codemoduleapi
# from nitsm.enums import Capability
# from nidaqmx.constants import TerminalConfiguration
# from nitsm.enums import InstrumentTypeIdConstants


import nidevtools.common as ni_dt_common

# Types Definition

PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]
InstrumentTypeId = '782xFPGA'
CurrentPath = os.getcwd()
PinQuery = nitsm.pinquerycontexts.PinQueryContext


class ConnectorResources(typing.NamedTuple):
    Port0: str
    Port1: str  # TODO Missing Port type
    Port2: str
    Port3: str


class I2CDataType(typing.NamedTuple):
    Data: int
    ACK: bool
    Valid: bool


class I2CSlaveStates(Enum):
    WaitOnStartCondition = 0
    Addressing = 1
    AddressAck = 2
    MasterReadingData = 3
    RetrieveAck = 4
    MasterWritingData = 5
    SendAck = 6


class I2CTransferSettings(typing.NamedTuple):
    SendStopCondition: bool
    Divide: int
    Read: bool


class MasterState(Enum):
    Idle = 0
    SendStartCondition = 1
    SendData = 2
    SendRisingClock = 3
    SendFallingClock = 4
    Waiting = 5
    ReleaseClock = 6
    ReleaseData = 7
    StopConditionSetUp = 8


class ConnectorOverride(typing.NamedTuple):
    Output_Enable: int
    Output_Data: int
    Enable_Mask: int


class SlaveCaptureDataInterface(typing.NamedTuple):
    reset_data: bool
    capture_data: bool
    store_data: bool
    capture_header: bool


class WorldControllerState(Enum):
    Idle = 0
    WaitForReady = 1
    Address = 2
    Data = 3
    Waiting = 4


class DataArray(typing.NamedTuple):
    val0: int
    val1: int
    val2: int
    val3: int
    val4: int
    val5: int
    val6: int
    val7: int


class I2CHeaderWord(typing.NamedTuple):
    Address: int
    Read: bool
    Valid: bool


class I2CInterface(typing.NamedTuple):
    Clock: bool
    Data: bool


class ReadData(typing.NamedTuple):  # AllConnector Data
    Connector0: int
    Connector1: int
    Connector2: int
    Connector3: int


class I2CBusOutputEnableAndData(typing.NamedTuple):
    SDA_Output_Data: bool
    SDA_Output_Enable: bool
    SCL_Output_Data: bool
    SCL_Output_Enable: bool


class I2CMaster(Enum):
    I2C_3V3_7822_SINK = 0
    I2C_3V3_7822_LINT = 1
    DIB_I2C = 2
    I2C_3V3_7822_TLOAD = 3


class BoardType(Enum):
    PXIe_7822R = 0
    PXIe_7821R = 1
    PXIe_7820R = 2  # TODO Does order matters?


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


class Connectors(Enum):
    Connector0 = 0
    Connector1 = 1
    Connector2 = 2
    Connector3 = 3
    Con_None = 4


class StaticStates(Enum):
    Zero = 0
    One = 1
    X = 2


class States(Enum):  # DIO Line State with I2C
    Zero = 0
    One = 1
    X = 2
    I2C = 3


class LineLocation(typing.NamedTuple):  # Channel
    channel: DIOLines
    connector: Connectors
    '''
    def __init__(self, channel: DIOLines, connector: Connectors):
        self.channel = channel
        self.connector = connector
        '''


class DIOLineLocationandStaticState(typing.NamedTuple):  # Channel
    channel: DIOLines
    connector: Connectors
    state: StaticStates


class LineLocationandStates(typing.NamedTuple):  # Channel
    channel: DIOLines
    connector: Connectors
    state: States


class DIOLineLocationandReadState(typing.NamedTuple):  # Channel
    channel: DIOLines
    connector: Connectors
    state: bool


class I2CMasterLineConfiguration(typing.NamedTuple):  # I2C Channel Mapping
    SDA: LineLocation
    SCL: LineLocation


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


class _SSCFPGA(typing.NamedTuple):
    Session: nifpga.Session
    ChannelGroupID: str
    Channels: str
    ChannelList: str

    def ss_wr_static_array(self, static_states: typing.List[StaticStates]):
        ch_list = self.ChannelList.split(",")
        iq_list = []
        r_list = []
        for ch in ch_list[0]:
            iq_list.append(int(ch) // 32)
            r_list.append(int(ch) % 32)
        lines_to_write = []
        for s_s, iq, r in zip(static_states, iq_list, r_list):
            element = DIOLineLocationandStaticState(DIOLines(r), Connectors(iq), s_s)
            lines_to_write.append(element)
        self.write_multiple_dio_lines(lines_to_write)

    def ss_wr_static(self, static_states: typing.List[StaticStates]):
        ch_list = self.Channels.split(",")
        iq_list = []
        r_list = []
        for ch in ch_list:
            iq_list.append(int(ch) // 32)
            r_list.append(int(ch) % 32)
        lines_to_write = []
        for s_s, iq, r in zip(static_states, iq_list, r_list):
            element = DIOLineLocationandStaticState(DIOLines(r), Connectors(iq), s_s)
            lines_to_write.append(element)
        self.write_multiple_dio_lines(lines_to_write)
        # TODO Check difference with ss_wr_static_array

    def ss_read_static(self):
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
        Closes the reference to the FPGA session and, optionally, resets execution of the session. By default,
        the Close FPGA session Reference function closes the reference to the FPGA session and resets the FPGA session.
        To configure this function only to close the reference, change the value of the argument when calling the
        function. The Close FPGA session reference function also stops all DMA FIFOs on the FPGA.
        """
        self.Session.close(reset_if_last_session)

    def w_master_lc(self, control_label: str, cluster: I2CMasterLineConfiguration):
        control = self.Session.registers[control_label]
        sda = collections.OrderedDict()
        sda['Channel'] = cluster.SDA.channel.value
        sda['Connector'] = cluster.SDA.connector.value
        scl = collections.OrderedDict()
        scl['Channel'] = cluster.SCL.channel.value
        scl['Connector'] = cluster.SCL.connector.value
        data = collections.OrderedDict()
        data['SDA'] = sda
        data['SCL'] = scl
        control.write(data)

    def configure_master_sda_scl_lines(self,
                                       i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                       sda_channel: LineLocation = LineLocation(DIOLines.DIO0, Connectors.Connector0),
                                       scl_channel: LineLocation = LineLocation(DIOLines.DIO0, Connectors.Connector0)
                                       ):
        """"""
        cluster = I2CMasterLineConfiguration(sda_channel, scl_channel)
        if 0 <= i2c_master_in.value <= 3:
            control = 'I2C Master%d Line Configuration' % i2c_master_in.value
            self.w_master_lc(control, cluster)
        else:
            print("Requested I2C_master is not defined")
            raise Exception

    def configure_i2c_master_settings(self,
                                      i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                      divide: int = 8,
                                      ten_bit_addressing: bool = False,
                                      clock_stretching: bool = True
                                      ):
        """"""
        # cluster = WorldControllerSetting(divide=divide, ten_bit_addressing=ten_bit_addressing)
        if 0 <= i2c_master_in.value <= 3:
            master = self.Session.registers['I2C Master%d Configuration' % i2c_master_in.value]
            clock = self.Session.registers['I2C Master%d Enable Clock Stretching?' % i2c_master_in.value]
            cluster = master.read()
            cluster['10-bit Addressing'] = ten_bit_addressing
            cluster['Divide'] = divide
            clock.write(clock_stretching)
            master.write(cluster)  # without all info?
        else:
            print("Requested I2C_master is not defined")
            raise Exception

    def i2c_master_poll_until_ready(self,
                                    i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                                    start_time: float = 0.0,
                                    timeout: float = 0.0
                                    ):
        """"""

        if timeout == 0:
            timeout = start_time
        if 0 <= i2c_master_in.value <= 3:
            master_ready = self.Session.registers['I2C Master%d ready for input' % i2c_master_in.value]
        else:
            print("Requested I2C_master is not defined")
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
            raise nifpga.ErrorStatus(5000,
                                     ("I2C %s not ready for input" % i2c_master_in.name),
                                     "i2c_master_poll_until_ready()",
                                     ["i2c_master", "timeout"],
                                     (i2c_master_in, timeout))

    def i2c_master_read(self,
                        i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
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
        if 0 <= i2c_master_in.value <= 3:
            master_config = self.Session.registers['I2C Master%d Configuration' % i2c_master_in.value]
            master_go = self.Session.registers['I2C Master%d Go' % i2c_master_in.value]
            master_data = self.Session.registers['I2C Master%d Read Data' % i2c_master_in.value]
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        # config: WorldControllerSetting
        config = master_config.read()

        '''
        config.Device_Address = device_address
        config.Number_of_Bytes = number_of_bytes
        config.Read = True
        '''
        config['Device Address'] = device_address
        config['Number of Bytes'] = number_of_bytes
        config['Read'] = True
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
        master_config.write(config)
        master_go.write(True)
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
        data = master_data.read()
        data = data[0:number_of_bytes+1]
        return data

    def i2c_master_write(self,
                         i2c_master_in: I2CMaster = I2CMaster.I2C_3V3_7822_SINK,
                         timeout: float = 1,
                         device_address: int = 0,
                         data_to_write: typing.List[int] = []):
        start_time = time()
        if 0 <= i2c_master_in.value <= 3:
            master_config = self.Session.registers['I2C Master%d Configuration' % i2c_master_in.value]
            master_go = self.Session.registers['I2C Master%d Go' % i2c_master_in.value]
            master_data = self.Session.registers['I2C Master%d Write Data' % i2c_master_in.value]
        else:
            print("Requested I2C_master is not defined")
            raise Exception
        master_read: WorldControllerSetting
        master_read = master_config.read()
        master_read.Device_Address = device_address
        master_read.Number_of_Bytes = len(data_to_write)
        master_read.Read = False
        self.i2c_master_poll_until_ready(i2c_master_in, start_time, timeout)
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

    def read_multiple_dio_commanded_states(self, lines_to_read: typing.List[LineLocation]):
        out_list = []
        config_list = []
        for i in range(4):
            connector_enable = self.Session.registers["Connector%d Output Enable" % i]
            connector_data = self.Session.registers["Connector%d Output Data" % i]
            merge = (connector_enable.read(), connector_data.read())
            out_list.append(merge)
            master = self.Session.registers["I2C Master%d Line Configuration" % i]
            master_data = master.read()
            sda = master_data['SDA']
            scl = master_data['SCL']
            line_sda = LineLocation(sda['Channel'], sda['Connector'])
            line_scl = LineLocation(scl['Channel'], scl['Connector'])
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
            state = LineLocationandStates(line, connector, line_state)
            states_list.append(state)
        return states_list

    def read_multiple_lines(self, lines_to_read: typing.List[LineLocation]):
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
            state = DIOLineLocationandReadState(line, connector, line_state)
            readings.append(state)
        return readings

    def read_single_connector(self, connector: Connectors):
        data: int = 0
        if 0 <= connector.value <= 3:
            read_control = self.Session.registers["Connector%d Read Data" % connector.value]
            data = read_control.read()
        return data

    def read_single_dio_line(self, connector: Connectors = Connectors.Connector0, line: DIOLines = DIOLines.DIO0):
        data = self.read_single_connector(connector)
        state_list = list("{:032b}".format(data, "b"))[::-1]
        line_state = state_list[line.value]
        return line_state

    def write_multiple_dio_lines(self, lines_to_write: typing.List[DIOLineLocationandStaticState]):
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
                self.write_single_dio_line(lines.connector, lines.channel, lines.state)

    def write_single_dio_line(self,
                              connector: Connectors = Connectors.Connector0,
                              line: DIOLines = DIOLines.DIO0,
                              state: StaticStates = StaticStates.Zero):
        if 0 <= connector.value <= 3:
            con_enable = self.Session.registers['Connector%d Output Enable' % connector.value]
            con_data = self.Session.registers['Connector%d Output Data' % connector.value]
            enable, data = update_line_on_connector(con_enable.read(), con_data.read(), line, state)
            con_enable.write(enable)
            con_data.write(data)


class TSMFPGA(typing.NamedTuple):
    pin_query_context: Any
    SSC: typing.List[_SSCFPGA]
    site_numbers: typing.List[int]

    def configure_i2c_bus(self,
                          tenb_addresing: bool = False,
                          divide: int = 8,
                          clock_stretching: bool = True):
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        session.configure_i2c_master_settings(i2c, divide, tenb_addresing, clock_stretching)

    def read_i2c_data(self,
                      timeout: float = 1,
                      slave_address: int = 0,
                      number_of_bytes: int = 1):
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        i2c_read_data = session.i2c_master_read(i2c, slave_address, timeout, number_of_bytes)
        return i2c_read_data

    def write_i2c_data(self,
                       data_to_write: typing.List[int],
                       timeout: float = 1,
                       slave_address: int = 0):
        session: _SSCFPGA
        session, i2c = self.extract_i2c_master_from_sessions()
        session.i2c_master_write(i2c, timeout, slave_address, data_to_write)

    def extract_i2c_master_from_sessions(self):
        session = self.SSC[0]  # .Session
        ch_list = self.SSC[0].ChannelList
        sites_and_pins, sites, pins = channel_list_to_pins(ch_list)
        sites_and_pins.clear()
        sites.clear()
        scan = ''
        for i2c in I2CMaster:
            if i2c.name in pins[0]:
                scan = i2c
        if type(scan) != I2CMaster:
            raise nifpga.ErrorStatus(5000,
                                     "Invalid I2C Master Session Provided",
                                     "extract_i2c_master_from_sessions",
                                     ["self"],
                                     self)
        return session, scan

    def read_commanded_line_states(self):
        commanded_states = []
        current_commanded_states = []
        data = ()
        for ss in self.SSC:
            data = ss.ss_read_c_states()
        current_commanded_states.append(data[0])
        commanded_states += data[1]
        return current_commanded_states, commanded_states

    def read_static(self):
        readings = []
        line_states = []
        for ss in self.SSC:
            data = ss.ss_read_static()
            readings.append(data[0])
            line_states.append(data[0])
        return readings, line_states

    def write_static_array(self, static_state: typing.List[StaticStates]):
        for ss in self.SSC:
            ss.ss_wr_static_array(static_state)

    def write_static(self, static_state: typing.List[StaticStates]):
        print('SS:', self)
        for ss in self.SSC:
            ss.ss_wr_static(static_state)


def override_connector_data(static_data: int, override_enable: int, override_data: int):
    connector_data = (static_data & (not override_enable)) | (override_enable & override_data)
    return connector_data


def map_out_to_connector(out_data: bool, out_enable: bool, channel: DIOLines):
    ch_id = channel.value
    data = ['0'] * 32
    enable = ['0'] * 32
    mask = ['0'] * 32
    data[ch_id] = str(int(out_data))
    enable[ch_id] = str(int(out_enable))
    mask[ch_id] = '1'
    data = int(''.join(data), 2)
    enable = int(''.join(enable), 2)
    mask = int(''.join(mask), 2)
    connector_overrides = ConnectorOverride(enable, data, mask)
    return connector_overrides


def out_data_to_connector_1_interface(bus: I2CBusOutputEnableAndData, master_line_cnfg: I2CMasterLineConfiguration):
    map_sda = map_out_to_connector(bus.SDA_Output_Data, bus.SDA_Output_Enable, master_line_cnfg.SDA.channel)
    map_scl = map_out_to_connector(bus.SCL_Output_Data, bus.SCL_Output_Enable, master_line_cnfg.SCL.channel)
    sda = [ConnectorOverride(0, 0, 0)] * 4
    scl = [ConnectorOverride(0, 0, 0)] * 4
    if master_line_cnfg.SDA.connector.value < 4:
        sda[master_line_cnfg.SDA.connector.value] = map_sda
    if master_line_cnfg.SCL.connector.value < 4:
        scl[master_line_cnfg.SCL.connector.value] = map_scl
    connector_data = []
    for con in range(4):
        enable = sda[con].Output_Enable | sda[con].Output_Enable
        data = sda[con].Output_Data | sda[con].Output_Data
        mask = sda[con].Enable_Mask | sda[con].Enable_Mask
        connector_data.append(ConnectorOverride(enable, data, mask))
    return connector_data


def out_data_to_connector_4_interfaces(bus0: I2CBusOutputEnableAndData,
                                       bus1: I2CBusOutputEnableAndData,
                                       bus2: I2CBusOutputEnableAndData,
                                       bus3: I2CBusOutputEnableAndData,
                                       mstr0_ln_cnfg: I2CMasterLineConfiguration,
                                       mstr1_ln_cnfg: I2CMasterLineConfiguration,
                                       mstr2_ln_cnfg: I2CMasterLineConfiguration,
                                       mstr3_ln_cnfg: I2CMasterLineConfiguration):
    map0 = out_data_to_connector_1_interface(bus0, mstr0_ln_cnfg)
    map1 = out_data_to_connector_1_interface(bus1, mstr1_ln_cnfg)
    map2 = out_data_to_connector_1_interface(bus2, mstr2_ln_cnfg)
    map3 = out_data_to_connector_1_interface(bus3, mstr3_ln_cnfg)
    connector_data = []
    for con in range(4):
        enable = map0[con].Output_Enable | map1[con].Output_Enable | map2[con].Output_Enable | map3[con].Output_Enable
        data = map0[con].Output_Data | map1[con].Output_Data | map2[con].Output_Data | map3[con].Output_Data
        mask = map0[con].Enable_Mask | map1[con].Enable_Mask | map2[con].Enable_Mask | map3[con].Enable_Mask
        connector_data.append(ConnectorOverride(enable, data, mask))
    return connector_data


def i2c_bus_to_out_enable_and_data(bus: I2CInterface, enable_clk_stretch: bool):
    bus_out = I2CBusOutputEnableAndData(False,
                                        not bus.Data,
                                        bus.Clock and (not enable_clk_stretch),
                                        not (enable_clk_stretch and bus.Clock))
    return bus_out


def extract_data_from_connector(con_rd_data: int, sda_ch: DIOLines, scl_ch: DIOLines):
    con_rd_data = list("{:032b}".format(con_rd_data, "b"))[::-1]
    bus_out = I2CInterface(con_rd_data[scl_ch.value], con_rd_data[sda_ch.value])
    return bus_out


def extract_data_from_connectors(con0_bus: I2CInterface,
                                 con1_bus: I2CInterface,
                                 con2_bus: I2CInterface,
                                 con3_bus: I2CInterface,
                                 sda_con: Connectors,
                                 scl_con: Connectors):
    con_data = [con0_bus, con1_bus, con2_bus, con3_bus]
    clock = data = False
    if sda_con.value < 4:
        clock = con_data[sda_con.value]
    if scl_con.value < 4:
        data = con_data[sda_con.value]
    bus_out = I2CInterface(clock, data)
    return bus_out


def extract_i2c_data_1_interface(cn0_rd_data: int,
                                 cn1_rd_data: int,
                                 cn2_rd_data: int,
                                 cn3_rd_data: int,
                                 mstr_ln_cnfg: I2CMasterLineConfiguration):
    cn0 = extract_data_from_connector(cn0_rd_data, mstr_ln_cnfg.SDA.channel, mstr_ln_cnfg.SCL.channel)
    cn1 = extract_data_from_connector(cn1_rd_data, mstr_ln_cnfg.SDA.channel, mstr_ln_cnfg.SCL.channel)
    cn2 = extract_data_from_connector(cn2_rd_data, mstr_ln_cnfg.SDA.channel, mstr_ln_cnfg.SCL.channel)
    cn3 = extract_data_from_connector(cn3_rd_data, mstr_ln_cnfg.SDA.channel, mstr_ln_cnfg.SCL.channel)
    bus_out = extract_data_from_connectors(cn0, cn1, cn2, cn3, mstr_ln_cnfg.SDA.connector, mstr_ln_cnfg.SCL.connector)
    return bus_out


def extract_i2c_data_4_interfaces(cn0_rd_data: int,
                                  cn1_rd_data: int,
                                  cn2_rd_data: int,
                                  cn3_rd_data: int,
                                  mstr0_ln_cnfg: I2CMasterLineConfiguration,
                                  mstr1_ln_cnfg: I2CMasterLineConfiguration,
                                  mstr2_ln_cnfg: I2CMasterLineConfiguration,
                                  mstr3_ln_cnfg: I2CMasterLineConfiguration):
    bus0 = extract_i2c_data_1_interface(cn0_rd_data, cn1_rd_data, cn2_rd_data, cn3_rd_data, mstr0_ln_cnfg)
    bus1 = extract_i2c_data_1_interface(cn0_rd_data, cn1_rd_data, cn2_rd_data, cn3_rd_data, mstr1_ln_cnfg)
    bus2 = extract_i2c_data_1_interface(cn0_rd_data, cn1_rd_data, cn2_rd_data, cn3_rd_data, mstr2_ln_cnfg)
    bus3 = extract_i2c_data_1_interface(cn0_rd_data, cn1_rd_data, cn2_rd_data, cn3_rd_data, mstr3_ln_cnfg)
    return bus0, bus1, bus2, bus3


bus_input = None


def simple_register(bus_in: int, bus_wr_strobe: bool, bus_addr: int, reg_addr: int):
    global bus_input
    if (bus_input is None) or (bus_addr == reg_addr) and bus_wr_strobe:
        bus_input = bus_in
    bus_out = 0
    if bus_addr == reg_addr:
        bus_out = bus_input
    return bus_input, bus_out


def create_header(ten_bit_address: bool, address: int, read: bool):
    bin_address = "{:016b}".format(address, "b")
    addr1 = int(bin_address[8:16], 2)  # LO
    addr0 = int(bin_address[0:8], 2)  # HI
    if ten_bit_address:
        addr0 = (addr0 & 3) | 120
    else:
        addr0 = addr1
    addr0 = (addr0 << 1) | int(read)
    return addr0, addr1


def parse_header(header_word: I2CHeaderWord, data_in: int, ten_bit_addr_ack: bool):
    data_in = data_in % 256  # limited to U8
    ten_bit_addr_detected = (data_in & 248) == 240
    valid_out = (not ten_bit_addr_ack) and ten_bit_addr_detected
    if ten_bit_addr_ack:
        address_out = (header_word.Address << 8) | data_in
        read_out = header_word.Read
    else:
        read_out = bool(data_in % 2)
        address_out = data_in >> 1
        if valid_out:
            address_out = address_out & 3
    valid_out = not valid_out
    return I2CHeaderWord(address_out, read_out, valid_out), ten_bit_addr_detected


capture_header_reg = hd_enable_reg = rd_data_shft_reg = False
in_data_reg = 0
rd_data_reg = [0]*8


def data_and_header_capture(header_word_in: I2CHeaderWord,
                            i2c_input: I2CInterface,
                            control_interface: SlaveCaptureDataInterface,
                            index: int,
                            ten_bit_addr_ack: bool):
    global capture_header_reg, in_data_reg, hd_enable_reg, rd_data_shft_reg, rd_data_reg
    reset = control_interface.reset_data
    capture_d = control_interface.capture_data
    store = control_interface.store_data
    ack_request = rd_data_shft_reg or hd_enable_reg  #
    read_data_shifted = rd_data_shft_reg  #
    read_data = rd_data_reg  #
    header_enable = capture_header_reg or reset  #
    header_word_out, ten_bit_addr_detected = parse_header(header_word_in, index, ten_bit_addr_ack)  #
    if reset:
        header_word_out = I2CHeaderWord(0, False, False)
        in_data_temp = 0
        rd_data_temp = [0]*8
    else:
        in_data_temp = in_data_reg
        if capture_d:
            in_data_temp = int(i2c_input.Data) | (in_data_reg << 1)
        rd_data_temp = rd_data_reg[:]
        rd_data_temp[index] = in_data_reg
    rd_data_updt = reset or store
    hd_enable_reg = header_enable
    capture_header_reg = control_interface.capture_header
    rd_data_shft_reg = store
    if rd_data_updt:
        rd_data_reg = rd_data_temp
    in_data_reg = in_data_temp
    return read_data, read_data_shifted, ack_request, header_enable, header_word_out, ten_bit_addr_detected


input_reg = I2CInterface(False, False)
clk_md_reg = data_md_reg = 0
clk_reg = data_reg = False


def filter_input(filter_delay: int, input_interface: I2CInterface):
    global input_reg, clk_md_reg, data_md_reg, clk_reg, data_reg
    clock_in = input_reg.Clock == input_interface.Clock
    if clock_in:
        clk_md_temp = clk_md_reg
        if filter_delay != clk_md_reg:
            clk_md_temp += 1
    else:
        clk_md_temp = 0
    if clk_md_temp == filter_delay:
        clk_temp = input_interface.Clock
    else:
        clk_temp = clk_reg
    data_in = input_reg.Data == input_interface.Data
    if data_in:
        data_md_temp = data_md_reg
        if filter_delay != data_md_reg:
            data_md_temp += 1
    else:
        data_md_temp = 0
    if data_md_temp == filter_delay:
        data_temp = input_interface.Data
    else:
        data_temp = data_reg
    output = I2CInterface(clk_temp, data_temp)
    clk_reg = clk_temp
    data_reg = data_temp
    clk_md_reg = clk_md_temp
    data_md_reg = data_md_temp
    input_reg = input_interface
    return output


transfer_settings_reg = I2CTransferSettings(False, 0, False)
write_data_reg = I2CDataType(0, False, False)
master_value_reg = 0
match_divide_reg = False
master_state_reg = MasterState.Idle
state_counter_reg = 0
state_condition_reg = False
condition_md1_reg = False
condition_md2_reg = False
valid_reg = False
data_pre_reg = 0


def byte_controller(data_in: I2CInterface,
                    transfer_settings: I2CTransferSettings,
                    write_data: I2CDataType,
                    abort: bool,
                    direction_ready: bool):
    global transfer_settings_reg,\
        write_data_reg,\
        master_value_reg,\
        match_divide_reg,\
        master_state_reg,\
        state_counter_reg,\
        state_condition_reg,\
        condition_md1_reg,\
        condition_md2_reg,\
        valid_reg,\
        data_pre_reg
    valid = valid_reg
    data = data_pre_reg >> 1
    ack = transfer_settings_reg.Read or (data_pre_reg & 1 == 0)
    read_data = I2CDataType(data, ack, valid)  # 2nd out
    write_data_temp = write_data if write_data.Valid else write_data_reg
    transfer_setting_temp = transfer_settings if write_data.Valid else transfer_settings_reg
    if master_state_reg == MasterState.Idle:
        out1 = direction_ready
        out2 = write_data.Valid
        out3 = False
        out4 = MasterState.SendStartCondition if write_data.Valid else MasterState.Idle
        out5 = True
        out6 = False
        out7 = not write_data.Valid
        out8 = 9
    elif master_state_reg == MasterState.SendStartCondition:
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.SendData if match_divide_reg else MasterState.SendStartCondition
        out5 = not match_divide_reg
        out6 = False
        out7 = False
        out8 = state_counter_reg
    elif master_state_reg == MasterState.SendData:
        if transfer_settings_reg.Read:
            release_sda = not write_data_reg.ACK
            data_index = '11111111'
        else:
            release_sda = True
            data_index = "{:08b}".format(write_data_reg.Data, "b")
        word = '1' + str(int(release_sda)) + data_index
        word_list = []
        word_list[:0] = word
        ack_data = word_list[state_counter_reg]
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.SendRisingClock if match_divide_reg else MasterState.SendData
        out5 = False
        out6 = False
        out7 = ack_data if match_divide_reg else state_condition_reg
        out8 = state_counter_reg-1 if match_divide_reg else state_counter_reg
    elif master_state_reg == MasterState.SendRisingClock:
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.SendFallingClock if match_divide_reg else MasterState.SendRisingClock
        out5 = False
        out6 = False
        out7 = False
        out8 = state_counter_reg
    elif master_state_reg == MasterState.SendFallingClock:
        out1 = False
        out2 = False
        out3 = match_divide_reg
        temp_stat = MasterState.StopConditionSetUp if transfer_settings_reg.SendStopCondition else MasterState.Waiting
        temp_stat = temp_stat if state_counter_reg == 0 else MasterState.SendData
        out4 = temp_stat if match_divide_reg else MasterState.SendFallingClock
        out5 = not match_divide_reg
        out6 = state_counter_reg == 0
        out7 = state_condition_reg
        out8 = state_counter_reg
    elif master_state_reg == MasterState.Waiting:
        out1 = direction_ready
        out2 = write_data.Valid
        out3 = False
        temp_state = MasterState.SendData if write_data.Valid else MasterState.Waiting
        out4 = MasterState.StopConditionSetUp if abort else temp_state
        out5 = False
        out6 = False
        out7 = state_condition_reg
        out8 = 9
    elif master_state_reg == MasterState.ReleaseClock:
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.ReleaseData if match_divide_reg else MasterState.ReleaseClock
        out5 = match_divide_reg
        out6 = False
        out7 = False
        out8 = state_counter_reg
    elif master_state_reg == MasterState.ReleaseData:
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.Idle if match_divide_reg else MasterState.ReleaseData
        out5 = True
        out6 = False
        out7 = match_divide_reg
        out8 = state_counter_reg
    elif master_state_reg == MasterState.StopConditionSetUp:
        out1 = False
        out2 = False
        out3 = False
        out4 = MasterState.ReleaseClock if match_divide_reg else MasterState.StopConditionSetUp
        out5 = False
        out6 = False
        out7 = False if match_divide_reg else state_condition_reg
        out8 = state_counter_reg
    else:
        out1 = False
        out2 = False
        out3 = False
        out4 = 0
        out5 = False
        out6 = False
        out7 = False
        out8 = 0
    match_divide_reg = transfer_settings_reg.Divide == master_value_reg
    if (master_state_reg.value != MasterState.Idle.value) and direction_ready:
        master_value_reg = 0 if (match_divide_reg or out2) else master_value_reg+1
    master_state_reg = out4
    state_condition_reg = out7
    state_counter_reg = out8
    valid_reg = condition_md2_reg
    data_pre_reg = int(data_in.Data) | (data_pre_reg << 1)
    condition_md1_reg = out3
    condition_md2_reg = out3 and out6
    data_out = I2CInterface(out5, out7)
    ready = out1
    write_data_reg = write_data_temp
    transfer_settings_reg = transfer_setting_temp
    return ready, read_data, data_out


go_reg = True
i2c_master_state_reg = WorldControllerState.Idle
i2c_master_valid_reg = False
i2c_ready_reg = False
i2c_value_reg = 0
i2c_master_ack_reg = False
cond_md1_reg = False
cond_md2_reg = False
rd_master_data_reg = 0
rd_master_data_list_reg: typing.List[int] = [0]*8


def i2c_master(i2c_bus_in: I2CInterface,
               direction_ready: bool,
               settings: WorldControllerSetting,
               write_data: typing.List[int],
               go: bool):
    global go_reg, i2c_master_state_reg, i2c_master_valid_reg, i2c_ready_reg, i2c_value_reg, i2c_master_ack_reg,\
        cond_md1_reg, cond_md2_reg, rd_master_data_reg, rd_master_data_list_reg
    in1, in2 = create_header(settings.Ten_Bit_Addressing, settings.Device_Address, settings.Read)
    if i2c_master_state_reg == WorldControllerState.Idle:
        out2 = (settings.Number_of_Bytes == 0) and (go and not go_reg)
        out1 = not out2
        out3 = 0
        out4 = False
        out5 = WorldControllerState.WaitForReady if out2 else WorldControllerState.Idle
        out6 = False
        out7 = False
        out8 = False
        out9 = False
        out10 = 0
    elif i2c_master_state_reg == WorldControllerState.WaitForReady:
        out1 = False
        out2 = False
        out3 = in1
        out4 = False
        out5 = WorldControllerState.Address if i2c_ready_reg else WorldControllerState.WaitForReady
        out6 = i2c_ready_reg
        out7 = False
        out8 = False
        out9 = False
        out10 = 0
    elif i2c_master_state_reg == WorldControllerState.Address:
        out1 = False
        out2 = False
        out3 = in2 if settings.Ten_Bit_Addressing else write_data[i2c_value_reg]
        temp1 = (not settings.Ten_Bit_Addressing) and settings.Read
        t2 = settings.Number_of_Bytes <= 1
        out4 = temp1 and not t2
        out6 = i2c_master_valid_reg and i2c_master_ack_reg
        out7 = temp1
        out8 = t2 and not settings.Ten_Bit_Addressing
        out9 = i2c_master_valid_reg and not i2c_master_ack_reg
        out10 = int(i2c_master_valid_reg and not settings.Ten_Bit_Addressing)
        temp_status = WorldControllerState.Waiting if out8 else WorldControllerState.Data
        temp_status = WorldControllerState.Idle if out9 else temp_status
        out5 = temp_status if i2c_master_valid_reg else WorldControllerState.Address
    elif i2c_master_state_reg == WorldControllerState.Data:
        out1 = False
        out2 = False
        out3 = write_data[i2c_value_reg]
        temp1 = (settings.Number_of_Bytes == (i2c_value_reg+1))
        out4 = settings.Read and not temp1
        t2 = i2c_master_valid_reg and not i2c_master_ack_reg
        t3 = i2c_master_valid_reg and temp1
        out5 = WorldControllerState.Idle if t2 else WorldControllerState.Waiting if t3 else WorldControllerState.Data
        out6 = i2c_master_valid_reg and i2c_master_ack_reg
        out7 = settings.Read
        out8 = temp1
        out9 = t2
        out10 = i2c_value_reg+1 if out6 else i2c_value_reg
    elif i2c_master_state_reg == WorldControllerState.Waiting:
        out1 = False
        out2 = False
        out3 = 0
        out4 = False
        out5 = WorldControllerState.Idle if i2c_master_valid_reg else WorldControllerState.Waiting
        out6 = False
        out7 = False
        out8 = False
        out9 = False
        out10 = i2c_value_reg
    else:
        out1 = False
        out2 = False
        out3 = 0
        out4 = False
        out5 = WorldControllerState.Idle
        out6 = False
        out7 = False
        out8 = False
        out9 = False
        out10 = 0
    read_data = rd_master_data_list_reg
    ready_for_input = out1
    transfer_set = I2CTransferSettings(out8, settings.Divide, out7)
    write_data_out = I2CDataType(out3, out4, out6)
    i2c_bus_out, data, i2c_ready_temp =\
        byte_controller(i2c_bus_in, transfer_set, write_data_out, out9, direction_ready)
    read_data[rd_master_data_reg] = data.Data
    temp2 = data.Valid and (cond_md2_reg if settings.Ten_Bit_Addressing else cond_md1_reg)
    rd_master_data_list_reg = [0]*8 if out2 or temp2 else read_data
    rd_master_data_reg = 0 if out1 else rd_master_data_reg+1 if temp2 else rd_master_data_reg
    condition = data.Valid or out1
    cond_md2_reg = cond_md1_reg if condition else cond_md2_reg
    cond_md1_reg = not out1 if condition else cond_md1_reg
    i2c_master_ack_reg = data.ACK
    i2c_ready_reg = i2c_ready_temp
    i2c_master_valid_reg = data.Valid
    i2c_value_reg = out10
    i2c_master_state_reg = out5
    go_reg = go
    return i2c_bus_out, ready_for_input, read_data


filter_input_reg = I2CInterface(False, False)
ack_in_reg = False
slave_state_reg = I2CSlaveStates.WaitOnStartCondition
bit_counter_reg = 0
next_state_reg = 0
byte_counter_reg = 0
ten_bit_addr_reg = False
ten_bit_addr_detected_reg = False
ack_requested_reg = False
case_out_reg = False
data_header_reg = I2CHeaderWord(0, False, False)


def i2c_slave(i2c_input: I2CInterface, return_data: typing.List[int], filter_in: int, ack_in: bool):
    global filter_input_reg, ack_in_reg, slave_state_reg, bit_counter_reg, next_state_reg, byte_counter_reg,\
        ten_bit_addr_detected_reg, ack_requested_reg, case_out_reg, data_header_reg, ten_bit_addr_reg
    filtered_input = filter_input(filter_in, i2c_input)
    falling_edge = I2CInterface(filter_input_reg.Clock and not filtered_input.Clock,
                                filter_input_reg.Data and not filtered_input.Data)
    rising_edge = I2CInterface(filtered_input.Clock and not filter_input_reg.Clock,
                               filtered_input.Data and not filter_input_reg.Data)
    filter_input_reg = filtered_input
    in9 = rising_edge.Data and filter_input_reg.Clock  # STOP_CON
    in4 = falling_edge.Data and filter_input_reg.Clock  # start_con
    in1 = i2c_input
    in3 = ten_bit_addr_detected_reg
    in5 = ten_bit_addr_reg
    in6 = rising_edge.Clock
    in7 = byte_counter_reg
    in8 = falling_edge.Clock
    in10 = ack_in_reg
    ack_in_reg = ack_in
    in11 = next_state_reg
    in12 = data_header_reg
    in13 = bit_counter_reg
    in14 = bit_counter_reg-1
    in2 = list("{:08b}".format(return_data[in7], "b"))[in13]
    if slave_state_reg == I2CSlaveStates.WaitOnStartCondition:
        out1 = in4
        out2 = False
        out3 = False
        out4 = False
        out5 = True
        out6 = True
        out7 = 0
        out8 = 7
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = False
        out11 = I2CSlaveStates.Addressing if in4 else I2CSlaveStates.WaitOnStartCondition
    elif slave_state_reg == I2CSlaveStates.Addressing:
        out1 = False
        out2 = in5
        out3 = in6
        out4 = (in14 == 0) and in6
        out5 = True
        out6 = True
        out7 = 0
        out8 = 10 if out4 else in14 if out3 else in13
        out9 = 0
        out10 = False
        temp = I2CSlaveStates.AddressAck if out4 else I2CSlaveStates.Addressing
        out11 = I2CSlaveStates.WaitOnStartCondition if in9 else temp
    elif slave_state_reg == I2CSlaveStates.AddressAck:
        out1 = False
        temp = in3 and (not in5) and (in13 == 7)
        out2 = in5 or temp
        out3 = False
        out4 = False
        out5 = True
        temp2 = not (in3 or in10)
        if in13 == 7:
            out6 = in2 or temp2 or not in12.Read
        elif in13 == 8:
            out6 = temp2
        elif in13 == 9:
            out6 = temp2
        else:
            out6 = True
        out7 = 0
        out8 = 7 if temp else in14 if in6 or in8 else in13
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = False
        out11 = I2CSlaveStates.MasterReadingData if in12.Read else I2CSlaveStates.MasterWritingData
        out11 = I2CSlaveStates.WaitOnStartCondition if temp2 else out11
        out11 = I2CSlaveStates.Addressing if temp else out11
        out11 = out11 if in13 == 7 else I2CSlaveStates.AddressAck
    elif slave_state_reg == I2CSlaveStates.MasterReadingData:
        out1 = False
        out2 = False
        out3 = False
        out4 = False
        out5 = True
        out6 = in2
        out7 = in7
        out8 = in14 if in8 else in13
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = False
        temp = I2CSlaveStates.RetrieveAck if (in8 and (in13 == 0)) else I2CSlaveStates.MasterReadingData
        out11 = I2CSlaveStates.WaitOnStartCondition if in9 else temp
    elif slave_state_reg == I2CSlaveStates.RetrieveAck:
        out1 = False
        out2 = False
        out3 = False
        out4 = False
        out5 = True
        out6 = True
        out7 = in7+1 if in8 else in7
        out8 = 7
        temp = I2CSlaveStates.WaitOnStartCondition if in1.Data else I2CSlaveStates.MasterReadingData
        out9 = temp if in6 else in11
        out10 = False
        out11 = I2CSlaveStates.WaitOnStartCondition if in9 else (in11 if in8 else I2CSlaveStates.RetrieveAck)
    elif slave_state_reg == I2CSlaveStates.MasterWritingData:
        out1 = False
        out2 = False
        out3 = in6
        out4 = False
        out5 = True
        out6 = True
        out7 = in7
        temp = in6 and (in13 == 0)
        out8 = 3 if temp else in14 if in6 else in13
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = temp
        temp2 = I2CSlaveStates.SendAck if temp else I2CSlaveStates.MasterWritingData
        out11 = I2CSlaveStates.WaitOnStartCondition if in9 else temp2
    elif slave_state_reg == I2CSlaveStates.SendAck:
        out1 = False
        out2 = False
        out3 = False
        out4 = False
        out5 = True
        out6 = True if in13 == 0 else not in10 if in13 == 1 or in13 == 2 else True
        out7 = in7 + 1 if in13 == 0 else in7
        out8 = 7 if in13 == 0 else in14 if in6 or in8 else in13
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = False
        temp = I2CSlaveStates.MasterWritingData if in10 else I2CSlaveStates.WaitOnStartCondition
        temp = temp if in13 == 0 else I2CSlaveStates.SendAck
        out11 = I2CSlaveStates.WaitOnStartCondition if in9 else temp
    else:
        out1 = False
        out2 = False
        out3 = False
        out4 = False
        out5 = False
        out6 = False
        out7 = 0
        out8 = 0
        out9 = I2CSlaveStates.WaitOnStartCondition
        out10 = False
        out11 = I2CSlaveStates.WaitOnStartCondition
    slave_state_reg = out11
    bit_counter_reg = out8
    next_state_reg = out9
    byte_counter_reg = out7
    ten_bit_addr_reg = out2
    temp = SlaveCaptureDataInterface(out1, out3, case_out_reg, out4)
    read_data, read_data_shifted, ack_requested, header_enable, header_word, ten_bit_addr_detect =\
        data_and_header_capture(data_header_reg, i2c_input, temp, in7, out2)
    case_out_reg = out10
    header = data_header_reg
    data_header_reg = header_word if header_enable else data_header_reg
    ten_bit_addr_detected_reg = ten_bit_addr_detect
    ack_requested_reg = ack_requested
    i2c_output = I2CInterface(out5, out6)
    return read_data, read_data_shifted, ack_requested, i2c_output, header


def join_numbers_8bit(hi_in: int, lo_in: int):
    hi = "{:08b}".format(hi_in, "b")
    lo = "{:08b}".format(lo_in, "b")
    return int(hi + lo, 2)


def join_numbers_16bit(hi_in: int, lo_in: int):
    hi = "{:16b}".format(hi_in, "b")
    lo = "{:16b}".format(lo_in, "b")
    return int(hi + lo, 2)


def split_number_32_to_8(num: int):
    num = "{:32b}".format(num, "b")
    hi_hi = int(num[16:32], 2)
    hi_lo = int(num[16:24], 2)
    lo_hi = int(num[8:16], 2)
    lo_lo = int(num[0:8], 2)
    return [hi_hi, hi_lo, lo_hi, lo_lo]


reg_1 = 0
reg_2 = 0


def user_logic(ack_in: bool, device_addr: int, header: I2CHeaderWord, read_data_shft: bool, data_in: typing.List[int]):
    global reg_1, reg_2
    temp = (reg_1 != 4) if read_data_shft else (device_addr == header.Address)
    ack_out = ack_in and temp
    temp = reg_2 if header.Read else data_in[0]
    temp2 = reg_1 == 5
    reg_1 = 0 if temp2 or not header.Valid else reg_1+1 if read_data_shft else reg_1
    reg_2 = data_in[1] if data_in[0] == 0 else reg_2
    num = join_numbers_8bit(join_numbers_8bit(data_in[1], data_in[2]), join_numbers_8bit(data_in[3], data_in[4]))
    simp_reg_1 = simple_register(int("12345678", 16), True, temp, 1)
    simp_reg_2 = simple_register(num, temp2 and not header.Read, temp, 129)
    simp_reg = simp_reg_1[1] | simp_reg_2[1]
    data_out = split_number_32_to_8(simp_reg)
    return ack_out, data_out


def read_and_write_port(port_resourse: str, output_data: int, output_en: int):
    print(port_resourse, output_data, output_en)
    # write_port(port_resourse, output_data, output_en)
    read_data = read_port(port_resourse)
    return read_data


def read_port(port_resourse: str):
    print(port_resourse)
    read_data = 0  # TODO set IO item
    return read_data


def read_connector(resources: ConnectorResources):
    p0 = read_port(resources.Port0)
    p1 = read_port(resources.Port1)
    p2 = read_port(resources.Port2)
    p3 = read_port(resources.Port3)
    p10 = join_numbers_8bit(p1, p0)
    p32 = join_numbers_8bit(p3, p2)
    return join_numbers_16bit(p32, p10)


def write_connector(resources: ConnectorResources, out_data: int, out_enable: int):
    data = split_number_32_to_8(out_data)
    enable = split_number_32_to_8(out_enable)
    print(resources, data, enable)
    # write_port(resources.Port3, data[3], enable[3])
    # write_port(resources.Port2, data[2], enable[2])
    # write_port(resources.Port1, data[1], enable[1])
    # write_port(resources.Port0, data[0], enable[0])


def debug_ui_launcher(semiconductor_module_manager: nitsm.codemoduleapi.SemiconductorModuleContext):
    # TODO missing Type?
    print(semiconductor_module_manager)
    pass


def search_line(line: LineLocation, ch_list: typing.List[LineLocation]):
    index = 0
    for element in ch_list:
        if element.channel == line.channel and element.connector == line.connector:
            return index
        else:
            index += 1
    return -1


def update_line_on_connector(enable_in: int = 0,
                             data_in: int = 0,
                             dio_line: DIOLines = DIOLines.DIO0,
                             line_state: StaticStates = StaticStates.Zero):
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
    ch_list = channel_list.split(",")
    sites_and_pins = []
    sites = []
    pins = []
    for ch in ch_list:
        ch = ch.lstrip()
        sites_and_pins.append(ch)
        ch_l = ch.replace('/', '\\').split('\\')
        if '\\' in ch or '/' in ch:
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


def close_sessions(tsm_context: TSMContext):
    # session_data, channel_group_ids, channel_lists = tsm_context.get_all_custom_sessions(InstrumentTypeId)
    session_data, _, _ = tsm_context.get_all_custom_sessions(InstrumentTypeId)
    for session in session_data:
        session.close()


def initialize_sessions(tsm_context: TSMContext, ldb_type: str = ''):
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(InstrumentTypeId)
    # when the output from a function is unused use _ instead of variables like below
    # instrument_names, channel_group_ids, _ = tsm_context.get_custom_instrument_names(InstrumentTypeId) 
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
    debug = tsm_context.pins_to_custom_sessions(InstrumentTypeId, dut_pins+system_pins)
    # Todo - debug is global variable in labview how is it handled in here.
    return debug


def pins_to_sessions(tsm_context: TSMContext, pins: typing.List[str], site_numbers: typing.List[int] = []):
    pin_query_context, session_data, channel_group_ids, channels_lists =\
        tsm_context.pins_to_custom_sessions(InstrumentTypeId, pins)
    session_data: typing.Tuple[nifpga.Session]
    channel_list, sites = ni_dt_common.pin_query_context_to_channel_list(pin_query_context, [], site_numbers)
    new_sessions = []
    for session, channel_id, channel, site in zip(session_data, channel_group_ids, channels_lists, sites):
        new_sessions.append(_SSCFPGA(session, channel_id, channel, site))
    return TSMFPGA(pin_query_context, new_sessions, channel_list)


def open_reference(rio_resource: str, target: BoardType, ldb_type: str):
    if target == BoardType.PXIe_7820R:
        name_of_relative_path = '7820R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target == BoardType.PXIe_7821R:
        name_of_relative_path = '7821R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target == BoardType.PXIe_7822R:
        if 'seq' in ldb_type.lower():
            name_of_relative_path = '7822R Static IO and I2C FPGA Main 3.3V.lvbitx'
        else:
            name_of_relative_path = '7822R Static IO and I2C FPGA Main Conn01 3.3V Conn 23 1.2V.lvbitx'
    else:
        name_of_relative_path = ''
    path = os.path.join(CurrentPath, '..\\..\\FPGA Bitfiles\\', name_of_relative_path)
    reference = nifpga.Session(path, rio_resource)
    return reference


def get_i2c_master_session(tsm_context: TSMContext,
                           i2c_master_in: I2CMaster.I2C_3V3_7822_SINK,
                           apply_i2c_settings: bool = True):
    sda = "%s_SDA" % i2c_master_in.name
    scl = "%s_SCL" % i2c_master_in.name
    session_data = pins_to_sessions(tsm_context, [sda, scl], [])
    session = session_data.SSC[0]
    ch_list = session_data.SSC[0].Channels.split(",")
    iq_list = []
    r_list = []
    for ch in ch_list:  # TODO CHECK
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
        path_teststand: str = 'C:\\Users\\Public\\Documents\\National Instruments\\TestStand 2019 (64-bit)'
):
    path_icons = os.path.join(path_teststand, 'Components\\Icons')
    path_in = os.path.join(path_in, '..\\Code Modules\\Common\\Instrument Control\\782x FPGA\\CustomInstrument')
    path_debug = os.path.join(path_icons, '782x FPGA Debug UI.ico')
    if not os.path.exists(path_debug):
        source = os.path.join(path_in, '782x FPGA Debug UI.ico')
        target = path_icons
        shutil.copy2(source, target)
    path_panels = os.path.join(path_teststand, 'Components\\Modules\\NI_SemiconductorModule\\CustomInstrumentPanels')
    path_debug = os.path.join(path_panels, '782x FPGA Debug UI.seq')
    path_debug2 = os.path.join(path_panels, '782x FPGA Debug UI')
    condition = os.path.exists(path_debug) and os.path.exists(path_debug2)
    if not False:  # TODO connected to condition?
        source = os.path.join(path_in, '.\\782x FPGA Debug UI\\')
        target = path_panels
        shutil.copy2(source, target)
        source = os.path.join(path_in, '.\\782x FPGA Debug UI.seq')
        shutil.copy2(source, target)
