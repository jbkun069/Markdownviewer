# Markdown Viewer

A lightweight, cross-platform desktop Markdown editor and previewer built with PyQt6.

## Features

- **Live Preview**: See your Markdown rendered as HTML in real-time as you type.
- **Split View**: A convenient side-by-side view with the Markdown text on the left and the rendered HTML preview on the right.
- **Syntax Highlighting**: Code blocks are highlighted for better readability.
- **Find & Replace**: Quickly search for and replace text within your documents.
- **Session Restore**: Automatically re-opens the files and tabs from your last session on startup.
- **Drag & Drop**: Easily open Markdown files by dragging and dropping them into the editor window.

## Supported Markdown Extensions

This editor uses the [Python-Markdown](https://python-markdown.github.io/) library and supports several extensions out of the box:

- Fenced code blocks (`fenced_code`)
- Tables (`tables`)
- Code highlighting (`codehilite`)
- Table of contents (`toc`)
- Abbreviations (`abbr`)
- Attribute lists (`attr_list`)

## Installation

### Prerequisites

- Python 3.8+
- pip

### Install from `requirements.txt`

install it using:

```bash
pip install -r requirements.txt
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
