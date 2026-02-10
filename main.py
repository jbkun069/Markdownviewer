import sys
import os
import json
import markdown # type: ignore
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QTextEdit, QFileDialog, QMessageBox,
    QDialog, QLineEdit, QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView # type: ignore
from PyQt6.QtGui import QAction, QTextCursor

SESSION_FILE = "session.json"

# B. CSS Styling for a better looking preview
CSS_STYLE = """
<style>
    body { 
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; 
        padding: 20px; 
        line-height: 1.6; 
        color: #24292e;
    }
    h1, h2, h3 { border-bottom: 1px solid #eaecef; padding-bottom: .3em; }
    code { background-color: #f0f0f0; padding: 2px 4px; border-radius: 4px; font-family: Consolas, "Courier New", monospace; }
    pre { background-color: #f6f8fa; padding: 16px; border-radius: 6px; overflow: auto; }
    blockquote { border-left: 4px solid #dfe2e5; padding-left: 1em; color: #6a737d; }
    table { border-collapse: collapse; width: 100%; margin-bottom: 1em; }
    th, td { border: 1px solid #dfe2e5; padding: 6px 13px; }
    tr:nth-child(2n) { background-color: #f6f8fa; }
    a { color: #0366d6; text-decoration: none; }
    a:hover { text-decoration: underline; }
</style>
"""

