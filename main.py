from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QTextEdit, QFileDialog, QMessageBox,
    QDialog, QLineEdit, QPushButton, QLabel, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView # type: ignore
from PyQt6.QtGui import QAction
import sys
import os
import json
import markdown # type: ignore


SESSION_FILE = "session.json"


def convert_markdown_to_html(md_text: str) -> str:
    """
    Convert Markdown text to HTML using python's markdown library
    """
    return markdown.markdown(
        md_text,
        extensions=[
            "fenced_code",
            "tables",
            "codehilite",
            "toc",
            "abbr",
            "attr_list",
        ]
    )


class FindReplaceDialog(QDialog):
    def __init__(self, editor):
        super().__init__()
        self.editor = editor
        self.setWindowTitle("Find / Replace")
        self.setModal(True)

        self.find_input = QLineEdit()
        self.replace_input = QLineEdit()
        self.find_btn = QPushButton("Find Next")
        self.replace_btn = QPushButton("Replace")
        self.replace_all_btn = QPushButton("Replace All")

        layout = QVBoxLayout()
        box1 = QHBoxLayout()
        box1.addWidget(QLabel("Find:"))
        box1.addWidget(self.find_input)

        box2 = QHBoxLayout()
        box2.addWidget(QLabel("Replace:"))
        box2.addWidget(self.replace_input)

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
        cursor = self.editor.textCursor()
        start = cursor.position()
        doc = self.editor.document()
        found = doc.find(text, start)
        if not found.isNull():
            self.editor.setTextCursor(found)
        else:
            found = doc.find(text, 0)
            if not found.isNull():
                self.editor.setTextCursor(found)

    def replace_one(self):
        t = self.find_input.text()
        r = self.replace_input.text()
        cursor = self.editor.textCursor()
        if cursor.selectedText() == t:
            cursor.insertText(r)
        self.find_next()

    def replace_all(self):
        t = self.find_input.text()
        r = self.replace_input.text()
        text = self.editor.toPlainText().replace(t, r)
        self.editor.setPlainText(text)


def create_menu(self):
    """
    create a simple menu bar
    """
    menubar = self.menuBar()
    file_menu = menubar.addMenu("File")

    new_action = QAction("New", self)
    new_action.triggered.connect(self.new_file)
    file_menu.addAction(new_action)

    open_action = QAction("Open", self)
    open_action.triggered.connect(self.open_file)
    file_menu.addAction(open_action)

    save_action = QAction("Save", self)
    save_action.triggered.connect(self.save_file)
    file_menu.addAction(save_action)

    save_as_action = QAction("Save As", self)
    save_as_action.triggered.connect(self.save_file_as)
    file_menu.addAction(save_as_action)

    edit_menu = menubar.addMenu("Edit")
    find_action = QAction("Find / Replace", self)
    find_action.triggered.connect(self.open_find_replace)
    edit_menu.addAction(find_action)

    view_menu = menubar.addMenu("View")
    self.toggle_preview_action = QAction("Show Preview", self)
    self.toggle_preview_action.setCheckable(True)
    self.toggle_preview_action.setChecked(True)
    self.toggle_preview_action.triggered.connect(self.toggle_preview_mode)
    view_menu.addAction(self.toggle_preview_action)


def open_file(self):
    """
    Open a file dialog, load markdown content into the editor.
    """
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


def save_file(self):
    """
    Save current editor content into the currently opened file.
    If no file is open, fallback to Save As.
    """
    if not getattr(self, "current_file_path", None):
        return self.save_file_as()

    try:
        with open(self.current_file_path, "w", encoding="utf-8") as f:
            f.write(self.left_pane.toPlainText())
        self.is_modified = False
        self.update_window_title()
    except Exception as e:
        QMessageBox.critical(self, "Save Error", f"Could not save file:\n{self.current_file_path}\n\nError: {e}")


def save_file_as(self):
    """
    Save editor content to a new file path chosen by the user.
    """
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


class MainWindow(QMainWindow):
    def __init__(self, argv):
        super().__init__()

        self.setWindowTitle("My PyQt6 QMainWindow")
        self.resize(900, 600)

        self.open_file = open_file.__get__(self)
        self.save_file = save_file.__get__(self)
        self.save_file_as = save_file_as.__get__(self)

        self.toggle_preview_action = None
        create_menu(self)  

        self.current_file_path = None
        self.is_modified = False
        self.preview_visible = True

        central_widget = QWidget()
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_pane = QTextEdit()
        self.left_pane.setAcceptDrops(False)
        self.left_pane.setPlaceholderText("Write your markdown here")
        self.left_pane.textChanged.connect(self.on_text_modified)
        splitter.addWidget(self.left_pane)

        self.right_pane = QWebEngineView()
        self.right_pane.setHtml("<h2>HTML Preview will appear here</h2>")
        splitter.addWidget(self.right_pane)

        splitter.setSizes([400, 400])
        layout.addWidget(splitter)
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        if os.path.exists(SESSION_FILE):
            self.restore_last_session()
        elif len(argv) > 1:
            self.try_open_startup_file(argv[1])

        self.setAcceptDrops(True)

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

    def load_file_content(self, path):
        encodings = ["utf-8", "utf-16", "latin-1"]
        content = None
        err = None
        for enc in encodings:
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

    def try_open_startup_file(self, path):
        if os.path.exists(path):
            self.load_file_content(path)
        else:
            QMessageBox.critical(self, "File Not Found", f"The file was not found:\n{path}")

    def restore_last_session(self):
        try:
            with open(SESSION_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            return
        last_path = data.get("last_file")
        last_text = data.get("last_text")
        if last_path and os.path.exists(last_path):
            self.load_file_content(last_path)
        else:
            self.left_pane.blockSignals(True)
            self.left_pane.setPlainText(last_text or "")
            self.left_pane.blockSignals(False)
            self.current_file_path = None
            self.is_modified = False
            self.update_window_title()
            self.update_preview()

    def save_session(self):
        data = {
            "last_file": self.current_file_path,
            "last_text": self.left_pane.toPlainText() if self.current_file_path is None else ""
        }
        try:
            with open(SESSION_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except:
            pass

    def update_preview(self):
        md_text = self.left_pane.toPlainText()
        if not self.right_pane.isVisible():
            return
        html_content = convert_markdown_to_html(md_text)
        self.right_pane.setHtml(html_content)

    def open_find_replace(self):
        dlg = FindReplaceDialog(self.left_pane)
        dlg.exec()

    def on_text_modified(self):
        if not self.is_modified:
            self.is_modified = True
            self.update_window_title()
        self.update_preview()

    def update_window_title(self):
        name = self.current_file_path if self.current_file_path else "Untitled"
        mark = "*" if self.is_modified else ""
        self.setWindowTitle(f"{name}{mark} - My PyQt6 QMainWindow")

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
            self.load_file_content(path)


def main():
    app = QApplication(sys.argv)
    window = MainWindow(sys.argv)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
