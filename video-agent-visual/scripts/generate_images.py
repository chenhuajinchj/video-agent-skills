#!/usr/bin/env python3
"""
批量图片生成脚本 — 读取 storyboard.json，调用 Gemini Image API 生成图片

用法：
    python generate_images.py <project_dir> [--style <风格文件>] [--concurrency <并发数>] [--aspect-ratio <比例>]

示例：
    python generate_images.py ~/CC视频/projects/my-video
    python generate_images.py ~/CC视频/projects/my-video --style tech --concurrency 3

环境变量：
    GEMINI_API_KEY — Gemini API 密钥
"""

import json
import os
import sys
import time
import base64
import argparse
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from concurrent.futures import ThreadPoolExecutor, as_completed

SCRIPT_DIR = Path(__file__).parent
STYLES_DIR = SCRIPT_DIR.parent / "styles"

GEMINI_IMAGE_MODEL = "gemini-2.0-flash-exp-image-generation"
GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def load_style(style_name: str) -> str:
    """加载风格指令文件"""
    style_path = STYLES_DIR / f"{style_name}.txt"
    if not style_path.exists():
        available = [f.stem for f in STYLES_DIR.glob("*.txt")]
        print(f"⚠️  风格 '{style_name}' 不存在，可用风格：{available}")
        print(f"   使用默认风格 'default'")
        style_path = STYLES_DIR / "default.txt"
        if not style_path.exists():
            return ""
    return style_path.read_text(encoding="utf-8").strip()


def load_storyboard(project_dir: Path) -> list:
    """读取分镜 JSON"""
    json_path = project_dir / "storyboard.json"
    if not json_path.exists():
        print(f"错误：找不到 {json_path}")
        print("请先运行 generate_storyboard.py 生成分镜表")
        sys.exit(1)
    with open(json_path, encoding="utf-8") as f:
        return json.load(f)


def generate_single_image(
    shot: dict,
    style_prefix: str,
    aspect_ratio: str,
    output_dir: Path,
    api_key: str,
) -> dict:
    """为单个镜头生成图片，返回结果字典"""
    shot_num = shot.get("shot_number", 0)
    image_prompt = shot.get("image_prompt", "")
    filename = f"{str(shot_num).zfill(3)}.png"
    output_path = output_dir / filename

    # 组合 prompt：风格前缀 + 镜头 prompt + 宽高比
    full_prompt = f"{style_prefix}\n\n{image_prompt}\n\nAspect ratio: {aspect_ratio}. High quality, detailed."

    result = {
        "shot_number": shot_num,
        "file": f"visuals/{filename}",
        "status": "pending",
        "prompt": image_prompt,
    }

    url = GEMINI_API_URL.format(model=GEMINI_IMAGE_MODEL) + f"?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"],
        },
    }
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")

    max_retries = 2
    for attempt in range(max_retries):
        try:
            with urlopen(req, timeout=120) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))

            # 从响应中提取图片数据
            parts = resp_data["candidates"][0]["content"]["parts"]
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"]["data"]
                    break

            if image_data is None:
                raise RuntimeError("响应中未找到图片数据")

            # 解码并保存图片
            img_bytes = base64.b64decode(image_data)
            output_path.write_bytes(img_bytes)

            result["status"] = "success"
            return result

        except (HTTPError, URLError, RuntimeError, KeyError, IndexError) as e:
            if attempt < max_retries - 1:
                time.sleep(3)
            else:
                result["status"] = "failed"
                result["error"] = str(e)
                return result

    return result


