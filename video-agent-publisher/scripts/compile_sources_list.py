#!/usr/bin/env python3
"""
引用出处整理工具。
从 script.md 提取所有【出处：...】标注，生成 Markdown 格式的引用出处列表。
"""

import re
import sys
from pathlib import Path
from typing import List, Dict


def extract_sources(script_path: str) -> List[Dict]:
    """从逐字稿提取所有出处标注。"""
    path = Path(script_path)
    if not path.exists():
        raise FileNotFoundError(f"找不到文件: {path}")

    content = path.read_text(encoding="utf-8")
    sources = []
    idx = 1

    # 查找所有【出处：...】标注及其上下文
    lines = content.split("\n")
    for i, line in enumerate(lines):
        matches = re.findall(r"【出处：([^】]+)】", line)
        for source_text in matches:
            # 向上查找关联的案例描述
            context = ""
            for j in range(max(0, i - 3), i):
                if lines[j].strip() and not lines[j].strip().startswith("[画面"):
                    context = lines[j].strip()
                    break

            # 推断来源类型
            source_type = classify_source(source_text)

            sources.append({
                "id": idx,
                "source": source_text.strip(),
                "context": context[:100],
                "type": source_type
            })
            idx += 1

    return sources


def classify_source(source_text: str) -> str:
    """推断来源类型。"""
    text = source_text.lower()
    if any(kw in text for kw in ["书", "《", "》", "出版"]):
        return "书籍"
    if any(kw in text for kw in ["新闻", "报道", "日报", "时报", "网"]):
        return "新闻"
    if any(kw in text for kw in ["演讲", "ted", "讲座"]):
        return "演讲"
    if any(kw in text for kw in ["论文", "研究", "实验", "大学"]):
        return "研究"
    if any(kw in text for kw in ["视频", "youtube", "bilibili"]):
        return "视频"
    return "其他"


def generate_sources_md(sources: List[Dict]) -> str:
    """生成 Markdown 格式的引用出处列表。"""
    lines = ["# 视频引用出处\n"]

    if not sources:
        lines.append("暂无引用出处。\n")
        return "\n".join(lines)

    # 按类型分组
    by_type = {}
    for s in sources:
        t = s["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(s)

    lines.append("## 案例来源\n")
    for i, s in enumerate(sources, 1):
        lines.append(f"{i}. **{s['context'][:60]}**")
        lines.append(f"   - 来源：{s['source']}")
        lines.append(f"   - 类型：{s['type']}")
        lines.append("")

    # 按类型汇总
    lines.append("## 来源类型统计\n")
    lines.append("| 类型 | 数量 |")
    lines.append("|------|------|")
    for t, items in sorted(by_type.items()):
        lines.append(f"| {t} | {len(items)} |")
    lines.append("")

    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("用法: python compile_sources_list.py <script.md> [output.md]")
        print("示例: python compile_sources_list.py ./script.md ./publish/sources.md")
        sys.exit(1)

    script_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "sources.md"

    try:
        sources = extract_sources(script_path)

        if not sources:
            print("⚠️ 未找到任何出处标注")
        else:
            print(f"🔍 找到 {len(sources)} 个出处标注")

        md_content = generate_sources_md(sources)
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        Path(output_path).write_text(md_content, encoding="utf-8")

        print(f"✅ 出处列表已生成: {output_path}")
        for s in sources:
            print(f"   📌 [{s['type']}] {s['source'][:40]}")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
