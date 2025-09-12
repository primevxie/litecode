from __future__ import annotations

"""
find/replace panel with regex, case sensitivity, whole word.
also does "find in files" with a results list.
"""

import re
from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt, Signal, QThread
from PySide6.QtGui import QTextCursor, QTextDocument
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, 
    QCheckBox, QLabel, QListWidget, QListWidgetItem, QSplitter,
    QTextEdit, QGroupBox, QFrame
)


class FindInFilesWorker(QThread):
    """background thread for searching files"""
    result_found = Signal(str, int, str)  # file_path, line_num, line_text
    finished = Signal()
    
    def __init__(self, search_path: Path, pattern: str, use_regex: bool, case_sensitive: bool, whole_word: bool):
        super().__init__()
        self.search_path = search_path
        self.pattern = pattern
        self.use_regex = use_regex
        self.case_sensitive = case_sensitive
        self.whole_word = whole_word
        self._stop = False
    
    def stop(self):
        self._stop = True
    
    def run(self):
        try:
            if self.use_regex:
                flags = 0 if self.case_sensitive else re.IGNORECASE
                regex = re.compile(self.pattern, flags)
            else:
                if not self.case_sensitive:
                    search_text = self.pattern.lower()
                else:
                    search_text = self.pattern
            
            for file_path in self.search_path.rglob("*"):
                if self._stop:
                    break
                if not file_path.is_file() or file_path.suffix in {'.pyc', '.pyo', '.pyd', '.so', '.dll', '.exe'}:
                    continue
                
                try:
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        for line_num, line in enumerate(f, 1):
                            if self._stop:
                                break
                            
                            if self.use_regex:
                                if regex.search(line):
                                    self.result_found.emit(str(file_path), line_num, line.rstrip())
                            else:
                                search_line = line if self.case_sensitive else line.lower()
                                if self.whole_word:
                                    if f" {search_text} " in f" {search_line} ":
                                        self.result_found.emit(str(file_path), line_num, line.rstrip())
                                else:
                                    if search_text in search_line:
                                        self.result_found.emit(str(file_path), line_num, line.rstrip())
                except Exception:
                    continue
        except Exception:
            pass
        finally:
            self.finished.emit()


class FindPanel(QWidget):
    """find/replace panel with all the goodies"""
    find_requested = Signal(str, bool, bool, bool)  # text, regex, case, whole_word
    replace_requested = Signal(str, str, bool, bool, bool)  # find, replace, regex, case, whole_word
    file_result_clicked = Signal(str, int)  # file_path, line_num
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(120)
        self.setVisible(False)
        
        # find controls
        find_layout = QHBoxLayout()
        find_layout.addWidget(QLabel("Find:"))
        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("search text...")
        self.find_input.returnPressed.connect(self._find_next)
        find_layout.addWidget(self.find_input)
        
        self.find_next_btn = QPushButton("Next")
        self.find_next_btn.clicked.connect(self._find_next)
        find_layout.addWidget(self.find_next_btn)
        
        self.find_prev_btn = QPushButton("Prev")
        self.find_prev_btn.clicked.connect(self._find_prev)
        find_layout.addWidget(self.find_prev_btn)
        
        # replace controls
        replace_layout = QHBoxLayout()
        replace_layout.addWidget(QLabel("Replace:"))
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("replacement text...")
        replace_layout.addWidget(self.replace_input)
        
        self.replace_btn = QPushButton("Replace")
        self.replace_btn.clicked.connect(self._replace_current)
        replace_layout.addWidget(self.replace_btn)
        
        self.replace_all_btn = QPushButton("Replace All")
        self.replace_all_btn.clicked.connect(self._replace_all)
        replace_layout.addWidget(self.replace_all_btn)
        
        # options
        options_layout = QHBoxLayout()
        self.regex_cb = QCheckBox("Regex")
        self.case_cb = QCheckBox("Case")
        self.whole_word_cb = QCheckBox("Whole Word")
        options_layout.addWidget(self.regex_cb)
        options_layout.addWidget(self.case_cb)
        options_layout.addWidget(self.whole_word_cb)
        options_layout.addStretch()
        
        # close button
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.hide)
        options_layout.addWidget(self.close_btn)
        
        # main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.addLayout(find_layout)
        layout.addLayout(replace_layout)
        layout.addLayout(options_layout)
    
    def _find_next(self):
        text = self.find_input.text()
        if text:
            self.find_requested.emit(text, self.regex_cb.isChecked(), self.case_cb.isChecked(), self.whole_word_cb.isChecked())
    
    def _find_prev(self):
        text = self.find_input.text()
        if text:
            # TODO: implement reverse search
            self.find_requested.emit(text, self.regex_cb.isChecked(), self.case_cb.isChecked(), self.whole_word_cb.isChecked())
    
    def _replace_current(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if find_text:
            self.replace_requested.emit(find_text, replace_text, self.regex_cb.isChecked(), self.case_cb.isChecked(), self.whole_word_cb.isChecked())
    
    def _replace_all(self):
        find_text = self.find_input.text()
        replace_text = self.replace_input.text()
        if find_text:
            # TODO: implement replace all
            self.replace_requested.emit(find_text, replace_text, self.regex_cb.isChecked(), self.case_cb.isChecked(), self.whole_word_cb.isChecked())
    
    def show_panel(self):
        self.setVisible(True)
        self.find_input.setFocus()
        self.find_input.selectAll()


class FindInFilesPanel(QWidget):
    """find in files results panel"""
    file_result_clicked = Signal(str, int)  # file_path, line_num
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setVisible(False)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # header
        header_layout = QHBoxLayout()
        header_layout.addWidget(QLabel("Find in Files Results"))
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(24, 24)
        self.close_btn.clicked.connect(self.hide)
        header_layout.addStretch()
        header_layout.addWidget(self.close_btn)
        
        # results list
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self._on_result_clicked)
        layout.addLayout(header_layout)
        layout.addWidget(self.results_list)
        
        self.search_worker = None
    
    def _on_result_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.UserRole)
        if data:
            file_path, line_num = data
            self.file_result_clicked.emit(file_path, line_num)
    
    def start_search(self, search_path: Path, pattern: str, use_regex: bool, case_sensitive: bool, whole_word: bool):
        if self.search_worker:
            self.search_worker.stop()
        
        self.results_list.clear()
        self.setVisible(True)
        
        self.search_worker = FindInFilesWorker(search_path, pattern, use_regex, case_sensitive, whole_word)
        self.search_worker.result_found.connect(self._add_result)
        self.search_worker.finished.connect(self._search_finished)
        self.search_worker.start()
    
    def _add_result(self, file_path: str, line_num: int, line_text: str):
        item = QListWidgetItem(f"{Path(file_path).name}:{line_num} - {line_text[:80]}")
        item.setData(Qt.UserRole, (file_path, line_num))
        self.results_list.addItem(item)
    
    def _search_finished(self):
        self.search_worker = None
        if self.results_list.count() == 0:
            item = QListWidgetItem("No results found")
            item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
            self.results_list.addItem(item)
