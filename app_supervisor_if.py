
from enum import Enum
from collections.abc import Callable
from typing import Any
from abc import ABC, abstractmethod

DEFAULT_WRITE_FILE_DIALOG_CAPTION: str = 'Save to file...'
DEFAULT_READ_FILE_DIALOG_CAPTION: str = 'Open file...'
DEFAULT_FILE_DIALOG_FILT_TEXT: str = 'File '

DEFAULT_SAVE_MSG_BOX_TEXT: str = 'There are unsaved changes in the current file.'
DEFAULT_SAVE_MSG_BOX_QUEST: str = 'Do you want to save changes?'
DEFAULT_REWRITE_MSG_BOX_TEXT: str = 'File exists'
DEFAULT_REWRITE_MSG_BOX_QUEST: str = 'The file you specified is already exists. Do you want to rewrite it?'


class BadContentType(Exception):
    def __init__(self):
        super().__init__('Content shall have type specified during application supervisor initialization')


class BadContentGuiType(Exception):
    def __init__(self):
        super().__init__('Type of user data handling GUI class you provided shall be an implementation '
                         'of ContentGuiIf class')


class BadUiPlotType(Exception):
    def __init__(self):
        super().__init__('Type of UI plot you provided shall have the "setupUi" method')


class State(Enum):
    EMPTY: int = 0,
    FRESH: int = 1,
    SYNCHED: int = 2,
    CHANGED: int = 3,
    INVALID: int = 4

    def is_unsaved(self) -> bool:
        result: bool = self == State.FRESH or self == State.CHANGED
        return result


class ContentGuiIf(ABC):
    @abstractmethod
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @abstractmethod
    def create_content(self) -> bool:
        pass

    @abstractmethod
    def set_content(self, content):
        pass

    @abstractmethod
    def get_content(self) -> Any:
        pass


class AppSupervisorIf(ABC):
    @abstractmethod
    def __init__(self, content_type: type, content_gui: ContentGuiIf,
                 file_extension: str, cli_args: list[str],
                 save_cb: Callable[[Any, str], None], load_cb: Callable[[str], Any],
                 write_file_dialog_caption: str, read_file_dialog_caption: str, file_dialog_filt_text: str,
                 save_msg_box_text: str, save_msg_box_quest: str, rewrite_msg_box_text: str, rewrite_msg_box_quest: str,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._content_gui: ContentGuiIf | None = None
        self._assign_content_gui_safely(content_gui)
        self._content_type: type = content_type

        self._save_cb: Callable[[Any, str], None] = save_cb
        self._load_cb: Callable[[str], Any] = load_cb

        self._file_extension: str = file_extension
        self._write_file_dialog_caption: str = write_file_dialog_caption
        self._read_file_dialog_caption: str = read_file_dialog_caption
        self._file_dialog_filt_text: str = '{filt_text} (*{extension})'.format(extension=self._file_extension,
                                                                               filt_text=file_dialog_filt_text)
        self._save_msg_box_text: str = save_msg_box_text
        self._save_msg_box_quest: str = save_msg_box_quest
        self._rewrite_msg_box_text: str = rewrite_msg_box_text
        self._rewrite_msg_box_quest: str = rewrite_msg_box_quest

        self._state: State = State.INVALID
        self._init_state(cli_args)
        self._data: Any | None = None
        self._active_file_name: str | None = None

    @abstractmethod
    def receive_new(self):
        self._ask_save_to_file_and_enter_to_synced()
        is_success: bool = self._content_gui.create_content()
        if is_success:
            self._state = State.FRESH

    @abstractmethod
    def receive_edit(self):
        if self._state == State.SYNCHED:
            self._state = State.CHANGED

    @abstractmethod
    def receive_save(self):
        if self._state == State.FRESH:
            file_path: str = self._create_file_via_dialog()
            if self._active_file_name == '':
                return
            self._active_file_name = file_path
        if self._state.is_unsaved():
            self._save_to_file_and_enter_to_synced()

    @abstractmethod
    def receive_load(self):
        self._ask_save_to_file_and_enter_to_synced()
        file_path: str = self._ask_file_to_load_via_dialog()
        file_content = self._load_cb(file_path)
        if not isinstance(file_content, self._content_type):
            raise BadContentType
        self._active_file_name = file_path
        self._content_gui.set_content(file_content)
        self._state = State.SYNCHED

    @abstractmethod
    def receive_close(self):
        self._ask_save_to_file_and_enter_to_synced()

    def _assign_content_gui_safely(self, content_gui: ContentGuiIf):
        if not isinstance(content_gui, ContentGuiIf):
            raise BadContentGuiType
        self._content_gui = content_gui

    def _init_state(self, cli_args: list[str]):
        self._state = State.SYNCHED if (cli_args is not None) else State.EMPTY

    def _ask_save_to_file_and_enter_to_synced(self):
        is_saving_needed: bool = False
        if self._state.is_unsaved():
            is_saving_needed = self._ask_is_action_needed_via_dialog(self._save_msg_box_text,
                                                                     self._save_msg_box_quest)
            if is_saving_needed and self._state == State.FRESH:
                file_path: str = self._create_file_via_dialog()
                if file_path == '':
                    is_saving_needed = False
                self._active_file_name = file_path
        if self._state.is_unsaved() and is_saving_needed:
            self._save_to_file_and_enter_to_synced()

    def _save_to_file_and_enter_to_synced(self):
        file_content = self._content_gui.get_content()
        if not isinstance(file_content, self._content_type):
            raise BadContentType
        self._save_cb(file_content, self._active_file_name)
        self._state = State.SYNCHED

    def _create_file_via_dialog(self) -> str:
        file_path = self._ask_file_to_write_via_dialog()
        if file_path != '':
            file = open(file_path, 'x')
            file.close()
        return file_path

    @abstractmethod
    def _ask_file_to_write_via_dialog(self) -> str:
        pass

    @abstractmethod
    def _ask_file_to_load_via_dialog(self) -> str:
        pass

    @abstractmethod
    def _ask_is_action_needed_via_dialog(self, title: str, text: str) -> bool:
        pass
