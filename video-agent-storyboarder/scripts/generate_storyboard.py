#!/usr/bin/env python3
"""
分镜表生成脚本 — 调用 Gemini Flash API 批量生成分镜

用法：
    python generate_storyboard.py <project_dir> [--style <风格>] [--duration <时长>]

示例：
    python generate_storyboard.py ~/CC视频/projects/my-video
    python generate_storyboard.py ~/CC视频/projects/my-video --style "AI科技" --duration "8分钟"

环境变量：
    GEMINI_API_KEY — Gemini API 密钥
"""

import json
import os
import re
import sys
import time
import argparse
from pathlib import Path
from string import Template
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

SCRIPT_DIR = Path(__file__).parent
PROMPT_TEMPLATE_PATH = SCRIPT_DIR.parent / "prompts" / "storyboard_prompt.txt"

GEMINI_MODEL = "gemini-2.5-flash"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_prompt_template() -> str:
    """加载 prompt 模板"""
    if not PROMPT_TEMPLATE_PATH.exists():
        print(f"错误：找不到 prompt 模板文件 {PROMPT_TEMPLATE_PATH}")
        sys.exit(1)
    return PROMPT_TEMPLATE_PATH.read_text(encoding="utf-8")


def load_script(project_dir: Path) -> str:
    """读取逐字稿"""
    script_path = project_dir / "script.md"
    if not script_path.exists():
        print(f"错误：找不到逐字稿 {script_path}")
        sys.exit(1)
    return script_path.read_text(encoding="utf-8")


def build_prompt(script_content: str, video_style: str, total_duration: str) -> str:
    """构建完整 prompt"""
    template_text = load_prompt_template()
    template = Template(template_text)
    return template.safe_substitute(
        script_content=script_content,
        video_style=video_style,
        total_duration=total_duration,
    )


