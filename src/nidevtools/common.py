import nitsm.codemoduleapi

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
