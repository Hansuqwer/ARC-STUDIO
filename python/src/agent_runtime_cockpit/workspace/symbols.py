"""Workspace symbol extraction — Python and TypeScript/JavaScript."""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel

SYMBOL_SUFFIXES = (".py", ".ts", ".tsx", ".js", ".jsx")


class WorkspaceSymbol(BaseModel):
    qualname: str
    name: str
    kind: str
    path: str
    relpath: str
    line: int
    column: int
    parent: Optional[str] = None


class SymbolExtractionError(BaseModel):
    path: str
    relpath: str
    error: str


class SymbolInventory(BaseModel):
    symbols: list[WorkspaceSymbol] = []
    errors: list[SymbolExtractionError] = []
    total_files_scanned: int = 0
    total_symbols: int = 0
    truncated: bool = False
    oversized_skipped: int = 0


def extract_python_symbols(path: Path, relpath: str, text: str) -> list[WorkspaceSymbol]:
    symbols: list[WorkspaceSymbol] = []
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return symbols
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols.append(
                WorkspaceSymbol(
                    qualname=node.name,
                    name=node.name,
                    kind="class",
                    path=str(path),
                    relpath=relpath,
                    line=node.lineno or 0,
                    column=node.col_offset or 0,
                )
            )
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    parent_qual = node.name
                    symbols.append(
                        WorkspaceSymbol(
                            qualname=f"{parent_qual}.{item.name}",
                            name=item.name,
                            kind="method",
                            path=str(path),
                            relpath=relpath,
                            line=item.lineno or 0,
                            column=item.col_offset or 0,
                            parent=parent_qual,
                        )
                    )
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not _is_nested_function(node, tree):
                symbols.append(
                    WorkspaceSymbol(
                        qualname=node.name,
                        name=node.name,
                        kind="function",
                        path=str(path),
                        relpath=relpath,
                        line=node.lineno or 0,
                        column=node.col_offset or 0,
                    )
                )
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            if isinstance(node, ast.AnnAssign) and node.target:
                target = node.target
            elif isinstance(node, ast.Assign):
                target = node.targets[0] if node.targets else None
            else:
                continue
            if isinstance(target, ast.Name):
                symbols.append(
                    WorkspaceSymbol(
                        qualname=target.id,
                        name=target.id,
                        kind="variable",
                        path=str(path),
                        relpath=relpath,
                        line=node.lineno or 0,
                        column=node.col_offset or 0,
                    )
                )
    return symbols


