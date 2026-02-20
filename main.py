import json
import os
import sys

import markdown # type: ignore
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QAction, QTextCursor
from PyQt6.QtWebEngineWidgets import QWebEngineView # type: ignore
from PyQt6.QtWidgets import (
    QApplication, QDialog, QFileDialog, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QTextEdit, QVBoxLayout, QWidget
)

SESSION_FILE = "session.json"
DEFAULT_TITLE = "Markdown Viewer"

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

def convert_markdown_to_html(md_text: str) -> str:
    """Convert Markdown text to HTML."""
    extensions = ["fenced_code", "tables", "toc", "abbr", "attr_list"]
    try:
        import pygments
        extensions.append("codehilite")
    except ImportError:
        pass

    return markdown.markdown(md_text, extensions=extensions)


class FindReplaceDialog(QDialog):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Find / Replace")
        self.setModal(False)

        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        self.find_btn = QPushButton("Find Next")
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")

        layout = QVBoxLayout()
        f_box, r_box, b_box = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        
        f_box.addWidget(QLabel("Find:")); f_box.addWidget(self.find_input)
        r_box.addWidget(QLabel("Replace:")); r_box.addWidget(self.replace_input)
        b_box.addWidget(self.find_btn); b_box.addWidget(self.replace_btn); b_box.addWidget(self.replace_all_btn)

        layout.addLayout(f_box); layout.addLayout(r_box); layout.addLayout(b_box)
        self.setLayout(layout)

        self.find_btn.clicked.connect(self.find_next)
        self.replace_btn.clicked.connect(self.replace_one)
        self.replace_all_btn.clicked.connect(self.replace_all)

    def find_next(self):
        text = self.find_input.text()
        if text and not self.editor.find(text):
            self.editor.moveCursor(QTextCursor.MoveOperation.Start)
            self.editor.find(text)

    def replace_one(self):
        cursor = self.editor.textCursor()
        if cursor.hasSelection() and cursor.selectedText() == self.find_input.text():
            cursor.insertText(self.replace_input.text())
            self.find_next()
        else:
            self.find_next()

    def replace_all(self):
        """FIX: Uses a background cursor to prevent the editor view from jumping."""
        target = self.find_input.text()
        replacement = self.replace_input.text()
        if not target: return

        doc = self.editor.document()
        cursor = QTextCursor(doc)
        cursor.beginEditBlock()
        
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        while True:
    
            found_cursor = doc.find(target, cursor)
            if found_cursor.isNull():
                break
            found_cursor.insertText(replacement)
            cursor.setPosition(found_cursor.position())
            
        cursor.endEditBlock()


