"""Python 语法高亮器。"""
import re
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QSyntaxHighlighter, QTextCharFormat, QFont, QColor


_KEYWORDS = [
    "and", "as", "assert", "break", "class", "continue", "def",
    "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal",
    "not", "or", "pass", "raise", "return", "try", "while",
    "with", "yield", "True", "False", "None",
]

_BUILTINS = [
    "abs", "all", "any", "bin", "bool", "chr", "dict", "dir",
    "enumerate", "eval", "exec", "filter", "float", "format",
    "frozenset", "getattr", "hasattr", "hash", "hex", "id",
    "input", "int", "isinstance", "issubclass", "iter", "len",
    "list", "map", "max", "min", "next", "object", "oct",
    "open", "ord", "pow", "print", "property", "range",
    "repr", "reversed", "round", "set", "setattr", "slice",
    "sorted", "str", "sum", "super", "tuple", "type", "vars",
    "zip", "__import__",
]

_SPECIAL = ["self", "cls", "__init__", "__name__", "__main__"]


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class PythonHighlighter(QSyntaxHighlighter):
    """Python 代码语法高亮。"""

    def __init__(self, parent=None):
        super().__init__(parent)

        self._rules = [
            (re.compile(r'"""[\s\S]*?"""'), _fmt("#008000")),
            (re.compile(r"'''[\s\S]*?'''"), _fmt("#008000")),
            (re.compile(r'"(?:[^"\\]|\\.)*"'), _fmt("#008000")),
            (re.compile(r"'(?:[^'\\]|\\.)*'"), _fmt("#008000")),
            (re.compile(r"#.*$"), _fmt("#808080", italic=True)),
            (re.compile(r"@\w+"), _fmt("#AA5500")),
            (re.compile(r"\b[0-9]+\.?[0-9]*\b"), _fmt("#D04000")),
            (re.compile(r"\b(" + "|".join(_KEYWORDS) + r")\b"), _fmt("#0000CC", bold=True)),
            (re.compile(r"\b(" + "|".join(_BUILTINS) + r")\b"), _fmt("#795E26")),
            (re.compile(r"\b(" + "|".join(_SPECIAL) + r")\b"), _fmt("#7B30D0", bold=True)),
        ]

    def highlightBlock(self, text: str):
        if not text:
            return
        for pattern, fmt in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), fmt)
        self.setCurrentBlockState(0)
