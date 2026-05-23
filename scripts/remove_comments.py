#!/usr/bin/env python3
"""
Remove comments from Python files while preserving docstrings and code structure.
"""
import re
import ast
import sys
from pathlib import Path


def remove_comments_from_source(source: str) -> str:
    """
    Remove comments from Python source code while preserving docstrings.
    """
    lines = source.split('\n')
    result = []
    
    for line in lines:
        stripped = line.strip()
        
        # Skip empty lines
        if not stripped:
            result.append(line)
            continue
        
        # Skip shebang and encoding
        if stripped.startswith('#!') or stripped.startswith('# -*- coding:'):
            result.append(line)
            continue
        
        # Check if line is a comment (starts with # after stripping)
        if stripped.startswith('#'):
            continue
        
        # Handle inline comments
        # Need to be careful about strings that contain #
        in_string = False
        string_char = None
        i = 0
        comment_start = -1
        
        while i < len(line):
            char = line[i]
            
            if not in_string:
                if char in ('"', "'"):
                    # Check for triple quotes
                    if i + 2 < len(line) and line[i:i+3] in ('"""', "'''"):
                        in_string = True
                        string_char = line[i:i+3]
                        i += 2
                    else:
                        in_string = True
                        string_char = char
                elif char == '#':
                    comment_start = i
                    break
            else:
                # Check for end of string
                if string_char in ('"""', "'''"):
                    if i + 2 < len(line) and line[i:i+3] == string_char:
                        in_string = False
                        string_char = None
                        i += 2
                else:
                    if char == string_char:
                        in_string = False
                        string_char = None
            
            i += 1
        
        if comment_start >= 0:
            result.append(line[:comment_start].rstrip())
        else:
            result.append(line)
    
    return '\n'.join(result)


def process_file(file_path: Path):
    """Process a single Python file to remove comments."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        # Check if file has syntax errors
        try:
            ast.parse(source)
        except SyntaxError:
            print(f"Skipping {file_path} - has syntax errors")
            return
        
        cleaned = remove_comments_from_source(source)
        
        # Only write if changed
        if cleaned != source:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(cleaned)
            print(f"Processed: {file_path}")
        else:
            print(f"No comments to remove: {file_path}")
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")


def main():
    root = Path(__file__).parent.parent
    py_files = list(root.rglob('*.py'))
    
    print(f"Found {len(py_files)} Python files")
    
    for py_file in py_files:
        # Skip the script itself
        if py_file.name == 'remove_comments.py':
            continue
        process_file(py_file)
    
    print("Done!")


if __name__ == '__main__':
    main()