def call_gemini_api(prompt: str, api_key: str) -> str:
    """调用 Gemini Flash API"""
    url = GEMINI_API_URL.format(model=GEMINI_MODEL) + f"?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 16384,
            "responseMimeType": "application/json",
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    try:
        with urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini API 返回 {e.code}: {body}")
    except URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")

    # 提取文本
    try:
        text = result["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"Gemini 响应格式异常: {json.dumps(result, ensure_ascii=False)[:500]}")

    return text


def parse_json_response(text: str) -> list:
    """解析 JSON 响应，容忍 markdown 代码块包裹"""
    # 去掉 markdown 代码块标记
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*\n?", "", text)
        text = re.sub(r"\n?```\s*$", "", text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"JSON 解析失败: {e}\n原始文本前 500 字符:\n{text[:500]}")

    if not isinstance(data, list):
        raise RuntimeError(f"期望 JSON 数组，实际得到 {type(data).__name__}")

    return data


VALID_ASSET_TYPES = {"截图", "真实人物", "文字卡", "数据图表", "概念画面", "引用片段", "信息图", "留白", "书籍", "分屏"}
VALID_MEDIA_FORMATS = {"ai_video", "ai_image", "manual", "post_production", "simple"}


def validate_storyboard(shots: list) -> list[str]:
    """校验分镜数据，返回警告列表"""
    warnings = []
    for i, shot in enumerate(shots):
        required = ["shot_number", "time_range", "script_text", "asset_type", "media_format", "visual_description", "mood", "duration_seconds"]
        missing = [k for k in required if k not in shot]
        if missing:
            warnings.append(f"镜头 {i+1}: 缺少字段 {missing}")

        asset_type = shot.get("asset_type", "")
        if asset_type and asset_type not in VALID_ASSET_TYPES:
            warnings.append(f"镜头 {shot.get('shot_number', i+1)}: 未知 asset_type '{asset_type}'")

        media_format = shot.get("media_format", "")
        if media_format and media_format not in VALID_MEDIA_FORMATS:
            warnings.append(f"镜头 {shot.get('shot_number', i+1)}: 未知 media_format '{media_format}'")

    # 比例检查
    if shots:
        total = len(shots)
        ai_count = sum(1 for s in shots if s.get("media_format") in ("ai_video", "ai_image"))
        if ai_count / total > 0.5:
            warnings.append(f"⚠️  AI 生成素材占比 {ai_count}/{total} ({round(ai_count/total*100)}%)，建议不超过 50%")

        type_set = {s.get("asset_type") for s in shots}
        if "文字卡" not in type_set:
            warnings.append("⚠️  缺少「文字卡」类型，核心概念和结论应使用文字卡")
        if not type_set & {"截图", "真实人物", "引用片段"}:
            warnings.append("⚠️  缺少手动素材（截图/真实人物/引用片段），视频缺乏真实感")

    return warnings


def generate_markdown(shots: list, title: str = "视频") -> str:
    """从 JSON 数据生成可读的 markdown 分镜表"""
    lines = [
        f"# 分镜表 — {title}",
        "",
        f"> 总镜头数：{len(shots)} 个",
        "",
        "---",
        "",
        "| 镜头 | 时间 | 秒 | 对应逐字稿 | 素材类型 | 媒体格式 | 画面说明 | 情绪 |",
        "|------|------|----|-----------|---------|---------|---------|------|",
    ]

    for shot in shots:
        num = str(shot.get("shot_number", "")).zfill(3)
        time_range = shot.get("time_range", "")
        duration = shot.get("duration_seconds", "")
        script_text = shot.get("script_text", "")[:30]
        asset_type = shot.get("asset_type", "")
        media_format = shot.get("media_format", "")
        desc = shot.get("visual_description", shot.get("image_prompt", ""))[:50]
        mood = shot.get("mood", "")
        lines.append(f"| {num} | {time_range} | {duration} | {script_text} | {asset_type} | {media_format} | {desc} | {mood} |")

    # asset_type 统计
    type_counts: dict[str, int] = {}
    for shot in shots:
        t = shot.get("asset_type", "其他")
        type_counts[t] = type_counts.get(t, 0) + 1

    # media_format 统计
    format_counts: dict[str, int] = {}
    for shot in shots:
        f = shot.get("media_format", "其他")
        format_counts[f] = format_counts.get(f, 0) + 1

    lines.extend([
        "",
        "---",
        "",
        "## 分镜统计",
        "",
        f"- 总镜头数：{len(shots)} 个",
        "",
        "### 按素材类型（asset_type）",
    ])
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = round(c / len(shots) * 100)
        lines.append(f"- {t}：{c} 个（{pct}%）")

    lines.extend([
        "",
        "### 按媒体格式（media_format）",
    ])
    for f, c in sorted(format_counts.items(), key=lambda x: -x[1]):
        pct = round(c / len(shots) * 100)
        lines.append(f"- {f}：{c} 个（{pct}%）")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="生成分镜表")
    parser.add_argument("project_dir", help="项目目录路径")
    parser.add_argument("--style", default="AI科技/知识分享", help="视频风格（默认：AI科技/知识分享）")
    parser.add_argument("--duration", default="6-10分钟", help="目标时长（默认：6-10分钟）")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        print(f"错误：项目目录不存在 {project_dir}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("错误：请设置 GEMINI_API_KEY 环境变量")
        sys.exit(1)

    # 1. 读取逐字稿
    print("📖 读取逐字稿...")
    script_content = load_script(project_dir)

    # 2. 构建 prompt
    print("📝 构建 prompt...")
    prompt = build_prompt(script_content, args.style, args.duration)

    # 3. 调用 Gemini Flash API（失败重试 1 次）
    print(f"🤖 调用 {GEMINI_MODEL} 生成分镜...")
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response_text = call_gemini_api(prompt, api_key)
            shots = parse_json_response(response_text)
            break
        except RuntimeError as e:
            if attempt < max_retries - 1:
                print(f"⚠️  第 {attempt+1} 次失败: {e}")
                print("   等待 3 秒后重试...")
                time.sleep(3)
            else:
                print(f"❌ 生成失败: {e}")
                sys.exit(1)

    # 4. 校验
    warnings = validate_storyboard(shots)
    if warnings:
        print("⚠️  校验警告：")
        for w in warnings:
            print(f"   - {w}")

    # 5. 输出 JSON
    json_path = project_dir / "storyboard.json"
    json_path.write_text(json.dumps(shots, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ storyboard.json 已生成 → {json_path}")

    # 6. 输出 Markdown
    title = project_dir.name
    md_content = generate_markdown(shots, title)
    md_path = project_dir / "storyboard.md"
    md_path.write_text(md_content, encoding="utf-8")
    print(f"✅ storyboard.md 已生成 → {md_path}")

    # 7. 输出摘要
    format_counts: dict[str, int] = {}
    for s in shots:
        f = s.get("media_format", "其他")
        format_counts[f] = format_counts.get(f, 0) + 1
    print(f"\n📊 分镜摘要：")
    print(f"   总镜头数：{len(shots)}")
    for f, c in sorted(format_counts.items(), key=lambda x: -x[1]):
        pct = round(c / len(shots) * 100)
        print(f"   {f}：{c} 个（{pct}%）")


if __name__ == "__main__":
    main()
