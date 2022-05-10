from PyQt5 import QtWidgets

import UI_Debug_AbstractSwitch
import UI_Debug_FPGA

if __name__ == "__main__":
    import sys

    app = QtWidgets.QApplication(sys.argv)

    AbstractSwitchDebugWindow = UI_Debug_AbstractSwitch.MainWindow()
    ui_abstract_switch_debug_window = UI_Debug_AbstractSwitch.UiAbstractSwitchDebugWindow()
    ui_abstract_switch_debug_window.setup_ui(AbstractSwitchDebugWindow)

    FPGADebugWindow = UI_Debug_FPGA.MainWindow()
    ui_fpga_debug_window = UI_Debug_FPGA.UiFPGADebugWindow()
    ui_fpga_debug_window.setup_ui(FPGADebugWindow)

    AbstractSwitchDebugWindow.show()
    FPGADebugWindow.show()
    sys.exit(app.exec_())