def generate_report(results: list, project_dir: Path) -> str:
    """生成素材报告 markdown"""
    total = len(results)
    success = sum(1 for r in results if r["status"] == "success")
    failed = sum(1 for r in results if r["status"] == "failed")
    skipped = sum(1 for r in results if r["status"] == "skipped")

    lines = [
        "# 素材生成报告",
        "",
        "## 统计",
        "",
        f"- 总镜头数：{total}",
        f"- 生成成功：{success}",
        f"- 生成失败：{failed}",
        f"- 后期制作（跳过）：{skipped}",
        "",
        "## 明细",
        "",
        "| 镜头 | 状态 | 文件 | 备注 |",
        "|------|------|------|------|",
    ]

    for r in sorted(results, key=lambda x: x["shot_number"]):
        num = str(r["shot_number"]).zfill(3)
        status_icon = {"success": "✅", "failed": "❌", "skipped": "📋"}.get(r["status"], "?")
        file_col = r.get("file", "-")
        note = r.get("error", r.get("skip_reason", ""))
        lines.append(f"| {num} | {status_icon} | {file_col} | {note} |")

    if failed > 0:
        lines.extend([
            "",
            "## 失败镜头（需人工处理）",
            "",
        ])
        for r in results:
            if r["status"] == "failed":
                lines.append(f"- 镜头 {str(r['shot_number']).zfill(3)}: {r.get('error', '未知错误')}")
                lines.append(f"  Prompt: {r.get('prompt', '')}")

    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description="批量生成图片素材")
    parser.add_argument("project_dir", help="项目目录路径")
    parser.add_argument("--style", default="default", help="风格名称（对应 styles/ 下的文件名，默认：default）")
    parser.add_argument("--concurrency", type=int, default=5, help="并发数（默认：5）")
    parser.add_argument("--aspect-ratio", default="16:9", help="宽高比（默认：16:9）")
    args = parser.parse_args()

    project_dir = Path(args.project_dir).expanduser().resolve()
    if not project_dir.exists():
        print(f"错误：项目目录不存在 {project_dir}")
        sys.exit(1)

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("错误：请设置 GEMINI_API_KEY 环境变量")
        sys.exit(1)

    # 1. 读取分镜
    print("📖 读取 storyboard.json...")
    shots = load_storyboard(project_dir)

    # 2. 加载风格
    style_prefix = load_style(args.style)
    if style_prefix:
        print(f"🎨 使用风格：{args.style}")

    # 3. 创建输出目录
    visuals_dir = project_dir / "visuals"
    visuals_dir.mkdir(exist_ok=True)

    # 4. 过滤镜头
    to_generate = []
    results = []
    for shot in shots:
        if shot.get("is_post_production"):
            results.append({
                "shot_number": shot.get("shot_number", 0),
                "file": None,
                "status": "skipped",
                "skip_reason": f"后期制作 ({shot.get('asset_type', '')})",
            })
        else:
            to_generate.append(shot)

    print(f"🖼️  需要生成 {len(to_generate)} 张图片（跳过 {len(results)} 个后期镜头）")

    # 5. 并发生成
    print(f"🚀 开始生成（并发数：{args.concurrency}）...")
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = {}
        for shot in to_generate:
            future = executor.submit(
                generate_single_image,
                shot, style_prefix, args.aspect_ratio, visuals_dir, api_key,
            )
            futures[future] = shot.get("shot_number", 0)

        for future in as_completed(futures):
            shot_num = futures[future]
            try:
                result = future.result()
                results.append(result)
                icon = "✅" if result["status"] == "success" else "❌"
                print(f"   {icon} 镜头 {str(shot_num).zfill(3)}: {result['status']}")
            except Exception as e:
                results.append({
                    "shot_number": shot_num,
                    "status": "failed",
                    "error": str(e),
                })
                print(f"   ❌ 镜头 {str(shot_num).zfill(3)}: {e}")

    # 6. 生成报告
    report = generate_report(results, project_dir)
    report_path = project_dir / "visual-report.md"
    report_path.write_text(report, encoding="utf-8")
    print(f"\n✅ visual-report.md 已生成 → {report_path}")

    # 7. 生成 visual-timeline.json
    timeline = {
        "video_specs": {
            "resolution": "1920x1080",
            "fps": 30,
            "aspect_ratio": args.aspect_ratio,
        },
        "visuals": [],
    }

    for shot in sorted(shots, key=lambda x: x.get("shot_number", 0)):
        shot_num = shot.get("shot_number", 0)
        is_post = shot.get("is_post_production", False)
        matching = [r for r in results if r["shot_number"] == shot_num]
        status = matching[0]["status"] if matching else "unknown"

        # 解析时间范围
        time_range = shot.get("time_range", "0:00-0:00")
        parts = time_range.split("-")
        start_str = parts[0].strip() if len(parts) >= 1 else "0:00"
        end_str = parts[1].strip() if len(parts) >= 2 else start_str

        def parse_time(t: str) -> float:
            segments = t.split(":")
            if len(segments) == 2:
                return int(segments[0]) * 60 + float(segments[1])
            elif len(segments) == 3:
                return int(segments[0]) * 3600 + int(segments[1]) * 60 + float(segments[2])
            return 0.0

        start = parse_time(start_str)
        end = parse_time(end_str)

        entry = {
            "shot": str(shot_num).zfill(3),
            "file": f"visuals/{str(shot_num).zfill(3)}.png" if not is_post and status == "success" else None,
            "description": shot.get("image_prompt", ""),
            "start_time": start,
            "end_time": end,
            "duration": round(end - start, 2),
            "asset_type": shot.get("asset_type", ""),
            "acquire_method": "post_production" if is_post else "ai_generate",
            "mood": shot.get("mood", ""),
        }
        if is_post:
            entry["editor_note"] = shot.get("image_prompt", "")

        timeline["visuals"].append(entry)

    timeline["total_duration"] = max((v["end_time"] for v in timeline["visuals"]), default=0)

    timeline_path = project_dir / "visual-timeline.json"
    timeline_path.write_text(json.dumps(timeline, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"✅ visual-timeline.json 已生成 → {timeline_path}")

    # 8. 汇总
    success_count = sum(1 for r in results if r["status"] == "success")
    failed_count = sum(1 for r in results if r["status"] == "failed")
    print(f"\n📊 生成汇总：成功 {success_count} / 失败 {failed_count} / 跳过 {len(shots) - len(to_generate)}")
    if failed_count > 0:
        print(f"⚠️  有 {failed_count} 个镜头生成失败，请查看 visual-report.md")


if __name__ == "__main__":
    main()
