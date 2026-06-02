#!/usr/bin/env python3
"""
用途：检查 raw/ 文件的提炼状态，显示哪些文件已提炼、哪些待提炼
用法：python check_status.py
参数：无
输出：终端输出状态报告
依赖：Python 3.6+
"""

import os
import re

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "raw")
CORE_DIR = os.path.join(BASE_DIR, "core")


def get_core_sources():
    sources = set()
    if not os.path.exists(CORE_DIR):
        return sources
    
    for f in os.listdir(CORE_DIR):
        if not f.endswith('.md'):
            continue
        filepath = os.path.join(CORE_DIR, f)
        with open(filepath, 'r', encoding='utf-8') as file:
            content = file.read()
            matches = re.findall(r'- \[x\] (\d+_\S+)', content)
            sources.update(matches)
    
    return sources


def scan_raw_files():
    files = []
    for root, dirs, filenames in os.walk(RAW_DIR):
        if 'tmp' in root.split(os.sep):
            continue
        for f in filenames:
            if f.endswith('.md'):
                rel_path = os.path.relpath(os.path.join(root, f), RAW_DIR)
                files.append(rel_path)
    return sorted(files)


def main():
    core_sources = get_core_sources()
    raw_files = scan_raw_files()
    
    extracted = []
    pending = []
    
    for f in raw_files:
        basename = os.path.basename(f)
        name_without_ext = basename.replace('.md', '')
        if name_without_ext in core_sources or basename in core_sources:
            extracted.append(f)
        else:
            pending.append(f)
    
    print("=" * 50)
    print("知识库提炼状态报告")
    print("=" * 50)
    print(f"\n✅ 已提炼：{len(extracted)} 个文件")
    for f in extracted:
        print(f"   {f}")
    
    print(f"\n⬜ 待提炼：{len(pending)} 个文件")
    for f in pending:
        print(f"   {f}")
    
    print(f"\n总计：{len(raw_files)} 个文件")
    print(f"完成率：{len(extracted)/len(raw_files)*100:.1f}%" if raw_files else "完成率：N/A")


if __name__ == "__main__":
    main()