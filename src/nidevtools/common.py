import nitsm.codemoduleapi
import re
import enum
import typing
from nitsm.codemoduleapi import SemiconductorModuleContext
from nitsm.pinquerycontexts import PinQueryContext

_pin_names = []  # pin cache
_pin_types = []  # pin type cache


# class _Pin:
#     def __init__(self, name):
#         self._name = name
#
#     @property
#     def name(self):
#         return self._name
#
#     def __eq__(self, other):
#         return self.name == other.name
#
#
# class DutPin(_Pin):
#     pass
#
#
# class SystemPin(_Pin):
#     pass
#
#
# class PinGroup(_Pin):
#     pass


class PinType(enum.Enum):
    DUT_PIN = 0
    r"""
    This pin belongs to the device under test
    """
    SYSTEM_PIN = 1
    r"""
    system pin belongs to the PCB for powering up components
    """
    PIN_GROUP = 2
    r"""
    Pin Group is logical grouping of pins with similar attributes
    """
    NOT_DETERMINED = 3
    r"""
    This pin type is not defined 
    """


class PinInformation(typing.NamedTuple):
    # pin: _Pin
    pin: str
    type: PinType
    count: int


class ExpandedPinInformation(typing.NamedTuple):
    # pin: _Pin
    pin: str
    type: PinType
    index: int


def channel_list_to_pins(channel_list: str):
    sites_and_pins = []
    sites = []
    pins = []
    for pin in channel_list.split(","):
        clean_pin = pin.strip()
        sites_and_pins.append(clean_pin)
        a = re.split(r"[/\\]", clean_pin, 2)
        if len(a) >= 2:
            sites.append(int(a[0][4:]))
            pins.append(a[1])
        else:
            sites.append(-1)
            pins.append(a[0])
    return sites_and_pins, sites, pins


@nitsm.codemoduleapi.code_module
def get_all_pins(tsm_context: SemiconductorModuleContext, reload_cache=False):
    """Returns all pins and its types (DUT or system) available in the Semiconductor Module context.
    Maintains a cache of these pin details and reloads them when requested or required."""
    global _pin_names, _pin_types
    # rebuild cache if empty
    if len(_pin_names) == 0 or reload_cache:
        dut_pins, system_pins = tsm_context.get_pin_names()
        dut_pin_types = [PinType.DUT_PIN] * len(dut_pins)
        system_pin_types = [PinType.SYSTEM_PIN] * len(system_pins)
        _pin_names = dut_pins + system_pins
        _pin_types = dut_pin_types + system_pin_types
    return _pin_names, _pin_types


def get_pin_names_from_expanded_pin_information(
    expanded_pin_info: typing.List[ExpandedPinInformation],
):
    return [pin_info.pin for pin_info in expanded_pin_info]


def get_dut_pins_and_system_pins_from_expanded_pin_list(
    expanded_pin_info: typing.List[ExpandedPinInformation],
):
    dut_pins = []
    system_pins = []
    for pin in expanded_pin_info:
        if pin.type == PinType.DUT_PIN:
            dut_pins.append(pin)
        elif pin.type == PinType.SYSTEM_PIN:
            system_pins.append(pin)
    return dut_pins, system_pins


@nitsm.codemoduleapi.code_module
def expand_pin_groups_and_identify_pin_types(tsm_context: SemiconductorModuleContext, pins_in):
    pins_temp, pin_types_temp = get_all_pins(tsm_context)
    pins_info = []
    pins_expanded = []
    i = 0
    for d_pin in pins_in:
        if d_pin in pins_temp:
            index_d = pins_temp.index(d_pin)
            d_pin_type = pin_types_temp[index_d]
            count = 1
            pin_expanded = ExpandedPinInformation(d_pin, d_pin_type, i)
            pins_expanded.append(pin_expanded)
        else:
            d_pin_type = PinType.PIN_GROUP
            temp_exp_pins = tsm_context.get_pins_in_pin_groups(d_pin)  # This works fine
            count = len(temp_exp_pins)
            for a_pin in temp_exp_pins:
                index_a = pins_temp.index(a_pin)
                a_pin_type = pin_types_temp[index_a]
                pin_expanded = ExpandedPinInformation(a_pin, a_pin_type, i)  # Found bug here due to class & fixed it.
                pins_expanded.append(pin_expanded)
        pin_info = PinInformation(d_pin, d_pin_type, count)
        pins_info.append(pin_info)
        i += 1
    pins_expanded = remove_duplicates_from_tsm_pin_information_array(pins_info, pins_expanded)
    return pins_info, pins_expanded


