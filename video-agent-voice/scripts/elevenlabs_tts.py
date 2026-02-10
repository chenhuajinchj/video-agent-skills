#!/usr/bin/env python3
"""
使用 ElevenLabs REST API 将文本转换为语音。
支持长文本自动分段，用 ffmpeg 合并。
"""

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import List


# 默认配置
DEFAULT_MODEL = "eleven_multilingual_v2"
DEFAULT_STABILITY = 0.5
DEFAULT_SIMILARITY_BOOST = 0.75
MAX_CHUNK_CHARS = 5000


def get_api_key() -> str:
    """从环境变量获取 ElevenLabs API Key"""
    key = os.environ.get("ELEVENLABS_API_KEY")
    if not key:
        print("❌ 未设置 ELEVENLABS_API_KEY 环境变量")
        print("   请运行: export ELEVENLABS_API_KEY='your-api-key'")
        sys.exit(1)
    return key


def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> List[str]:
    """
    将长文本按自然断句分段，每段不超过 max_chars 字符。
    优先在句号、问号、感叹号处断开。
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # 在 max_chars 范围内找最后一个句子结束符
        search_range = remaining[:max_chars]
        split_pos = -1

        # 优先按句号、问号、感叹号断开
        for sep in ["。", "？", "！", ".", "?", "!", "\n\n", "\n"]:
            pos = search_range.rfind(sep)
            if pos > 0:
                split_pos = pos + len(sep)
                break

        # 找不到句子结束符，按逗号断开
        if split_pos == -1:
            for sep in ["，", "；", ",", ";"]:
                pos = search_range.rfind(sep)
                if pos > 0:
                    split_pos = pos + len(sep)
                    break

        # 实在找不到，强制截断
        if split_pos == -1:
            split_pos = max_chars

        chunk = remaining[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_pos:].strip()

    return chunks


def tts_single_chunk(
    text: str,
    output_path: str,
    voice_id: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    stability: float = DEFAULT_STABILITY,
    similarity_boost: float = DEFAULT_SIMILARITY_BOOST,
) -> None:
    """调用 ElevenLabs API 将单段文本转为语音"""
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    payload = json.dumps({
        "text": text,
        "model_id": model,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
        },
    })

    # 使用 curl 调用 API（避免额外 Python 依赖）
    cmd = [
        "curl", "-s", "-w", "%{http_code}",
        "-X", "POST", url,
        "-H", f"xi-api-key: {api_key}",
        "-H", "Content-Type: application/json",
        "-d", payload,
        "-o", output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    http_code = result.stdout.strip()[-3:] if result.stdout else "000"

    if http_code != "200":
        # 读取错误响应
        error_msg = ""
        if Path(output_path).exists():
            try:
                error_msg = Path(output_path).read_text(encoding="utf-8")
                Path(output_path).unlink()
            except Exception:
                pass
        raise RuntimeError(
            f"ElevenLabs API 返回 {http_code}: {error_msg}"
        )

    if not Path(output_path).exists() or Path(output_path).stat().st_size == 0:
        raise RuntimeError("API 返回空响应，请检查 voice_id 和 API Key")


def merge_audio_files(file_list: List[str], output_path: str) -> None:
    """使用 ffmpeg 合并多个音频文件"""
    if len(file_list) == 1:
        Path(file_list[0]).rename(output_path)
        return

    # 创建 ffmpeg 合并列表
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as f:
        for audio_file in file_list:
            f.write(f"file '{audio_file}'\n")
        list_path = f.name

    try:
        cmd = [
            "ffmpeg", "-y", "-f", "concat", "-safe", "0",
            "-i", list_path, "-c", "copy", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg 合并失败: {result.stderr}")
    finally:
        Path(list_path).unlink(missing_ok=True)


def generate_tts(
    input_text: str,
    output_dir: str,
    voice_id: str,
    api_key: str,
) -> str:
    """
    主流程：读取文本 → 分段 → 逐段调用 API → 合并输出。
    返回最终音频文件路径。
    """
    text = Path(input_text).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("输入文本为空")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "voiceover.mp3")

    # 分段
    chunks = split_text(text)
    total = len(chunks)
    print(f"📝 文本总长: {len(text)} 字符，分为 {total} 段")

    if total == 1:
        # 单段直接生成
        print("🔊 正在生成语音...")
        tts_single_chunk(text, output_path, voice_id, api_key)
    else:
        # 多段逐个生成后合并
        temp_files = []
        try:
            for i, chunk in enumerate(chunks, 1):
                temp_path = str(output_dir / f"_chunk_{i:03d}.mp3")
                print(f"🔊 生成第 {i}/{total} 段 ({len(chunk)} 字符)...")
                tts_single_chunk(chunk, temp_path, voice_id, api_key)
                temp_files.append(temp_path)

            print("🔗 正在合并音频...")
            merge_audio_files(temp_files, output_path)
        finally:
            # 清理临时文件
            for f in temp_files:
                Path(f).unlink(missing_ok=True)

    return output_path


def main():
    if len(sys.argv) < 3:
        print("用法: python elevenlabs_tts.py <input.txt> <output_dir> [voice_id]")
        print("示例: python elevenlabs_tts.py ./script-plain.txt ./audio pNInz6obpgDQGcFmaJgB")
        print("")
        print("参数:")
        print("  input.txt   纯文本文件路径（由 extract_plain_text.py 生成）")
        print("  output_dir  输出目录（音频将保存为 voiceover.mp3）")
        print("  voice_id    ElevenLabs 语音 ID（可选，默认 21m00Tcm4TlvDq8ikWAM）")
        print("")
        print("环境变量:")
        print("  ELEVENLABS_API_KEY  ElevenLabs API 密钥（必需）")
        sys.exit(1)

    input_text = sys.argv[1]
    output_dir = sys.argv[2]
    voice_id = sys.argv[3] if len(sys.argv) > 3 else "21m00Tcm4TlvDq8ikWAM"

    # 检查输入文件
    if not Path(input_text).exists():
        print(f"❌ 找不到输入文件: {input_text}")
        sys.exit(1)

    api_key = get_api_key()

    try:
        output_path = generate_tts(input_text, output_dir, voice_id, api_key)
        size_mb = Path(output_path).stat().st_size / (1024 * 1024)
        print(f"✅ 语音已生成: {output_path} ({size_mb:.1f} MB)")
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
