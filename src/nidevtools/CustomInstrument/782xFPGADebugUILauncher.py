import sys

import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext

from PyQt5 import QtWidgets

from src.nidevtools import UI_Debug_FPGA


@nitsm.codemoduleapi.code_module
def run_ui(tsm: SMContext):
    app = QtWidgets.QApplication(sys.argv)

    FPGADebugWindow = UI_Debug_FPGA.MainWindow(tsm)
    ui_fpga_debug_window = UI_Debug_FPGA.UiFPGADebugWindow()
    ui_fpga_debug_window.setup_ui(FPGADebugWindow)

    FPGADebugWindow.show()
    sys.exit(app.exec_())
