import sys
from PyQt5 import QtWidgets
from Code.UI.splash_ui import MainWindowUI
from PyQt5 import QtCore
import sys, traceback

if QtCore.QT_VERSION >= 0x50501:
    def excepthook(type_, value, traceback_):
        traceback.print_exception(type_, value, traceback_)
        QtCore.qFatal('')
    sys.excepthook = excepthook

def run():
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = MainWindowUI(MainWindow)
    MainWindow.show()
    print('Showing')
    sys.exit(app.exec_())

run()