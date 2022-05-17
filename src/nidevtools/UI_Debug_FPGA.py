import sys
import threading

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QMessageBox, QMainWindow
from typing import List
# import digital
# import fpga

# fpga_ref = fpga.TSMFPGA()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

    def exit_app(self):
        print("Shortcut pressed")
        self.close()

    def closeEvent(self, *args, **kwargs):
        super().closeEvent(*args, **kwargs)
        print("you just closed the UI window!!!")


class UiFPGADebugWindow(object):
    def __init__(self):
        self.cb_new_state: QtWidgets.QComboBox = None
        self.main_window = None
        self.central_widget = None
        self.push_button_update_command_state = None
        self.label_new_state = None
        self.label_update_time = None
        self.label_name_filter = None
        self.line_edit_update_time = None
        self.line_edit_name_filter: QtWidgets.QLineEdit = None
        self.tableWidget: QtWidgets.QTableWidget = None

    def setup_ui(self, main_window):
        self.main_window = main_window
        self.main_window.setObjectName("FPGA Debug Tool")
        self.main_window.setWindowTitle("FPGA Debug Tool")
        self.main_window.resize(940, 650)
        self.main_window.setMinimumSize(QtCore.QSize(940, 650))
        self.main_window.setMaximumSize(QtCore.QSize(940, 650))
        self.central_widget = QtWidgets.QWidget(self.main_window)
        self.central_widget.setObjectName("central_widget")

        self.label_new_state = QtWidgets.QLabel(self.central_widget)
        self.label_new_state.setGeometry(QtCore.QRect(280, 0, 160, 40))
        self.label_new_state.setAlignment(QtCore.Qt.AlignCenter)
        self.label_new_state.setObjectName("label_new_state")
        self.label_new_state.setText("New State")

        self.label_update_time = QtWidgets.QLabel(self.central_widget)
        self.label_update_time.setGeometry(QtCore.QRect(455, 0, 160, 40))
        self.label_update_time.setAlignment(QtCore.Qt.AlignCenter)
        self.label_update_time.setObjectName("label_update_time")
        self.label_update_time.setText("UI Update Time")

        self.label_name_filter = QtWidgets.QLabel(self.central_widget)
        self.label_name_filter.setGeometry(QtCore.QRect(640, 0, 281, 40))
        self.label_name_filter.setLayoutDirection(QtCore.Qt.LeftToRight)
        self.label_name_filter.setAlignment(QtCore.Qt.AlignCenter)
        self.label_name_filter.setObjectName("label_name_filter")
        self.label_name_filter.setText("Name Filter")

        self.cb_new_state = QtWidgets.QComboBox(self.central_widget)
        self.cb_new_state.setGeometry(QtCore.QRect(280, 40, 160, 40))
        self.cb_new_state.setObjectName("cb_view")
        self.cb_new_state.addItems(["0", "1", "X"])

        self.line_edit_update_time = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_update_time.setEnabled(False)
        self.line_edit_update_time.setGeometry(QtCore.QRect(460, 40, 160, 40))
        self.line_edit_update_time.setObjectName("line_edit_update_time")
        self.line_edit_update_time.setText("0")

        self.line_edit_name_filter = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_name_filter.setGeometry(QtCore.QRect(640, 40, 281, 40))
        self.line_edit_name_filter.setObjectName("line_edit_name_filter")

        self.push_button_update_command_state = QtWidgets.QPushButton(self.central_widget)
        self.push_button_update_command_state.setGeometry(QtCore.QRect(20, 40, 240, 40))
        self.push_button_update_command_state.setObjectName("push_button_update_command_state")
        self.push_button_update_command_state.setText("Update Command State")
        self.push_button_update_command_state.clicked.connect(
            self.update_command_state_button_clicked
        )

        self.tableWidget = QtWidgets.QTableWidget(self.central_widget)
        self.tableWidget.setGeometry(QtCore.QRect(10, 100, 900, 541))
        self.tableWidget.setRowCount(25)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(4)
        self.init_table()
        self.tableWidget.horizontalHeader().setCascadingSectionResizes(True)
        self.tableWidget.horizontalHeader().setDefaultSectionSize(280)
        self.tableWidget.verticalHeader().setVisible(False)
        self.tableWidget.verticalHeader().setCascadingSectionResizes(True)
        self.tableWidget.verticalHeader().setDefaultSectionSize(23)

        self.main_window.setCentralWidget(self.central_widget)
        QtCore.QMetaObject.connectSlotsByName(self.main_window)

        self.qTimer = QTimer()
        self.qTimer.setInterval(250)
        self.qTimer.timeout.connect(self.timeout_event)
        self.qTimer.start()

    def update_command_state_button_clicked(self, cluster):
        # i = 0
        # output_site_numbers: str = ""
        # for ssc in fpga_ref.SSC:
        #     for site_number in digital._site_list_to_site_numbers(ssc.Channels):
        #         i += 1
        #         selectedRows: List[int] = []
        #         for selectedItem in self.tableWidget.selectedItems():
        #             try:
        #                 selectedRows.index(selectedItem.row())
        #             except:
        #                 selectedRows.append(selectedItem.row())
        #         try:
        #             if selectedRows.index(i) >= 0:
        #                 output_site_numbers += site_number + ","
        #         except:
        #             pass
        #
        #     output_site_numbers = output_site_numbers[:-1]
        #     output_site_numbers = output_site_numbers.strip()
        #     ssc.channels = output_site_numbers
        # print(selectedRows)
        # fpga_ref.write_static_array(str(self.cb_new_state.currentText()))
        self.timeout_event()

    def timeout_event(self):
        # typed_str = self.line_edit_name_filter.text()
        # typed_str = typed_str.upper()
        # typed_str = typed_str.strip()
        # if typed_str != "":
        #     for ssc in fpga_ref.SSC:
        #         arr_of_site_numbers = digital._site_list_to_site_numbers(ssc.Channels)
        #         arr_of_pins = digital._channel_list_to_pins(ssc.ChannelList)
        #         output_pins = ""
        #         output_site_numbers = ""
        #         for pin in arr_of_pins:
        #             if pin.upper().find(typed_str) != -1:
        #                 output_pins += pin + ","
        #                 output_site_numbers += arr_of_site_numbers[arr_of_pins.index(pin)] + ","
        #
        #         output_pins = output_pins[:-1]
        #         output_pins = output_pins.strip()
        #         output_site_numbers = output_site_numbers[:-1]
        #         output_site_numbers = output_site_numbers.strip()
        #         ssc.ChannelList = output_pins
        #         ssc.Channels = output_site_numbers
        #
        # fpga_ref.read_commanded_line_states()
        # self.tableWidget.setRowCount(fpga_ref.read_static())
        # for elem in fpga_ref.read_static():
        #     if elem:
        #         item = QtWidgets.QTableWidgetItem()
        #         self.tableWidget.setItem(fpga_ref.read_static().index(elem), 3, item)
        #         item.setText(str(1))
        #     else:
        #         item = QtWidgets.QTableWidgetItem()
        #         self.tableWidget.setItem(fpga_ref.read_static().index(elem), 3, item)
        #         item.setText(str(0))
        #     item = QtWidgets.QTableWidgetItem()
        #     self.tableWidget.setItem(fpga_ref.read_static().index(elem), 3, item)
        #     item.setText(str(0))

        print("Timeout Event")

    def init_table(self):

        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(0, item)
        item.setText("TSM Channel Name")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(1, item)
        item.setText("Device Channel")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(2, item)
        item.setText("Command Line State")
        item = QtWidgets.QTableWidgetItem()
        self.tableWidget.setHorizontalHeaderItem(3, item)
        item.setText("Line State")


def run_ui():
    app = QtWidgets.QApplication(sys.argv)
    fpga_window = MainWindow()
    fpga_debug_window = UiFPGADebugWindow()
    fpga_debug_window.setup_ui(fpga_window)
    fpga_window.show()
    sys.exit(app.exec_())


def load_ui_in_new_thread():

    th = threading.Thread(target=run_ui)
    try:
        th.start()
    except:
        pass


if __name__ == "__main__":
    run_ui()
