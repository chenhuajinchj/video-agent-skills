#!/usr/bin/env python3
"""
使用 Whisper 从音频生成字幕文件。
输出 SRT 格式字幕。
"""

import subprocess
import sys
from pathlib import Path


def check_whisper_installed() -> bool:
    """检查 whisper 是否已安装"""
    try:
        result = subprocess.run(
            ["whisper", "--help"],
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def generate_subtitles(
    audio_path: str,
    output_dir: str = None,
    language: str = "zh",
    model: str = "medium"
) -> str:
    """
    使用 Whisper 生成字幕。

    Args:
        audio_path: 音频文件路径
        output_dir: 输出目录，默认与音频同目录
        language: 语言代码，默认中文
        model: Whisper 模型，默认 medium

    Returns:
        生成的 SRT 文件路径
    """
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"找不到音频文件: {audio_path}")

    if output_dir is None:
        output_dir = audio_path.parent
    else:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 构建 whisper 命令
    cmd = [
        "whisper",
        str(audio_path),
        "--language", language,
        "--model", model,
        "--output_format", "srt",
        "--output_dir", str(output_dir),
        "--word_timestamps", "True"
    ]

    print(f"🎙️ 正在转写音频: {audio_path.name}")
    print(f"   模型: {model}")
    print(f"   语言: {language}")

    # 运行 whisper
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ Whisper 错误: {result.stderr}")
        raise RuntimeError("Whisper 转写失败")

    # 查找生成的 SRT 文件
    srt_path = output_dir / f"{audio_path.stem}.srt"

    if not srt_path.exists():
        raise FileNotFoundError(f"未找到生成的字幕文件: {srt_path}")

    # 重命名为 subtitles.srt
    final_path = output_dir / "subtitles.srt"
    if srt_path != final_path:
        srt_path.rename(final_path)

    return str(final_path)


def get_audio_duration(audio_path: str) -> float:
    """获取音频时长（秒）"""
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                audio_path
            ],
            capture_output=True,
            text=True
        )
        return float(result.stdout.strip())
    except (subprocess.CalledProcessError, ValueError):
        return 0.0


def main():
    if len(sys.argv) < 2:
        print("用法: python generate_subtitles.py <audio.mp3> [output_dir] [model]")
        print("示例: python generate_subtitles.py ./audio/voiceover.mp3 ./audio medium")
        print("")
        print("可用模型: tiny, base, small, medium, large")
        print("推荐: medium（平衡速度和质量）")
        sys.exit(1)

    # 检查 whisper
    if not check_whisper_installed():
        print("❌ 未安装 whisper，请先运行:")
        print("   pip install openai-whisper")
        sys.exit(1)

    audio_path = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    model = sys.argv[3] if len(sys.argv) > 3 else "medium"

    try:
        # 获取音频时长
        duration = get_audio_duration(audio_path)
        if duration > 0:
            print(f"📊 音频时长: {duration:.1f} 秒 ({duration/60:.1f} 分钟)")

        # 生成字幕
        srt_path = generate_subtitles(audio_path, output_dir, model=model)

        print(f"✅ 字幕已生成: {srt_path}")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    except RuntimeError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
