import enum
import os.path
import shutil
import time
import typing
import xml.etree.ElementTree as Et
import nidaqmx.constants
import nidigital
import nifpga
import niswitch
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext
import nitsm.enums
import nitsm.pinquerycontexts
import nidevtools.daqmx
import nidevtools.digital
import nidevtools.fpga
import nidevtools.switch

instrument_type_id = "Matrix"
PinsArg = typing.Union[str, typing.Sequence[str]]
Any = typing.Any
StringTuple = typing.Tuple[str]


class Control(enum.Enum):
    get_connections = 0
    disconnect_all = 1
    init = 2


class InstrumentTypes:
    daqmx = "niDAQmx"
    digitalpattern = "niDigitalPattern"
    fpga = "782xFPGA"
    switch = "_niSwitch"


class Session:
    def __init__(
        self,
        enable_pin: str,
        instrument_type: typing.Union[InstrumentTypes, str],
        route_value: str,
        site: int,
        status: str,
    ):
        self.enable_pin = enable_pin
        self.instrument_type = instrument_type
        self.route_value = route_value
        self.site = site
        self.status = status

    def ss_connect(self, tsm: SMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(tsm, self.enable_pin)
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = False
            multiple_session.sessions[0].Task.stop()
            multiple_session.sessions[0].Task.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
            multiple_session.sessions[0].Task.write(bool(self.route_value), True)
        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session = nidevtools.digital.pin_to_sessions(tsm, self.enable_pin)
            multiple_session.ssc.select_function(nidigital.enums.SelectedFunction.DIGITAL)
            if self.route_value == "0":
                data = nidigital.enums.WriteStaticPinState.ZERO
            elif self.route_value == "1":
                data = nidigital.enums.WriteStaticPinState.ONE
            else:
                data = nidigital.enums.WriteStaticPinState.X
            multiple_session.ssc.write_static(data)
        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session = nidevtools.fpga.pins_to_sessions(tsm, [self.enable_pin], [])
            if self.route_value == "0":
                data = nidevtools.fpga.StaticStates.Zero
            elif self.route_value == "1":
                data = nidevtools.fpga.StaticStates.One
            else:
                data = nidevtools.fpga.StaticStates.X
            multiple_session.write_static(data)
        elif self.instrument_type == InstrumentTypes.switch:
            handler = nidevtools.switch.pin_to_sessions_session_info(tsm, self.enable_pin)
            handler = nidevtools.switch.MultipleSessions([handler])
            handler.action_session_info(self.route_value, nidevtools.switch.Action.Connect)
        else:
            pass
        if "BUCKLX_DAMP" in self.enable_pin:
            time.sleep(0.15)

    def ss_disconnect(self, tsm: SMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(
                tsm, [self.enable_pin]
            )
            for channel in multiple_session.sessions[0].Task.do_channels:
                channel.do_tristate = True
            multiple_session: nidevtools.daqmx.MultipleSessions
            multiple_session.sessions[0].Task.stop()
            multiple_session.sessions[0].Task.control(nidaqmx.constants.TaskMode.TASK_COMMIT)
        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session_info = nidevtools.digital.pin_to_sessions(tsm, self.enable_pin)
            data = nidigital.enums.WriteStaticPinState.X
            multiple_session_info.ssc.write_static(data)
        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session_info = nidevtools.fpga.pins_to_sessions(tsm, [self.enable_pin], [])
            data = [nidevtools.fpga.StaticStates.X]  # *128 todo check
            multiple_session_info.write_static(data)
        elif self.instrument_type == InstrumentTypes.switch:
            data = nidevtools.switch.pin_to_sessions_session_info(tsm, self.enable_pin)
            data = nidevtools.switch.MultipleSessions([data])
            if self.route_value == "":
                data.action_session_info(self.route_value, nidevtools.switch.Action.Disconnect_All)
            else:
                data.action_session_info(self.route_value, nidevtools.switch.Action.Disconnect)
        else:
            pass

    def ss_read_state(self, tsm: SMContext):
        if self.instrument_type == InstrumentTypes.daqmx:
            multiple_session = nidevtools.daqmx.pins_to_session_sessions_info(tsm, self.enable_pin)
            multiple_session: nidevtools.daqmx.MultipleSessions
            data = ""
            for bit in multiple_session.sessions[0].Task.read(1):
                data += str(bit)
            self.status = data
        elif self.instrument_type == InstrumentTypes.digitalpattern:
            multiple_session_info = nidevtools.digital.pin_to_sessions(tsm, self.enable_pin)
            multiple_session_info.ssc.select_function(nidigital.enums.SelectedFunction.DIGITAL)
            data = multiple_session_info.ssc.read_static()
            status = ["0", "1", "", "L", "H", "X", "M", "V", "D", "E"]
            self.status = status[data[0][0]]
        elif self.instrument_type == InstrumentTypes.fpga:
            multiple_session_info = nidevtools.fpga.pins_to_sessions(tsm, [self.enable_pin], [])
            data = multiple_session_info.read_static()
            text = "Disconnected"
            if data[0]:
                text = "Connected"
            self.status = text
        elif self.instrument_type == InstrumentTypes.switch:
            data = nidevtools.switch.pin_to_sessions_session_info(tsm, self.enable_pin)
            data = nidevtools.switch.MultipleSessions([data])
            capability = data.action_session_info(self.route_value, nidevtools.switch.Action.Read)
            if capability[0] == niswitch.PathCapability.PATH_EXISTS:
                self.status = "Connected To: %s" % self.route_value
            else:
                self.status = "Not Connected"
        else:
            pass
        return self


class AbstractSession(typing.NamedTuple):
    enable_pins: typing.List[Session]

    def set_sessions(self, tsm: SMContext, switch_name: str = ""):  # CHECK
        """
        Sets abstract switch sessions contained in the Abstract Switch object
        """
        tsm.set_switch_session(switch_name, self, instrument_type_id)

    def connect_sessions_info(self, tsm: SMContext):
        """
        Connects the sessions in the pinmap to the TSM context
        """
        for session in self.enable_pins:

            if (
                session.instrument_type == InstrumentTypes.switch
                or session.instrument_type == "_niSwitch"
            ):
                data = nidevtools.switch.pin_to_sessions_session_info(tsm, session.enable_pin)
                session_handler = nidevtools.switch.MultipleSessions([data])
                session_handler.action_session_info(action=nidevtools.switch.Action.Disconnect_All)
        for session in self.enable_pins:
            session.ss_connect(tsm)

    def disconnect_sessions_info(self, tsm: SMContext):  # CHECK
        """
        Disconnects the provided session from the TSM context it works for DAQmx, Digital Pattern, FPGA and Switch
        sessions only
        """
        for session in self.enable_pins:
            session.ss_disconnect(tsm)

    def read_state(self, tsm: SMContext):
        """
        Reads the state of each session in AbstractSession object and returns a list of values
        """
        data = []
        for session in self.enable_pins:
            data.append(session.ss_read_state(tsm))
        return data


def check_debug_ui_tool(
    path_in: str,
    path_teststand: str = "C:\\Users\\Public\\Documents\\National Instruments\\TestStand 2019 (64-bit)",
):
    """ """
    path_icons = os.path.join(path_teststand, "Components\\Icons")
    path_in = os.path.join(
        path_in, "..\\Code Modules\\Common\\Instrument Control\\Abstract Switch\\Debug UI"
    )
    path_debug = os.path.join(path_icons, "Abstract Switch Debug UI.ico")
    if not os.path.exists(path_debug):
        source = os.path.join(path_in, "Abstract Switch Debug UI.ico")
        target = path_icons
        shutil.copy2(source, target)
    path_panels = os.path.join(
        path_teststand, "Components\\Modules\\NI_SemiconductorModule\\CustomInstrumentPanels"
    )
    path_abstract = os.path.join(path_panels, "Abstract Switch Debug UI.seq")
    path_abstract2 = os.path.join(path_panels, "Abstract Switch Debug UI")
    condition = os.path.exists(path_abstract) and os.path.exists(path_abstract2)
    if not False:  # TODO connected to condition?
        source = os.path.join(path_in, "CustomInstrument\\Abstract Switch Debug UI\\")
        target = path_panels
        shutil.copy2(source, target)
        source = os.path.join(path_in, "CustomInstrument\\Abstract Switch Debug UI.seq")
        shutil.copy2(source, target)


def close_sessions(tsm: SMContext):  # Comment: Nothing to do
    pass


# Not used
"""
def debug_ui(tsm: SMContext):
    pass
"""


def disconnect_all(tsm: SMContext):  # CHECK
    """
    Disconnects all abstract switch related pins in the context provided
    """
    sessions = get_all_sessions(tsm).enable_pins
    array1 = []
    array2 = []
    for session in sessions:
        if "BUCKLX_DAMP" in session.enable_pin:
            array2.append(session)
        else:
            array1.append(session)
    multi_session = AbstractSession(array1 + array2)
    multi_session.disconnect_sessions_info(tsm)


def disconnect_pin(tsm: SMContext, pin: str):
    """
    Disconnects the pin provided on the TSM context, the pin provided should be part of the pinmap
    """
    sessions = pins_to_sessions_sessions_info(tsm, pin)
    sessions.disconnect_sessions_info(tsm)


def initialize(tsm: SMContext):  # CHECK
    """
    Initialize the TSM context with all the Abstract switch sessions. Based on the instrument type it will create
    session to individual drivers. so it is essential to
    Args:
        tsm: TSM context where the sessions will be initialized
    """
    switch_names = tsm.get_all_switch_names(instrument_type_id)
    if len(switch_names) == 1:
        dut_pins, sys_pins = tsm.get_pin_names()
        en_pins = []
        for pin in dut_pins + sys_pins:
            if pin.lower().find("en_") == 0:
                en_pins.append(pin)
        en_sessions = []
        for instrument in ["niDAQmx", "niDigitalPattern", "782xFPGA", "_niSwitch"]:
            filtered_pins = tsm.filter_pins_by_instrument_type(
                en_pins, instrument, nitsm.enums.Capability.ALL
            )
            for pin in filtered_pins:
                session = Session(pin, instrument, "", 0, "")
                en_sessions.append(session)
        multi_session = AbstractSession(en_sessions)
        multi_session.set_sessions(tsm, switch_names[0])
    else:
        raise nifpga.ErrorStatus(
            5000,
            (
                "Unsupported Pin Map for the Abstract Switch."
                "Ensure you only have one abstract switch in the pinmap"
            ),
            "initialize()",
            ["tsm_context"],
            (tsm,),
        )


def pin_fgv(tsm: SMContext, pin: str = "", action: Control = Control.get_connections):
    """ """
    connections = []
    while True:
        if action == Control.get_connections:
            for connection in connections:
                if connection[1] == "AbstractInstrument":
                    sessions = pins_to_sessions_sessions_info(tsm, connection[0])
                    data = sessions.read_state(tsm)
                    conditions = []
                    condition = False
                    for info in data:
                        if info.instrument_type == InstrumentTypes.daqmx:
                            if info.route_value:
                                condition = info.status
                            else:
                                condition = not info.status
                        elif info.instrument_type == InstrumentTypes.digitalpattern:
                            if info.route_value == "1":
                                condition = info.status == "1"
                            else:
                                condition = info.status != "1"
                        elif info.instrument_type == InstrumentTypes.fpga:
                            if info.route_value == "1":
                                condition = info.status == "Connected"
                            else:
                                condition = info.status == "Disconnected"
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
                        connections[5] = "Connected"
                    else:
                        connections[5] = "Disconnected"
        elif action == Control.disconnect_all:
            disconnect_all(tsm)
        elif action == Control.init:
            pinmap_path = tsm.pin_map_file_path
            connections += pin_name_to_instrument(pinmap_path)
        break


def get_first_matched_node(tree: Et.ElementTree, key: str):
    key = "{http://www.ni.com/TestStand/SemiconductorModule/PinMap.xsd}" + key
    root = tree.getroot()
    for i in root:
        if key in i.tag:
            return i


def get_all_matched_nodes(element: Et.Element, key: str):
    key = "{http://www.ni.com/TestStand/SemiconductorModule/PinMap.xsd}" + key
    children = list(element)
    output = []
    for i in children:
        if i.tag == key:
            output.append(i)
    return output


def pin_name_to_instrument(pinmap_path: str = ""):
    """
    From pinmap location it parce the abstract switch connections into an Array.
    Args:
        pinmap_path: Location of the pinmap to use
    """
    tree = Et.parse(pinmap_path)
    connections = get_first_matched_node(tree, "Connections")
    pingroups = get_first_matched_node(tree, "PinGroups")
    connection = get_all_matched_nodes(connections, "Connection")
    multiplexedconnection = get_all_matched_nodes(connections, "MultiplexedConnection")
    pingroup = get_all_matched_nodes(pingroups, "PinGroup")
    subarray1 = []
    subarray2 = []
    for element in connection:
        var1 = [
            element.attrib["pin"],
            element.attrib["instrument"],
            element.attrib["channel"],
            "",
            "",
            "",
        ]
        subarray1.append(var1)
    subarray21 = []
    for element in multiplexedconnection:
        dut_route = get_all_matched_nodes(element, "MultiplexedDUTPinRoute")
        subarray21 = []
        for j in dut_route:
            subarray21.append(
                [j.attrib["pin"], element.attrib["instrument"], element.attrib["channel"]]
            )
    subarray22 = []
    for element in pingroup:
        reference = get_all_matched_nodes(element, "PinReference")
        subarray22_e = [element.attrib["name"] + "_DUT"]
        for j in reference:
            subarray22_e.append(j.attrib["pin"])
        subarray22.append(subarray22_e)
    for element in subarray21:
        r = 0
        for j in subarray22:
            if j[0] == element[0]:
                break
            else:
                r += 1
        if element[1] == "AbstractInstrument":
            print(subarray22)
            out1 = subarray22[r][2]
        else:
            out1 = ""
        r = 0
        for j in subarray1:
            if j[0] == out1:
                break
            else:
                r += 1
        out2 = "%s, %s" % (subarray1[r][1], subarray1[r][2])
        subarray2.append(element + [out1] + [out2] + ["Disconnected"])
    return subarray1 + subarray2


def enable_pins_to_sessions(tsm: SMContext, enable_pins: typing.List[str]):
    """
    Receives enable pins list and return a Multi-session object with the sessions corresponding to those pins
    Args:
        tsm: Pin context
        enable_pins: List of pins for session creation
    Returns:
        MultipleSession object that contains the session for the selected pins.
    """
    sessions = get_all_sessions(tsm)
    array = []
    for pin in enable_pins:
        for session in sessions.enable_pins:
            if pin == session.enable_pin:
                array.append(session)
    return AbstractSession(array)


def get_all_instruments_names(tsm: SMContext):
    """
    Gets a list of all instrument names set on TSM context for Abstract switch
    """
    switch_names = tsm.get_all_switch_names(instrument_type_id)
    return switch_names


def get_all_sessions(tsm: SMContext):  # CHECK
    """
    Gets a list of Abstract Switch references corresponding to the set Abstract sessions on TSM Context
    """
    session_data = tsm.get_all_switch_sessions(instrument_type_id)
    if len(session_data) == 0:
        # Raise Error?
        session = AbstractSession([])
    else:
        session = session_data[0]
    return session


@nitsm.codemoduleapi.code_module
def pins_to_sessions_sessions_info(tsm: SMContext, pin: str):
    """
    Returns an AbstractSession object containing a list al Abstract switch sessions detailed on the pinmap
    Args:
        tsm: Pin context defined by pin map
        pin: The name of the pin to translate to a session.
    Return:
        session: An object that tracks the session associated with pin provided.
    """
    session_list = []
    contexts, sessions, switch_routes = tsm.pin_to_switch_sessions(pin, instrument_type_id)
    i = 0
    for context, session, route in zip(contexts, sessions, switch_routes):
        data = route.split(",")
        list1 = []
        list2 = []
        for route_data in data:
            data2 = route_data.split("=")
            out1 = data2[0].strip()
            out2 = "".join(data2[1:]).strip()
            list1.append(out1)
            list2.append(out2)
        for element1, element2 in zip(list1, list2):
            condition = False
            for single_session in session.enable_pins:
                single_session.route_value = element2
                single_session.site = i
                if single_session.enable_pin.strip().lower() == element1.lower():
                    session_list.append(single_session)
                    break
        del tsm
    return AbstractSession(session_list)


@nitsm.codemoduleapi.code_module
def pins_to_task_and_connect(tsm: SMContext, task_name: PinsArg, pins: PinsArg):
    """
    Returns a pin query contex and a list of properties defined in the pin map.
    The list of properties returned can be used to fill a new object type MultipleSessions
    Args:
        tsm: Pin context defined by pin map
        task_name: The name of the pin(s) or pin group(s) to translate to a set of tasks.
        pins: The name of the pin(s) or pin group(s) to translate to a set of abstract sessions.
    Return:
        session: An object that tracks the tasks associated with this pin query. Use this object to publish
        measurements and extract data from a set of measurements.
    """
    pin_list = tsm.filter_pins_by_instrument_type(pins, "abstinst", nitsm.enums.Capability.ALL)
    multiple_session_info = nidevtools.daqmx.pins_to_session_sessions_info(tsm, task_name)
    sessions = []
    for pin in pin_list:
        sessions += pins_to_sessions_sessions_info(tsm, pin).enable_pins
    multi_session = AbstractSession(sessions)
    if len(sessions) != 0:
        multi_session.connect_sessions_info(tsm)
    return multiple_session_info
