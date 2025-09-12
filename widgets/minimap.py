from __future__ import annotations

"""
tiny minimap widget for code overview.
shows a scaled-down version of the document with current viewport highlighted.
"""

from PySide6.QtCore import Qt, QRect, QSize
from PySide6.QtGui import QPainter, QColor, QFont
from PySide6.QtWidgets import QWidget, QScrollBar


class Minimap(QWidget):
    """minimap showing document overview with viewport highlight"""
    
    def __init__(self, editor=None, parent=None):
        super().__init__(parent)
        self.editor = None
        self.setFixedWidth(120)
        self.setMinimumHeight(100)
        
        # scroll bar for minimap navigation
        self.scroll_bar = QScrollBar(Qt.Vertical, self)
        self.scroll_bar.valueChanged.connect(self._on_scroll)
        
        # minimap settings
        self.line_height = 2  # pixels per line in minimap
        self.char_width = 1   # pixels per character in minimap
        
        if editor is not None:
            self.set_editor(editor)

    def set_editor(self, editor) -> None:
        """Attach to a QPlainTextEdit-like editor or detach with None."""
        # disconnect old
        if self.editor is not None:
            try:
                self.editor.updateRequest.disconnect(self.update)
            except Exception:
                pass
            try:
                self.editor.cursorPositionChanged.disconnect(self.update)
            except Exception:
                pass
        self.editor = editor
        if self.editor is not None:
            # connect updates
            try:
                self.editor.updateRequest.connect(self.update)
            except Exception:
                pass
            try:
                self.editor.cursorPositionChanged.connect(self.update)
            except Exception:
                pass
        self.update()
    
    def resizeEvent(self, event):  # noqa: N802
        super().resizeEvent(event)
        self.scroll_bar.setGeometry(self.width() - 16, 0, 16, self.height())
    
    def _on_scroll(self, value):
        """scroll the main editor when minimap is scrolled"""
        if not self.editor:
            return
        if hasattr(self.editor, 'verticalScrollBar'):
            scroll_bar = self.editor.verticalScrollBar()
            max_val = scroll_bar.maximum()
            if max_val > 0 and self.scroll_bar.maximum() > 0:
                ratio = value / self.scroll_bar.maximum()
                scroll_bar.setValue(int(ratio * max_val))
    
    def paintEvent(self, event):
        """paint the minimap"""
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(30, 30, 30))
        
        if not self.editor or not hasattr(self.editor, 'document'):
            return
            
        doc = self.editor.document()
        if not doc:
            return
            
        # get document metrics
        block_count = doc.blockCount()
        if block_count == 0:
            return
            
        # calculate minimap dimensions
        minimap_height = block_count * self.line_height
        self.scroll_bar.setMaximum(max(0, minimap_height - self.height()))
        
        # get current viewport
        scroll_bar = self.editor.verticalScrollBar()
        viewport_top = scroll_bar.value()
        viewport_height = self.editor.viewport().height()
        line_height = self.editor.fontMetrics().height()
        
        # draw viewport highlight
        if viewport_height > 0 and line_height > 0:
            viewport_start = (viewport_top / line_height) * self.line_height
            viewport_end = ((viewport_top + viewport_height) / line_height) * self.line_height
            highlight_rect = QRect(0, int(viewport_start), self.width() - 16, int(viewport_end - viewport_start))
            painter.fillRect(highlight_rect, QColor(100, 100, 100, 50))
        
        # draw document content (simplified)
        painter.setPen(QColor(150, 150, 150))
        font = QFont("Consolas", 6)
        painter.setFont(font)
        
        block = doc.firstBlock()
        y = 0
        while block.isValid() and y < self.height():
            text = block.text()
            if text.strip():  # only draw non-empty lines
                display_text = text[: self.width() // 2]
                painter.drawText(2, y + self.line_height - 1, display_text)
            y += self.line_height
            block = block.next()
    
    def mousePressEvent(self, event):
        """click to jump to position in document"""
        if event.button() == Qt.LeftButton and self.editor:
            y = event.y()
            line_height = self.editor.fontMetrics().height()
            minimap_line = y // self.line_height
            target_pos = minimap_line * line_height
            self.editor.verticalScrollBar().setValue(target_pos)
    
    def wheelEvent(self, event):
        """scroll minimap with mouse wheel"""
        self.scroll_bar.setValue(self.scroll_bar.value() - event.angleDelta().y() // 8)
