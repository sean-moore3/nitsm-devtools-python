import nitsm.codemoduleapi
import re
import enum
import typing


_SemiconductorModuleContext = nitsm.codemoduleapi.SemiconductorModuleContext

_pins = []  # pin cache


class _Pin:
    def __init__(self, name):
        self._name = name

    @property
    def name(self):
        return self._name

    def __eq__(self, other):
        return self.name == other.name


class DutPin(_Pin):
    pass


class SystemPin(_Pin):
    pass


class PinGroup(_Pin):
    pass


class PinType(enum.Enum):
    DUT_PIN = 0
    r'''
    This pin belongs to the device under test
    '''
    SYSTEM_PIN = 1
    r'''
    system pin belongs to the PCB for powering up components
    '''
    PIN_GROUP = 2
    r'''
    Pin Group is logical grouping of pins with similar attributes
    '''
    NOT_DETERMINED = 3
    r'''
    This pin type is not defined 
    '''


class PinInformation(typing.NamedTuple):
    pin: _Pin
    type: PinType
    count: int


class ExpandedPinInformation(typing.NamedTuple):
    pin: _Pin
    type: PinType
    index: int


def channel_list_to_pins(channel_list: str):
    sites_and_pins = []
    sites = []
    pins = []
    for pin in channel_list.split(","):
        clean_pin = pin.strip()
        sites_and_pins.append(clean_pin)
        a = re.split(r'[/\\]', clean_pin, 2)
        if len(a) >= 2:
            sites.append(int(a[0][4:]))
            pins.append(a[1])
        else:
            sites.append(-1)
            pins.append(a[0])
    return sites_and_pins, sites, pins


@nitsm.codemoduleapi.code_module
def get_all_pins(tsm_context: _SemiconductorModuleContext, reload_cache=False):
    """todo(smooresni): Future docstring."""
    global _pins
    # rebuild cache if empty
    if not _pins or reload_cache:
        dut_pin_names, system_pin_names = tsm_context.get_pin_names()
        _pins = []  # reset to empty list in case reload_cache is true
        _pins.extend(DutPin(dut_pin_name) for dut_pin_name in dut_pin_names)
        _pins.extend(SystemPin(system_pin_name) for system_pin_name in system_pin_names)
    return _pins


def get_pin_names_from_expanded_pin_information(expanded_pin_info: typing.List[ExpandedPinInformation]):
    return [pin_info.pin for pin_info in expanded_pin_info]


def get_dut_pins_and_system_pins_from_expanded_pin_list(expanded_pin_info: typing.List[ExpandedPinInformation]):
    dut_pins = []
    system_pins = []
    for pin in expanded_pin_info:
        if pin.type == PinType.DUT_PIN:
            dut_pins.append(pin)
        elif pin.type == PinType.SYSTEM_PIN:
            system_pins.append(pin)
    return dut_pins, system_pins


def expand_pin_groups_and_identify_pin_types(tsm_context: _SemiconductorModuleContext, pins):
    pins_info = []
    pins_expanded = []
    return pins_info, pins_expanded


def pin_query_context_to_channel_list(pin_query_context: typing.Any,
                                      expanded_pin_info: typing.List[ExpandedPinInformation],
                                      site_numbers: typing.List[int]):
    per_session_channel_list = []
    return per_session_channel_list, site_numbers
