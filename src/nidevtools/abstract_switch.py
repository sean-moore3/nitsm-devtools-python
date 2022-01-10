import typing
import os.path as path
import shutil

import nifpga
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
from enum import Enum as Enum
from nidigital import enums
import nidaqmx.constants as constants
import nidevtools.daqmx as ni_daqmx
import nidevtools.digital as ni_digital
import nidevtools.fpga as ni_fpga
# import nidevtools._switch as ni_switch
import time

instrument_type_id = "Matrix"


class Control(Enum):
    get_connections = 0
    disconnect_all = 1
    init = 2


class InstrumentTypes(Enum):
    daqmx = 0
    digitalpattern = 1
    fpga = 2
    switch = 3


class Session(typing.NamedTuple):
    enable_pin: str
    instrument_type: typing.Union[InstrumentTypes, str]
    route_value: str
    site: int
    status: str

    def ss_connect(self, tsm_context: TSMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, self.enable_pin)
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = False
            multiple_session.sessions[0].Task.control(constants.TaskMode.TASK_COMMIT)
            multiple_session.sessions[0].Task.write(bool(self.route_value), True)

        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = ni_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            multiple_session = ni_digital.tsm_ssc_select_function(multiple_session, enums.SelectedFunction.DIGITAL)
            if self.route_value == "0":
                data = enums.WriteStaticPinState.ZERO
            elif self.route_value == "1":
                data = enums.WriteStaticPinState.ONE
            else:
                data = enums.WriteStaticPinState.X
            ni_digital.tsm_ssc_write_static(multiple_session, data)

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = ni_fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            if self.route_value == "0":
                data = ni_fpga.StaticStates.Zero
            elif self.route_value == "1":
                data = ni_fpga.StaticStates.One
            else:
                data = ni_fpga.StaticStates.X
            multiple_session.write_static(data)

        elif self.instrument_type == InstrumentTypes.switch:
            pass  # TODO where is switch module?
        else:
            pass
        if 'BUCKLX_DAMP' in self.enable_pin:
            time.sleep(0.15)

    def ss_disconnect(self, tsm_context: TSMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, self.enable_pin)
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = True
            multiple_session.sessions[0].Task.control(constants.TaskMode.TASK_COMMIT)

        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = ni_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            data = enums.WriteStaticPinState.X
            ni_digital.tsm_ssc_write_static(multiple_session, data)

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = ni_fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            data = ni_fpga.StaticStates.X
            multiple_session.write_static(data)

        elif self.instrument_type == InstrumentTypes.switch:
            pass  # TODO where is switch module?
        else:
            pass

    def ss_read_state(self, tsm_context: TSMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = ni_daqmx.pins_to_session_sessions_info(tsm_context, self.enable_pin)
            data = ''.join(multiple_session.sessions[0].Task.read(1))
            self.status = data

        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = ni_digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            multiple_session = ni_digital.tsm_ssc_select_function(multiple_session, enums.SelectedFunction.DIGITAL)
            data = ni_digital.tsm_ssc_read_static(multiple_session)
            status = ['0', '1', '', 'L', 'H', 'X', 'M', 'V', 'D', 'E']
            self.status = status[data[0][0]]

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = ni_fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            data = multiple_session.read_static()
            text = 'Disconnected'
            if data[0]:
                text = 'Connected'
            self.status = text

        elif self.instrument_type == InstrumentTypes.switch:
            pass  # TODO where is switch module?
        else:
            pass
        return self


class AbstractSession(typing.NamedTuple):
    enable_pins: typing.List[Session]

    def set_sessions(self, tsm_context: TSMContext, switch_name: str = ''):
        tsm_context.set_relay_driver_niswitch_session(switch_name, self.enable_pins)  # TODO CHECK

    def connect_sessions_info(self, tsm_context: TSMContext):
        for session in self.enable_pins:
            session.ss_connect(tsm_context)

    def disconnect_sessions_info(self, tsm_context: TSMContext):
        for session in self.enable_pins:
            session.ss_disconnect(tsm_context)

    def read_state(self, tsm_context: TSMContext):
        data = []
        for session in self.enable_pins:
            data.append(session.ss_read_state(tsm_context))
        return data


def check_debug_ui_tool(
        path_in: str,
        path_teststand: str = 'C:\\Users\\Public\\Documents\\National Instruments\\TestStand 2019 (64-bit)'
):
    path_icons = path.join(path_teststand, 'Components\\Icons')
    path_in = path.join(path_in, '..\\Code Modules\Common\\Instrument Control\\Abstract Switch\\Debug UI')
    path_debug = path.join(path_icons, 'Abstract Switch Debug UI.ico')
    if not path.exists(path_debug):
        source = path.join(path_in, 'Abstract Switch Debug UI.ico')
        target = path_icons
        shutil.copy2(source, target)
    path_panels = path.join(path_teststand, 'Components\\Modules\\NI_SemiconductorModule\\CustomInstrumentPanels')
    path_abstract = path.join(path_panels, 'Abstract Switch Debug UI.seq')
    path_abstract2 = path.join(path_panels, 'Abstract Switch Debug UI')
    condition = path.exists(path_abstract) and path.exists(path_abstract2)
    if not False:  # TODO connected to condition?
        source = path.join(path_in, 'CustomInstrument\\Abstract Switch Debug UI\\')
        target = path_panels
        shutil.copy2(source, target)
        source = path.join(path_in, 'CustomInstrument\\Abstract Switch Debug UI.seq')
        shutil.copy2(source, target)


def close_sessions(tsm_context: TSMContext):
    pass


# Not used
'''
def debug_ui(tsm_context: TSMContext):
    pass  # TODO CHECK
'''


def disconnect_all(tsm_context: TSMContext):
    sessions = get_all_sessions(tsm_context)
    array1 = []
    array2 = []
    for session in sessions:
        if 'BUCKLX_DAMP' in session.enable_pin:
            array2.append(session)
        else:
            array1.append(session)
    multi_session = AbstractSession(array1 + array2)
    multi_session.disconnect_sessions_info(tsm_context)


def disconnect_pin(tsm_context: TSMContext, pins: typing.List[str]):
    sessions = pins_to_sessions_sessions_info(tsm_context, pins)
    sessions.disconnect_sessions_info(tsm_context)


def initialize_tsm_context(tsm_context: TSMContext):
    names = tsm_context.get_all_relay_driver_niswitch_sessions()  # TODO Names??
    if len(names) == 1:
        dut_pins, sys_pins = tsm_context.get_pin_names()
        array = []
        for pin in dut_pins+sys_pins:
            if '^[Ee][Nn]_' in pin:
                array.append(pin)
        data = []
        for instrument in ['niDAQmx', 'niDigitalIP', '782xFPGA', '_niSwitch']:
            for pin in tsm_context.filter_pins_by_instrument_type(array, instrument, ''):
                session = Session(pin, instrument, '', 0, '')  # Not all info
                data.append(session)
        multi_session = AbstractSession(data)
        multi_session.set_sessions(tsm_context, names[0])
    else:
        raise nifpga.ErrorStatus(5000,
                                 ("Unsupported Pin Map for the Abstract Switch."
                                  "Ensure you only have one abstract switch in the pinmap"),
                                 "initialize_tsm_context()",
                                 ["tsm_context"],
                                 (tsm_context,))


def pin_fgv(tsm_context: TSMContext, pin: str = '', action: Control = Control.get_connections):
    connections = []
    while True:
        if action == Control.get_connections:
            for connection in connections:
                if connection[1] == 'AbstractInstrument':
                    sessions = pins_to_sessions_sessions_info(tsm_context, connection[0])
                    data = sessions.read_state(tsm_context)
                    conditions = []
                    condition = False
                    for info in data:
                        if info.instrument_type == InstrumentTypes.daqmx:
                            if info.route_value:
                                condition = info.status
                            else:
                                condition = not info.status
                        elif info.instrument_type == InstrumentTypes.digitalpattern:
                            if info.route_value == '1':
                                condition = info.status == '1'
                            else:
                                condition = info.status != '1'
                        elif info.instrument_type == InstrumentTypes.fpga:
                            if info.route_value == '1':
                                condition = info.status == 'Connected'
                            else:
                                condition = info.status == 'Disconnected'
                        elif info.instrument_type == InstrumentTypes.switch:
                            condition = info.status in info.route_value
                        conditions.append(condition)
                    if len(conditions) == 0:
                        condition = True
                    else:
                        if False in conditions:
                            condition = False
                        else:
                            condition = True
                    if condition:
                        connections[5] = 'Connected'
                    else:
                        connections[5] = 'Disconnected'  # TODO Why Element 5?
        elif action == Control.disconnect_all:
            disconnect_all(tsm_context)
        elif action == Control.init:
            pinmap_path = tsm_context.pin_map_file_path
            connections += pin_name_to_instrument(pinmap_path)


def pin_name_to_instrument(pinmap_path: str = ''):
    pass  # TODO CHECK


def enable_pins_to_sessions(tsm_context: TSMContext, enable_pins: typing.List[str]):
    sessions = get_all_sessions(tsm_context)
    array = []
    for pin in enable_pins:
        for session in sessions:
            if pin == session.enable_pin:
                array.append(session)
    return AbstractSession(array)


def get_all_instruments_names(tsm_context: TSMContext):
    switch_names = tsm_context.get_custom_instrument_names(instrument_type_id)
    return switch_names


def get_all_sessions(tsm_context: TSMContext):
    data = tsm_context.get_all_relay_driver_niswitch_sessions()
    if len(data) == 0:
        # Raise Error?
        session = AbstractSession([])
    else:
        session = data[0]
    return session


def pins_to_sessions_sessions_info(tsm_context: TSMContext, pins: typing.List[str]):
    return AbstractSession([])
# TODO CHECK
