from PyQt5 import QtWidgets

from . import UI_Debug_AbstractSwitch, UI_Debug_FPGA
from UI_Debug_AbstractSwitch import UiAbstractSwitchDebugWindow
from UI_Debug_FPGA import UiFPGADebugWindow

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    AbstractSwitchDebugWindow = AbstractSwitchDebugTool.MainWindow()
    ui_abstract_switch_debug_window = UiAbstractSwitchDebugWindow()
    ui_abstract_switch_debug_window.setup_ui(AbstractSwitchDebugWindow)

    FPGADebugWindow = FPGADebugTool.MainWindow()
    ui_fpga_debug_window = UiFPGADebugWindow()
    ui_fpga_debug_window.setup_ui(FPGADebugWindow)

    AbstractSwitchDebugWindow.show()
    FPGADebugWindow.show()
    sys.exit(app.exec_())
