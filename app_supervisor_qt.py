
from typing import Optional
from os import remove
from os.path import exists
from abc import ABCMeta

import PyQt6.sip
from PyQt6.QtCore import QObject, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox

from lib.app_supervisor.app_supervisor_if import *


class BadMainWinType(Exception):
    def __init__(self):
        super().__init__('Type of Main Window you provided shall be an implementation of MainWinQt class')


class NotQtObjType(Exception):
    def __init__(self):
        super().__init__('Resources under application supervisor control (main window, content GUI) you provided '
                         'shall have Qt implementation')


class BadWidgetParent(Exception):
    def __init__(self):
        super().__init__("Type of widget's parent you specify shall be QWidget")


class AppSupervisorQtMeta(ABCMeta, PyQt6.sip.wrappertype):
    pass


class MainWinQt(QMainWindow):
    def __init__(self, ui: object):
        super().__init__(parent=None)
        self._ui = None
        try:
            self._assign_ui_safely(ui)
        except BadUiPlotType as exception:
            print(exception)

    new = pyqtSignal(name='new')
    save = pyqtSignal(name='save')
    load = pyqtSignal(name='load')
    close = pyqtSignal(name='close')

    def closeEvent(self, a0: Optional[QCloseEvent]) -> None:
        self.close.emit()

    def _assign_ui_safely(self, ui: object):
        if not hasattr(ui, "setupUi") or not callable(getattr(ui, "setupUi")):
            raise BadUiPlotType
        self._ui = ui
        self._ui.setupUi(self)


class ContentGuiQt(QObject, ContentGuiIf, metaclass=AppSupervisorQtMeta):
    @abstractmethod
    def __init__(self, parent: MainWinQt):
        super().__init__(parent)
        pass

    @abstractmethod
    def create_content(self):
        pass

    @abstractmethod
    def set_content(self, content):
        pass

    @abstractmethod
    def get_content(self) -> Any:
        pass

    edit = pyqtSignal(name='edit')


class AppSupervisorQt(AppSupervisorIf, QObject, metaclass=AppSupervisorQtMeta):
    def __init__(self, main_win: MainWinQt, content_type: type, content_gui: ContentGuiQt,
                 file_extension: str, cli_args: list[str],
                 save_cb: Callable[[Any, str], None], load_cb: Callable[[str], Any],
                 write_file_dialog_caption: str = DEFAULT_WRITE_FILE_DIALOG_CAPTION,
                 read_file_dialog_caption: str = DEFAULT_READ_FILE_DIALOG_CAPTION,
                 file_dialog_filt_text: str = DEFAULT_FILE_DIALOG_FILT_TEXT,
                 save_msg_box_text: str = DEFAULT_SAVE_MSG_BOX_TEXT,
                 save_msg_box_quest: str = DEFAULT_SAVE_MSG_BOX_QUEST,
                 rewrite_msg_box_text: str = DEFAULT_REWRITE_MSG_BOX_TEXT,
                 rewrite_msg_box_quest: str = DEFAULT_REWRITE_MSG_BOX_QUEST):
        super().__init__(content_type, content_gui, file_extension, cli_args, save_cb, load_cb,
                         write_file_dialog_caption, read_file_dialog_caption, file_dialog_filt_text,
                         save_msg_box_text, save_msg_box_quest, rewrite_msg_box_text, rewrite_msg_box_quest,
                         parent=None)
        self._main_win: MainWinQt | None = None
        self._assign_main_win_safely(main_win)
        if AppSupervisorQt._is_content_gui_valid(content_gui):
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

    def _assign_main_win_safely(self, main_win: MainWinQt):
        if not isinstance(main_win, MainWinQt):
            raise BadMainWinType
        self._main_win = main_win

    def _make_links(self):
        self._main_win.new.connect(self.receive_new)
        self._content_gui.edit.connect(self.receive_edit)
        self._main_win.save.connect(self.receive_save)
        self._main_win.load.connect(self.receive_load)
        self._main_win.close.connect(self.receive_close)

    def _init_state(self, cli_args: list[str]):
        if cli_args is not None:
            self._state: State = State.SYNCHED
        else:
            self._state: State = State.EMPTY

    def _ask_file_to_write_via_dialog(self) -> str:
        file_path: str | None = None
        while file_path is None:
            file_url_tuple = QFileDialog.getSaveFileUrl(self._main_win, caption=self._write_file_dialog_caption,
                                                        filter=self._file_dialog_filt_text,
                                                        options=QFileDialog.Option.DontConfirmOverwrite)
            if not file_url_tuple[0].isEmpty():
                file_path: str = file_url_tuple[0].toString().removeprefix('file:///')
                if not file_path.endswith(self._file_extension):
                    file_path += self._file_extension

                if exists(file_path):
                    is_rewrite_needed = self._ask_is_action_needed_via_dialog(self._rewrite_msg_box_text,
                                                                              self._rewrite_msg_box_quest)
                    if is_rewrite_needed:
                        remove(file_path)
                    else:
                        file_path = None
            else:
                file_path = ''
        return file_path

    def _ask_file_to_load_via_dialog(self) -> str:
        file_url_tuple = QFileDialog.getOpenFileUrl(self._main_win, caption=self._read_file_dialog_caption,
                                                    filter=self._file_dialog_filt_text)
        if file_url_tuple[0].isEmpty():
            return ''
        file_path: str = file_url_tuple[0].toString().removeprefix('file:///')
        return file_path

    def _ask_is_action_needed_via_dialog(self, title: str, text: str) -> bool:
        pressed_button = QMessageBox.question(self._main_win, title, text)
        result: bool = False
        if pressed_button == QMessageBox.StandardButton.Yes:
            result = True
        return result

    @staticmethod
    def _is_content_gui_valid(content_gui: ContentGuiQt) -> bool:
        result: bool = True if isinstance(content_gui, ContentGuiQt) else False
        return result
