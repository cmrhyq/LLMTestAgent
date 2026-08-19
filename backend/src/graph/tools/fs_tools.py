"""文件系统与命令执行 LangChain Tools。

提供文件读取、目录列表、命令执行等工具，
供 LLM 通过 function calling 访问本地文件系统和执行系统命令。
兼容 Windows 和 Linux 系统。
"""

import platform
from datetime import datetime
from pathlib import Path

from langchain_core.tools import tool

_MAX_FILE_SIZE = 100 * 1024
_MAX_OUTPUT_LENGTH = 10000
# 仓库工作区根（backend/src/graph/tools -> 上溯 4 级）
_WORKSPACE_ROOT = Path(__file__).resolve().parents[4]


def _ensure_within_workspace(path: Path) -> str | None:
    """确保路径在仓库工作区内，越界时返回错误信息。"""
    if not path.is_relative_to(_WORKSPACE_ROOT):
        return f"错误: 路径超出工作区范围 - {path}"
    return None


@tool
def read_file(file_path: str, encoding: str = "utf-8") -> str:
    """读取指定路径的文件内容。支持文本文件，返回文件内容字符串。如果文件过大（超过100KB）则只返回前100KB的内容。

    Args:
        file_path: 文件的绝对路径或相对路径
        encoding: 文件编码，默认utf-8
    """
    try:
        path = Path(file_path).resolve()

        workspace_error = _ensure_within_workspace(path)
        if workspace_error:
            return workspace_error

        if not path.exists():
            return f"错误: 文件不存在 - {path}"

        if not path.is_file():
            return f"错误: 路径不是文件 - {path}"

        file_size = path.stat().st_size
        if file_size > _MAX_FILE_SIZE:
            with open(path, encoding=encoding, errors="replace") as f:
                content = f.read(_MAX_FILE_SIZE)
            return f"[文件过大({file_size}字节)，仅显示前{_MAX_FILE_SIZE}字节]\n{content}"

        with open(path, encoding=encoding, errors="replace") as f:
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

        workspace_error = _ensure_within_workspace(path)
        if workspace_error:
            return workspace_error

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
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
