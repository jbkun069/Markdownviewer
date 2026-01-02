# Markdown Viewer

A lightweight, desktop Markdown editor and previewer built with PyQt6.

## Features

- **Live Preview** - See your Markdown rendered as HTML in real-time
- **Split View** - Markdown text on the left, preview on the right
- **Find & Replace** - Search and replace text within your documents
- **Session Restore** - Automatically restores your last session on startup
- **Drag & Drop** - Drop Markdown files directly into the editor

## Supported Markdown Extensions

- Fenced code blocks
- Tables
- Code highlighting
- Table of contents
- Abbreviations
- Attribute lists

## Installation

### Prerequisites

- Python 3.8+
- pip

### Install Dependencies

```bash
pip install PyQt6 PyQt6-WebEngine markdown
```

### Run the Application

```bash
python main.py
```

### Open a File Directly

```bash
python main.py path/to/your/file.md
```

## Usage

| Action | Menu |
|--------|------|
| New File | File → New |
| Open File | File → Open |
| Save | File → Save |
| Save As | File → Save As |
| Find/Replace | Edit → Find / Replace |
| Toggle Preview | View → Show Preview |

## Project Structure

```
markdownviewer/
├── main.py              # Main application code
├── session.json         # Session state (auto-generated)
├── .gitignore        
└── README.md
```
