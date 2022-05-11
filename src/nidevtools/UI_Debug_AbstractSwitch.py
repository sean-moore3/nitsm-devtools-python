import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QMessageBox, QMainWindow
import threading
from . import abstract_switch
import nitsm.codemoduleapi
from nitsm.codemoduleapi import SemiconductorModuleContext as SMContext


class TimeoutThread(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._is_running = True

    def run(self):
        while self._is_running:
            time.sleep(0.5)
            print("TimeOut Event Occurred")

    def stop(self):
        self._is_running = False


@nitsm.codemoduleapi.code_module
class MainWindow(QMainWindow):
    def __init__(self, tsm: SMContext):
        super().__init__()
        self.tsm_context = tsm
        self.timeoutThread = TimeoutThread()
        self.timeoutThread.start()

    def exit_app(self):
        print("Shortcut pressed")
        self.close()

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        self.timeoutThread.stop()
        print("you just closed the pyqt window!!!")


class UiAbstractSwitchDebugWindow(object):
    def __init__(self):
        self.main_window = None
        self.central_widget = None
        self.push_button_configure_mux = None
        self.push_button_new_mux_state = None
        self.push_button_disable_all = None
        self.label_new_mux_state = None
        self.label_update_time = None
        self.label_pin_name_filter = None
        self.label_view = None
        self.label_status = None
        self.line_edit_update_time = None
        self.line_edit_pin_name_filter = None
        self.line_edit_view = None
        self.line_edit_status = None

    def setup_ui(self, main_window):
        self.main_window = main_window
        self.main_window.setObjectName("Abstract Switch Debug Tool")
        self.main_window.setWindowTitle("Abstract Switch Debug Tool")
        self.main_window.resize(1200, 694)
        self.main_window.setMinimumSize(QtCore.QSize(1200, 694))
        self.main_window.setMaximumSize(QtCore.QSize(1200, 694))
        self.central_widget = QtWidgets.QWidget(self.main_window)
        self.central_widget.setObjectName("central_widget")

        self.label_new_mux_state = QtWidgets.QLabel(self.central_widget)
        self.label_new_mux_state.setGeometry(QtCore.QRect(150, 0, 200, 40))
        self.label_new_mux_state.setAlignment(QtCore.Qt.AlignCenter)
        self.label_new_mux_state.setObjectName("label_new_mux_state")
        self.label_new_mux_state.setText("New MUX State")

        self.label_update_time = QtWidgets.QLabel(self.central_widget)
        self.label_update_time.setGeometry(QtCore.QRect(310, 0, 200, 40))
        self.label_update_time.setAlignment(QtCore.Qt.AlignCenter)
        self.label_update_time.setObjectName("label_update_time")
        self.label_update_time.setText("UI Update Time")

        self.label_pin_name_filter = QtWidgets.QLabel(self.central_widget)
        self.label_pin_name_filter.setGeometry(QtCore.QRect(520, 0, 150, 40))
        self.label_pin_name_filter.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_pin_name_filter.setAlignment(QtCore.Qt.AlignCenter)
        self.label_pin_name_filter.setObjectName("label_pin_name_filter")
        self.label_pin_name_filter.setText("PIN Name Filter")

        self.label_view = QtWidgets.QLabel(self.central_widget)
        self.label_view.setGeometry(QtCore.QRect(680, 0, 160, 40))
        self.label_view.setAlignment(QtCore.Qt.AlignCenter)
        self.label_view.setObjectName("label_view")
        self.label_view.setText("View")

        self.label_status = QtWidgets.QLabel(self.central_widget)
        self.label_status.setGeometry(QtCore.QRect(1000, 0, 160, 40))
        self.label_status.setAlignment(QtCore.Qt.AlignCenter)
        self.label_status.setObjectName("label_status")
        self.label_status.setText("Status")

        self.line_edit_update_time = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_update_time.setEnabled(False)
        self.line_edit_update_time.setGeometry(QtCore.QRect(310, 40, 200, 40))
        self.line_edit_update_time.setObjectName("line_edit_update_time")
        self.line_edit_update_time.setText("0")

        self.line_edit_pin_name_filter = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_pin_name_filter.setGeometry(QtCore.QRect(520, 40, 150, 40))
        self.line_edit_pin_name_filter.setObjectName("line_edit_pin_name_filter")
        self.line_edit_pin_name_filter.textChanged.connect(self.pin_name_filter_value_changed)

        self.cb_view = QtWidgets.QComboBox(self.central_widget)
        self.cb_view.setGeometry(QtCore.QRect(680, 40, 160, 40))
        self.cb_view.setObjectName("cb_view")
        self.cb_view.addItems(["DMM Pins", "SMU Pins", "Scope Pins", "All Pins", "Abstract Pins"])
        self.cb_view.currentTextChanged.connect(self.cb_view_value_changed)

        self.line_edit_status = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_status.setEnabled(False)
        self.line_edit_status.setGeometry(QtCore.QRect(1000, 40, 160, 40))
        self.line_edit_status.setObjectName("line_edit_status")

        self.push_button_configure_mux = QtWidgets.QPushButton(self.central_widget)
        self.push_button_configure_mux.setGeometry(QtCore.QRect(20, 40, 170, 40))
        self.push_button_configure_mux.setObjectName("push_button_configure_mux")
        self.push_button_configure_mux.setText("Configure MUX")
        self.push_button_configure_mux.clicked.connect(self.configure_mux_button_clicked)

        self.push_button_new_mux_state = QtWidgets.QPushButton(self.central_widget)
        self.push_button_new_mux_state.setGeometry(QtCore.QRect(200, 40, 100, 40))
        self.push_button_new_mux_state.setObjectName("push_button_new_mux_state")
        self.push_button_new_mux_state.setText("OK")
        self.push_button_new_mux_state.clicked.connect(self.new_mux_state_button_clicked)

        self.push_button_disable_all = QtWidgets.QPushButton(self.central_widget)
        self.push_button_disable_all.setGeometry(QtCore.QRect(850, 40, 140, 40))
        self.push_button_disable_all.setObjectName("push_button_disable_all")
        self.push_button_disable_all.setText("Disable All")
        self.push_button_disable_all.clicked.connect(self.disable_all_button_clicked)

        self.tableWidget = QtWidgets.QTableWidget(self.central_widget)
        self.tableWidget.setGeometry(QtCore.QRect(10, 100, 1150, 571))
        self.tableWidget.setRowCount(27)
        self.tableWidget.setColumnCount(6)
        self.tableWidget.setObjectName("tableWidget")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item.setText("PIN Name")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item.setText("Instrument Name")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item.setText("Channel")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item.setText("Muxed Instrument")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(4, item)
        item.setText("Muxed Instrument Resource")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(5, item)
        item.setText("Status")
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(280)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setCascadingSectionResizes(True)
        self.tableWidget.verticalHeader().setDefaultSectionSize(23)

        self.main_window.setCentralWidget(self.central_widget)
        QtCore.QMetaObject.connectSlotsByName(self.main_window)

    def configure_mux_button_clicked(self):
        QMessageBox.about(self.main_window, "Message", "Configure MUX button Clicked")

    def new_mux_state_button_clicked(self):
        QMessageBox.about(self.main_window, "Message", "New Mux button Clicked")

    def disable_all_button_clicked(self, ref):
        # abstract_switch.pin_fgv(ref, action=abstract_switch.Control.disconnect_all)
        QMessageBox.about(self.main_window, "Message", "Disable All button Clicked")

    def pin_name_filter_value_changed(self, typed_str, arr_of_str: [str] = None):
        typed_str = typed_str.upper()
        matched_strings = []
        if typed_str != "":
            for st in arr_of_str:
                if st.upper().find(typed_str) != -1:
                    matched_strings.append(st)

        print(matched_strings)

    def cb_view_value_changed(self, value_of_cb, arr_of_str=None, ref=None):
        if value_of_cb == "All Pins":
            pass
            # todo  call the tsm.filter_pins_by_instrument_type("abstinst") with right arguments
        if value_of_cb == "Abstract Pins":
            pass
            # todo  call the tsm.filter_pins_by_instrument_type("abstinst") with right arguments
        if value_of_cb == "Scope Pins":
            pass
            # todo  call the tsm.filter_pins_by_instrument_type("niScope") with right arguments
        if value_of_cb == "SMU Pins":
            pass
            # todo  call the tsm.filter_pins_by_instrument_type("niDCPower") with right arguments
        if value_of_cb == "DMM Pins":
            print("cb_view_value_changed " + value_of_cb)
            # todo  call the tsm.filter_pins_by_instrument_type("niDMM") with right arguments
