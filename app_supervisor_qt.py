
from typing import Optional
from os.path import exists
from abc import ABCMeta

import PyQt6.sip
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox

from lib.app_supervisor.app_supervisor_if import *


class NotQtObjType(Exception):
    def __init__(self):
        super().__init__('Some of objects (main window, content GUI) you provided has not Qt implementation')


class AppSupervisorQtMeta(ABCMeta, PyQt6.sip.wrappertype):
    pass


class MainWinQt(QMainWindow, MainWinIf, metaclass=AppSupervisorQtMeta):
    @abstractmethod
    def __init__(self, ui: object):
        super().__init__(parent=None)
        try:
            self._assign_ui_safely(ui)
        except BadUiPlotType as exception:
            print(exception)

    new = pyqtSignal(name='new')
    edit = pyqtSignal(name='edit')
    save = pyqtSignal(name='save')
    load = pyqtSignal(name='load')
    close = pyqtSignal(name='close')

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        self.close.emit()

    def _assign_ui_safely(self, ui: object):
        if not hasattr(ui, "setupUi") or not callable(getattr(ui, "setupUi")):
            raise BadUiPlotType
        self._ui: type(ui) = ui
        self._ui.setupUi(self)


class ContentGuiQt(QObject, ContentGuiIf, metaclass=AppSupervisorQtMeta):
    @abstractmethod
    def __init__(self, parent: MainWinQt):
        QObject.__init__(self, parent)

    @abstractmethod
    def create_content(self):
        pass

    @abstractmethod
    def set_content(self, content):
        pass

    @abstractmethod
    def get_content(self) -> Any:
        pass


def _are_obj_types_valid(main_win: MainWinQt, content_gui: ContentGuiQt) -> bool:
    result: bool = True
    if not isinstance(main_win, MainWinQt) or not isinstance(content_gui, ContentGuiQt):
        result = False
    return result


class AppSupervisorQt(AppSupervisorIf, QObject, metaclass=AppSupervisorQtMeta):
    def __init__(self, main_win: MainWinQt, content_type: type, content_gui: ContentGuiQt,
                 file_extension: str, cli_args: list[str],
                 save_cb: Callable[[Any, str], None], load_cb: Callable[[str], Any],
                 write_file_dialog_caption: str = DEFAULT_WRITE_FILE_DIALOG_CAPTION,
                 read_file_dialog_caption: str = DEFAULT_READ_FILE_DIALOG_CAPTION,
                 file_dialog_filt_text: str = DEFAULT_FILE_DIALOG_FILT_TEXT,
                 save_msg_box_text: str = DEFAULT_SAVE_MSG_BOX_TEXT,
                 save_msg_box_quest: str = DEFAULT_SAVE_MSG_BOX_QUEST):
        super().__init__(main_win, content_type, content_gui, file_extension, cli_args, save_cb, load_cb,
                         write_file_dialog_caption, read_file_dialog_caption, file_dialog_filt_text,
                         save_msg_box_text, save_msg_box_quest, parent=None)
        are_obj_types_valid: bool = _are_obj_types_valid(main_win, content_gui)
        if are_obj_types_valid:
            self._make_links()
        else:
            raise NotQtObjType

    @pyqtSlot()
    def receive_new(self):
        AppSupervisorIf.receive_new(self)

    @pyqtSlot()
    def receive_edit(self):
        AppSupervisorIf.receive_edit(self)

    @pyqtSlot()
    def receive_save(self):
        AppSupervisorIf.receive_save(self)

    @pyqtSlot()
    def receive_load(self):
        AppSupervisorIf.receive_load(self)

    @pyqtSlot()
    def receive_close(self):
        AppSupervisorIf.receive_close(self)

    def _make_links(self):
        self._main_win.new.connect(self.receive_new)
        self._main_win.edit.connect(self.receive_edit)
        self._main_win.save.connect(self.receive_save)
        self._main_win.load.connect(self.receive_new)
        self._main_win.close.connect(self.receive_close)

    def _init_state(self, cli_args: list[str]):
        if cli_args is not None:
            self._state: State = State.SYNCHED
        else:
            self._state: State = State.EMPTY

    def _call_write_file_dialog(self) -> str:
        file_url_tuple = QFileDialog.getSaveFileUrl(self._main_win, caption=self._write_file_dialog_caption,
                                                    filter=self._file_dialog_filt_text)
        if file_url_tuple[0].isEmpty():
            return ''
        file_path: str = file_url_tuple[0].toString().removeprefix('file:///')
        if not file_path.endswith(self._file_extension):
            file_path += self._file_extension

        if exists(file_path):
            msg_box_title: str = 'Existing {extension} file'.format(extension=self._file_extension)
            msg_box_text = 'The file you specified is already exists. Type another file name'
            QMessageBox.critical(self._main_win, msg_box_title, msg_box_text)
            return ''
        return file_path

    def _file_to_load_select(self) -> str:
        file_url_tuple = QFileDialog.getOpenFileUrl(self._main_win, caption=self._read_file_dialog_caption,
                                                    filter=self._file_dialog_filt_text)
        if file_url_tuple[0].isEmpty():
            return ''
        file_path: str = file_url_tuple[0].toString().removeprefix('file:///')
        return file_path

    def _is_saving_needed(self) -> bool:
        pressed_button = QMessageBox.question(self._main_win, self._save_msg_box_text, self._save_msg_box_quest)
        result: bool = False
        if pressed_button == QMessageBox.StandardButton.Yes:
            result = True
        return result
