#!/usr/bin/env python3
"""
发布元数据生成工具。
从 script.md 和 outline.md 提取信息，生成标题、描述、标签等发布元数据。
"""

import json
import re
import sys
from pathlib import Path
from typing import List, Dict


def read_file(path: str) -> str:
    """读取文件内容。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到文件: {p}")
    return p.read_text(encoding="utf-8")


def extract_topic(outline: str) -> str:
    """从大纲提取主题。"""
    match = re.search(r"^# 视频大纲：(.+)$", outline, re.MULTILINE)
    return match.group(1).strip() if match else "未知主题"


def extract_core_theme(outline: str) -> str:
    """从大纲提取核心主题。"""
    match = re.search(r"## 核心主题\s*\n(.+)", outline)
    return match.group(1).strip() if match else ""


def extract_points(outline: str) -> List[str]:
    """从大纲提取论点标题。"""
    return re.findall(r"### 论点 \d+：(.+)", outline)


def extract_keywords(script: str) -> List[str]:
    """从逐字稿提取关键词（高频实词）。"""
    # 去除标注
    text = re.sub(r"\[画面#\d{3}：[^\]]+\]", "", script)
    text = re.sub(r"【出处：[^】]+】", "", text)
    text = re.sub(r"[#\-*\n]", " ", text)

    # 简单的中文分词（按标点分割后取高频片段）
    segments = re.split(r"[，。！？、；：\u201c\u201d\u2018\u2019（）\s]+", text)
    # 过滤过短和过长的片段
    words = [s.strip() for s in segments if 2 <= len(s.strip()) <= 6]

    # 统计词频
    freq = {}
    for w in words:
        freq[w] = freq.get(w, 0) + 1

    # 取前 10 个高频词
    sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
    return [w for w, _ in sorted_words[:10]]


def generate_titles(topic: str, core_theme: str, points: List[str]) -> List[str]:
    """生成多种风格的标题候选。"""
    titles = []

    # 疑问式
    titles.append(f"为什么{topic}如此重要？")

    # 数字式
    if points:
        titles.append(f"关于{topic}，你必须知道的{len(points)}件事")

    # 反常识式
    titles.append(f"你以为的{topic}，可能完全是错的")

    # 故事式
    if core_theme:
        titles.append(f"从{core_theme}说起：重新理解{topic}")

    return titles


def generate_hashtags(topic: str, keywords: List[str]) -> List[str]:
    """生成标签。"""
    tags = [f"#{topic}"]
    for kw in keywords[:5]:
        tags.append(f"#{kw}")
    tags.extend(["#认知成长", "#个人成长", "#知识分享"])
    return list(dict.fromkeys(tags))  # 去重保序


def generate_description(topic: str, core_theme: str, points: List[str]) -> str:
    """生成视频描述。"""
    lines = []
    if core_theme:
        lines.append(core_theme)
    lines.append("")
    if points:
        lines.append("本期内容：")
        for i, p in enumerate(points, 1):
            lines.append(f"{i}. {p}")
    lines.append("")
    lines.append("如果觉得有帮助，请点赞关注！")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("用法: python generate_metadata.py <script.md> <outline.md> [output_dir]")
        print("示例: python generate_metadata.py ./script.md ./outline.md ./publish")
        sys.exit(1)

    script_path = sys.argv[1]
    outline_path = sys.argv[2]
    output_dir = sys.argv[3] if len(sys.argv) > 3 else "publish"

    try:
        script = read_file(script_path)
        outline = read_file(outline_path)

        topic = extract_topic(outline)
        core_theme = extract_core_theme(outline)
        points = extract_points(outline)
        keywords = extract_keywords(script)

        print(f"📝 主题: {topic}")
        print(f"💡 核心: {core_theme}")
        print(f"📌 论点: {len(points)} 个")
        print(f"🔑 关键词: {', '.join(keywords[:5])}")

        # 生成元数据
        titles = generate_titles(topic, core_theme, points)
        description = generate_description(topic, core_theme, points)
        hashtags = generate_hashtags(topic, keywords)

        metadata = {
            "topic": topic,
            "titles": titles,
            "description": description,
            "hashtags": hashtags,
            "keywords": keywords,
            "recommended_bgm": [
                {"name": "轻松思考", "mood": "calm-thinking", "source": "pixabay"},
                {"name": "温暖叙事", "mood": "warm-narrative", "source": "pixabay"},
                {"name": "积极向上", "mood": "uplifting", "source": "pixabay"}
            ]
        }

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        meta_file = out_path / "metadata.json"
        meta_file.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")

        print(f"\n✅ 元数据已生成: {meta_file}")
        print(f"\n📋 标题候选:")
        for i, t in enumerate(titles, 1):
            print(f"   {i}. {t}")
        print(f"\n🏷️ 标签: {' '.join(hashtags[:6])}")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
