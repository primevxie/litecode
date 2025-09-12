from __future__ import annotations

"""
very smol QSyntaxHighlighter with Dark+ish colors.
supports: generic code (strings, numbers, comments) + keyword sets for py/js/json.
"""

from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtCore import QRegularExpression


def fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Bold)
    if italic:
        f.setFontItalic(True)
    return f


DARK_PLUS = {
    "keyword": fmt("#c586c0", bold=True),
    "string": fmt("#ce9178"),
    "number": fmt("#b5cea8"),
    "comment": fmt("#6a9955", italic=True),
    "builtin": fmt("#4fc1ff"),
    "property": fmt("#9cdcfe"),
}


class SimpleHighlighter(QSyntaxHighlighter):
    def __init__(self, document, language: str = "generic") -> None:
        super().__init__(document)
        self.language = language
        self.rules: list[tuple[QRegularExpression, QTextCharFormat]] = []
        self._build_rules()

    def _build_rules(self) -> None:
        # strings and numbers
        self.rules.append((QRegularExpression(r"'[^'\\]*(?:\\.[^'\\]*)*'"), DARK_PLUS["string"]))
        self.rules.append((QRegularExpression(r'"[^"\\]*(?:\\.[^"\\]*)*"'), DARK_PLUS["string"]))
        self.rules.append((QRegularExpression(r"\b\d+(?:_\d+)*(?:\.\d+)?\b"), DARK_PLUS["number"]))

        # comments
        if self.language in {"python"}:
            self.rules.append((QRegularExpression(r"#.*$"), DARK_PLUS["comment"]))
        else:
            self.rules.append((QRegularExpression(r"//.*$"), DARK_PLUS["comment"]))
            # /* block */ handled in highlightBlock

        # keywords
        if self.language == "python":
            words = "False|class|finally|is|return|None|continue|for|lambda|try|True|def|from|nonlocal|while|and|del|global|not|with|as|elif|if|or|yield|assert|else|import|pass|break|except|in|raise"
        elif self.language == "javascript":
            words = "break|case|catch|class|const|continue|debugger|default|delete|do|else|export|extends|finally|for|function|if|import|in|instanceof|let|new|return|super|switch|this|throw|try|typeof|var|void|while|with|yield"
        elif self.language == "json":
            words = "true|false|null"
        else:
            words = ""
        if words:
            self.rules.append((QRegularExpression(fr"\b(?:{words})\b"), DARK_PLUS["keyword"]))

        # properties like identifiers before a colon (foo: 1)
        self.rules.append((QRegularExpression(r"(?<=\n|\{|\[|\(|\s)([A-Za-z_][\w-]*)(?=\s*:)"), DARK_PLUS["property"]))

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, form in self.rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), form)

        # crude JS/CSS block comment
        if self.language != "python":
            comment_start = text.find("/*")
            comment_end = text.find("*/")
            if comment_start != -1 and comment_end == -1:
                self.setCurrentBlockState(1)
                self.setFormat(comment_start, len(text) - comment_start, DARK_PLUS["comment"])
            elif comment_start == -1 and self.previousBlockState() == 1:
                self.setCurrentBlockState(1)
                self.setFormat(0, len(text), DARK_PLUS["comment"])
            elif comment_start != -1 and comment_end != -1 and comment_end > comment_start:
                self.setFormat(comment_start, comment_end - comment_start + 2, DARK_PLUS["comment"])
            else:
                self.setCurrentBlockState(0)


def guess_language(filename: str | None) -> str:
    if not filename:
        return "generic"
    name = filename.lower()
    if name.endswith((".py", ".pyw")):
        return "python"
    if name.endswith((".js", ".ts", ".tsx", ".jsx")):
        return "javascript"
    if name.endswith((".json",)):
        return "json"
    return "generic"


