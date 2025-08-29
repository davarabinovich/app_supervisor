
from enum import Enum
from collections.abc import Callable
from typing import Any
from os.path import exists
from PyQt6.QtCore import QObject, pyqtSlot
from PyQt6.QtWidgets import QMainWindow, QFileDialog, QMessageBox


class AppSupervisor(QObject):
    DEFAULT_WRITE_FILE_DIALOG_CAPTION: str = 'Save to file...'
    DEFAULT_READ_FILE_DIALOG_CAPTION: str = 'Open file...'
    DEFAULT_FILE_DIALOG_FILT_TEXT: str = 'File '
    DEFAULT_SAVE_MSG_BOX_TEXT: str = 'There are unsaved changes in the current file.'
    DEFAULT_SAVE_MSG_BOX_QUEST: str = 'Do you want to save changes?'

    class State(Enum):
        EMPTY: int = 0,
        FRESH: int = 1,
        SYNCHED: int = 2,
        CHANGED: int = 3

        def is_unsaved(self) -> bool:
            result: bool = self.value == AppSupervisor.State.FRESH or self.value == AppSupervisor.State.CHANGED
            return result

    def __init__(self, main_win: QMainWindow, cli_args: list[str], file_content_type: type, file_extension: str,
                 save_cb: Callable[[Any, str]], create_cb: Callable[[]], load_cb: Callable[[str], Any],
                 get_data_cb: Callable[[], Any], set_data_cb: Callable[[Any]],
                 write_file_dialog_caption: str = DEFAULT_WRITE_FILE_DIALOG_CAPTION,
                 read_file_dialog_caption: str = DEFAULT_READ_FILE_DIALOG_CAPTION,
                 file_dialog_filt_text: str = DEFAULT_FILE_DIALOG_FILT_TEXT,
                 save_msg_box_text: str = DEFAULT_SAVE_MSG_BOX_TEXT,
                 save_msg_box_quest: str = DEFAULT_SAVE_MSG_BOX_QUEST):
        super().__init__(None)

        self._main_win: QMainWindow = main_win
        self._save_cb: Callable[[Any, str]] = save_cb
        self._create_cb: Callable[[]] = create_cb
        self._load_cb: Callable[[str], Any] = load_cb
        self._get_data_cb: Callable[[], Any] = get_data_cb
        self._set_data_cb: Callable[[Any]] = set_data_cb

        if cli_args is not None:
            self._state: AppSupervisor.State = AppSupervisor.State.SYNCHED
        self._active_file: str = ''
        self._file_content_type: type = file_content_type
        self__data: Any = None

        self._file_extension: str = file_extension
        self._write_file_dialog_caption: str = write_file_dialog_caption
        self._read_file_dialog_caption: str = read_file_dialog_caption
        self._file_dialog_filt_text: str = '{filt_text} (*{extension})'.format(extension=self._file_extension,
                                                                               filt_text=file_dialog_filt_text)
        self._save_msg_box_text: str = save_msg_box_text
        self._save_msg_box_quest: str = save_msg_box_quest

    @pyqtSlot()
    def receive_save(self):
        if self._state == AppSupervisor.State.FRESH:
            self._active_file = self._create_file_via_dialog()
            if self._active_file == '':
                return
        if self._state.is_unsaved():
            self._save_to_file_and_enter_to_synced()

    @pyqtSlot()
    def receive_edit(self):
        if self._state == AppSupervisor.State.SYNCHED:
            self._state = AppSupervisor.State.CHANGED

    @pyqtSlot()
    def receive_new(self):
        self._ask_save_to_file_and_enter_to_synced()
        self._create_cb()
        self._state = AppSupervisor.State.FRESH

    @pyqtSlot()
    def receive_load(self):
        self._ask_save_to_file_and_enter_to_synced()
        file_path: str = self._file_to_load_select()
        file_content = self._load_cb(file_path)
        self._set_data_cb(file_content)
        self._state = AppSupervisor.State.SYNCHED

    def prepare_to_close(self):
        self._ask_save_to_file_and_enter_to_synced()

    def _ask_save_to_file_and_enter_to_synced(self):
        is_saving_needed: bool = False
        if self._state.is_unsaved():
            is_saving_needed = self._is_saving_needed()
            if is_saving_needed and self._state == AppSupervisor.State.FRESH:
                self._active_file = self._create_file_via_dialog()
                if self._active_file == '':
                    is_saving_needed = False
        if self._state.is_unsaved() and is_saving_needed:
            self._save_to_file_and_enter_to_synced()

    def _save_to_file_and_enter_to_synced(self):
        file_content = self._get_data_cb()
        self._save_cb(file_content, self._active_file)
        self._state = AppSupervisor.State.SYNCHED

    def _create_file_via_dialog(self) -> str:
        file_path: str = self._call_write_file_dialog()
        while file_path != '': # TODO and exist
            file_path = self._call_write_file_dialog()
            if file_path == '':
                break

        if file_path != '':
            # TODO: Rework
            file = open(file_path, 'w')
            file.close()
        return file_path

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
