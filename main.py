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
        return  # User cancelled

    encodings_to_try = ["utf-8", "utf-16", "latin-1"]
    content = None
    last_exception = None

    # Try multiple encodings safely
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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("My PyQt6 QMainWindow")
        self.resize(900, 600)
        
        self.open_file = open_file.__get__(self)

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