class MainWindow(QMainWindow):
    def __init__(self, argv):
        super().__init__()
        self.current_file_path = None
        self.is_modified = False
        self.init_ui()
        self.setup_timer()
        self.load_initial_content(argv)

    def init_ui(self):
        self.setWindowTitle(DEFAULT_TITLE)
        self.resize(1000, 700)
        self.setAcceptDrops(True)
        self.create_menu()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.left_pane = QTextEdit()
        self.left_pane.setPlaceholderText("Write your markdown here...")
        self.left_pane.textChanged.connect(self.on_text_modified)
        
        self.right_pane = QWebEngineView()
        self.right_pane.setHtml(f"<html><head>{CSS_STYLE}</head><body><div id='content'></div></body></html>")

        splitter.addWidget(self.left_pane)
        splitter.addWidget(self.right_pane)
        self.setCentralWidget(splitter)

    def setup_timer(self):
        self.debounce_timer = QTimer()
        self.debounce_timer.setSingleShot(True)
        self.debounce_timer.setInterval(300)
        self.debounce_timer.timeout.connect(self.update_preview)

    def create_menu(self):
        menubar = self.menuBar()
        assert menubar is not None
        file_menu = menubar.addMenu("File")
        assert file_menu is not None
        for n, s, c in [("New", "Ctrl+N", self.new_file), ("Open", "Ctrl+O", self.open_file), 
                        ("Save", "Ctrl+S", self.save_file), ("Save As", "Ctrl+Shift+S", self.save_file_as)]:
            a = QAction(n, self); a.setShortcut(s); a.triggered.connect(c); file_menu.addAction(a)
        
        edit_menu = menubar.addMenu("Edit")
        assert edit_menu is not None
        f = QAction("Find / Replace", self); f.setShortcut("Ctrl+F"); f.triggered.connect(self.open_find_replace); edit_menu.addAction(f)

    def update_preview(self):
        """FIX: Uses JavaScript to update the preview content without resetting scroll position."""
        if not self.right_pane.isVisible(): return
        
        raw_html = convert_markdown_to_html(self.left_pane.toPlainText())
        
        safe_html = raw_html.replace("\\", "\\\\").replace("`", "\\`").replace("$", "\\$")
        
        js = f"document.getElementById('content').innerHTML = `{safe_html}`;"
        self.right_pane.page().runJavaScript(js)

    def _update_editor_content(self, text, path):
        self.left_pane.blockSignals(True)
        self.left_pane.setPlainText(text)
        self.left_pane.blockSignals(False)
        self.current_file_path, self.is_modified = path, False
        self.update_window_title()
        self.update_preview()

    def on_text_modified(self):
        if not self.is_modified:
            self.is_modified = True
            self.update_window_title()
        self.debounce_timer.start()

    def load_initial_content(self, argv):
        if os.path.exists(SESSION_FILE): self.restore_last_session()
        elif len(argv) > 1: self.load_file_content(argv[1])

    def new_file(self):
        if not self.is_modified or self.confirm_discard(): self._update_editor_content("", None)

    def open_file(self):
        if not self.is_modified or self.confirm_discard():
            p, _ = QFileDialog.getOpenFileName(self, "Open", "", "Markdown (*.md);;All Files (*)")
            if p: self.load_file_content(p)

    def load_file_content(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f: self._update_editor_content(f.read(), path)
        except: QMessageBox.critical(self, "Error", f"Could not read {path}")

    def save_file(self):
        if not self.current_file_path: return self.save_file_as()
        self._write_to_disk(self.current_file_path)

    def save_file_as(self):
        p, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Markdown (*.md)")
        if p: self._write_to_disk(p)

    def _write_to_disk(self, path):
        try:
            with open(path, "w", encoding="utf-8") as f: f.write(self.left_pane.toPlainText())
            self.current_file_path, self.is_modified = path, False
            self.update_window_title()
        except Exception as e: QMessageBox.critical(self, "Save Error", str(e))

    def restore_last_session(self):
        try:
            with open(SESSION_FILE, "r") as f: data = json.load(f)
            if data.get("last_file") and os.path.exists(data["last_file"]): self.load_file_content(data["last_file"])
            elif data.get("last_text"): self._update_editor_content(data["last_text"], None); self.is_modified = True; self.update_window_title()
        except: pass

    def save_session(self):
        try:
            with open(SESSION_FILE, "w") as f: json.dump({"last_file": self.current_file_path, "last_text": self.left_pane.toPlainText() if not self.current_file_path else ""}, f)
        except: pass

    def open_find_replace(self): self.find_dialog = FindReplaceDialog(self.left_pane); self.find_dialog.show()

    def update_window_title(self):
        f = os.path.basename(self.current_file_path) if self.current_file_path else "Untitled"
        self.setWindowTitle(f"{f}{'*' if self.is_modified else ''} - {DEFAULT_TITLE}")

    def confirm_discard(self):
        return QMessageBox.question(self, "Unsaved Changes", "Discard changes?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes

    def closeEvent(self, e):
        self.save_session()
        if self.is_modified and not self.confirm_discard(): e.ignore()
        else: e.accept()

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls(): e.acceptProposedAction()

    def dropEvent(self, e):
        urls = e.mimeData().urls()
        if urls and (not self.is_modified or self.confirm_discard()): self.load_file_content(urls[0].toLocalFile())

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow(sys.argv)
    window.show()
    sys.exit(app.exec())