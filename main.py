
from sys import argv
from typing import Optional
from PyQt6.QtCore import *
from PyQt6.QtWidgets import QApplication, QMainWindow, QFileDialog
from MainWin import *
from app_supervisor import *


EXTENSION = '.dprj'


class Type:
    def __init__(self):
        self.field: str = 'Test field value'

def save (content: Type, file_path: str):
    pass

def load (file_path: str) -> Type:
    pass

def create ():
    pass

def get_data () -> Type:
    pass

def set_data (data: Type):
    pass


class MainWin(QMainWindow):
    def __init__(self, ui: Ui_MainWin):
        super().__init__()
        self._ui = ui
        self._ui.setupUi(self)


def main():
    app = QApplication(argv)
    ui = Ui_MainWin()
    win = MainWin(ui)

    supervisor = AppSupervisor(win, argv, Type, EXTENSION, save, load, create, get_data, set_data)

    win.show()
    app.exec()
    exit()


if __name__ == '__main__':
    main()
