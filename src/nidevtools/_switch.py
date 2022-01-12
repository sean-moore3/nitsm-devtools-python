import typing
from nitsm.codemoduleapi import SemiconductorModuleContext as TSMContext
import niswitch
from enum import Enum


class Action(Enum):
    Disconnect = 0
    Connect = 1
    Disconnect_All = 2
    Read = 3


class Topology(typing.NamedTuple):
    matrix_2738 = '2738/2-Wire 8x32 Matrix'
    mux_2525 = '2525/2-Wire Octal 8x1 Mux'
    matrix_2503 = '2503/2-Wire 4x6 Matrix'


class Session(typing.NamedTuple):
    Session: niswitch.Session
    Pin: str
    Channel: str

    def info(self, route_value: str, action: Action, timeout: int):
        data = []
        if action == Action.Disconnect_All:
            self.Session.disconnect_all()
        elif action == Action.Connect:
            path_capability = self.Session.can_connect(self.Channel, route_value)
            data.append(path_capability)
            if path_capability == 1:
                self.Session.connect(self.Channel, route_value)
            self.Session.wait_for_debounce(timeout)
        elif action == Action.Disconnect:
            self.Session.disconnect(self.Channel, route_value)
        elif action == Action.Read:
            data.append(self.Session.can_connect(self.Channel, route_value))
        return data


class MultipleSessions:
    Sessions: typing.List[Session]

    def session_info(self, route_value: str, action: Action, timeout: int = 40):
        read_path_capability = []
        data = []
        for session in self.Sessions:
            data = session.info(route_value, action, timeout)
        read_path_capability += data


instrument_type_id = '_niSwitch'


def get_all_instruments_names(tsm_context: TSMContext):
    instrument_names, channel_group_ids, channel_lists = tsm_context.get_custom_instrument_names(instrument_type_id)
    return instrument_names, channel_group_ids  # TODO CHECK for better equivalent


def get_all_sessions(tsm_context: TSMContext):
    sessions = tsm_context.get_all_relay_driver_niswitch_sessions()
    list_of_sessions = []
    for session in sessions:
        list_of_sessions.append(session)
    return list_of_sessions


def pin_to_sessions_session_info(tsm_context: TSMContext, pin: str = ''):
    try:
        session, relay_names = tsm_context.relays_to_relay_driver_niswitch_sessions(pin)
        # TODO CHECK for better equivalent
        return Session(session, pin, relay_names)
    except Exception:
        # TODO what should it return
        return None
    # pin_query_context,session_data,channel_group_ids,channel_lists =
    # tsm_context.pins_to_custom_sessions(instrument_type_id, pin)


def set_sessions(tsm_context: TSMContext, switch_name: str, session: niswitch.Session, channel_group_id: str):
    tsm_context.set_relay_driver_niswitch_session(switch_name, session)  # TODO CH_GROUP_ID not requiered?


def close_sessions(tsm_context: TSMContext):
    sessions = get_all_sessions(tsm_context)
    # TODO first part is requiered?
    for session in sessions:
        session.close()


def name_to_topology(name: str = ''):
    if name.lower().index('matrix_2738') == 0:
        return Topology.matrix_2738
    elif name.lower().index('mux_2525') == 0:
        return Topology.mux_2525
    elif name.lower().index('matrix_2503') == 0:
        return Topology.matrix_2503
    else:
        return ''


def initialize_sessions(tsm_context: TSMContext):
    switch_name = ''
    session_list = []
    instrument_names, channel_group_ids = get_all_instruments_names(tsm_context)
    for name, channel_id in zip(instrument_names, channel_group_ids):
        if name != switch_name:
            topology = name_to_topology(name)
            handle = niswitch.Session(name, topology)
            session_list.append(handle)
    return session_list
