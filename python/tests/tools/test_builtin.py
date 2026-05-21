"""Tests for built-in read-only tools."""

from __future__ import annotations


import pytest

from agent_runtime_cockpit.cli_repl.cancellation import CancellationReason, CancellationToken, never_cancelled
from agent_runtime_cockpit.tools.builtin import (
    GetCurrentTimeTool,
    GetCurrentTimeArgs,
    ListDirectoryTool,
    ListDirectoryArgs,
    ReadFileTool,
    ReadFileArgs,
)


def test_read_file_reads_existing_file(tmp_path):
    """read_file returns file contents for valid file."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("hello world")
    
    tool = ReadFileTool()
    result = tool.execute(ReadFileArgs(path=str(test_file)), never_cancelled())
    
    assert result.content == "hello world"


def test_read_file_returns_error_for_missing_file(tmp_path):
    """read_file returns error message for non-existent file."""
    tool = ReadFileTool()
    result = tool.execute(ReadFileArgs(path=str(tmp_path / "missing.txt")), never_cancelled())
    
    assert "Error: File not found" in result.content


def test_read_file_returns_error_for_directory(tmp_path):
    """read_file returns error when path is a directory."""
    tool = ReadFileTool()
    result = tool.execute(ReadFileArgs(path=str(tmp_path)), never_cancelled())
    
    assert "Error: Not a file" in result.content


def test_read_file_truncates_large_files(tmp_path):
    """read_file truncates files exceeding byte limit."""
    test_file = tmp_path / "large.txt"
    large_content = "x" * 100000
    test_file.write_text(large_content)
    
    tool = ReadFileTool()
    result = tool.execute(ReadFileArgs(path=str(test_file)), never_cancelled())
    
    assert "[TRUNCATED:" in result.content
    assert len(result.content) <= tool.output_byte_limit


def test_read_file_respects_cancellation(tmp_path):
    """read_file raises Cancelled when token is cancelled."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    
    tool = ReadFileTool()
    with pytest.raises(Exception):  # Cancelled
        tool.execute(ReadFileArgs(path=str(test_file)), token)


def test_read_file_trust_level_is_untrusted():
    """read_file declares untrusted output_trust_level."""
    tool = ReadFileTool()
    assert tool.output_trust_level == "untrusted"


def test_list_directory_lists_files_and_dirs(tmp_path):
    """list_directory returns sorted entries with / suffix for dirs."""
    (tmp_path / "file.txt").write_text("content")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "another.txt").write_text("content")
    
    tool = ListDirectoryTool()
    result = tool.execute(ListDirectoryArgs(path=str(tmp_path)), never_cancelled())
    
    lines = result.content.split("\n")
    assert "subdir/" in lines
    assert "another.txt" in lines
    assert "file.txt" in lines


def test_list_directory_returns_error_for_missing_dir(tmp_path):
    """list_directory returns error for non-existent directory."""
    tool = ListDirectoryTool()
    result = tool.execute(ListDirectoryArgs(path=str(tmp_path / "missing")), never_cancelled())
    
    assert "Error: Directory not found" in result.content


def test_list_directory_returns_error_for_file(tmp_path):
    """list_directory returns error when path is a file."""
    test_file = tmp_path / "file.txt"
    test_file.write_text("content")
    
    tool = ListDirectoryTool()
    result = tool.execute(ListDirectoryArgs(path=str(test_file)), never_cancelled())
    
    assert "Error: Not a directory" in result.content


def test_list_directory_handles_empty_directory(tmp_path):
    """list_directory returns empty marker for empty directory."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    
    tool = ListDirectoryTool()
    result = tool.execute(ListDirectoryArgs(path=str(empty_dir)), never_cancelled())
    
    assert result.content == "(empty directory)"


def test_list_directory_respects_cancellation(tmp_path):
    """list_directory raises Cancelled when token is cancelled."""
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    
    tool = ListDirectoryTool()
    with pytest.raises(Exception):  # Cancelled
        tool.execute(ListDirectoryArgs(path=str(tmp_path)), token)


def test_list_directory_trust_level_is_untrusted():
    """list_directory declares untrusted output_trust_level."""
    tool = ListDirectoryTool()
    assert tool.output_trust_level == "untrusted"


def test_list_directory_truncates_large_output(tmp_path):
    """list_directory truncates output exceeding byte limit."""
    # Create many files to exceed byte limit
    for i in range(10000):
        (tmp_path / f"file_{i:05d}.txt").write_text("x")
    
    tool = ListDirectoryTool()
    result = tool.execute(ListDirectoryArgs(path=str(tmp_path)), never_cancelled())
    
    assert "[TRUNCATED:" in result.content
    assert len(result.content) <= tool.output_byte_limit


def test_get_current_time_returns_iso_format():
    """get_current_time returns ISO 8601 formatted timestamp."""
    tool = GetCurrentTimeTool()
    result = tool.execute(GetCurrentTimeArgs(), never_cancelled())
    
    # Check format: YYYY-MM-DDTHH:MM:SS.ffffff+00:00
    assert "T" in result.content
    assert ":" in result.content
    assert len(result.content) > 20


def test_get_current_time_respects_cancellation():
    """get_current_time raises Cancelled when token is cancelled."""
    token = CancellationToken()
    token.cancel(CancellationReason.USER, "stop")
    
    tool = GetCurrentTimeTool()
    with pytest.raises(Exception):  # Cancelled
        tool.execute(GetCurrentTimeArgs(), token)


def test_get_current_time_trust_level_is_trusted():
    """get_current_time declares trusted output_trust_level."""
    tool = GetCurrentTimeTool()
    assert tool.output_trust_level == "trusted"


def test_all_tools_have_required_attributes():
    """All built-in tools have required ToolHandler attributes."""
    tools = [ReadFileTool(), ListDirectoryTool(), GetCurrentTimeTool()]
    
    for tool in tools:
        assert hasattr(tool, "name")
        assert hasattr(tool, "description")
        assert hasattr(tool, "output_trust_level")
        assert hasattr(tool, "args_schema")
        assert hasattr(tool, "output_byte_limit")
        assert hasattr(tool, "execute")
        assert tool.output_byte_limit == 65536
