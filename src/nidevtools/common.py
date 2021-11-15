import nitsm.codemoduleapi
import re
import enum
import typing
from nitsm.codemoduleapi import SemiconductorModuleContext


_pins = []  # pin cache
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
    """todo(smooresni): Future docstring."""
    global _pins, _pin_types
    # rebuild cache if empty
    if not _pins or reload_cache:
        dut_pin_names, system_pin_names = tsm_context.get_pin_names()
        _pins = []  # reset to empty list in case reload_cache is true
        # _pins.extend(DutPin(dut_pin_name) for dut_pin_name in dut_pin_names)
        # _pins = [DutPin(dut_pin_name) for dut_pin_name in dut_pin_names] # disabled the class wrapper
        # _pins.extend([SystemPin(system_pin_name) for system_pin_name in system_pin_names]) # disabled the classwrapper
        _pins = dut_pin_names + system_pin_names
        _pin_types = [PinType.DUT_PIN] * len(dut_pin_names)
        _pin_types.extend(([PinType.SYSTEM_PIN] * len(system_pin_names)))
    return _pins, _pin_types


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
    pin_query_context: typing.Any,
    expanded_pin_info: typing.List[ExpandedPinInformation],
    site_numbers: typing.List[int],
):
    """
    Todo - find a way to fix the site number issue.For now assume that if site number is not passed
    no site is selected i.e. empty site array.
    """
    tsm_context = pin_query_context._tsm_context
    if not site_numbers:
        try:
            site_numbers = list(tsm_context.site_numbers())
            # print(site_numbers)  # Need to test this case after bug fix
        except Exception:
            site_numbers = []
    if expanded_pin_info:
        pins = [pin_info.pin for pin_info in expanded_pin_info]
        pin_types = [pin_info.type for pin_info in expanded_pin_info]
    else:
        pins = pin_query_context._pins
        pin_types, pin_group_found = identify_pin_types(tsm_context, pins)
        if pin_group_found:
            pins = tsm_context.get_pins_in_pin_groups(pins)
            pin_types, pin_group_found = identify_pin_types(tsm_context, pins)
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

    for site_number, channel_group_index_s, channel_index_s in zip(
        site_numbers, channel_group_indices, channel_indices
    ):
        for channel_group_index, channel_index, pin, pin_type in zip(
            channel_group_index_s, channel_index_s, pins, pin_types
        ):
            if pin_type == PinType.SYSTEM_PIN:
                data[channel_group_index][channel_index] = str(pin)
            else:
                if data[channel_group_index][channel_index]:
                    temp = data[channel_group_index][channel_index].split("/")
                    data[channel_group_index][channel_index] = (
                        temp[0] + "+" + str(site_number) + "/" + temp[1]
                    )
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
    return per_session_pin_list, site_numbers


@nitsm.codemoduleapi.code_module
def identify_pin_types(tsm_context: SemiconductorModuleContext, pins):
    all_pins, all_pin_types = get_all_pins(tsm_context)
    pin_group_found = False
    pin_types = []
    for pin in pins:
        if pin in all_pins:
            temp_index = all_pins.index(pin)
            pin_type = all_pin_types[temp_index]
        else:
            pin_type = PinType.PIN_GROUP
            pin_group_found = True
        pin_types.append(pin_type)
    return pin_types, pin_group_found
