#!/usr/bin/env python3
"""
MiniMax Speech-02 语音生成脚本
中文语音质量全球第一，支持声音克隆、情绪控制。

用法:
    # 使用系统预设语音
    python minimax_tts.py <input.txt> <output_dir> [--voice <voice_id>]

    # 使用克隆语音
    python minimax_tts.py <input.txt> <output_dir> --voice <cloned_voice_id>

    # 克隆语音（一次性操作）
    python minimax_tts.py --clone <audio_file> --voice-id <custom_id>

环境变量:
    MINIMAX_API_KEY   — MiniMax API 密钥（必需）
    MINIMAX_GROUP_ID  — MiniMax Group ID（克隆语音时必需）
"""

import argparse
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


# 默认配置
DEFAULT_MODEL = "speech-02-hd"
DEFAULT_VOICE = "Chinese_Calm_Male"  # 系统预设中文男声
MAX_CHUNK_CHARS = 8000  # MiniMax 单次上限 10000，留余量

API_BASE = "https://api.minimaxi.com/v1"


def get_api_key() -> str:
    key = os.environ.get("MINIMAX_API_KEY")
    if not key:
        print("❌ 未设置 MINIMAX_API_KEY 环境变量")
        print("   请运行: export MINIMAX_API_KEY='your-api-key'")
        sys.exit(1)
    return key


def get_group_id() -> str:
    gid = os.environ.get("MINIMAX_GROUP_ID")
    if not gid:
        print("❌ 未设置 MINIMAX_GROUP_ID 环境变量（克隆语音需要）")
        sys.exit(1)
    return gid


def api_request(endpoint: str, payload: dict, api_key: str, timeout: int = 120) -> dict:
    """通用 MiniMax API 请求"""
    url = f"{API_BASE}/{endpoint}"
    data = json.dumps(payload).encode("utf-8")
    req = Request(url, data=data, headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }, method="POST")

    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"MiniMax API 返回 {e.code}: {body}")
    except URLError as e:
        raise RuntimeError(f"网络错误: {e.reason}")


def tts_single_chunk(
    text: str,
    output_path: str,
    voice_id: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    speed: float = 1.0,
    emotion: str = "auto",
) -> None:
    """调用 MiniMax T2A v2 API 将单段文本转为语音"""
    voice_setting = {
        "voice_id": voice_id,
        "speed": speed,
        "vol": 1.0,
        "pitch": 0,
    }
    if emotion and emotion != "none":
        voice_setting["emotion"] = emotion

    payload = {
        "model": model,
        "text": text,
        "voice_setting": voice_setting,
        "audio_setting": {
            "format": "mp3",
            "sample_rate": 32000,
        },
        "language_boost": "zh",
        "stream": False,
        "output_format": "hex",
    }

    result = api_request("t2a_v2", payload, api_key, timeout=180)

    # 检查错误
    base_resp = result.get("base_resp", {})
    if base_resp.get("status_code", 0) != 0:
        raise RuntimeError(f"MiniMax TTS 错误: {base_resp.get('status_msg', '未知错误')}")

    # 解码 hex 音频
    audio_hex = result.get("data", {}).get("audio", "")
    if not audio_hex:
        raise RuntimeError("MiniMax 返回空音频数据")

    audio_bytes = bytes.fromhex(audio_hex)
    Path(output_path).write_bytes(audio_bytes)


def split_text(text: str, max_chars: int = MAX_CHUNK_CHARS) -> list[str]:
    """将长文本按自然断句分段"""
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        search_range = remaining[:max_chars]
        split_pos = -1

        for sep in ["。", "？", "！", ".", "?", "!", "\n\n", "\n"]:
            pos = search_range.rfind(sep)
            if pos > 0:
                split_pos = pos + len(sep)
                break

        if split_pos == -1:
            for sep in ["，", "；", ",", ";"]:
                pos = search_range.rfind(sep)
                if pos > 0:
                    split_pos = pos + len(sep)
                    break

        if split_pos == -1:
            split_pos = max_chars

        chunk = remaining[:split_pos].strip()
        if chunk:
            chunks.append(chunk)
        remaining = remaining[split_pos:].strip()

    return chunks


def merge_audio_files(file_list: list[str], output_path: str) -> None:
    """使用 ffmpeg 合并多个音频文件"""
    if len(file_list) == 1:
        Path(file_list[0]).rename(output_path)
        return

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


