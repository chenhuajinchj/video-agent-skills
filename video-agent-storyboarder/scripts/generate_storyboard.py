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
    template = load_prompt_template()
    return template.format(
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
            "maxOutputTokens": 8192,
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


def validate_storyboard(shots: list) -> list[str]:
    """校验分镜数据，返回警告列表"""
    warnings = []
    for i, shot in enumerate(shots):
        required = ["shot_number", "time_range", "script_text", "asset_type", "image_prompt", "mood", "is_post_production"]
        missing = [k for k in required if k not in shot]
        if missing:
            warnings.append(f"镜头 {i+1}: 缺少字段 {missing}")

        if shot.get("asset_type") in ("数据", "文字", "分屏") and not shot.get("is_post_production"):
            warnings.append(f"镜头 {shot.get('shot_number', i+1)}: {shot['asset_type']} 类型应标记 is_post_production=true")

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
        "| 镜头 | 时间 | 对应逐字稿 | 素材类型 | 图片生成 Prompt | 情绪/节奏 | 后期 |",
        "|------|------|-----------|---------|----------------|----------|------|",
    ]

    for shot in shots:
        num = str(shot.get("shot_number", "")).zfill(3)
        time_range = shot.get("time_range", "")
        script_text = shot.get("script_text", "")[:30]
        asset_type = shot.get("asset_type", "")
        prompt = shot.get("image_prompt", "")[:60]
        mood = shot.get("mood", "")
        post = "✅" if shot.get("is_post_production") else ""
        lines.append(f"| {num} | {time_range} | {script_text} | {asset_type} | {prompt} | {mood} | {post} |")

    # 统计
    type_counts: dict[str, int] = {}
    for shot in shots:
        t = shot.get("asset_type", "其他")
        type_counts[t] = type_counts.get(t, 0) + 1

    post_count = sum(1 for s in shots if s.get("is_post_production"))
    lines.extend([
        "",
        "---",
        "",
        "## 分镜统计",
        "",
        f"- 总镜头数：{len(shots)} 个",
        f"- 需生成图片：{len(shots) - post_count} 个",
        f"- 后期制作：{post_count} 个",
        "- 素材类型分布：",
    ])
    for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
        pct = round(c / len(shots) * 100)
        lines.append(f"  - {t}：{c} 个（{pct}%）")

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
    post_count = sum(1 for s in shots if s.get("is_post_production"))
    print(f"\n📊 分镜摘要：")
    print(f"   总镜头数：{len(shots)}")
    print(f"   需生成图片：{len(shots) - post_count}")
    print(f"   后期制作：{post_count}")


if __name__ == "__main__":
    main()
