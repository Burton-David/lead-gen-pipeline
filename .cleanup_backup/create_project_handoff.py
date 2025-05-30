# create_project_handoff.py
# Version: Gemini-2025-05-27 T16:20:00Z (Ready to Run)
# Description: Generates a Markdown handoff document including a directory tree
#              and the content of all Python scripts in the project.

import os
from pathlib import Path
import time
from typing import List # Ensures List is imported

# --- Configuration ---
# Assume this script is in the project root directory.
PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_FILENAME = PROJECT_ROOT / "PROJECT_HANDOFF_DOCUMENT.md"

# Directories to exclude from both directory tree and file inclusion
EXCLUDE_DIRS = {".git", ".venv", "__pycache__", "logs", "reports", "data"} 

# Specific files to exclude
EXCLUDE_FILES = {OUTPUT_FILENAME.name, Path(__file__).name}

# --- Helper Functions ---

def generate_directory_tree_recursive(current_path: Path, project_root: Path, prefix: str = "", indent_str: str = "    ") -> List[str]:
    """Recursively generates directory tree lines."""
    tree_lines = []
    
    # Get items and filter exclusions
    try:
        items = list(current_path.iterdir())
    except PermissionError:
        tree_lines.append(f"{prefix}└── [Permission Denied]")
        return tree_lines
        
    items_to_process = [
        item for item in items
        if item.name not in EXCLUDE_DIRS and not (item.is_file() and item.name in EXCLUDE_FILES)
    ]
    items_to_process.sort(key=lambda p: (p.is_file(), p.name.lower()))
    
    for i, item in enumerate(items_to_process):
        is_last_item = (i == len(items_to_process) - 1)
        connector = "└── " if is_last_item else "├── "
        tree_lines.append(f"{prefix}{connector}{item.name}")

        if item.is_dir():
            new_prefix = prefix + ("    " if is_last_item else "│   ")
            tree_lines.extend(generate_directory_tree_recursive(item, project_root, new_prefix, indent_str))
    return tree_lines

def generate_directory_tree_for_markdown(start_path: Path) -> str:
    """Generates the full directory tree string for Markdown, starting with the root."""
    if not start_path.is_dir():
        return "[Error: Project root is not a directory]"
    
    # Start with the root directory itself
    tree_lines = [f"{start_path.name}/"]
    # Then generate the tree for its contents
    tree_lines.extend(generate_directory_tree_recursive(start_path, start_path))
    return "\n".join(tree_lines)


def get_python_files(start_path: Path) -> List[Path]:
    """Finds all Python files, respecting exclusions."""
    py_files = []
    for item_path in start_path.rglob("*.py"):
        is_excluded = False
        # Check if the file itself is excluded
        if item_path.name in EXCLUDE_FILES:
            continue
            
        # Check if any parent directory is in the exclusion list
        try:
            # Iterate through parents relative to the project root
            # to check if any part of the path matches an excluded directory name.
            current_relative_path = item_path.relative_to(start_path)
            for part in current_relative_path.parents:
                if part.name in EXCLUDE_DIRS:
                    is_excluded = True
                    break
            if is_excluded:
                continue
        except ValueError: # Should not happen if item_path is under start_path
            pass

        py_files.append(item_path)
    return sorted(py_files)

def get_file_content(filepath: Path) -> str:
    """Reads and returns the content of a file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"!!! Error reading file {filepath}: {e} !!!"

# --- Main Script ---

def main():
    markdown_parts = []

    # Document Header
    markdown_parts.append("# Project Handoff Document")
    markdown_parts.append(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}\n")
    markdown_parts.append(f"**Project Root:** `{PROJECT_ROOT.resolve()}`\n")

    # 1. Directory Tree
    markdown_parts.append("## 1. Project Directory Tree")
    markdown_parts.append("\n```text")
    try:
        tree_output = generate_directory_tree_for_markdown(PROJECT_ROOT)
        markdown_parts.append(tree_output if tree_output else "[Directory tree is empty or fully excluded]")
    except Exception as e:
        markdown_parts.append(f"[Error generating directory tree: {e}]")
    markdown_parts.append("```\n")

    # 2. Python Script Contents
    markdown_parts.append("## 2. Python Script Contents\n")
    
    python_files = get_python_files(PROJECT_ROOT)
    if not python_files:
        markdown_parts.append("No Python scripts found (or all were excluded).\n")
    
    for py_file in python_files:
        try:
            relative_path = py_file.relative_to(PROJECT_ROOT)
        except ValueError: # Should not happen if get_python_files is correct
            relative_path = py_file 
            
        markdown_parts.append(f"### `{relative_path}`\n")
        markdown_parts.append("```python")
        markdown_parts.append(get_file_content(py_file)) # Appends the entire file content as one string
        markdown_parts.append("```\n")

    # Assemble and Write Document
    final_markdown = "\n".join(markdown_parts)
    try:
        with open(OUTPUT_FILENAME, 'w', encoding='utf-8') as f:
            f.write(final_markdown)
        print(f"Successfully generated handoff document: {OUTPUT_FILENAME.resolve()}")
    except Exception as e:
        print(f"Error writing handoff document {OUTPUT_FILENAME.resolve()}: {e}")

if __name__ == "__main__":
    main()