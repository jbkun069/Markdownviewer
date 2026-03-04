import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Optional

import markdown  # type: ignore
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QTextCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView  # type: ignore
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
)

SESSION_FILE: Path = Path("session.json")
DEFAULT_TITLE: str = "Markdown Viewer"
PREVIEW_DEBOUNCE_MS: int = 300

CSS_STYLE = """
<style>
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto;
        padding: 20px; line-height: 1.6; color: #24292e;
    }
    code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; }
    pre { background-color: #f6f8fa; padding: 16px; border-radius: 6px; }
    table { border-collapse: collapse; width: 100%; }
    th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
</style>
"""

@dataclass
class SessionData:
    """Holds the application state to be persisted between sessions."""

    last_file: Optional[str] = None
    last_text: str = ""


def load_session(path: Path) -> Optional[SessionData]:
    """Load a persisted session from disk.

    Args:
        path: Path to the session JSON file.

    Returns:
        A ``SessionData`` instance when the file is present and valid, else ``None``.
    """
    if not path.exists():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            data = json.load(fh)
        return SessionData(
            last_file=data.get("last_file"),
            last_text=data.get("last_text", ""),
        )
    except (OSError, json.JSONDecodeError):
        return None


def save_session(path: Path, session: SessionData) -> None:
    """Persist session state to disk.

    Args:
        path: Destination path for the JSON file.
        session: The session data to serialize.
    """
    try:
        with path.open("w", encoding="utf-8") as fh:
            json.dump(asdict(session), fh)
    except OSError:
        pass


def convert_markdown_to_html(md_text: str) -> str:
    """Convert Markdown text to an HTML string.

    Args:
        md_text: Raw Markdown source text.

    Returns:
        Rendered HTML string.
    """
    extensions = ["fenced_code", "tables", "toc", "abbr", "attr_list"]
    try:
        import pygments  # noqa: F401
        extensions.append("codehilite")
    except ImportError:
        pass
    return markdown.markdown(md_text, extensions=extensions)


class FindReplaceDialog(QDialog):
    """A non-modal dialog for finding and replacing text in the editor."""

    def __init__(self, editor: QTextEdit) -> None:
        super().__init__()
        self.editor = editor
        self._init_ui()

    def _init_ui(self) -> None:
        """Build and wire the dialog's widget layout."""
        self.setWindowTitle("Find / Replace")
        self.setModal(False)

        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        find_btn = QPushButton("Find Next")
        replace_btn = QPushButton("Replace")
        replace_all_btn = QPushButton("Replace All")

        find_row = QHBoxLayout()
        find_row.addWidget(QLabel("Find:"))
        find_row.addWidget(self.find_input)

        replace_row = QHBoxLayout()
        replace_row.addWidget(QLabel("Replace:"))
        replace_row.addWidget(self.replace_input)

        button_row = QHBoxLayout()
        button_row.addWidget(find_btn)
        button_row.addWidget(replace_btn)
        button_row.addWidget(replace_all_btn)

        layout = QVBoxLayout()
        layout.addLayout(find_row)
        layout.addLayout(replace_row)
        layout.addLayout(button_row)
        self.setLayout(layout)

        find_btn.clicked.connect(self.find_next)
        replace_btn.clicked.connect(self.replace_one)
        replace_all_btn.clicked.connect(self.replace_all)

    def find_next(self) -> None:
        """Advance to the next match, wrapping around at end of document."""
        text = self.find_input.text()
        if not text:
            return
        if not self.editor.find(text):
            self.editor.moveCursor(QTextCursor.MoveOperation.Start)
            self.editor.find(text)

    def replace_one(self) -> None:
        """Replace the current selection if it matches, then move to the next occurrence."""
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
        self.find_next()

    def replace_all(self) -> None:
        """Replace every occurrence without moving the visible scroll position."""
        target = self.find_input.text()
        replacement = self.replace_input.text()
        if not target:
            return

        doc = self.editor.document()
        if doc is None:
            return
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        while True:
            found = doc.find(target, cursor)
            if found.isNull():
                break
            found.insertText(replacement)
            cursor.setPosition(found.position())

        cursor.endEditBlock()


