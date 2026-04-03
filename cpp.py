import os
import fnmatch
from pathlib import Path
import pyperclip

# List of file extensions to process (add or remove extensions here)
FILE_EXTENSIONS = [".py", ".json", ".txt"]

def read_ignore_patterns(ignore_file=".cppignore"):
    """Read ignore patterns from .cppignore file."""
    ignore_patterns = []
    try:
        with open(ignore_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    ignore_patterns.append(line)
    except FileNotFoundError:
        pass  # No .cppignore file, proceed without ignoring anything
    return ignore_patterns

def should_ignore(path, ignore_patterns):
    """Check if a path should be ignored based on ignore patterns."""
    path_str = str(path)
    for pattern in ignore_patterns:
        if fnmatch.fnmatch(path_str, pattern) or fnmatch.fnmatch(path_str, f"*/{pattern}"):
            return True
    return False

def copy_files_content_to_clipboard():
    """Recursively collect filenames and content of files with specified extensions, ignoring specified folders, and copy to clipboard."""
    ignore_patterns = read_ignore_patterns()
    file_count = 0
    total_lines = 0
    content_buffer = []

    for root, dirs, files in os.walk("."):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if not should_ignore(Path(root) / d, ignore_patterns)]
        
        for file in files:
            if any(file.endswith(ext) for ext in FILE_EXTENSIONS):
                file_path = Path(root) / file
                if not should_ignore(file_path, ignore_patterns):
                    try:
                        with open(file_path, "r", encoding="utf-8") as infile:
                            content = infile.read()
                            lines = content.splitlines()
                            line_count = len(lines)
                            total_lines += line_count
                            file_count += 1
                            # Append relative file path and content to buffer
                            relative_path = str(file_path).replace(os.sep, "/")  # Use forward slashes for consistency
                            content_buffer.append(f"--- File: {relative_path} ---")
                            content_buffer.append(content)
                            content_buffer.append("")  # Empty line for separation
                    except Exception as e:
                        content_buffer.append(f"--- File: {file_path} ---")
                        content_buffer.append(f"Error reading file: {str(e)}")
                        content_buffer.append("")

    # Join content buffer with newlines and copy to clipboard
    final_content = "\n".join(content_buffer)
    pyperclip.copy(final_content)

    # Print summary
    print(f"Processed {file_count} files with extensions {FILE_EXTENSIONS}.")
    print(f"Total lines across all files: {total_lines}")
    print("Content has been copied to the clipboard.")

if __name__ == "__main__":
    copy_files_content_to_clipboard()