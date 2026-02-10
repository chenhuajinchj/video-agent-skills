#!/usr/bin/env python3
"""
Edge-TTS 语音生成脚本
使用微软 Edge TTS 服务生成语音和字幕，无需 API key。

用法:
    python edge_tts_generate.py <input.txt> <output_dir> [voice]

参数:
    input.txt   - 纯文本文件（script-plain.txt）
    output_dir  - 输出目录（如 audio/）
    voice       - 可选，语音名称（默认 zh-CN-YunxiNeural）

输出:
    output_dir/voiceover.mp3   - 语音文件
    output_dir/subtitles.srt   - SRT 字幕文件

可用中文语音:
    zh-CN-YunxiNeural      男声（默认）
    zh-CN-XiaoxiaoNeural   女声
    zh-CN-YunjianNeural    男声（新闻风格）
    zh-CN-XiaoyiNeural     女声（活泼）
"""

import asyncio
import sys
import os

try:
    import edge_tts
except ImportError:
    print("错误: 请先安装 edge-tts: pip install edge-tts")
    sys.exit(1)


DEFAULT_VOICE = "zh-CN-YunxiNeural"


async def generate(text: str, output_dir: str, voice: str):
    """生成语音和字幕。"""
    os.makedirs(output_dir, exist_ok=True)

    mp3_path = os.path.join(output_dir, "voiceover.mp3")
    srt_path = os.path.join(output_dir, "subtitles.srt")

    print(f"语音: {voice}")
    print(f"文本长度: {len(text)} 字符")
    print(f"输出目录: {output_dir}")

    communicate = edge_tts.Communicate(text, voice)
    submaker = edge_tts.SubMaker()

    print("正在生成语音...")
    with open(mp3_path, "wb") as mp3_file:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                mp3_file.write(chunk["data"])
            elif chunk["type"] in ("WordBoundary", "SentenceBoundary"):
                submaker.feed(chunk)

    # 直接生成 SRT 字幕
    srt_content = submaker.get_srt()
    with open(srt_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    # 验证输出
    mp3_size = os.path.getsize(mp3_path)
    srt_size = os.path.getsize(srt_path)
    print(f"\n生成完成:")
    print(f"  音频: {mp3_path} ({mp3_size / 1024:.1f} KB)")
    print(f"  字幕: {srt_path} ({srt_size / 1024:.1f} KB)")

    if mp3_size == 0:
        print("警告: 音频文件为空！")
        sys.exit(1)
    if srt_size == 0:
        print("警告: 字幕文件为空！")
        sys.exit(1)


def main():
    if len(sys.argv) < 3:
        print("用法: python edge_tts_generate.py <input.txt> <output_dir> [voice]")
        print(f"默认语音: {DEFAULT_VOICE}")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]
    voice = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_VOICE

    if not os.path.exists(input_path):
        print(f"错误: 输入文件不存在: {input_path}")
        sys.exit(1)

    with open(input_path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    if not text:
        print("错误: 输入文件为空")
        sys.exit(1)

    asyncio.run(generate(text, output_dir, voice))


if __name__ == "__main__":
    main()
