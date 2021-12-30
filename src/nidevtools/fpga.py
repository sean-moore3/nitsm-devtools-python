import enum
import os
import nifpga
import nitsm.codemoduleapi
from nitsm.enums import Capability
from nidaqmx.constants import TerminalConfiguration
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from nitsm.enums import InstrumentTypeIdConstants
from nitsm.pinquerycontexts import PinQueryContext
from enum import Enum
import typing

# Types Definition

PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]
InstrumentTypeId = '782xFPGA'
CurrentPath = os.getcwd()

class Channel(typing.NamedTuple):
    channel: str
    connector: str

class _SSCFPGA(typing.NamedTuple):
    Session: nifpga.Session
    ChannelGroupID: str
    Channels: str
    ChannelList: str

    def close_session(self,reset_if_last_session: bool=True):
        """
        Closes the reference to the FPGA session and, optionally, resets execution of the session. By default,
        the Close FPGA session Reference function closes the reference to the FPGA session and resets the FPGA session.
        To configure this function only to close the reference, change the value of the argument when calling the
        function. The Close FPGA session reference function also stops all DMA FIFOs on the FPGA.
        """
        self.Session.close(reset_if_last_session)

    def configure_i2c_master_sda_scl_lines(self,
                                           i2c_master: str='I2C_3v3_7822_SINK',
                                           sda_channel: Channel=Channel('DIO0','Connector0'),
                                           scl_channel: Channel=Channel('DIO0','Connector0')
                                           ):
        """"""
        pass
    #TODO define how to modify the property

class TSMFPGA(typing.NamedTuple):
    pin_query_context: Any
    SSC: typing.List[_SSCFPGA]

    def get_i2c_master(self):
        for element in self.SSC:
            session = element.Session
            ch_list = element.ChannelList

    def write_i2c_data(self, data_to_write: typing.List[int], timeout: float=1, slave_address: int=0):
        pass

def open_reference(rio_resource: str, target: str, ldb_type: str):
    if target=='PXIe-7820R':
        name_of_relative_path = '7820R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target=='PXIe-7821R':
        name_of_relative_path = '7821R Static IO and I2C FPGA Main 3.3V.lvbitx'
    elif target=='PXIe-7822R':
        if 'Seq' in ldb_type:
            name_of_relative_path = '7822R Static IO and I2C FPGA Main 3.3V.lvbitx'
        else:
            name_of_relative_path = '7822R Static IO and I2C FPGA Main Conn01 3.3V Conn 23 1.2V.lvbitx'
    else:
        name_of_relative_path = ''
    path = os.path.join(CurrentPath,'..\\..\\FPGA Bitfiles\\',name_of_relative_path)
    reference = os.path.join(rio_resource,path)
    #Review Reference
    return reference



def initialize_session(tsm_context: TSMContext, ldb_type: str):
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(InstrumentTypeId)
    for instrument, group in zip(instrument_names, channel_group_ids):
        traget_list = ["PXIe-7822R", "PXIe-7821R", "PXIe-7820R"]
        for target in traget_list:
            ref_out = open_reference(instrument, target, ldb_type)
            #Error to clear
        tsm_context.set_custom_session(InstrumentTypeId,instrument,group,ref_out)
        dut_pins, system_pins = tsm_context.get_pin_names(InstrumentTypeId)
        debug = tsm_context.pins_to_custom_sessions(InstrumentTypeId, dut_pins+system_pins)
        return debug

