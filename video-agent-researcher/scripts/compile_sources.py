#!/usr/bin/env python3
"""
素材汇总工具。
扫描 materials 目录，为每个文件生成摘要，汇总到 sources.json。
"""

import json
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def scan_materials(materials_dir: str) -> List[Dict]:
    """扫描素材目录，收集所有文件信息。"""
    base = Path(materials_dir)
    sources = []
    idx = 1

    # 扫描文章
    articles_dir = base / "articles"
    if articles_dir.exists():
        for f in sorted(articles_dir.glob("*.txt")):
            content = f.read_text(encoding="utf-8", errors="replace")
            summary = extract_summary(content)
            sources.append({
                "id": f"src_{idx:03d}",
                "type": "article",
                "title": extract_title_from_file(content, f.stem),
                "file": str(f),
                "summary": summary,
                "char_count": len(content)
            })
            idx += 1

    # 扫描字幕
    transcripts_dir = base / "transcripts"
    if transcripts_dir.exists():
        for f in sorted(transcripts_dir.glob("*.txt")):
            content = f.read_text(encoding="utf-8", errors="replace")
            summary = extract_summary(content)
            sources.append({
                "id": f"src_{idx:03d}",
                "type": "youtube",
                "title": extract_title_from_file(content, f.stem),
                "file": str(f),
                "summary": summary,
                "char_count": len(content)
            })
            idx += 1

    return sources


def extract_summary(content: str, max_chars: int = 200) -> str:
    """提取文件前 200 字作为摘要。"""
    # 跳过元信息头部（来源、时间等）
    lines = content.split("\n")
    text_lines = []
    skip_header = True
    for line in lines:
        if skip_header and (line.startswith("来源:") or line.startswith("视频标题:") or
                           line.startswith("抓取时间:") or line.startswith("下载时间:") or
                           not line.strip()):
            continue
        skip_header = False
        text_lines.append(line.strip())

    text = " ".join(text_lines)
    if len(text) > max_chars:
        text = text[:max_chars] + "..."
    return text


def extract_title_from_file(content: str, fallback: str) -> str:
    """从文件内容提取标题。"""
    for line in content.split("\n"):
        line = line.strip()
        if line.startswith("视频标题:"):
            return line.replace("视频标题:", "").strip()
        if line and not line.startswith("来源:") and not line.startswith("抓取时间:"):
            return line[:80]
    return fallback


def main():
    if len(sys.argv) < 3:
        print("用法: python compile_sources.py <materials_dir> <topic>")
        print("示例: python compile_sources.py ./materials '认知偏差'")
        sys.exit(1)

    materials_dir = sys.argv[1]
    topic = sys.argv[2]

    if not Path(materials_dir).exists():
        print(f"❌ 错误: 目录不存在: {materials_dir}")
        sys.exit(1)

    print(f"🔍 正在扫描素材目录: {materials_dir}")
    sources = scan_materials(materials_dir)

    if not sources:
        print("⚠️ 未找到任何素材文件")
        sys.exit(0)

    # 汇总到 sources.json
    result = {
        "topic": topic,
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "total_sources": len(sources),
        "sources": sources
    }

    output_path = Path(materials_dir) / "sources.json"
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n✅ 素材汇总完成: {output_path}")
    print(f"📊 统计:")
    articles = [s for s in sources if s["type"] == "article"]
    transcripts = [s for s in sources if s["type"] == "youtube"]
    print(f"   文章: {len(articles)} 篇")
    print(f"   字幕: {len(transcripts)} 个")
    total_chars = sum(s["char_count"] for s in sources)
    print(f"   总字数: {total_chars}")


if __name__ == "__main__":
    main()
