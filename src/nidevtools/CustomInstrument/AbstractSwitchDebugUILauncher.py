import sys

import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

from PyQt5 import QtWidgets

from src.nidevtools import UI_Debug_AbstractSwitch


@nitsm.codemoduleapi.code_module
def run_ui(tsm: SMContext):
    app = QtWidgets.QApplication(sys.argv)

    UI_Debug_AbstractSwitch.tsm_context = tsm

    AbstractSwitchDebugWindow = UI_Debug_AbstractSwitch.MainWindow(tsm)
    ui_abstract_switch_debug_window = UI_Debug_AbstractSwitch.UiAbstractSwitchDebugWindow()
    ui_abstract_switch_debug_window.setup_ui(AbstractSwitchDebugWindow)

    AbstractSwitchDebugWindow.show()
    sys.exit(app.exec_())
