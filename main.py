from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QSplitter, QTextEdit
)
from PyQt6.QtCore import Qt
from PyQt6.QtWebEngineWidgets import QWebEngineView  # pyright: ignore[reportMissingImports]
import sys

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
       
        self.setWindowTitle("My PyQt6 QMainWindow")
        self.resize(500, 500)

        central_widget = QWidget()
        layout = QVBoxLayout()
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.left_pane =  QTextEdit()
        self.left_pane.textChanged.connect(self.update_preview)
        splitter.addWidget(self.left_pane)
        
        self.right_pane = QWebEngineView()
        self.right_pane.setHtml("<h2>HTML Preview will appear here</h2>")
        splitter.addWidget(self.right_pane)
        
        splitter.setSizes([400,400])
        #splitter.setSizes([400,400])
        
        layout.addWidget(splitter)

        central_widget.setLayout(layout)

        self.setCentralWidget(central_widget)
    
    def update_preview(self):
        content = self.left_pane.toPlainText()
        self.right_pane.setHtml(content)

def main():
    app = QApplication(sys.argv)

    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
