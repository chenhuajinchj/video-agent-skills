#!/usr/bin/env python3
"""
大纲生成工具。
读取 sources.json，提取关键信息，生成结构化的 outline.md 模板。
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict


def load_sources(sources_path: str) -> Dict:
    """读取 sources.json。"""
    path = Path(sources_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def extract_key_points(sources: List[Dict]) -> List[Dict]:
    """从素材中提取关键信息点。"""
    points = []
    for src in sources:
        file_path = Path(src.get("file", ""))
        if not file_path.exists():
            continue

        content = file_path.read_text(encoding="utf-8", errors="replace")

        # 提取前 500 字作为关键内容
        lines = [l.strip() for l in content.split("\n") if l.strip()]
        # 跳过元信息
        text_lines = []
        for line in lines:
            if line.startswith("来源:") or line.startswith("视频标题:") or \
               line.startswith("抓取时间:") or line.startswith("下载时间:"):
                continue
            text_lines.append(line)

        key_content = " ".join(text_lines)[:500]

        points.append({
            "title": src.get("title", "未知"),
            "type": src.get("type", "unknown"),
            "summary": src.get("summary", ""),
            "key_content": key_content,
            "source_id": src.get("id", "")
        })

    return points


def estimate_duration(num_points: int) -> Dict:
    """根据论点数量估算时长和字数。"""
    # 每个论点约 300-400 字，2 分钟
    word_count = num_points * 350
    duration = max(5, num_points * 2)
    return {
        "duration": duration,
        "word_count": word_count,
        "num_points": num_points
    }


def generate_outline_md(topic: str, points: List[Dict], estimates: Dict) -> str:
    """生成 outline.md 内容。"""
    lines = []
    lines.append(f"# 视频大纲：{topic}\n")
    lines.append("## 核心主题")
    lines.append(f"[请根据以下素材概括核心主题]\n")

    lines.append("## 预估信息")
    lines.append(f"- 预估时长：{estimates['duration']} 分钟")
    lines.append(f"- 预估字数：{estimates['word_count']} 字")
    lines.append(f"- 论点数量：{estimates['num_points']} 个\n")

    lines.append("## 论点结构\n")

    for i, point in enumerate(points, 1):
        lines.append(f"### 论点 {i}：{point['title']}")
        lines.append(f"- 核心观点：[待补充]")
        lines.append(f"- 案例：{point['summary'][:100]}")
        lines.append(f"- 出处：{point['title']}（{point['type']}）")
        lines.append(f"- 素材 ID：{point['source_id']}")
        lines.append("")

    lines.append("## 素材摘要\n")
    for point in points:
        lines.append(f"### {point['source_id']}: {point['title']}")
        lines.append(f"- 类型：{point['type']}")
        lines.append(f"- 内容摘要：{point['key_content'][:200]}")
        lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_outline.py <sources.json> [output.md]")
        print("示例: python generate_outline.py ./materials/sources.json ./outline.md")
        sys.exit(1)

    sources_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "outline.md"

    try:
        data = load_sources(sources_path)
        topic = data.get("topic", "未知主题")
        sources = data.get("sources", [])

        if not sources:
            print("⚠️ sources.json 中没有素材")
            sys.exit(0)

        print(f"📖 主题: {topic}")
        print(f"📚 素材数量: {len(sources)}")

        # 提取关键信息
        points = extract_key_points(sources)
        estimates = estimate_duration(len(points))

        # 生成大纲
        outline = generate_outline_md(topic, points, estimates)
        Path(output_path).write_text(outline, encoding="utf-8")

        print(f"\n✅ 大纲已生成: {output_path}")
        print(f"📊 预估:")
        print(f"   时长: {estimates['duration']} 分钟")
        print(f"   字数: {estimates['word_count']} 字")
        print(f"   论点: {estimates['num_points']} 个")
        print(f"\n📝 请检查大纲并补充核心观点后确认")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
