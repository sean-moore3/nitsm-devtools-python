import typing
import os.path
import shutil
import nifpga
import niswitch
import nitsm.codemoduleapi
import nitsm.enums
import nitsm.pinquerycontexts
import enum
import nidigital
import nidaqmx.constants
import nidevtools.digital
import nidevtools.fpga
import nidevtools.switch
import nidevtools.daqmx
import time
import numpy as np
import xml.etree.ElementTree as ET

instrument_type_id = "Matrix"
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


class Control(enum.Enum):
    get_connections = 0
    disconnect_all = 1
    init = 2


class InstrumentTypes:
    daqmx = 'niDAQmx'
    digitalpattern = 'niDigitalPattern'
    fpga = '782xFPGA'
    switch = '_niSwitch'


class Session():
    def __init__(self,
                 enable_pin: str,
                 instrument_type: typing.Union[InstrumentTypes, str],
                 route_value: str,
                 site: int,
                 status: str):
        self.enable_pin = enable_pin
        self.instrument_type = instrument_type
        self.route_value = route_value
        self.site = site
        self.status = status


    def ss_connect(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(tsm_context, self.enable_pin)
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = False
            multiple_session.sessions[0].Task.stop()
            multiple_session.sessions[0].Task.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
            multiple_session.sessions[0].Task.write(bool(self.route_value), True)

        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = nidevtools.digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            multiple_session = nidevtools.digital.tsm_ssc_select_function(multiple_session,
                                                                          nidigital.enums.SelectedFunction.DIGITAL)
            if self.route_value == "0":
                data = nidigital.enums.WriteStaticPinState.ZERO
            elif self.route_value == "1":
                data = nidigital.enums.WriteStaticPinState.ONE
            else:
                data = nidigital.enums.WriteStaticPinState.X
            nidevtools.digital.tsm_ssc_write_static(multiple_session, data)

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = nidevtools.fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            if self.route_value == "0":
                data = nidevtools.fpga.StaticStates.Zero
            elif self.route_value == "1":
                data = nidevtools.fpga.StaticStates.One
            else:
                data = nidevtools.fpga.StaticStates.X
            multiple_session.write_static(data)
        elif self.instrument_type == InstrumentTypes.switch:
            handler = nidevtools.switch.pin_to_sessions_session_info(tsm_context, self.enable_pin)
            handler = nidevtools.switch.MultipleSessions([handler])
            handler.action_session_info(self.route_value, nidevtools.switch.Action.Connect)
        else:
            pass
        if 'BUCKLX_DAMP' in self.enable_pin:
            time.sleep(0.15)

    def ss_disconnect(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(tsm_context, [self.enable_pin])
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = True
            multiple_session: nidevtools.daqmx.MultipleSessions
            multiple_session.sessions[0].Task.stop()
            multiple_session.sessions[0].Task.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = nidevtools.digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            data = nidigital.enums.WriteStaticPinState.X
            nidevtools.digital.tsm_ssc_write_static(multiple_session, data)

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = nidevtools.fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            data = [nidevtools.fpga.StaticStates.X]  #*128 todo check
            print('D:', data)
            multiple_session.write_static(data)

        elif self.instrument_type == InstrumentTypes.switch:
            data = nidevtools.switch.pin_to_sessions_session_info(tsm_context, self.enable_pin)
            print("SD:", self.enable_pin)
            data = nidevtools.switch.MultipleSessions([data])
            if self.route_value == '':
                data.action_session_info(self.route_value, nidevtools.switch.Action.Disconnect_All)
            else:
                data.action_session_info(self.route_value, nidevtools.switch.Action.Disconnect)
        else:
            pass

    def ss_read_state(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(tsm_context, self.enable_pin)
            multiple_session: nidevtools.daqmx.MultipleSessions
            data=''
            for bit in multiple_session.sessions[0].Task.read(1):
                data+=str(bit)
            self.status = data

        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = nidevtools.digital.tsm_ssc_1_pin_to_n_sessions(tsm_context, self.enable_pin)
            multiple_session = nidevtools.digital.tsm_ssc_select_function(multiple_session,
                                                                          nidigital.enums.SelectedFunction.DIGITAL)
            data = nidevtools.digital.tsm_ssc_read_static(multiple_session)
            status = ['0', '1', '', 'L', 'H', 'X', 'M', 'V', 'D', 'E']
            self.status = status[data[0][0]]

        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = nidevtools.fpga.pins_to_sessions(tsm_context, [self.enable_pin], [])
            data = multiple_session.read_static()
            text = 'Disconnected'
            if data[0]:
                text = 'Connected'
            self.status = text

        elif self.instrument_type == InstrumentTypes.switch:
            data = nidevtools.switch.pin_to_sessions_session_info(tsm_context, self.enable_pin)
            data = nidevtools.switch.MultipleSessions([data])
            capability = data.action_session_info(self.route_value, nidevtools.switch.Action.Read)
            if capability[0] == niswitch.PathCapability.PATH_EXISTS:
                self.status = 'Connected To: %s' % self.route_value
            else:
                self.status = 'Not Connected'
        else:
            pass
        return self


class AbstractSession(typing.NamedTuple):
    enable_pins: typing.List[Session]

    def set_sessions(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext, switch_name: str = ''):  # CHECK
        tsm_context.set_switch_session(switch_name, self, instrument_type_id)

    def connect_sessions_info(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
        print('QQ', self)
        for session in self.enable_pins:

            if session.instrument_type == InstrumentTypes.switch or session.instrument_type == '_niSwitch':
                data = nidevtools.switch.pin_to_sessions_session_info(tsm_context, session.enable_pin)
                session_handler = nidevtools.switch.MultipleSessions([data])
                session_handler.action_session_info(action=nidevtools.switch.Action.Disconnect_All)
        for session in self.enable_pins:
            session.ss_connect(tsm_context)

    def disconnect_sessions_info(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):  # CHECK
        for session in self.enable_pins:
            session.ss_disconnect(tsm_context)

    def read_state(self, tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
        data = []
        print(self.enable_pins)
        for session in self.enable_pins:
            data.append(session.ss_read_state(tsm_context))
        return data


def check_debug_ui_tool(
        path_in: str,
        path_teststand: str = 'C:\\Users\\Public\\Documents\\National Instruments\\TestStand 2019 (64-bit)'):
    path_icons = os.path.join(path_teststand, 'Components\\Icons')
    path_in = os.path.join(path_in, '..\\Code Modules\\Common\\Instrument Control\\Abstract Switch\\Debug UI')
    path_debug = os.path.join(path_icons, 'Abstract Switch Debug UI.ico')
    if not os.path.exists(path_debug):
        source = os.path.join(path_in, 'Abstract Switch Debug UI.ico')
        target = path_icons
        shutil.copy2(source, target)
    path_panels = os.path.join(path_teststand, 'Components\\Modules\\NI_SemiconductorModule\\CustomInstrumentPanels')
    path_abstract = os.path.join(path_panels, 'Abstract Switch Debug UI.seq')
    path_abstract2 = os.path.join(path_panels, 'Abstract Switch Debug UI')
    condition = os.path.exists(path_abstract) and os.path.exists(path_abstract2)
    if not False:  # TODO connected to condition?
        source = os.path.join(path_in, 'CustomInstrument\\Abstract Switch Debug UI\\')
        target = path_panels
        shutil.copy2(source, target)
        source = os.path.join(path_in, 'CustomInstrument\\Abstract Switch Debug UI.seq')
        shutil.copy2(source, target)


def close_sessions(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):  # Comment: Nothing to do
    pass


# Not used
'''
def debug_ui(tsm_context: TSMContext):
    pass  # TODO CHECK
'''


def disconnect_all(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):  # CHECK
    sessions = get_all_sessions(tsm_context).enable_pins
    array1 = []
    array2 = []
    for session in sessions:
        if 'BUCKLX_DAMP' in session.enable_pin:
            array2.append(session)
        else:
            array1.append(session)
    multi_session = AbstractSession(array1 + array2)
    multi_session.disconnect_sessions_info(tsm_context)


def disconnect_pin(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext, pin: str):
    sessions = pins_to_sessions_sessions_info(tsm_context, pin)
    sessions.disconnect_sessions_info(tsm_context)


def initialize_tsm_context(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):  # CHECK
    switch_names = tsm_context.get_all_switch_names(instrument_type_id)
    if len(switch_names) == 1:
        dut_pins, sys_pins = tsm_context.get_pin_names()
        array = []
        for pin in dut_pins+sys_pins:
            if pin.lower().find('en_') == 0:
                array.append(pin)
        data = []
        for instrument in ['niDAQmx', 'niDigitalPattern', '782xFPGA', '_niSwitch']:
            filtered_pins = tsm_context.filter_pins_by_instrument_type(array, instrument, nitsm.enums.Capability.ALL)
            for pin in filtered_pins:
                session = Session(pin, instrument, '', 0, '')  # TODO Not all info
                data.append(session)
        multi_session = AbstractSession(data)
        multi_session.set_sessions(tsm_context, switch_names[0])
    else:
        raise nifpga.ErrorStatus(5000,
                                 ("Unsupported Pin Map for the Abstract Switch."
                                  "Ensure you only have one abstract switch in the pinmap"),
                                 "initialize_tsm_context()",
                                 ["tsm_context"],
                                 (tsm_context,))


def pin_fgv(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext,
            pin: str = '',
            action: Control = Control.get_connections):
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

def get_first_matched_node(tree: ET.ElementTree, key: str):
    key = "{http://www.ni.com/TestStand/SemiconductorModule/PinMap.xsd}"+key
    root = tree.getroot()
    for i in root:
        if key in i.tag:
            return i

def get_all_matched_nodes(element: ET.Element, key: str):
    key = "{http://www.ni.com/TestStand/SemiconductorModule/PinMap.xsd}"+key
    children = element.getchildren()
    output = []
    for i in children:
        if i.tag == key:
            output.append(i)
    return output

def pin_name_to_instrument(pinmap_path: str = ''):
    tree = ET.parse(pinmap_path)
    connections = get_first_matched_node(tree,'Connections')
    pingroups = get_first_matched_node(tree, 'PinGroups')
    connection = get_all_matched_nodes(connections, 'Connection')
    multiplexedconnection = get_all_matched_nodes(connections, 'MultiplexedConnection')
    pingroup = get_all_matched_nodes(pingroups, 'PinGroup')
    subarray1 = []
    for element in connection:
         subarray1.append([element.attrib['pin'],element.attrib['instrument'],element.attrib['channel'],"","",""])
    for element in multiplexedconnection:
        dut_route = get_all_matched_nodes(element,"MultiplexedDUTPinRoute")
        subarray21 = []
        for j in dut_route:
            subarray21.append([j.attrib['pin'], element.attrib['instrument'], element.attrib['channel']])
    for element in pingroup:
        reference = get_all_matched_nodes(element,"PinReference")
        subarray22 = [element.attrib['name']]
        for j in reference:
            subarray22.append(j.attrib['pin'])
        #TODO Join Sub21 and Sub22

def enable_pins_to_sessions(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext, enable_pins: typing.List[str]):
    sessions = get_all_sessions(tsm_context)
    array = []
    for pin in enable_pins:
        for session in sessions.enable_pins:
            if pin == session.enable_pin:
                array.append(session)
    return AbstractSession(array)


def get_all_instruments_names(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):
    switch_names = tsm_context.get_all_switch_names(instrument_type_id)
    return switch_names


def get_all_sessions(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext):  # CHECK
    session_data = tsm_context.get_all_switch_sessions(instrument_type_id)
    if len(session_data) == 0:
        # Raise Error?
        session = AbstractSession([])
    else:
        session = session_data[0]
    return session


@nitsm.codemoduleapi.code_module
def pins_to_sessions_sessions_info(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext, pin: str):
    session_list = []
    contexts, sessions, switch_routes = tsm_context.pin_to_switch_sessions(pin, instrument_type_id)
    i = 0
    for context, session, route in zip(contexts, sessions, switch_routes):
        data = route.split(',')
        list1 = []
        list2 = []
        for route_data in data:
            data2 = route_data.split('=')
            out1 = data2[0].strip()
            out2 = ''.join(data2[1:]).strip()
            list1.append(out1)
            list2.append(out2)
        for element1, element2 in zip(list1, list2):
            condition = False
            for single_session in session.enable_pins:
                single_session.route_value = element2
                single_session.site = i
                if single_session.enable_pin.strip().lower() == element1.lower():
                    print("E:", single_session)
                    session_list.append(single_session)
                    break
        del tsm_context
    return AbstractSession(session_list)


@nitsm.codemoduleapi.code_module
def pins_to_task_and_connect(tsm_context: nitsm.codemoduleapi.SemiconductorModuleContext,
                             task_name: PinsArg,
                             pins: PinsArg):
    print('TT', pins)
    pin_list = tsm_context.filter_pins_by_instrument_type(pins, 'abstinst', nitsm.enums.Capability.ALL)
    multiple_session_info = nidevtools.daqmx.pins_to_session_sessions_info(tsm_context, task_name)
    sessions = []
    for pin in pin_list:
        sessions += pins_to_sessions_sessions_info(tsm_context, pin).enable_pins
    multi_session = AbstractSession(sessions)
    if len(sessions) != 0:
        multi_session.connect_sessions_info(tsm_context)
    return multiple_session_info
