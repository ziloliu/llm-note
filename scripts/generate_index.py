#!/usr/bin/env python3
"""
用途：自动扫描 raw/ 和 core/ 目录，生成 index/全文目录.md
用法：python generate_index.py
参数：无
输出：index/全文目录.md
依赖：Python 3.6+
"""

import os
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "raw")
CORE_DIR = os.path.join(BASE_DIR, "core")
INDEX_FILE = os.path.join(BASE_DIR, "index", "全文目录.md")

FOLDER_ICON = "📁"
FILE_ICON = "📄"


def get_file_summary(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.read().split('\n')
            in_code_block = False
            for line in lines[1:]:
                line = line.strip()
                if line.startswith('```'):
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    continue
                if not line:
                    continue
                if line.startswith('#') or line.startswith('>') or line.startswith('---'):
                    continue
                if line.startswith('|') or line.startswith('-') or line.startswith('📄'):
                    continue
                if len(line) > 10:
                    return line[:40] + "..." if len(line) > 40 else line
    except:
        pass
    return "..."


def scan_raw_directory():
    result = []
    core_files = os.listdir(CORE_DIR) if os.path.exists(CORE_DIR) else []
    
    for root, dirs, files in os.walk(RAW_DIR):
        rel_path = os.path.relpath(root, RAW_DIR)
        level = 0 if rel_path == "." else rel_path.count(os.sep) + 1
        
        if "tmp" in rel_path.split(os.sep):
            continue
        
        if level > 0:
            indent = "  " * (level - 1)
            folder_name = os.path.basename(root)
            result.append(f"{indent}- {FOLDER_ICON} **{folder_name}**")
        
        md_files = sorted([f for f in files if f.endswith('.md')])
        for f in md_files:
            indent = "  " * level
            filepath = os.path.join(root, f)
            summary = get_file_summary(filepath)
            status = "✅ 已提炼" if core_files else "⬜ 待提炼"
            result.append(f"{indent}- {FILE_ICON} [{f}](../raw/{rel_path}/{f}) — {summary} {status}")
    
    return "\n".join(result)


def scan_core_directory():
    result = []
    
    if not os.path.exists(CORE_DIR):
        return "- （暂无核心笔记）"
    
    md_files = sorted([f for f in os.listdir(CORE_DIR) if f.endswith('.md')])
    
    if not md_files:
        return "- （暂无核心笔记）"
    
    for f in md_files:
        filepath = os.path.join(CORE_DIR, f)
        summary = get_file_summary(filepath)
        mtime = datetime.fromtimestamp(os.path.getmtime(filepath)).strftime('%Y-%m-%d')
        result.append(f"- {FILE_ICON} [{f}](../core/{f}) — {summary} — 更新：{mtime}")
    
    return "\n".join(result)


def generate_index():
    now = datetime.now().strftime('%Y-%m-%d %H:%M')
    raw_tree = scan_raw_directory()
    core_tree = scan_core_directory()
    
    content = f"""# 知识库目录

> 更新：{now}

---

## raw/ 原始笔记

{raw_tree}

---

## core/ 核心笔记

{core_tree}
"""
    
    os.makedirs(os.path.dirname(INDEX_FILE), exist_ok=True)
    with open(INDEX_FILE, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ 索引已生成：{INDEX_FILE}")
    print(f"   更新时间：{now}")


if __name__ == "__main__":
    generate_index()