def convert_markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown text to HTML with CSS styling and safer extension handling.
    """
    extensions = [
        "fenced_code",
        "tables",
        "toc",
        "abbr",
        "attr_list",
    ]
    
    # C. Try to use code highlighting, but fallback gracefully if Pygments is missing
    try:
        import pygments  # noqa: F401
        extensions.append("codehilite")
    except ImportError:
        pass

    html_body = markdown.markdown(md_text, extensions=extensions)
    return CSS_STYLE + html_body


class FindReplaceDialog(QDialog):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setWindowTitle("Find / Replace")
        self.setModal(False) # Non-modal so user can edit while searching

        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        self.find_btn = QPushButton("Find Next")
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")

        layout = QVBoxLayout()
        
        # Row 1: Find
        box1 = QHBoxLayout()
        box1.addWidget(QLabel("Find:"))
        box1.addWidget(self.find_input)

        # Row 2: Replace
        box2 = QHBoxLayout()
        box2.addWidget(QLabel("Replace:"))
        box2.addWidget(self.replace_input)

        # Row 3: Buttons
        box3 = QHBoxLayout()
        box3.addWidget(self.find_btn)
        box3.addWidget(self.replace_btn)
        box3.addWidget(self.replace_all_btn)

        layout.addLayout(box1)
        layout.addLayout(box2)
        layout.addLayout(box3)
        self.setLayout(layout)

        self.find_btn.clicked.connect(self.find_next)
        self.replace_btn.clicked.connect(self.replace_one)
        self.replace_all_btn.clicked.connect(self.replace_all)

    def find_next(self):
        text = self.find_input.text()
        if not text:
            return
        
        # QEditText.find moves the cursor if found
        found = self.editor.find(text)
        
        # Wrap around if not found
        if not found:
            cursor = self.editor.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.editor.setTextCursor(cursor)
            self.editor.find(text)

    def replace_one(self):
        cursor = self.editor.textCursor()
        # Only replace if currently selected text matches
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_next()
        else:
            self.find_next()

    def replace_all(self):
        target = self.find_input.text()
        replacement = self.replace_input.text()
        if not target:
            return

        # D. Undo-safe Replace All
        cursor = self.editor.textCursor()
        cursor.beginEditBlock()  # Start transaction
        
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.editor.setTextCursor(cursor)
        
        while self.editor.find(target):
            self.editor.textCursor().insertText(replacement)
            
        cursor.endEditBlock()  # End transaction


class MainWindow(QMainWindow):
    def __init__(self, argv):
        super().__init__()

        self.setWindowTitle("Markdown Viewer")
        self.resize(1000, 700)

        self.current_file_path = None
        self.is_modified = False
        self.preview_visible = True

        # A. Setup Debounce Timer for Live Preview
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300) # 300ms delay
        self.debounce_timer.timeout.connect(self.update_preview)

        self.create_menu()

        central_widget = QWidget()
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left Pane: Editor
        self.left_pane = QTextEdit()
        self.left_pane.setAcceptDrops(False)
        self.left_pane.setPlaceholderText("Write your markdown here...")
        self.left_pane.textChanged.connect(self.on_text_modified)
        splitter.addWidget(self.left_pane)

        # Right Pane: Preview
        self.right_pane = QWebEngineView()
        self.right_pane.setHtml(CSS_STYLE + "<h2>Preview</h2>")
        splitter.addWidget(self.right_pane)

        splitter.setSizes([500, 500])
        layout.addWidget(splitter)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        self.setAcceptDrops(True)

        # Logic: Session Restore or Command Line Arg
        if os.path.exists(SESSION_FILE):
            self.restore_last_session()
        elif len(argv) > 1:
            self.try_open_startup_file(argv[1])

    def create_menu(self):
        menubar = self.menuBar()
        assert menubar is not None
        file_menu = menubar.addMenu("File")
        assert file_menu is not None

        new_action = QAction("New", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_file)
        file_menu.addAction(new_action)

        open_action = QAction("Open", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)

        save_action = QAction("Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save As", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)

        edit_menu = menubar.addMenu("Edit")
        assert edit_menu is not None
        find_action = QAction("Find / Replace", self)
        find_action.setShortcut("Ctrl+F")
        find_action.triggered.connect(self.open_find_replace)
        edit_menu.addAction(find_action)

        view_menu = menubar.addMenu("View")
        assert view_menu is not None
        self.toggle_preview_action = QAction("Show Preview", self)
        self.toggle_preview_action.setCheckable(True)
        self.toggle_preview_action.setChecked(True)
        self.toggle_preview_action.setShortcut("Ctrl+P")
        self.toggle_preview_action.triggered.connect(self.toggle_preview_mode)
        view_menu.addAction(self.toggle_preview_action)

    def new_file(self):
        if self.is_modified and not self.confirm_discard_changes():
            return
        self.left_pane.blockSignals(True)
        self.left_pane.setPlainText("")
        self.left_pane.blockSignals(False)
        self.current_file_path = None
        self.is_modified = False
        self.update_window_title()
        self.update_preview()

    def open_file(self):
        if self.is_modified and not self.confirm_discard_changes():
            return

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Markdown File",
            "",
            "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return
        self.load_file_content(file_path)

    def load_file_content(self, path):
        content = None
        err = None
        # Try multiple encodings to be safe
        for enc in ["utf-8", "utf-16", "latin-1"]:
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                    break
            except Exception as e:
                err = e
                continue
        
        if content is None:
            QMessageBox.critical(self, "File Read Error", f"Failed to read file:\n{path}\n\nError: {err}")
            return

        self.left_pane.blockSignals(True)
        self.left_pane.setPlainText(content)
        self.left_pane.blockSignals(False)
        self.current_file_path = path
        self.is_modified = False
        self.update_window_title()
        self.update_preview()

    def save_file(self):
        if not self.current_file_path:
            return self.save_file_as()

        try:
            with open(self.current_file_path, "w", encoding="utf-8") as f:
                f.write(self.left_pane.toPlainText())
            self.is_modified = False
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{self.current_file_path}\n\nError: {e}")

    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Markdown File",
            "",
            "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
        )
        if not file_path:
            return
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(self.left_pane.toPlainText())
            self.current_file_path = file_path
            self.is_modified = False
            self.update_window_title()
        except Exception as e:
            QMessageBox.critical(self, "Save Error", f"Could not save file:\n{file_path}\n\nError: {e}")

    def try_open_startup_file(self, path):
        if os.path.exists(path):
            self.load_file_content(path)

    def restore_last_session(self):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError):
            return

        last_path = data.get("last_file")
        last_text = data.get("last_text")

        if last_path and os.path.exists(last_path):
            self.load_file_content(last_path)
        elif last_text:
            self.left_pane.blockSignals(True)
            self.left_pane.setPlainText(last_text)
            self.left_pane.blockSignals(False)
            self.current_file_path = None
            self.is_modified = True # Text restored without file = unsaved
            self.update_window_title()
            self.update_preview()

    def save_session(self):
        # Save current state for next restart
        data = {
            "last_file": self.current_file_path,
            "last_text": self.left_pane.toPlainText() if self.current_file_path is None else ""
        }
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass

    def update_preview(self):
        # Called by timer
        md_text = self.left_pane.toPlainText()
        if not self.right_pane.isVisible():
            return
        html_content = convert_markdown_to_html(md_text)
        self.right_pane.setHtml(html_content)

    def open_find_replace(self):
        # Keep reference to avoid garbage collection
        self.find_dialog = FindReplaceDialog(self.left_pane)
        self.find_dialog.show()

    def on_text_modified(self):
        if not self.is_modified:
            self.is_modified = True
            self.update_window_title()
        # Reset timer on every keystroke
        self.debounce_timer.start()

    def update_window_title(self):
        name = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        mark = "*" if self.is_modified else ""
        self.setWindowTitle(f"{name}{mark} - Markdown Viewer")

    def toggle_preview_mode(self, checked=None):
        show_preview = self.right_pane.isVisible() if checked is None else checked
        if checked is None:
            show_preview = not show_preview
            
        self.preview_visible = show_preview
        self.right_pane.setVisible(show_preview)
        
        if self.toggle_preview_action:
            self.toggle_preview_action.setChecked(show_preview)
            
        if show_preview:
            self.update_preview()

    def confirm_discard_changes(self):
        if not self.is_modified:
            return True
        r = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved changes. Do you want to discard them?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        return r == QMessageBox.StandardButton.Yes

    def closeEvent(self, event):
        self.save_session()
        if self.is_modified and not self.confirm_discard_changes():
            event.ignore()
        else:
            event.accept()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            return
        path = urls[0].toLocalFile()
        if path:
            # Check for modification before loading drop
            if self.is_modified and not self.confirm_discard_changes():
                return
            self.load_file_content(path)


def main():
    app = QApplication(sys.argv)
    window = MainWindow(sys.argv)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()