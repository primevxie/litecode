"""
ok hi. tiny editor vibes. brain smooth, code clean.
this file wires the whole lil app together: window, tabs, explorer, save/open.
think mini vscode but without the 400mb snacks. crunchy.
"""

import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QSize, QFile, QTextStream, QTimer
from PySide6.QtGui import QAction, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMainWindow,
    QSplitter,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QMessageBox,
    QStyle,
    QLabel,
)

from widgets.code_editor import CodeEditor
from widgets.file_explorer import FileExplorer


APP_NAME = "LiteCode"


def resource_path(relative: str) -> str:
    base_path = Path(__file__).parent
    return str(base_path / relative)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1200, 800)

        self._current_folder: Path | None = None

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.tabs.currentChanged.connect(self.update_status)

        self.explorer = FileExplorer()
        self.explorer.file_open_requested.connect(self.open_file_in_editor)

        splitter = QSplitter()  # two-pane sandwich: explorer | editor tabs
        splitter.addWidget(self.explorer)
        splitter.addWidget(self.tabs)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(splitter, 1)
        self.setCentralWidget(container)

        # segmented status bar: Path | Ln/Col | UTF-8 | LF | Spaces | AutoSave
        self.path_label = QLabel("")
        self.status_label = QLabel("Ready")
        self.encoding_label = QLabel("UTF-8")
        self.eol_label = QLabel("LF")
        self.indent_label = QLabel("Spaces:4")
        self.autosave_label = QLabel("AutoSave: Off")
        for w in [self.path_label, self.status_label, self.encoding_label, self.eol_label, self.indent_label, self.autosave_label]:
            w.setMargin(4)
            self.statusBar().addPermanentWidget(w)

        self._create_actions()
        self._create_menus_and_toolbar()
        self._load_theme()

        # Auto save
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self._autosave_tick)

    # UI wiring
    def _create_actions(self) -> None:
        """buttons go brr. file + nav + autosave toggles."""
        style = self.style()

        self.new_action = QAction(QIcon.fromTheme("document-new", style.standardIcon(QStyle.SP_FileIcon)), "New", self)
        self.new_action.setShortcut(QKeySequence.New)
        self.new_action.triggered.connect(self.new_file)

        self.open_file_action = QAction(QIcon.fromTheme("document-open", style.standardIcon(QStyle.SP_DirOpenIcon)), "Open File…", self)
        self.open_file_action.setShortcut(QKeySequence.Open)
        self.open_file_action.triggered.connect(self.open_file_dialog)

        self.open_folder_action = QAction("Open Folder…", self)
        self.open_folder_action.setShortcut("Ctrl+K, Ctrl+O")
        self.open_folder_action.triggered.connect(self.open_folder_dialog)

        self.save_action = QAction(QIcon.fromTheme("document-save", style.standardIcon(QStyle.SP_DialogSaveButton)), "Save", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_file)

        self.save_as_action = QAction("Save As…", self)
        self.save_as_action.setShortcut(QKeySequence.SaveAs)
        self.save_as_action.triggered.connect(self.save_file_as)

        self.close_tab_action = QAction("Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence.Close)
        self.close_tab_action.triggered.connect(lambda: self.close_tab(self.tabs.currentIndex()))

        self.exit_action = QAction("Exit", self)
        self.exit_action.setShortcut(QKeySequence.Quit)
        self.exit_action.triggered.connect(self.close)

        # Tab navigation like VS Code
        self.next_tab_action = QAction("Next Tab", self)
        self.next_tab_action.setShortcut("Ctrl+Tab")
        self.next_tab_action.triggered.connect(self.goto_next_tab)

        self.prev_tab_action = QAction("Previous Tab", self)
        self.prev_tab_action.setShortcut("Ctrl+Shift+Tab")
        self.prev_tab_action.triggered.connect(self.goto_prev_tab)

        # Auto Save toggle
        self.autosave_action = QAction("Auto Save", self)
        self.autosave_action.setCheckable(True)
        self.autosave_action.setChecked(False)
        self.autosave_action.triggered.connect(self._toggle_autosave)

    def _create_menus_and_toolbar(self) -> None:
        """stick actions into menus and a smol toolbar."""
        menu_file = self.menuBar().addMenu("File")
        menu_file.addAction(self.new_action)
        menu_file.addSeparator()
        menu_file.addAction(self.open_file_action)
        menu_file.addAction(self.open_folder_action)
        menu_file.addSeparator()
        menu_file.addAction(self.save_action)
        menu_file.addAction(self.save_as_action)
        menu_file.addAction(self.autosave_action)
        menu_file.addSeparator()
        menu_file.addAction(self.close_tab_action)
        menu_file.addSeparator()
        menu_file.addAction(self.exit_action)

        toolbar = self.addToolBar("Main")
        toolbar.setIconSize(QSize(16, 16))
        toolbar.setMovable(False)
        toolbar.setFloatable(False)
        toolbar.setToolButtonStyle(Qt.ToolButtonIconOnly)
        toolbar.addAction(self.new_action)
        toolbar.addAction(self.open_file_action)
        toolbar.addAction(self.save_action)

        menu_nav = self.menuBar().addMenu("Navigate")
        menu_nav.addAction(self.next_tab_action)
        menu_nav.addAction(self.prev_tab_action)

        # Breadcrumbs bar (simple path label) above tabs
        # lightweight approach without custom widget complexity
        # shows current file relative path if available

    def _load_theme(self) -> None:
        """put on the dark drip (qss)."""
        qss_path = resource_path("resources/theme.qss")
        if os.path.exists(qss_path):
            file = QFile(qss_path)
            if file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(file)
                self.setStyleSheet(stream.readAll())

    # File operations
    def new_file(self) -> None:
        """spawn fresh tab. smells like new code."""
        editor = CodeEditor()
        editor.setProperty("file_path", None)
        editor.set_associated_path(None)
        editor.cursorPositionChanged.connect(self.update_status)
        editor.document().modificationChanged.connect(self._update_tab_modified_flag)
        self.tabs.addTab(editor, "Untitled")
        self.tabs.setCurrentWidget(editor)
        self.update_status()

    def open_file_dialog(self) -> None:
        """pick file from the void and open it."""
        path, _ = QFileDialog.getOpenFileName(self, "Open File")
        if path:
            self.open_file_in_editor(Path(path))

    def open_folder_dialog(self) -> None:
        """aim explorer at a new lair (folder)."""
        path = QFileDialog.getExistingDirectory(self, "Open Folder")
        if path:
            folder = Path(path)
            self._current_folder = folder
            self.setWindowTitle(f"{APP_NAME} — {folder}")
            self.explorer.set_root(folder)

    def open_file_in_editor(self, path: Path) -> None:
        """read file bytes. yeet text into a tab."""
        try:
            text = Path(path).read_text(encoding="utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Open Failed", str(exc))
            return

        editor = CodeEditor()
        editor.setPlainText(text)
        editor.setProperty("file_path", str(path))
        editor.set_associated_path(str(path))
        editor.cursorPositionChanged.connect(self.update_status)
        editor.document().modificationChanged.connect(self._update_tab_modified_flag)
        self.tabs.addTab(editor, path.name)
        self.tabs.setTabToolTip(self.tabs.count() - 1, str(path))
        self.tabs.setCurrentWidget(editor)
        self._update_path_indicator()
        self.update_status()

    def _current_editor(self) -> CodeEditor | None:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, CodeEditor) else None

    def save_file(self) -> None:
        """save current tab if it exists. tidy up crumbs."""
        editor = self._current_editor()
        if not editor:
            return
        file_path = editor.property("file_path")
        if not file_path:
            self.save_file_as()
            return
        try:
            Path(str(file_path)).write_text(editor.toPlainText(), encoding="utf-8")
            self.status_label.setText("Saved")
            editor.document().setModified(False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Failed", str(exc))

    def save_file_as(self) -> None:
        """save but let u choose the destiny path."""
        editor = self._current_editor()
        if not editor:
            return
        path, _ = QFileDialog.getSaveFileName(self, "Save As")
        if not path:
            return
        try:
            Path(path).write_text(editor.toPlainText(), encoding="utf-8")
            editor.setProperty("file_path", path)
            self.tabs.setTabText(self.tabs.currentIndex(), Path(path).name)
            self.tabs.setTabToolTip(self.tabs.currentIndex(), path)
            self.status_label.setText("Saved")
            editor.document().setModified(False)
        except Exception as exc:  # noqa: BLE001
            QMessageBox.critical(self, "Save Failed", str(exc))

    def close_tab(self, index: int) -> None:
        if index >= 0:
            self.tabs.removeTab(index)
            self.update_status()

    def update_status(self) -> None:
        editor = self._current_editor()
        if editor:
            cursor = editor.textCursor()
            self.status_label.setText(f"Ln {cursor.blockNumber()+1}, Col {cursor.columnNumber()+1}")
            self._update_path_indicator()
        else:
            self.status_label.setText("Ready")

    # Tab navigation helpers
    def goto_next_tab(self) -> None:
        count = self.tabs.count()
        if count == 0:
            return
        self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % count)

    def goto_prev_tab(self) -> None:
        count = self.tabs.count()
        if count == 0:
            return
        self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % count)

    # Modified indicator handling
    def _update_tab_modified_flag(self) -> None:
        idx = self.tabs.currentIndex()
        if idx < 0:
            return
        editor = self._current_editor()
        if not editor:
            return
        base = Path(editor.property("file_path") or "Untitled").name
        if editor.document().isModified():
            title = f"{base} •"
        else:
            title = base
        self.tabs.setTabText(idx, title)

    # Autosave
    def _toggle_autosave(self, checked: bool) -> None:
        if checked:
            self.autosave_timer.start(5000)
            self.autosave_label.setText("AutoSave: On")
        else:
            self.autosave_timer.stop()
            self.autosave_label.setText("AutoSave: Off")

    def _autosave_tick(self) -> None:
        for i in range(self.tabs.count()):
            widget = self.tabs.widget(i)
            if not isinstance(widget, CodeEditor):
                continue
            file_path = widget.property("file_path")
            if file_path and widget.document().isModified():
                try:
                    Path(str(file_path)).write_text(widget.toPlainText(), encoding="utf-8")
                    widget.document().setModified(False)
                except Exception:
                    # Ignore autosave failures silently
                    pass

    # Drag & Drop
    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dropEvent(self, event):  # noqa: N802
        for url in event.mimeData().urls():
            path = Path(url.toLocalFile())
            if path.is_dir():
                self._current_folder = path
                self.setWindowTitle(f"{APP_NAME} — {path}")
                self.explorer.set_root(path)
            elif path.is_file():
                self.open_file_in_editor(path)
        event.acceptProposedAction()

    # Path indicator helper (status bar)
    def _update_path_indicator(self) -> None:
        editor = self._current_editor()
        if not editor:
            self.path_label.setText("")
            return
        path = editor.property("file_path")
        if not path:
            self.path_label.setText("untitled")
            return
        p = Path(str(path))
        if self._current_folder and str(p).startswith(str(self._current_folder)):
            rel = p.relative_to(self._current_folder)
            self.path_label.setText(str(rel).replace("\\", " / ").replace("/", " / "))
        else:
            self.path_label.setText(p.name)


def main() -> int:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())


