"""Tests for workspace symbol extraction."""

from __future__ import annotations

from pathlib import Path

from agent_runtime_cockpit.workspace.symbols import (
    collect_workspace_symbols,
    extract_js_symbols,
    extract_python_symbols,
    extract_ts_symbols,
)


def test_python_class_extraction():
    text = """class FooBar:
    pass
"""
    symbols = extract_python_symbols(Path("/f.py"), "f.py", text)
    assert len(symbols) == 1
    assert symbols[0].name == "FooBar"
    assert symbols[0].kind == "class"
    assert symbols[0].line == 1


def test_python_function_extraction():
    text = """def hello():
    pass

async def async_fn():
    pass
"""
    symbols = extract_python_symbols(Path("/f.py"), "f.py", text)
    names = {s.name for s in symbols}
    kinds = {s.name: s.kind for s in symbols}
    assert "hello" in names
    assert "async_fn" in names
    assert kinds["hello"] == "function"
    assert kinds["async_fn"] == "function"


def test_python_method_extraction():
    text = """class MyClass:
    def method_one(self):
        pass

    async def method_two(self):
        pass
"""
    symbols = extract_python_symbols(Path("/f.py"), "f.py", text)
    methods = [s for s in symbols if s.kind == "method"]
    assert len(methods) == 2
    names = {m.name for m in methods}
    assert "method_one" in names
    assert "method_two" in names
    for m in methods:
        assert m.parent == "MyClass"
        assert m.qualname.startswith("MyClass.")


def test_python_variable_extraction():
    text = """x = 1
y: int = 2
"""
    symbols = extract_python_symbols(Path("/f.py"), "f.py", text)
    vars_found = [s for s in symbols if s.kind == "variable"]
    assert len(vars_found) == 2
    names = {v.name for v in vars_found}
    assert "x" in names
    assert "y" in names


def test_python_syntax_error_returns_empty():
    text = "def broken("
    symbols = extract_python_symbols(Path("/f.py"), "f.py", text)
    assert symbols == []


def test_ts_class_interface_type_enum_function():
    text = """export class MyClass {}
interface MyInterface {}
export type MyType = string;
enum MyEnum { A, B }
export function myFunc() {}
export async function myAsyncFunc() {}
"""
    symbols = extract_ts_symbols(Path("/f.ts"), "f.ts", text)
    kinds = {s.name: s.kind for s in symbols}
    assert kinds["MyClass"] == "class"
    assert kinds["MyInterface"] == "interface"
    assert kinds["MyType"] == "type"
    assert kinds["MyEnum"] == "enum"
    assert kinds["myFunc"] == "function"
    assert kinds["myAsyncFunc"] == "function"


def test_js_function_extraction():
    text = """function hello() {}
async function asyncHello() {}
const x = 1;
"""
    symbols = extract_js_symbols(Path("/f.js"), "f.js", text)
    kinds = {s.name: s.kind for s in symbols}
    assert kinds["hello"] == "function"
    assert kinds["asyncHello"] == "function"
    assert kinds["x"] == "variable"


def test_deterministic_ordering(tmp_path):
    files = [
        {"path": "b.py", "size": 10, "suffix": ".py", "provenance": "workspace_file"},
        {"path": "a.py", "size": 10, "suffix": ".py", "provenance": "workspace_file"},
    ]
    (tmp_path / "a.py").write_text("def a_fn(): pass\n")
    (tmp_path / "b.py").write_text("def b_fn(): pass\n")
    inv = collect_workspace_symbols(tmp_path, files)
    paths = [s.relpath for s in inv.symbols]
    assert paths == sorted(paths)


def test_oversized_file_skipped(tmp_path):
    (tmp_path / "big.py").write_text("x = 1\n")
    files = [
        {"path": "big.py", "size": 10, "suffix": ".py", "provenance": "workspace_file"},
    ]
    inv = collect_workspace_symbols(tmp_path, files, max_file_bytes=1)
    assert inv.oversized_skipped == 1
    assert len(inv.symbols) == 0


def test_max_symbols_truncation(tmp_path):
    (tmp_path / "a.py").write_text("\n".join(f"def func{i}(): pass" for i in range(100)))
    files = [
        {"path": "a.py", "size": 10, "suffix": ".py", "provenance": "workspace_file"},
    ]
    inv = collect_workspace_symbols(tmp_path, files, max_symbols=5)
    assert inv.truncated is True
    assert len(inv.symbols) <= 5
