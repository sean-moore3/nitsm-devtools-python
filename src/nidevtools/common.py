import nitsm.codemoduleapi
import re
import enum
import typing


_SemiconductorModuleContext = nitsm.codemoduleapi.SemiconductorModuleContext

_pins = []  # pin cache
_pin_types = []  # pin type cache


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
    global _pins, _pin_types
    # rebuild cache if empty
    if not _pins or reload_cache:
        dut_pin_names, system_pin_names = tsm_context.get_pin_names()
        _pins = []  # reset to empty list in case reload_cache is true
        _pin_types = []
        _pins.extend(DutPin(dut_pin_name) for dut_pin_name in dut_pin_names)
        _pins.extend(SystemPin(system_pin_name) for system_pin_name in system_pin_names)
        _pin_types.extend(PinType.DUT_PIN for dut_pin_name in dut_pin_names)
        _pin_types.extend(PinType.SYSTEM_PIN for system_pin_name in system_pin_names)
    return _pins, _pin_types


@nitsm.codemoduleapi.code_module
def get_pin_names_from_expanded_pin_information(expanded_pin_info: typing.List[ExpandedPinInformation]):
    return [pin_info.pin for pin_info in expanded_pin_info]


@nitsm.codemoduleapi.code_module
def get_dut_pins_and_system_pins_from_expanded_pin_list(expanded_pin_info: typing.List[ExpandedPinInformation]):
    dut_pins = []
    system_pins = []
    for pin in expanded_pin_info:
        if pin.type == PinType.DUT_PIN:
            dut_pins.append(pin)
        elif pin.type == PinType.SYSTEM_PIN:
            system_pins.append(pin)
    return dut_pins, system_pins


@nitsm.codemoduleapi.code_module
def expand_pin_groups_and_identify_pin_types(tsm_context: _SemiconductorModuleContext, pins_in):
    pins_temp, pin_types_temp = get_all_pins(tsm_context)
    pin_type_out = []
    count_out = []
    pins_out = []
    pin_type_ex_out = []
    index_out = []
    i = 0
    for d_pin in pins_in:
        if d_pin in pins_temp:
            index_d = pins_temp.index(d_pin)
            d_pin_type = pin_types_temp[index_d]
            pin_type_out.append(d_pin_type)
            count_out.append(1)
            pin_type_ex_out.append(d_pin_type)

            index_out.append(i)
            pins_out.append(d_pin)
        else:
            pin_type_out.append(PinType.PIN_GROUP)
            temp_exp_pins = tsm_context.get_pins_in_pin_groups(d_pin)
            count_out.append(len(temp_exp_pins))
            pins_out.extend(temp_exp_pins)
            for a_pin in temp_exp_pins:
                index_a = pins_temp.index(a_pin)
                a_pin_type = pin_types_temp[index_a]
                index_out.append(i)
                pin_type_ex_out.append(a_pin_type)
        i += 1

    pins_info = zip(pins_in, pin_type_out, count_out)
    pins_expanded = zip(pins_out, pin_type_ex_out, index_out)
    pins_expanded = remove_duplicates_from_tsm_pin_information_array(pins_info, pins_expanded)
    return pins_info, pins_expanded


@nitsm.codemoduleapi.code_module
def remove_duplicates_from_tsm_pin_information_array(pins_info: typing.List[PinInformation],
                                                     pins_expanded: typing.List[ExpandedPinInformation]):
    temp_pins = []
    temp_pins_expanded = []
    for pin_exp in pins_expanded:
        if pin_exp.pin in temp_pins:
            temp_index = temp_pins.index(pin_exp)
            temp_pin_info = temp_pins_expanded[temp_index]
            select_between_expanded_pin_information_options(temp_pin_info, pin_exp, pins_info)
            temp_pins_expanded[temp_index] = temp_pin_info
        else:
            temp_pins.append(pin_exp.pin)
            temp_pins_expanded.append(pin_exp)
    return temp_pins_expanded


@nitsm.codemoduleapi.code_module
def select_between_expanded_pin_information_options(current: ExpandedPinInformation,
                                                    duplicate: ExpandedPinInformation,
                                                    pin_group_info: typing.List[PinInformation]):
    a = pin_group_info[current.index].type
    b = pin_group_info[duplicate.index].type
    flag = (a != PinType.PIN_GROUP) and (b == PinType.PIN_GROUP)
    if flag:
        best_choice = current
    else:
        best_choice = duplicate
    return best_choice


def pin_query_context_to_channel_list(pin_query_context: typing.Any,
                                      expanded_pin_info: typing.List[ExpandedPinInformation],
                                      site_numbers: typing.List[int]):
    per_session_channel_list = []
    # to do develop functionality
    pin_query_context.get_ch
    return per_session_channel_list, site_numbers