def clone_voice(audio_path: str, voice_id: str, api_key: str) -> None:
    """克隆语音：上传音频文件 → 创建克隆语音"""
    audio_path = Path(audio_path)
    if not audio_path.exists():
        raise FileNotFoundError(f"音频文件不存在: {audio_path}")

    # Step 1: 上传音频文件
    print(f"📤 上传音频文件: {audio_path.name}")
    upload_url = f"{API_BASE}/files/upload"

    cmd = [
        "curl", "-s",
        "-X", "POST", upload_url,
        "-H", f"Authorization: Bearer {api_key}",
        "-F", "purpose=voice_clone",
        "-F", f"file=@{audio_path}",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"上传失败: {result.stderr}")

    resp = json.loads(result.stdout)
    file_id = resp.get("file", {}).get("file_id")
    if not file_id:
        raise RuntimeError(f"上传响应异常: {result.stdout}")

    print(f"   file_id: {file_id}")

    # Step 2: 克隆语音
    print(f"🔊 克隆语音: {voice_id}")
    clone_payload = {
        "file_id": file_id,
        "voice_id": voice_id,
        "need_noise_reduction": True,
        "need_volume_normalization": True,
        "text": "你好，这是一段测试语音，用来验证声音克隆的效果。",
        "model": "speech-02-hd",
        "language_boost": "Chinese",
    }

    result = api_request("voice_clone", clone_payload, api_key, timeout=120)

    status = result.get("base_resp", {}).get("status_code", -1)
    if status != 0:
        msg = result.get("base_resp", {}).get("status_msg", "未知错误")
        raise RuntimeError(f"克隆失败 (code={status}): {msg}")

    demo_audio = result.get("demo_audio", "")
    print(f"✅ 语音克隆成功！voice_id: {voice_id}")
    if demo_audio:
        print(f"   试听链接: {demo_audio}")
    print(f"   使用方式: python minimax_tts.py <input.txt> <output_dir> --voice {voice_id}")
    print(f"   注意: 克隆语音 7 天不使用会被自动删除")


def generate_tts(
    input_text: str,
    output_dir: str,
    voice_id: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    speed: float = 1.0,
    emotion: str = "auto",
) -> str:
    """主流程：读取文本 → 分段 → 逐段调用 API → 合并输出"""
    text = Path(input_text).read_text(encoding="utf-8").strip()
    if not text:
        raise ValueError("输入文本为空")

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = str(output_dir / "voiceover.mp3")

    chunks = split_text(text)
    total = len(chunks)
    print(f"📝 文本总长: {len(text)} 字符，分为 {total} 段")

    if total == 1:
        print("🔊 正在生成语音...")
        tts_single_chunk(text, output_path, voice_id, api_key, model, speed, emotion)
    else:
        temp_files = []
        try:
            for i, chunk in enumerate(chunks, 1):
                temp_path = str(output_dir / f"_chunk_{i:03d}.mp3")
                print(f"🔊 生成第 {i}/{total} 段 ({len(chunk)} 字符)...")
                tts_single_chunk(chunk, temp_path, voice_id, api_key, model, speed, emotion)
                temp_files.append(temp_path)
                # 避免频率限制
                if i < total:
                    time.sleep(0.5)

            print("🔗 正在合并音频...")
            merge_audio_files(temp_files, output_path)
        finally:
            for f in temp_files:
                Path(f).unlink(missing_ok=True)

    return output_path


def main():
    # 检查是否是 clone 命令
    if len(sys.argv) > 1 and sys.argv[1] == "clone":
        parser = argparse.ArgumentParser(description="MiniMax 声音克隆")
        parser.add_argument("command")  # "clone"
        parser.add_argument("audio_file", help="参考音频文件路径（10秒-5分钟）")
        parser.add_argument("--voice-id", required=True, help="自定义语音 ID（至少8字符，字母开头）")
        args = parser.parse_args()

        api_key = get_api_key()
        try:
            clone_voice(args.audio_file, args.voice_id, api_key)
        except Exception as e:
            print(f"❌ 克隆失败: {e}")
            sys.exit(1)
    else:
        parser = argparse.ArgumentParser(
            description="MiniMax Speech-02 语音生成",
            usage="%(prog)s <input.txt> <output_dir> [--voice VOICE] [--speed SPEED] [--emotion EMOTION]",
        )
        parser.add_argument("input_text", help="纯文本文件路径")
        parser.add_argument("output_dir", help="输出目录")
        parser.add_argument("--voice", default=DEFAULT_VOICE, help=f"语音 ID（默认: {DEFAULT_VOICE}）")
        parser.add_argument("--model", default=DEFAULT_MODEL, help=f"模型（默认: {DEFAULT_MODEL}）")
        parser.add_argument("--speed", type=float, default=1.0, help="语速（默认: 1.0）")
        parser.add_argument("--emotion", default="auto", help="情绪（auto/happy/sad/calm，默认: auto）")
        args = parser.parse_args()

        api_key = get_api_key()

        if not Path(args.input_text).exists():
            print(f"❌ 找不到输入文件: {args.input_text}")
            sys.exit(1)

        try:
            output_path = generate_tts(
                args.input_text, args.output_dir,
                args.voice, api_key,
                args.model, args.speed, args.emotion,
            )
            size_mb = Path(output_path).stat().st_size / (1024 * 1024)
            print(f"✅ 语音已生成: {output_path} ({size_mb:.1f} MB)")
        except Exception as e:
            print(f"❌ 错误: {e}")
            sys.exit(1)


if __name__ == "__main__":
    main()