class MainWindow(QMainWindow):
    """Main application window for the Markdown editor and live preview."""

    def __init__(self, argv: list[str]) -> None:
        super().__init__()
        self.current_file_path: Optional[Path] = None
        self.is_modified: bool = False
        self._find_dialog: Optional[FindReplaceDialog] = None
        self._init_ui()
        self._setup_timer()
        self._load_initial_content(argv)

    # ------------------------------------------------------------------ #
    # UI initialisation                                                    #
    # ------------------------------------------------------------------ #

    def _init_ui(self) -> None:
        """Construct the main window layout and widgets."""
        self.setWindowTitle(DEFAULT_TITLE)
        self.resize(1000, 700)
        self.setAcceptDrops(True)
        self._create_menu()

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Write your markdown here…")
        self.editor.textChanged.connect(self._on_text_modified)

        self.preview = QWebEngineView()
        self.preview.setHtml(
            f"<html><head>{CSS_STYLE}</head><body><div id='content'></div></body></html>"
        )

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(self.editor)
        splitter.addWidget(self.preview)
        self.setCentralWidget(splitter)

    def _setup_timer(self) -> None:
        """Configure the debounce timer that throttles preview refreshes."""
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(PREVIEW_DEBOUNCE_MS)
        self.debounce_timer.timeout.connect(self._update_preview)

    def _create_menu(self) -> None:
        """Populate the application menu bar with File and Edit menus."""
        menubar = self.menuBar()
        assert menubar is not None

        file_menu = menubar.addMenu("File")
        assert file_menu is not None

        file_actions: list[tuple[str, str, object]] = [
            ("New", "Ctrl+N", self.new_file),
            ("Open", "Ctrl+O", self.open_file),
            ("Save", "Ctrl+S", self.save_file),
            ("Save As", "Ctrl+Shift+S", self.save_file_as),
        ]
        for label, shortcut, handler in file_actions:
            action = QAction(label, self)
            action.setShortcut(shortcut)
            action.triggered.connect(handler)
            file_menu.addAction(action)

        edit_menu = menubar.addMenu("Edit")
        assert edit_menu is not None

        find_action = QAction("Find / Replace", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.open_find_replace)
        edit_menu.addAction(find_action)

    # ------------------------------------------------------------------ #
    # Preview                                                              #
    # ------------------------------------------------------------------ #

    def _update_preview(self) -> None:
        """Inject fresh HTML into the preview pane without resetting scroll position."""
        if not self.preview.isVisible():
            return
        raw_html = convert_markdown_to_html(self.editor.toPlainText())
        # Escape characters that would break the JS template literal.
        safe_html = (
            raw_html.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        )
        js = f"document.getElementById('content').innerHTML = `{safe_html}`;"
        self.preview.page().runJavaScript(js)

    # ------------------------------------------------------------------ #
    # File operations                                                      #
    # ------------------------------------------------------------------ #

    def _set_editor_content(self, text: str, path: Optional[Path]) -> None:
        """Populate the editor with *text* and update all related state.

        Args:
            text: Content to display in the editor.
            path: Associated file path, or ``None`` for an unsaved buffer.
        """
        self.editor.blockSignals(True)
        self.editor.setPlainText(text)
        self.editor.blockSignals(False)
        self.current_file_path = path
        self.is_modified = False
        self._update_window_title()
        self._update_preview()

    def _load_file_content(self, path: Path) -> None:
        """Read a file from disk and load it into the editor.

        Args:
            path: Path to the Markdown file to open.
        """
        try:
            self._set_editor_content(path.read_text(encoding="utf-8"), path)
        except OSError as exc:
            QMessageBox.critical(self, "Error", f"Could not read {path}:\n{exc}")

    def new_file(self) -> None:
        """Clear the editor to start a new unsaved document."""
        if not self.is_modified or self._confirm_discard():
            self._set_editor_content("", None)

    def open_file(self) -> None:
        """Show an open-file dialog and load the chosen Markdown document."""
        if self.is_modified and not self._confirm_discard():
            return
        raw_path, _ = QFileDialog.getOpenFileName(
            self, "Open", "", "Markdown (*.md);;All Files (*)"
        )
        if raw_path:
            self._load_file_content(Path(raw_path))

    def save_file(self) -> None:
        """Save the current buffer; delegate to *save_file_as* if untitled."""
        if not self.current_file_path:
            self.save_file_as()
        else:
            self._write_to_disk(self.current_file_path)

    def save_file_as(self) -> None:
        """Prompt for a destination path and save the current buffer there."""
        raw_path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Markdown (*.md)")
        if raw_path:
            self._write_to_disk(Path(raw_path))

    def _write_to_disk(self, path: Path) -> None:
        """Write the editor's content to *path* and update window state.

        Args:
            path: Destination file path.
        """
        try:
            path.write_text(self.editor.toPlainText(), encoding="utf-8")
            self.current_file_path = path
            self.is_modified = False
            self._update_window_title()
        except OSError as exc:
            QMessageBox.critical(self, "Save Error", str(exc))

    # ------------------------------------------------------------------ #
    # Session management                                                   #
    # ------------------------------------------------------------------ #

    def _restore_last_session(self) -> None:
        """Re-open the file or text buffer from the previous session, if any."""
        session = load_session(SESSION_FILE)
        if session is None:
            return
        if session.last_file:
            last = Path(session.last_file)
            if last.exists():
                self._load_file_content(last)
                return
        if session.last_text:
            self._set_editor_content(session.last_text, None)
            self.is_modified = True
            self._update_window_title()

    def _persist_session(self) -> None:
        """Write the current session state to disk before closing."""
        unsaved_text = "" if self.current_file_path else self.editor.toPlainText()
        session = SessionData(
            last_file=str(self.current_file_path) if self.current_file_path else None,
            last_text=unsaved_text,
        )
        save_session(SESSION_FILE, session)

    def _load_initial_content(self, argv: list[str]) -> None:
        """Determine what to show on startup: restored session, CLI argument, or blank.

        Args:
            argv: Command-line argument list (``sys.argv``).
        """
        if SESSION_FILE.exists():
            self._restore_last_session()
        elif len(argv) > 1:
            self._load_file_content(Path(argv[1]))

    # ------------------------------------------------------------------ #
    # Helpers                                                              #
    # ------------------------------------------------------------------ #

    def _on_text_modified(self) -> None:
        """Mark the buffer as dirty and restart the preview debounce timer."""
        if not self.is_modified:
            self.is_modified = True
            self._update_window_title()
        self.debounce_timer.start()

    def _update_window_title(self) -> None:
        """Refresh the title bar to reflect the current file name and dirty state."""
        name = self.current_file_path.name if self.current_file_path else "Untitled"
        dirty = "*" if self.is_modified else ""
        self.setWindowTitle(f"{name}{dirty} - {DEFAULT_TITLE}")

    def _confirm_discard(self) -> bool:
        """Ask the user whether unsaved changes may be discarded.

        Returns:
            ``True`` if the user consents to discard changes, ``False`` otherwise.
        """
        result = QMessageBox.question(
            self,
            "Unsaved Changes",
            "Discard unsaved changes?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        return result == QMessageBox.StandardButton.Yes

    def open_find_replace(self) -> None:
        """Open (or raise) the Find / Replace dialog."""
        if self._find_dialog is None or not self._find_dialog.isVisible():
            self._find_dialog = FindReplaceDialog(self.editor)
        self._find_dialog.show()
        self._find_dialog.raise_()

    # ------------------------------------------------------------------ #
    # Qt event overrides                                                   #
    # ------------------------------------------------------------------ #

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._persist_session()
        if self.is_modified and not self._confirm_discard():
            event.ignore()
        else:
            event.accept()

    def dragEnterEvent(self, event) -> None:  # type: ignore[override]
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:  # type: ignore[override]
        urls = event.mimeData().urls()
        if urls and (not self.is_modified or self._confirm_discard()):
            self._load_file_content(Path(urls[0].toLocalFile()))

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(sys.argv)
    window.show()
    sys.exit(app.exec())