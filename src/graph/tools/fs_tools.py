"""文件系统与命令执行 LangChain Tools。

提供文件读取、目录列表、命令执行等工具，
供 LLM 通过 function calling 访问本地文件系统和执行系统命令。
兼容 Windows 和 Linux 系统。
"""

import os
import platform
import subprocess
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool

_MAX_FILE_SIZE = 100 * 1024
_MAX_OUTPUT_LENGTH = 10000
_COMMAND_TIMEOUT = 30


@tool
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """读取指定路径的文件内容。支持文本文件，返回文件内容字符串。如果文件过大（超过100KB）则只返回前100KB的内容。

    Args:
        file_path: 文件的绝对路径或相对路径
        encoding: 文件编码，默认utf-8
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return f"错误: 文件不存在 - {path}"

        if not path.is_file():
            return f"错误: 路径不是文件 - {path}"

        file_size = path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            with open(path, "r", encoding=encoding, errors="replace") as f:
                content = f.read(_MAX_FILE_SIZE)
            return f"[文件过大({file_size}字节)，仅显示前{_MAX_FILE_SIZE}字节]\n{content}"

        with open(path, "r", encoding=encoding, errors="replace") as f:
            content = f.read()

        return content

    except PermissionError:
        return f"错误: 无权限读取文件 - {file_path}"
    except Exception as e:
        return f"错误: 读取文件失败 - {e}"


@tool
def list_directory(dir_path: str, show_hidden: bool = False) -> str:
    """列出指定目录下的文件和子目录。返回格式化的文件列表，包含文件类型标记（[DIR]表示目录，[FILE]表示文件）和文件大小。

    Args:
        dir_path: 目录的绝对路径或相对路径
        show_hidden: 是否显示隐藏文件（以.开头的文件），默认不显示
    """
    try:
        path = Path(dir_path).resolve()

        if not path.exists():
            return f"错误: 目录不存在 - {path}"

        if not path.is_dir():
            return f"错误: 路径不是目录 - {path}"

        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

        lines = [f"目录: {path}", ""]
        for entry in entries:
            if not show_hidden and entry.name.startswith("."):
                continue

            if entry.is_dir():
                lines.append(f"  [DIR]  {entry.name}/")
            else:
                size = entry.stat().st_size
                size_str = _format_size(size)
                lines.append(f"  [FILE] {entry.name}  ({size_str})")

        if len(lines) == 2:
            lines.append("  (空目录)")

        return "\n".join(lines)

    except PermissionError:
        return f"错误: 无权限访问目录 - {dir_path}"
    except Exception as e:
        return f"错误: 列出目录失败 - {e}"


@tool
def run_command(command: str, working_directory: Optional[str] = None, timeout: int = 30) -> str:
    """在系统Shell中执行命令并返回输出。Windows下使用cmd/powershell，Linux下使用bash。超时默认30秒。

    Args:
        command: 要执行的Shell命令
        working_directory: 命令执行的工作目录，默认为当前目录
        timeout: 命令超时时间（秒），默认30秒
    """
    if timeout <= 0 or timeout > 120:
        timeout = _COMMAND_TIMEOUT

    cwd = None
    if working_directory:
        cwd_path = Path(working_directory).resolve()
        if not cwd_path.exists():
            return f"错误: 工作目录不存在 - {working_directory}"
        if not cwd_path.is_dir():
            return f"错误: 工作目录路径不是目录 - {working_directory}"
        cwd = str(cwd_path)

    system = platform.system()

    if system == "Windows":
        shell_cmd = ["powershell", "-NoProfile", "-Command", command]
    else:
        shell_cmd = ["/bin/bash", "-c", command]

    try:
        result = subprocess.run(
            shell_cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env=os.environ.copy(),
        )

        output_parts = []

        if result.stdout:
            stdout = result.stdout
            if len(stdout) > _MAX_OUTPUT_LENGTH:
                stdout = stdout[:_MAX_OUTPUT_LENGTH] + "\n...(输出被截断)"
            output_parts.append(stdout)

        if result.stderr:
            stderr = result.stderr
            if len(stderr) > _MAX_OUTPUT_LENGTH:
                stderr = stderr[:_MAX_OUTPUT_LENGTH] + "\n...(错误输出被截断)"
            output_parts.append(f"[STDERR]\n{stderr}")

        output_parts.append(f"\n[退出码: {result.returncode}]")

        return "\n".join(output_parts)

    except subprocess.TimeoutExpired:
        return f"错误: 命令执行超时（{timeout}秒）- {command}"
    except FileNotFoundError:
        return f"错误: Shell不可用 - 系统: {system}"
    except Exception as e:
        return f"错误: 命令执行失败 - {e}"


@tool
def get_file_info(file_path: str) -> str:
    """获取文件或目录的详细信息，包括大小、修改时间、权限等元数据。

    Args:
        file_path: 文件或目录的绝对路径或相对路径
    """
    try:
        path = Path(file_path).resolve()

        if not path.exists():
            return f"错误: 路径不存在 - {path}"

        stat = path.stat()

        info_lines = [
            f"路径: {path}",
            f"类型: {'目录' if path.is_dir() else '文件'}",
            f"大小: {_format_size(stat.st_size)}",
            f"修改时间: {_format_timestamp(stat.st_mtime)}",
            f"创建时间: {_format_timestamp(stat.st_ctime)}",
        ]

        if path.is_file():
            info_lines.append(f"扩展名: {path.suffix or '(无)'}")

        if platform.system() != "Windows":
            info_lines.append(f"权限: {oct(stat.st_mode)[-3:]}")

        return "\n".join(info_lines)

    except PermissionError:
        return f"错误: 无权限访问 - {file_path}"
    except Exception as e:
        return f"错误: 获取文件信息失败 - {e}"


def _format_size(size_bytes: int) -> str:
    """格式化文件大小。"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def _format_timestamp(ts: float) -> str:
    """格式化时间戳。"""
    from datetime import datetime
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