def _is_nested_function(node: ast.AST, tree: ast.Module) -> bool:
    for parent in ast.walk(tree):
        if parent is node:
            continue
        if isinstance(parent, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            for child in ast.walk(parent):
                if child is node:
                    return True
    return False


_TS_KIND_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("class", re.compile(r"(?:export\s+)?class\s+(\w+)")),
    ("interface", re.compile(r"(?:export\s+)?interface\s+(\w+)")),
    ("type", re.compile(r"(?:export\s+)?type\s+(\w+)\s*=")),
    ("enum", re.compile(r"(?:export\s+)?enum\s+(\w+)")),
    ("function", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
    ("variable", re.compile(r"export\s+(?:const|let|var)\s+(\w+)")),
]

_JS_KIND_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("class", re.compile(r"class\s+(\w+)")),
    ("function", re.compile(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)")),
    ("variable", re.compile(r"(?:export\s+)?(?:const|let|var)\s+(\w+)")),
]


def _extract_ts_js_symbols(
    path: Path, relpath: str, text: str, patterns: list[tuple[str, re.Pattern]]
) -> list[WorkspaceSymbol]:
    symbols: list[WorkspaceSymbol] = []
    seen: set[tuple[str, int]] = set()
    lines = text.splitlines()

    for kind, pat in patterns:
        for m in pat.finditer(text):
            name = m.group(1)
            start = m.start()
            line_num = text[:start].count("\n") + 1
            col = start - text.rfind("\n", 0, start) - 1
            key = (name, line_num)
            if key in seen:
                continue
            seen.add(key)
            symbols.append(
                WorkspaceSymbol(
                    qualname=name,
                    name=name,
                    kind=kind,
                    path=str(path),
                    relpath=relpath,
                    line=line_num,
                    column=max(col, 0),
                )
            )

    # Method detection via naive brace-depth scanner
    class_lines: dict[int, str] = {}
    for i, line in enumerate(lines, 1):
        stripped = line.strip()
        for pat in (
            re.compile(r"(?:export\s+)?class\s+(\w+)"),
            re.compile(r"interface\s+(\w+)"),
        ):
            m = pat.search(stripped)
            if m:
                class_lines[i] = m.group(1)

    if class_lines:
        in_class: dict[int, str] = {}
        brace_depth = 0
        sorted_class_starts = sorted(class_lines.keys())
        class_stack: list[tuple[int, str]] = []

        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            # Track class boundaries
            for cls_start in sorted_class_starts:
                if cls_start == i:
                    class_stack.append((i, class_lines[i]))

            brace_depth += stripped.count("{") - stripped.count("}")

            if brace_depth <= 0 and class_stack:
                popped = False
                for cls_start, cls_name in reversed(class_stack):
                    if i > cls_start:
                        class_stack.pop()
                        popped = True
                        break
                if popped:
                    brace_depth = 0
                    continue

            if class_stack and brace_depth > 0:
                in_class[i] = class_stack[-1][1]
            elif class_stack and brace_depth <= 0:
                pass

            # Reset brace depth when leaving class
            if not class_stack:
                brace_depth = 0

        for i, line in enumerate(lines, 1):
            if i not in in_class:
                continue
            stripped = line.strip()
            # Match methodName(...) { pattern
            method_pat = re.compile(r"(\w+)\s*\([^)]*\)\s*\{")
            for m in method_pat.finditer(stripped):
                name = m.group(1)
                if name in ("if", "while", "for", "switch", "catch", "function"):
                    continue
                parent_name = in_class[i]
                key = (f"{parent_name}.{name}", i)
                if key in seen:
                    continue
                seen.add(key)
                symbols.append(
                    WorkspaceSymbol(
                        qualname=f"{parent_name}.{name}",
                        name=name,
                        kind="method",
                        path=str(path),
                        relpath=relpath,
                        line=i,
                        column=max(stripped.index(name), 0),
                        parent=parent_name,
                    )
                )

    return symbols


def extract_ts_symbols(path: Path, relpath: str, text: str) -> list[WorkspaceSymbol]:
    return _extract_ts_js_symbols(path, relpath, text, _TS_KIND_PATTERNS)


def extract_js_symbols(path: Path, relpath: str, text: str) -> list[WorkspaceSymbol]:
    return _extract_ts_js_symbols(path, relpath, text, _JS_KIND_PATTERNS)


_EXTRACTORS = {
    ".py": extract_python_symbols,
    ".ts": extract_ts_symbols,
    ".tsx": extract_ts_symbols,
    ".js": extract_js_symbols,
    ".jsx": extract_js_symbols,
}


def collect_workspace_symbols(
    workspace: Path,
    files: list[dict[str, Any]],
    max_files: int = 500,
    max_symbols: int = 5000,
    max_file_bytes: int = 524288,
) -> SymbolInventory:
    symbols: list[WorkspaceSymbol] = []
    errors: list[SymbolExtractionError] = []
    scanned = 0
    oversized_skipped = 0
    truncated = False

    for entry in files[:max_files]:
        relpath = entry.get("path", "")
        suffix = Path(relpath).suffix
        if suffix not in SYMBOL_SUFFIXES:
            continue
        extractor = _EXTRACTORS.get(suffix)
        if not extractor:
            continue

        filepath = workspace / relpath
        if not filepath.is_file():
            continue
        try:
            stat = filepath.stat()
        except OSError:
            continue
        if stat.st_size > max_file_bytes:
            oversized_skipped += 1
            continue

        try:
            text = filepath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            errors.append(
                SymbolExtractionError(path=str(filepath), relpath=relpath, error=str(exc))
            )
            continue

        try:
            extracted = extractor(filepath, relpath, text)
        except SyntaxError as exc:
            errors.append(
                SymbolExtractionError(
                    path=str(filepath), relpath=relpath, error=f"syntax error: {exc}"
                )
            )
            continue
        except Exception as exc:
            errors.append(
                SymbolExtractionError(path=str(filepath), relpath=relpath, error=str(exc))
            )
            continue

        remaining = max_symbols - len(symbols)
        symbols.extend(extracted[:remaining])
        scanned += 1

        if len(symbols) >= max_symbols:
            truncated = True
            break

    symbols.sort(key=lambda s: (s.path, s.line, s.column, s.kind, s.qualname))

    return SymbolInventory(
        symbols=symbols,
        errors=errors,
        total_files_scanned=scanned,
        total_symbols=len(symbols),
        truncated=truncated,
        oversized_skipped=oversized_skipped,
    )
