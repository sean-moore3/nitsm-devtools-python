"""
This is niswitch wrapper for use with STS test codes
"""
import typing
from enum import Enum

import niswitch
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext


class Action(Enum):
    """
    Switch Actions

    Args:
        Enum: Inherits from enum class
    """

    Disconnect = 0
    Connect = 1
    Disconnect_All = 2
    Read = 3


class Topology(typing.NamedTuple):
    """
    Currently supports 3 topologies need to add rest of the topologies for more general code

    Args:
        typing (tuple): topology and the names
    """

    matrix_2738 = "2738/2-Wire 8x32 Matrix"
    mux_2525 = "2525/2-Wire Octal 8x1 Mux"
    matrix_2503 = "2503/2-Wire 4x6 Matrix"


class Session(typing.NamedTuple):
    """
    Class to store on session

    Args:
        typing (tuple): session, pin, channel

    Returns:
        session_object: for one connection
    """

    Session: niswitch.Session
    Pin: str
    Channel: str

    def info(self, route_value: str, action: Action, timeout: int):
        """
        performs various actions like connect, disconnect or disconnect all.

        Args:
            route_value (str): list of Digital lines to drive
            action (Action): to be performed on the digital line
            timeout (int): time within which the operation needs to be finished

        Returns:
            list of path capability: can be connected or not connected is the path capability
        """
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
            midpoint = self.Session.can_connect(self.Channel, route_value)
            data.append(midpoint)
        return data


class MultipleSessions:
    """
    Class for storing multiple sessions

    Returns:
        object: containing list of sessions
    """

    sessions: typing.List[Session]

    def __init__(self, sessions: typing.List[Session]):
        """
        constructor to store the sessions

        Args:
            sessions (typing.List[Session]): list of sessions for the current context
        """
        self.sessions = sessions

    def action_session_info(
        self, route_value: str = "", action: Action = Action.Disconnect, timeout: int = 40
    ):
        """
        reads and returns the path capability

        Args:
            route_value (str, optional): comma separated list of "en_" routes. Defaults to "".
            action (Action, optional): connect or disconnect. Defaults to Action.Disconnect.
            timeout (int, optional): timeout for the operation in seconds. Defaults to 40.

        Returns:
            list of session: list of session for the connection
        """
        read_path_capability = []
        for session in self.sessions:
            # print(type(session))
            data = session.info(route_value, action, timeout)
            read_path_capability += data
        return read_path_capability


instrument_type_id = "_niSwitch"


@nitsm.codemoduleapi.code_module
def get_all_instruments_names(tsm: SMContext):
    """
    Returns all the switch based instruments in the tsm context

    Args:
        tsm (SMContext): Semiconductor module Reference from the TestStand.

    Returns:
        tuple : instrument_names, channel_group_ids
    """
    instrument_names, channel_group_ids, _ = tsm.get_custom_instrument_names(instrument_type_id)
    return instrument_names, channel_group_ids


@nitsm.codemoduleapi.code_module
def get_all_sessions(tsm: SMContext):
    """
    Gets a list of Switch references corresponding to the set sessions on TSM
    Context

    Args:
        tsm (SMContext): Semiconductor module Reference from the TestStand.

    Returns:
        list of sessions: all the switch sessions in the current context
    """
    session_data, _, _ = tsm.get_all_custom_sessions(instrument_type_id)
    list_of_sessions = []
    for session in session_data:
        list_of_sessions.append(session)
    return list_of_sessions


@nitsm.codemoduleapi.code_module
def pin_to_sessions_session_info(tsm: SMContext, pin: str = ""):
    """
    Returns a Switch Session object containing a list of switch sessions detailed on the pinmap

    Args:
        tsm (SMContext): Pin context defined by pin map
        pin (str, optional): The name of the pin to translate to a session. Defaults to "".

    Returns:
        session: An object that tracks the session associated with pin provided.
    """
    try:
        _, session_data, channel_group_id, _ = tsm.pins_to_custom_session(instrument_type_id, pin)
        relay_name = channel_group_id
        # TODO CHECK for better equivalent
        data = MultipleSessions([Session(session_data, pin, relay_name)])
        return data
    except Exception:
        return None
    # pin_query_context,session_data,channel_group_ids,channel_lists =
    # tsm.pins_to_custom_sessions(instrument_type_id, pin)


@nitsm.codemoduleapi.code_module
def set_sessions(tsm: SMContext, switch_name: str, session: niswitch.Session, channel_grp_id: str):
    """
    Adds the session to the list of switch sessions in tsm context

    Args:
        tsm (SMContext): Semiconductor module Reference from the TestStand.
        switch_name (str): name of the switch
        session (niswitch.Session): session created fo the switch
        channel_grp_id (str): unique id of the channel group
    """
    tsm.set_custom_session(instrument_type_id, switch_name, channel_grp_id, session)


@nitsm.codemoduleapi.code_module
def close_sessions(tsm: SMContext):
    """
    closes all the session associated with the switch drivers
    in the semiconductor module context.


    Args:
        tsm (SMContext): TestStand semiconductor module context
    """
    sessions = get_all_sessions(tsm)
    sessions_to_close = []
    for session in sessions:
        try:
            condition = sessions_to_close.index(session)
        except ValueError:
            condition = -1
        if condition == -1:
            sessions_to_close.append(session)
    for session in sessions_to_close:
        session.close()


def name_to_topology(name: str = ""):
    """
    converts the name to topology class object

    Args:
        name (str, optional): name of the topology in string. Defaults to "".

    Returns:
        Topology: multiplexer topology for the name provided.
    """
    if name.lower().find("matrix_2738") == 0:
        return Topology.matrix_2738
    elif name.lower().find("mux_2525") == 0:
        return Topology.mux_2525
    elif name.lower().find("matrix_2503") == 0:
        return Topology.matrix_2503
    else:
        return "Configured Topology"


@nitsm.codemoduleapi.code_module
def initialize_sessions(tsm: SMContext):
    """
    open sessions for all switch instrument channels that are defined in the pinmap associated with
     the tsm context

    Args:
        tsm (SMContext): TestStand semiconductor module context
    """
    switch_name = ""
    instrument_names, channel_group_ids = get_all_instruments_names(tsm)
    for name, channel_id in zip(instrument_names, channel_group_ids):
        if name != switch_name:
            switch_name = name
            topology = name_to_topology(name)
            handle = niswitch.Session(name, topology)
            set_sessions(tsm, name, handle, channel_id)
