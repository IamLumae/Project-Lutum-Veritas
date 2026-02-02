"""
Comment Statistics Script
Counts comment characters vs code characters in Python and TypeScript/JavaScript files
"""

import os
import re
from pathlib import Path

def count_python_comments(content):
    """Count comment chars in Python code"""
    comment_chars = 0
    in_docstring = False
    docstring_delim = None

    lines = content.split('\n')
    for line in lines:
        stripped = line.strip()

        # Check for docstring start/end
        if '"""' in line or "'''" in line:
            if '"""' in line:
                delim = '"""'
            else:
                delim = "'''"

            if not in_docstring:
                in_docstring = True
                docstring_delim = delim
                # Count everything after docstring start
                idx = line.find(delim)
                comment_chars += len(line[idx:])
            else:
                # Count everything up to and including end
                idx = line.find(docstring_delim)
                comment_chars += idx + len(docstring_delim)
                in_docstring = False
                docstring_delim = None
            continue

        # If inside docstring, count entire line
        if in_docstring:
            comment_chars += len(line) + 1  # +1 for newline
            continue

        # Single-line comments
        if '#' in line:
            idx = line.find('#')
            comment_chars += len(line[idx:])

    return comment_chars


def count_js_ts_comments(content):
    """Count comment chars in JavaScript/TypeScript code"""
    comment_chars = 0

    # Remove strings to avoid false positives
    content_no_strings = re.sub(r'"(?:[^"\\]|\\.)*"', '""', content)
    content_no_strings = re.sub(r"'(?:[^'\\]|\\.)*'", "''", content_no_strings)
    content_no_strings = re.sub(r'`(?:[^`\\]|\\.)*`', '``', content_no_strings)

    # Multi-line comments /* */
    multiline_comments = re.findall(r'/\*.*?\*/', content_no_strings, re.DOTALL)
    for comment in multiline_comments:
        comment_chars += len(comment)

    # Single-line comments //
    single_line_comments = re.findall(r'//.*?$', content_no_strings, re.MULTILINE)
    for comment in single_line_comments:
        comment_chars += len(comment)

    return comment_chars


def analyze_file(file_path):
    """Analyze a single file and return stats"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return None

    total_chars = len(content)
    ext = file_path.suffix.lower()

    if ext == '.py':
        comment_chars = count_python_comments(content)
    elif ext in ['.ts', '.tsx', '.js', '.jsx']:
        comment_chars = count_js_ts_comments(content)
    else:
        return None

    code_chars = total_chars - comment_chars
    comment_ratio = (comment_chars / total_chars * 100) if total_chars > 0 else 0

    return {
        'file': str(file_path),
        'total_chars': total_chars,
        'comment_chars': comment_chars,
        'code_chars': code_chars,
        'comment_ratio': comment_ratio
    }


def main():
    # Directories to scan
    directories = [
        'lutum-backend',
        'lutum-desktop/src',
        'lutum/researcher'
    ]

    extensions = {'.py', '.ts', '.tsx', '.js', '.jsx'}

    all_stats = []
    total_chars = 0
    total_comment_chars = 0

    print("Scanning Lutum Veritas codebase for comments...\n")

    for directory in directories:
        if not os.path.exists(directory):
            print(f"WARNING: Directory not found: {directory}")
            continue

        for root, dirs, files in os.walk(directory):
            # Skip node_modules and other build dirs
            dirs[:] = [d for d in dirs if d not in ['node_modules', 'dist', 'build', '__pycache__', '.next']]

            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in extensions:
                    stats = analyze_file(file_path)
                    if stats:
                        all_stats.append(stats)
                        total_chars += stats['total_chars']
                        total_comment_chars += stats['comment_chars']

    # Sort by comment ratio descending
    all_stats.sort(key=lambda x: x['comment_ratio'], reverse=True)

    # Print top 10 most commented files
    print("TOP 10 MOST COMMENTED FILES:\n")
    for i, stats in enumerate(all_stats[:10], 1):
        rel_path = stats['file'].replace('\\', '/')
        print(f"{i}. {rel_path}")
        print(f"   Comment Ratio: {stats['comment_ratio']:.1f}%")
        print(f"   Comments: {stats['comment_chars']:,} chars | Code: {stats['code_chars']:,} chars")
        print()

    # Overall statistics
    total_code_chars = total_chars - total_comment_chars
    overall_ratio = (total_comment_chars / total_chars * 100) if total_chars > 0 else 0

    print("\n" + "="*60)
    print("OVERALL STATISTICS")
    print("="*60)
    print(f"Total Files Analyzed: {len(all_stats)}")
    print(f"Total Characters: {total_chars:,}")
    print(f"Comment Characters: {total_comment_chars:,}")
    print(f"Code Characters: {total_code_chars:,}")
    print(f"Comment Ratio: {overall_ratio:.2f}%")
    print("="*60)


if __name__ == '__main__':
    main()
