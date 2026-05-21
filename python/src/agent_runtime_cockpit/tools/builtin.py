"""Built-in read-only tools for Phase 5."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from agent_runtime_cockpit.cli_repl.cancellation import CancellationToken
from agent_runtime_cockpit.tools.protocol import ToolResult


class ReadFileArgs(BaseModel):
    """Arguments for read_file tool."""
    path: str = Field(description="File path to read")


class ReadFileTool:
    """Read file contents (untrusted: user-controlled file contents)."""
    
    name = "read_file"
    description = "Read the contents of a file at the given path"
    output_trust_level = "untrusted"
    args_schema = ReadFileArgs
    output_byte_limit = 65536

    def execute(self, args: ReadFileArgs, cancellation_token: CancellationToken) -> ToolResult:
        """Read file contents with byte limit and cancellation support."""
        cancellation_token.raise_if_cancelled()
        
        try:
            path = Path(args.path).resolve()
            if not path.exists():
                return ToolResult(content=f"Error: File not found: {args.path}")
            if not path.is_file():
                return ToolResult(content=f"Error: Not a file: {args.path}")
            
            # Read with byte limit
            with open(path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(self.output_byte_limit)
                
            # Check if truncated
            file_size = path.stat().st_size
            if file_size > self.output_byte_limit:
                truncated_marker = f"\n\n[TRUNCATED: file is {file_size} bytes, showing first {self.output_byte_limit} bytes]"
                content = content[:self.output_byte_limit - len(truncated_marker)] + truncated_marker
                
            return ToolResult(content=content)
            
        except UnicodeDecodeError:
            return ToolResult(content=f"Error: File is not valid UTF-8: {args.path}")
        except PermissionError:
            return ToolResult(content=f"Error: Permission denied: {args.path}")
        except Exception as e:
            return ToolResult(content=f"Error reading file: {e}")


class ListDirectoryArgs(BaseModel):
    """Arguments for list_directory tool."""
    path: str = Field(description="Directory path to list")


class ListDirectoryTool:
    """List directory contents (untrusted: filenames can contain attacker-controlled payloads)."""
    
    name = "list_directory"
    description = "List the contents of a directory at the given path"
    output_trust_level = "untrusted"
    args_schema = ListDirectoryArgs
    output_byte_limit = 65536

    def execute(self, args: ListDirectoryArgs, cancellation_token: CancellationToken) -> ToolResult:
        """List directory contents with cancellation support."""
        cancellation_token.raise_if_cancelled()
        
        try:
            path = Path(args.path).resolve()
            if not path.exists():
                return ToolResult(content=f"Error: Directory not found: {args.path}")
            if not path.is_dir():
                return ToolResult(content=f"Error: Not a directory: {args.path}")
            
            entries = []
            for entry in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name)):
                cancellation_token.raise_if_cancelled()
                suffix = "/" if entry.is_dir() else ""
                entries.append(f"{entry.name}{suffix}")
                
            content = "\n".join(entries) if entries else "(empty directory)"
            
            # Apply byte limit
            if len(content) > self.output_byte_limit:
                truncated_marker = f"\n\n[TRUNCATED: output exceeds {self.output_byte_limit} bytes]"
                content = content[:self.output_byte_limit - len(truncated_marker)] + truncated_marker
                
            return ToolResult(content=content)
            
        except PermissionError:
            return ToolResult(content=f"Error: Permission denied: {args.path}")
        except Exception as e:
            return ToolResult(content=f"Error listing directory: {e}")


class GetCurrentTimeArgs(BaseModel):
    """Arguments for get_current_time tool (no args needed)."""
    pass


class GetCurrentTimeTool:
    """Get current system time (trusted: no user-controlled component)."""
    
    name = "get_current_time"
    description = "Get the current system time in ISO 8601 format"
    output_trust_level = "trusted"
    args_schema = GetCurrentTimeArgs
    output_byte_limit = 65536

    def execute(self, args: GetCurrentTimeArgs, cancellation_token: CancellationToken) -> ToolResult:
        """Return current UTC time."""
        cancellation_token.raise_if_cancelled()
        now = datetime.now(timezone.utc).isoformat()
        return ToolResult(content=now)
