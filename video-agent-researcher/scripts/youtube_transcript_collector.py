#!/usr/bin/env python3
"""
YouTube 字幕下载工具。
使用 yt-dlp 下载 YouTube 视频字幕并转为纯文本。
"""

import json
import re
import sys
import subprocess
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def download_subtitles(video_url: str, output_dir: str) -> Dict:
    """使用 yt-dlp 下载 YouTube 字幕。"""
    transcript_dir = Path(output_dir) / "transcripts"
    transcript_dir.mkdir(parents=True, exist_ok=True)

    # 先获取视频信息
    info_cmd = [
        "yt-dlp", "--dump-json", "--no-download", video_url
    ]
    try:
        result = subprocess.run(info_cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            raise RuntimeError(f"获取视频信息失败: {result.stderr.strip()}")
        info = json.loads(result.stdout)
        title = info.get("title", "unknown")
        video_id = info.get("id", "unknown")
    except (subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        raise RuntimeError(f"获取视频信息失败: {e}")

    # 下载字幕
    safe_title = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
    sub_cmd = [
        "yt-dlp",
        "--write-auto-sub",
        "--sub-lang", "zh,en",
        "--skip-download",
        "--sub-format", "srt/vtt/best",
        "-o", str(transcript_dir / f"{safe_title}_%(id)s.%(ext)s"),
        video_url
    ]
    result = subprocess.run(sub_cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        raise RuntimeError(f"下载字幕失败: {result.stderr.strip()}")

    # 查找下载的字幕文件并转为纯文本
    sub_files = list(transcript_dir.glob(f"*{video_id}*"))
    if not sub_files:
        raise RuntimeError("未找到下载的字幕文件")

    plain_text = ""
    sub_file = sub_files[0]
    for sf in sub_files:
        if "zh" in sf.name.lower():
            sub_file = sf
            break

    plain_text = convert_subtitle_to_text(sub_file)

    # 保存纯文本版本
    txt_filename = f"transcript_{safe_title}.txt"
    txt_path = transcript_dir / txt_filename
    header = f"视频标题: {title}\n来源: {video_url}\n下载时间: {datetime.now().isoformat()}\n\n"
    txt_path.write_text(header + plain_text, encoding="utf-8")

    # 清理原始字幕文件
    for sf in sub_files:
        if sf != txt_path:
            sf.unlink(missing_ok=True)

    return {
        "title": title,
        "video_id": video_id,
        "url": video_url,
        "file": str(txt_path),
        "char_count": len(plain_text)
    }


def convert_subtitle_to_text(sub_path: Path) -> str:
    """将 VTT/SRT 字幕文件转为纯文本。"""
    content = sub_path.read_text(encoding="utf-8", errors="replace")

    # 去除 VTT 头部
    content = re.sub(r"^WEBVTT.*?\n\n", "", content, flags=re.DOTALL)
    # 去除时间戳行（SRT 和 VTT 格式）
    content = re.sub(r"\d{2}:\d{2}:\d{2}[.,]\d{3}\s*-->.*\n", "", content)
    # 去除 SRT 序号行
    content = re.sub(r"^\d+\s*$", "", content, flags=re.MULTILINE)
    # 去除 VTT 标签
    content = re.sub(r"<[^>]+>", "", content)
    # 去除重复行（自动字幕常见问题）
    lines = content.split("\n")
    seen = set()
    unique_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and stripped not in seen:
            seen.add(stripped)
            unique_lines.append(stripped)
    # 合并为段落
    text = "\n".join(unique_lines)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def main():
    if len(sys.argv) < 3:
        print("用法: python youtube_transcript_collector.py <video_url> <output_dir>")
        print("示例: python youtube_transcript_collector.py 'https://youtube.com/watch?v=xxx' ./materials")
        print("\n支持多个 URL，用逗号分隔")
        sys.exit(1)

    urls_input = sys.argv[1]
    output_dir = sys.argv[2]

    # 支持逗号分隔的多个 URL
    urls = [u.strip() for u in urls_input.split(",") if u.strip()]

    results = []
    for i, url in enumerate(urls, 1):
        print(f"🎬 [{i}/{len(urls)}] 正在下载字幕: {url}")
        try:
            info = download_subtitles(url, output_dir)
            results.append(info)
            print(f"   ✅ 已保存: {Path(info['file']).name} ({info['char_count']} 字)")
        except RuntimeError as e:
            print(f"   ❌ 失败: {e}")
            continue

    print(f"\n📊 字幕下载完成: {len(results)}/{len(urls)}")
    for r in results:
        print(f"   📝 {r['title'][:40]}")


if __name__ == "__main__":
    main()
