from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QTimer
from pyqtgraph import PlotWidget
import pyqtgraph as pg
import numpy as np

class UiSMUDebugWindow(object):

    def __init__(self):
        self.is_measurements_paused = False
        self.main_window = None
        self.central_widget = None
        self.label_pin = None
        self.label_read_timeout = None
        self.label_pause_measurements = None
        self.label_status = None
        self.label_pin_status_table = None
        self.label_error_messages = None
        self.label_voltage = None
        self.label_current = None
        self.line_edit_pin: QtWidgets.QLineEdit = None
        self.line_edit_read_timeout: QtWidgets.QLineEdit = None
        self.line_edit_status: QtWidgets.QLineEdit = None
        self.line_edit_error_messages: QtWidgets.QLineEdit = None
        self.push_button_add_remove = None
        self.push_button_add_all = None
        self.push_button_add_vin = None
        self.push_button_custom_list = None
        self.push_button_clear_list = None
        self.push_button_pause_measurements = None
        self.line = None
        self.tab_widget = None
        self.tab_table = None
        self.tab_graph = None
        self.table_widget: QtWidgets.QTableWidget = None
        self.graph_voltage = None
        self.graph_current = None
        self.q_timer = None

    def setup_ui(self, main_window):
        self.main_window = main_window
        self.main_window.setObjectName("SMU Debug Tool")
        self.main_window.setWindowTitle("SMU Debug Tool")
        self.main_window.resize(1650, 750)
        self.main_window.setMinimumSize(QtCore.QSize(1650, 750))
        self.main_window.setMaximumSize(QtCore.QSize(1650, 750))

        self.central_widget = QtWidgets.QWidget(self.main_window)
        self.central_widget.setObjectName("central_widget")

        self.tab_widget = QtWidgets.QTabWidget(self.central_widget)
        self.tab_widget.setGeometry(QtCore.QRect(10, 110, 1621, 631))
        self.tab_widget.setContextMenuPolicy(QtCore.Qt.PreventContextMenu)
        self.tab_widget.setAutoFillBackground(False)
        self.tab_widget.setObjectName("tab_widget")

        self.tab_table = QtWidgets.QWidget()
        self.tab_table.setObjectName("tab_table")
        self.tab_widget.addTab(self.tab_table, "Table")

        self.tab_graph = QtWidgets.QWidget()
        self.tab_graph.setObjectName("tab_graph")
        self.tab_widget.addTab(self.tab_graph, "Graphs")

        self.label_pin = QtWidgets.QLabel(self.central_widget)
        self.label_pin.setGeometry(QtCore.QRect(10, 5, 161, 20))
        self.label_pin.setAlignment(QtCore.Qt.AlignCenter)
        self.label_pin.setObjectName("label_pin")
        self.label_pin.setText("Pin")

        self.label_read_timeout = QtWidgets.QLabel(self.central_widget)
        self.label_read_timeout.setGeometry(QtCore.QRect(770, 5, 150, 20))
        self.label_read_timeout.setAlignment(QtCore.Qt.AlignCenter)
        self.label_read_timeout.setObjectName("label_read_timeout")
        self.label_read_timeout.setText("Read Timeout(mS)")

        self.label_pause_measurements = QtWidgets.QLabel(self.central_widget)
        self.label_pause_measurements.setGeometry(QtCore.QRect(890, 45, 171, 21))
        self.label_pause_measurements.setAlignment(QtCore.Qt.AlignCenter)
        self.label_pause_measurements.setObjectName("label_pause_measurements")
        self.label_pause_measurements.setText("Pause Measurements")

        self.label_status = QtWidgets.QLabel(self.central_widget)
        self.label_status.setGeometry(QtCore.QRect(1060, 5, 161, 21))
        font = QtGui.QFont()
        font.setPointSize(10)
        font.setBold(True)
        font.setWeight(75)
        self.label_status.setFont(font)
        self.label_status.setAlignment(QtCore.Qt.AlignCenter)
        self.label_status.setObjectName("label_status")
        self.label_status.setText("Status")

        self.label_pin_status_table = QtWidgets.QLabel(self.tab_table)
        self.label_pin_status_table.setGeometry(QtCore.QRect(20, 0, 91, 21))
        self.label_pin_status_table.setObjectName("label_pin_status_table")
        self.label_pin_status_table.setText("Pin Status Table")

        self.label_error_messages = QtWidgets.QLabel(self.tab_table)
        self.label_error_messages.setGeometry(QtCore.QRect(20, 510, 161, 31))
        font = QtGui.QFont()
        font.setPointSize(12)
        font.setBold(True)
        font.setWeight(75)
        self.label_error_messages.setFont(font)
        self.label_error_messages.setObjectName("label_error_messages")
        self.label_error_messages.setText("Error Messages")

        self.label_voltage = QtWidgets.QLabel(self.tab_graph)
        self.label_voltage.setGeometry(QtCore.QRect(690, 30, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_voltage.setFont(font)
        self.label_voltage.setStyleSheet("color: rgb(68, 203, 203)")
        self.label_voltage.setObjectName("label_voltage")
        self.label_voltage.setText("Voltage")

        self.label_current = QtWidgets.QLabel(self.tab_graph)
        self.label_current.setGeometry(QtCore.QRect(700, 330, 101, 31))
        font = QtGui.QFont()
        font.setPointSize(14)
        font.setBold(True)
        font.setWeight(75)
        self.label_current.setFont(font)
        self.label_current.setStyleSheet("color: rgb(68, 203, 203)")
        self.label_current.setObjectName("label_current")
        self.label_current.setText("Current")

        self.line_edit_pin = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_pin.setGeometry(QtCore.QRect(20, 30, 160, 50))
        self.line_edit_pin.setObjectName("line_edit_pin")

        self.line_edit_read_timeout = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_read_timeout.setGeometry(QtCore.QRect(810, 30, 70, 50))
        self.line_edit_read_timeout.setObjectName("line_edit_read_timeout")

        self.line_edit_status = QtWidgets.QLineEdit(self.central_widget)
        self.line_edit_status.setGeometry(QtCore.QRect(1060, 30, 161, 50))
        self.line_edit_status.setObjectName("line_edit_status")

        self.line_edit_error_messages = QtWidgets.QLineEdit(self.tab_table)
        self.line_edit_error_messages.setGeometry(QtCore.QRect(10, 540, 1591, 61))
        self.line_edit_error_messages.setObjectName("line_edit_error_messages")

        self.push_button_add_remove = QtWidgets.QPushButton(self.central_widget)
        self.push_button_add_remove.setGeometry(QtCore.QRect(190, 30, 150, 50))
        self.push_button_add_remove.setObjectName("push_button_add_remove")
        self.push_button_add_remove.setText("Add/Remove Pin")

        self.push_button_add_all = QtWidgets.QPushButton(self.central_widget)
        self.push_button_add_all.setGeometry(QtCore.QRect(350, 30, 100, 50))
        self.push_button_add_all.setObjectName("push_button_add_all")
        self.push_button_add_all.setText("Add All")

        self.push_button_add_vin = QtWidgets.QPushButton(self.central_widget)
        self.push_button_add_vin.setGeometry(QtCore.QRect(460, 30, 100, 50))
        self.push_button_add_vin.setObjectName("push_button_add_vin")
        self.push_button_add_vin.setText("Add VIN")

        self.push_button_custom_list = QtWidgets.QPushButton(self.central_widget)
        self.push_button_custom_list.setGeometry(QtCore.QRect(570, 30, 120, 50))
        self.push_button_custom_list.setObjectName("push_button_custom_list")
        self.push_button_custom_list.setText("Custom List")

        self.push_button_clear_list = QtWidgets.QPushButton(self.central_widget)
        self.push_button_clear_list.setGeometry(QtCore.QRect(700, 30, 100, 50))
        self.push_button_clear_list.setObjectName("push_button_clear_list")
        self.push_button_clear_list.setText("Clear List")

        self.push_button_pause_measurements = QtWidgets.QPushButton(self.central_widget)
        self.push_button_pause_measurements.setGeometry(QtCore.QRect(900, 70, 140, 41))
        self.push_button_pause_measurements.setText("")
        icon = QtGui.QIcon()
        icon.addPixmap(QtGui.QPixmap("pause_icon.png"), QtGui.QIcon.Normal, QtGui.QIcon.Off)
        self.push_button_pause_measurements.setIcon(icon)
        self.push_button_pause_measurements.setIconSize(QtCore.QSize(35, 50))
        self.push_button_pause_measurements.setObjectName("push_button_pause_measurements")
        self.push_button_pause_measurements.clicked.connect(
            self.pause_measurements
        )
        self.push_button_pause_measurements.setStyleSheet("background-color:  rgb(232, 228, 228)")

        self.table_widget = QtWidgets.QTableWidget(self.tab_table)
        self.table_widget.setGeometry(QtCore.QRect(10, 20, 1591, 491))
        self.table_widget.setRowCount(27)
        self.table_widget.setColumnCount(24)
        self.init_table()
        self.table_widget.setObjectName("table_widget")
        self.table_widget.horizontalHeader().setCascadingSectionResizes(True)
        self.table_widget.horizontalHeader().setDefaultSectionSize(180)
        self.table_widget.verticalHeader().setVisible(False)
        self.table_widget.verticalHeader().setCascadingSectionResizes(True)
        self.table_widget.verticalHeader().setDefaultSectionSize(23)






        self.graph_voltage = PlotWidget(self.tab_graph)
        self.graph_voltage.setGeometry(QtCore.QRect(10, 60, 1431, 231))
        self.graph_voltage.setObjectName("graph_voltage")
        self.graph_current = PlotWidget(self.tab_graph)
        self.graph_current.setGeometry(QtCore.QRect(10, 360, 1431, 231))
        self.graph_current.setObjectName("graph_current")

        x = np.random.normal(size=1000)
        y = np.random.normal(size=(3,1000))
        self.graph_current.plot(x,y[0],pen=(pg.mkPen('y', width = 3)))
        self.graph_current.plot(x,y[1],pen=(pg.mkPen('r', width = 3)))
        self.graph_current.plot(x,y[2],pen=(pg.mkPen('y', width = 3)))

        self.tab_widget.setCurrentIndex(0)

        self.main_window.setCentralWidget(self.central_widget)
        QtCore.QMetaObject.connectSlotsByName(self.main_window)

        self.q_timer = QTimer()
        self.q_timer.setInterval(250)
        self.q_timer.timeout.connect(self.timeout_event)
        self.q_timer.start()

    def timeout_event(self):
        pass

    def init_table(self):

        column_headers = [
            "Pin", "Function", "Output", "Connected", "Current", "Voltage", "V Level", "V Range",
            "I limit", "I limit H", "I limit L", "I limit Range", "I level", "I Range", "V limit", "V limit H",
            "V limit L", "V limit Range", "Aperture", "Transient Response", "Sense", "Instrument", "Channel", "Compliance"
        ]
        col_number = 0
        for header in column_headers:
            item = QtWidgets.QTableWidgetItem()
            self.table_widget.setHorizontalHeaderItem(col_number, item)
            item.setText(header)
            col_number += 1

    def pause_measurements(self):
        if self.is_measurements_paused:
            self.push_button_pause_measurements.setStyleSheet("background-color:  rgb(232, 228, 228)")
            self.is_measurements_paused = not self.is_measurements_paused
        else:
            self.push_button_pause_measurements.setStyleSheet("background-color:  rgb(245, 221, 0)")
            self.is_measurements_paused = not self.is_measurements_paused


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = UiSMUDebugWindow()
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())