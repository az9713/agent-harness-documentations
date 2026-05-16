"""5 core tools with routing-logic descriptions. (Best Practice #4)"""
import subprocess
from pathlib import Path

try:
    import httpx
    _HTTPX = True
except ImportError:
    _HTTPX = False

TOOL_DEFINITIONS = [
    {
        "name": "read_file",
        "description": (
            "Read a file's full contents and return them as text. "
            "Do not use for directories — use list_files instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to the file."},
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file, creating or overwriting it. "
            "Do not use for appending — use run_shell with >> for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to write."},
                "content": {"type": "string", "description": "Content to write."},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_shell",
        "description": (
            "Execute a shell command and return combined stdout and stderr. "
            "Do not use for interactive commands or long-running background processes."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to run."},
                "timeout": {"type": "integer", "description": "Timeout in seconds (default 30)."},
            },
            "required": ["command"],
        },
    },
    {
        "name": "web_fetch",
        "description": (
            "Fetch the text content of a public URL. "
            "Do not use for authenticated pages or URLs requiring cookies/login."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to fetch."},
            },
            "required": ["url"],
        },
    },
    {
        "name": "list_files",
        "description": (
            "List files and directories at a given path. "
            "Do not use for deep recursive listing — use run_shell with find instead."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "directory": {"type": "string", "description": "Directory to list."},
                "show_hidden": {"type": "boolean", "description": "Include hidden files (default false)."},
            },
            "required": ["directory"],
        },
    },
]


def execute_tool(name: str, inputs: dict) -> str:
    handlers = {
        "read_file": _read_file,
        "write_file": _write_file,
        "run_shell": _run_shell,
        "web_fetch": _web_fetch,
        "list_files": _list_files,
    }
    handler = handlers.get(name)
    if handler is None:
        return f"Error: unknown tool '{name}'"
    return handler(inputs)


def _read_file(inputs: dict) -> str:
    path = inputs.get("path", "")
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except IsADirectoryError:
        return f"Error: {path} is a directory — use list_files instead"
    except Exception as e:
        return f"Error reading file: {e}"


def _write_file(inputs: dict) -> str:
    path = inputs.get("path", "")
    content = inputs.get("content", "")
    try:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} characters to {path}"
    except Exception as e:
        return f"Error writing file: {e}"


def _run_shell(inputs: dict) -> str:
    command = inputs.get("command", "")
    timeout = inputs.get("timeout", 30)
    try:
        result = subprocess.run(
            command, shell=True, capture_output=True, text=True, timeout=timeout
        )
        output = result.stdout + result.stderr
        if len(output) > 4000:
            output = output[:4000] + "\n[output truncated]"
        return output or "(no output)"
    except subprocess.TimeoutExpired:
        return f"Error: command timed out after {timeout}s"
    except Exception as e:
        return f"Error: {e}"


def _web_fetch(inputs: dict) -> str:
    url = inputs.get("url", "")
    if not _HTTPX:
        return "Error: httpx not installed. Run: pip install httpx"
    try:
        with httpx.Client(follow_redirects=True, timeout=20) as client:
            response = client.get(url, headers={"User-Agent": "agent-harness/1.0"})
            response.raise_for_status()
            text = response.text
            if len(text) > 8000:
                text = text[:8000] + "\n[content truncated]"
            return text
    except Exception as e:
        return f"Error fetching URL: {e}"


def _list_files(inputs: dict) -> str:
    directory = inputs.get("directory", ".")
    show_hidden = inputs.get("show_hidden", False)
    try:
        p = Path(directory)
        if not p.exists():
            return f"Error: directory not found: {directory}"
        entries = sorted(p.iterdir(), key=lambda x: (x.is_file(), x.name.lower()))
        if not show_hidden:
            entries = [e for e in entries if not e.name.startswith(".")]
        lines = [f"[{'file' if e.is_file() else 'dir '}] {e.name}" for e in entries]
        return "\n".join(lines) if lines else "(empty directory)"
    except Exception as e:
        return f"Error listing directory: {e}"
