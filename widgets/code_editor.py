from __future__ import annotations

"""
this is the text widget with lil line numbers.
no syntax fireworks yet, just comfy vibes and crisp glyphs.
"""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QTextFormat
from PySide6.QtWidgets import QPlainTextEdit, QWidget, QTextEdit
from .highlighter import SimpleHighlighter, guess_language


class LineNumberArea(QWidget):
    def __init__(self, editor: "CodeEditor") -> None:
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self) -> QSize:  # type: ignore[override]
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):  # noqa: N802
        self.code_editor.line_number_area_paint_event(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self) -> None:
        super().__init__()
        self.setTabStopDistance(4 * self.fontMetrics().horizontalAdvance(" "))
        self.setFrameStyle(0)
        self._line_number_area = LineNumberArea(self)

        # Editor font and padding for a cleaner look
        font = self.font()
        font.setFamily("Cascadia Code, Fira Code, Consolas, 'Courier New', monospace")
        font.setPointSize(11)
        self.setFont(font)
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)

        self.update_line_number_area_width(0)
        self.highlight_current_line()

        # attach syntax highlighter (guessed later when file path known)
        self._highlighter: SimpleHighlighter | None = SimpleHighlighter(self.document(), "generic")

    def set_associated_path(self, path: str | None) -> None:
        lang = guess_language(path)
        self._highlighter = SimpleHighlighter(self.document(), lang)

    # Layout
    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance("9") * digits
        return space + 8

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int):
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    # Painting
    def line_number_area_paint_event(self, event):
        # paint the lil left gutter like a midnight alley
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(37, 37, 38))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor(153, 153, 153))
                painter.drawText(0, top, self._line_number_area.width() - 6, self.fontMetrics().height(), Qt.AlignRight, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        # glow the line ur cursor is munching on
        extra_selections = []
        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            line_color = QColor(255, 255, 255, 15)
            selection.format.setBackground(line_color)
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)
        self.setExtraSelections(extra_selections)


