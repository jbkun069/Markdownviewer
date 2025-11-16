from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QTextEdit, QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView  # pyright: ignore[reportMissingImports]
from PyQt6.QtGui import QAction
import sys
import markdown  # type: ignore


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


def create_menu(self):
    """
    create a simple menu bar
    """
    menubar = self.menuBar()
    file_menu = menubar.addMenu("file")

    open_action = QAction("Open", self)
    open_action.triggered.connect(self.open_file)
    file_menu.addAction(open_action)
    
    save_action = QAction("Save", self)
    save_action.triggered.connect(self.save_file)
    file_menu.addAction(save_action)
    
    save_as_action = QAction("Save As", self)
    save_as_action.triggered.connect(self.save_file_as)
    file_menu.addAction(save_as_action)
    

def open_file(self):
    """
    Open a file dialog, load markdown content into the editor.
    """
    file_path, _ = QFileDialog.getOpenFileName(
        self,
        "Open Markdown File",
        "",
        "Markdown Files (*.md *.markdown);;Text Files (*.txt);;All Files (*)"
    )

    if not file_path:
        return  

    encodings_to_try = ["utf-8", "utf-16", "latin-1"]
    content = None
    last_exception = None

    for enc in encodings_to_try:
        try:
            with open(file_path, "r", encoding=enc) as f:
                content = f.read()
                break
        except Exception as e:
            last_exception = e
            continue

    if content is None:
        QMessageBox.critical(
            self,
            "File Read Error",
            f"Failed to read file:\n{file_path}\n\nError: {last_exception}"
        )
        return
    
    self.left_pane.setPlainText(content)

    self.update_preview()

def save_file(self):
    """
    Save current editor content into the currently opened file.
    """
    if not getattr(self, "current_file_path", None):
        return self.save_file_as()

    try:
        with open(self.current_file_path, "w", encoding="utf-8") as f:
            f.write(self.left_pane.toPlainText())
    except Exception as e:
        QMessageBox.critical(
            self,
            "Save Error",
            f"Could not save file:\n{self.current_file_path}\n\nError: {e}"
        )

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
    except Exception as e:
        QMessageBox.critical(
            self,
            "Save Error",
            f"Could not save file:\n{file_path}\n\nError: {e}"
        )
    

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My PyQt6 QMainWindow")
        self.resize(900, 600)
        
        self.open_file = open_file.__get__(self)
        self.save_file = save_file.__get__(self)
        self.save_file_as = save_file_as.__get__(self)

        create_menu(self)

        central_widget = QWidget()
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.left_pane = QTextEdit()
        self.left_pane.setPlaceholderText("Write your markdown here")
        self.left_pane.textChanged.connect(self.update_preview)
        splitter.addWidget(self.left_pane)

        self.right_pane = QWebEngineView()
        self.right_pane.setHtml("<h2>HTML Preview will appear here</h2>")
        splitter.addWidget(self.right_pane)

        splitter.setSizes([400, 400])

        layout.addWidget(splitter)
        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)

    def update_preview(self):
        md_text = self.left_pane.toPlainText()
        html_content = convert_markdown_to_html(md_text)
        self.right_pane.setHtml(html_content)


def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
