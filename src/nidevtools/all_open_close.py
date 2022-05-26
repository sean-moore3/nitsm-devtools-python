from . import abstract_switch
from . import daqmx
from . import dcpower
from . import digital
from . import dmm
from . import fgen
from . import fpga
# from . import relay
from . import scope
from . import switch
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

tsm_global: SMContext


def initialize_all(tsm: SMContext):
    abstract_switch.initialize(tsm)
    daqmx.set_task(tsm)
    dcpower.initialize_sessions(tsm)
    dmm.initialize_session(tsm)
    digital.initialize_sessions(tsm)
    fgen.initialize_sessions(tsm)
    fpga.initialize_sessions(tsm)
    scope.initialize_sessions(tsm)
    switch.initialize_sessions(tsm)
    global tsm_global
    tsm_global = tsm


def close_all(tsm: SMContext):
    abstract_switch.close_sessions(tsm)
    daqmx.clear_task(tsm)
    dcpower.close_sessions(tsm)
    dmm.close_session(tsm)
    digital.close_sessions(tsm)
    fgen.close_sessions(tsm)
    fpga.close_sessions(tsm)
    scope.initialize_sessions(tsm)
    switch.close_sessions(tsm)

