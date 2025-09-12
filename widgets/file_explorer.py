from __future__ import annotations

"""
side quest: lil tree that sniffs around your folders.
double-click a file to beam it into the editor.
"""

from pathlib import Path

from PySide6.QtCore import QModelIndex, QDir, Signal
from PySide6.QtWidgets import QFileSystemModel, QTreeView, QWidget, QVBoxLayout


class FileExplorer(QWidget):
    file_open_requested = Signal(object)  # Path

    def __init__(self) -> None:
        super().__init__()
        self.model = QFileSystemModel(self)
        self.model.setFilter(QDir.NoDotAndDotDot | QDir.AllDirs | QDir.Files)
        self.model.setRootPath("")

        self.view = QTreeView(self)
        self.view.setHeaderHidden(True)
        self.view.setModel(self.model)
        self.view.doubleClicked.connect(self._on_double_clicked)
        self.view.setAnimated(True)
        self.view.setIndentation(16)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

    def set_root(self, folder: Path) -> None:
        index = self.model.index(str(folder))
        self.view.setRootIndex(index)

    def _on_double_clicked(self, idx: QModelIndex) -> None:
        if self.model.isDir(idx):
            return
        path = Path(self.model.filePath(idx))
        self.file_open_requested.emit(path)