def remove_duplicates_from_tsm_pin_information_array(
    pins_info: typing.List[PinInformation], pins_expanded: typing.List[ExpandedPinInformation]
):
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


def select_between_expanded_pin_information_options(
    current: ExpandedPinInformation,
    duplicate: ExpandedPinInformation,
    pin_group_info: typing.List[PinInformation],
):
    a = pin_group_info[current.index].type
    b = pin_group_info[duplicate.index].type
    flag = (a != PinType.PIN_GROUP) and (b == PinType.PIN_GROUP)
    if flag:
        best_choice = current
    else:
        best_choice = duplicate
    return best_choice


def pin_query_context_to_channel_list(
    pin_query_context: PinQueryContext,
    expanded_pin_info: typing.List[ExpandedPinInformation],
    sites: typing.List[int],
):
    """
    provides the p.
    """
    tsm_context = pin_query_context._tsm_context
    tsm_context1 = nitsm.codemoduleapi.SemiconductorModuleContext(tsm_context)
    if not sites:
        """Get site numbers if not provided"""
        sites = list(tsm_context1.site_numbers)
    if expanded_pin_info:
        pins = [pin_info.pin for pin_info in expanded_pin_info]
        pin_types = [pin_info.type for pin_info in expanded_pin_info]
    else:
        """
        The list of pins from Pin Query Context Read Pins
        doesn't expand pin groups, it only contains the
        initial strings provided to pins to sessions

        If a pin group is found when identifying pin types,
        expand pin groups
        """
        pins = pin_query_context._pins
        pin_types, pins = _check_for_pin_group(tsm_context, pins)
    (
        num_pins_per_channel_group,
        channel_group_indices,
        channel_indices,
    ) = tsm_context.GetChannelGroupAndChannelIndex(pins=pins)
    channel_group_indices = tuple(zip(*channel_group_indices))  # transpose(channel_group_indices)
    channel_indices = tuple(zip(*channel_indices))  # transpose(channel_indices)
    data = []
    for pin_count in num_pins_per_channel_group:
        pin_str = [""]
        pins_array = pin_str * pin_count
        data.append(pins_array)

    for site_number, channel_group_index_s, channel_index_s in zip(sites, channel_group_indices, channel_indices):
        for channel_group_index, channel_index, pin, pin_type in zip(
            channel_group_index_s, channel_index_s, pins, pin_types
        ):
            if pin_type == PinType.SYSTEM_PIN:
                data[channel_group_index][channel_index] = str(pin)
            else:
                if data[channel_group_index][channel_index]:
                    temp = data[channel_group_index][channel_index].split("/")
                    data[channel_group_index][channel_index] = temp[0] + "+" + str(site_number) + "/" + temp[1]
                else:
                    data[channel_group_index][channel_index] = "Site" + str(site_number) + "/" + pin
    per_session_pin_list = []
    for row in data:
        row_data = ""
        for column in row:
            if column:
                if row_data == "":
                    row_data = column
                else:
                    row_data = row_data + "," + column
        per_session_pin_list.append(row_data.strip())
    return sites, per_session_pin_list


@nitsm.codemoduleapi.code_module
def identify_pin_types(
    tsm_context: SemiconductorModuleContext, pins_or_pins_group: typing.Union[str, typing.Sequence[str]]
):
    all_pin_names, all_pin_types = get_all_pins(tsm_context)
    pin_group_found = False
    pin_types = []
    for pin in pins_or_pins_group:
        if pin in all_pin_names:
            temp_index = all_pin_names.index(pin)
            pin_type = all_pin_types[temp_index]
        else:
            pin_type = PinType.PIN_GROUP
            pin_group_found = True
        pin_types.append(pin_type)
    return pin_types, pin_group_found


@nitsm.codemoduleapi.code_module
def _check_for_pin_group(
    tsm_context: SemiconductorModuleContext,
    pins_or_pins_group: typing.Union[str, typing.Sequence[str]],
):
    pins = pins_or_pins_group
    pins_types, pin_group_found = identify_pin_types(tsm_context, pins_or_pins_group)
    if pin_group_found:
        pins = tsm_context.get_pins_in_pin_groups(pins_or_pins_group)
        pins_types, _ = identify_pin_types(tsm_context, pins)
    return pins_types, pins
