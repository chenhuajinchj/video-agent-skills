#!/usr/bin/env python3
"""
合成视频脚本：将图片素材 + 音频 + 字幕合成为 MP4 视频
"""
import json
import os
import subprocess
import sys

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG = "/Users/chenhuajin/bin/ffmpeg"
OUTPUT = os.path.join(PROJECT_DIR, "output.mp4")

# 视频参数
WIDTH = 1920
HEIGHT = 1080
FPS = 30


def load_timeline():
    path = os.path.join(PROJECT_DIR, "visuals", "visual-timeline.json")
    with open(path, "r") as f:
        data = json.load(f)
    return data["visuals"]


def fix_timeline(visuals):
    """修复时间线中的异常值（负数duration等），确保连续"""
    fixed = []
    for i, v in enumerate(visuals):
        entry = dict(v)
        # 用上一个的 end_time 作为当前 start_time（确保连续）
        if i > 0:
            entry["start_time"] = fixed[i - 1]["end_time"]

        # 如果 end_time <= start_time，用下一个的 start_time 或估算
        if entry["end_time"] <= entry["start_time"]:
            if i + 1 < len(visuals) and visuals[i + 1]["start_time"] > 0:
                entry["end_time"] = visuals[i + 1]["start_time"]
            else:
                # 给一个合理的默认时长
                entry["end_time"] = entry["start_time"] + 10.0

        entry["duration"] = entry["end_time"] - entry["start_time"]
        fixed.append(entry)
    return fixed


def resolve_image(v):
    """找到实际存在的图片文件，缺失的用占位"""
    # visual-timeline.json 中的 file 字段是 "visuals/001_xxx.png"
    # 实际路径是 PROJECT_DIR/visuals/visuals/001_xxx.png
    filename = os.path.basename(v["file"])
    img_path = os.path.join(PROJECT_DIR, "visuals", "visuals", filename)
    if os.path.exists(img_path):
        return img_path
    return None


def main():
    print("=== 视频合成脚本 ===")
    print(f"项目目录: {PROJECT_DIR}")

    visuals = load_timeline()
    visuals = fix_timeline(visuals)

    audio_path = os.path.join(PROJECT_DIR, "audio", "voiceover.mp3")
    srt_path = os.path.join(PROJECT_DIR, "audio", "subtitles.srt")

    if not os.path.exists(audio_path):
        print("错误: 找不到音频文件")
        sys.exit(1)

    # 找出所有可用的图片，缺失的用前一张替代
    segments = []
    last_good_img = None
    for v in visuals:
        img = resolve_image(v)
        if img:
            last_good_img = img
        else:
            img = last_good_img
            print(f"  警告: {v['id']} 图片缺失，使用替代图片")

        if img is None:
            print(f"  错误: {v['id']} 无可用图片，跳过")
            continue

        segments.append({
            "image": img,
            "start": v["start_time"],
            "end": v["end_time"],
            "duration": v["duration"],
            "id": v["id"],
        })

    print(f"\n共 {len(segments)} 个片段")
    total_dur = segments[-1]["end"] if segments else 0
    print(f"总时长: {total_dur:.1f}s")

    # 方案：用 ffmpeg concat demuxer
    # 先把每张图片转成对应时长的视频片段，再拼接

    temp_dir = os.path.join(PROJECT_DIR, "_temp_compose")
    os.makedirs(temp_dir, exist_ok=True)

    segment_files = []
    for i, seg in enumerate(segments):
        out_seg = os.path.join(temp_dir, f"seg_{i:03d}.mp4")
        segment_files.append(out_seg)

        if os.path.exists(out_seg):
            print(f"  [{i+1}/{len(segments)}] {seg['id']} 已存在，跳过")
            continue

        dur = seg["duration"]
        print(f"  [{i+1}/{len(segments)}] {seg['id']} ({dur:.1f}s)")

        # 用 ffmpeg 将静态图片转为视频片段
        cmd = [
            FFMPEG, "-y",
            "-loop", "1",
            "-i", seg["image"],
            "-t", f"{dur:.3f}",
            "-vf", f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=decrease,"
                   f"pad={WIDTH}:{HEIGHT}:(ow-iw)/2:(oh-ih)/2:black",
            "-c:v", "libx264",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-r", str(FPS),
            out_seg,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"    错误: {result.stderr[-200:]}")
            sys.exit(1)

    # 生成 concat 列表
    concat_list = os.path.join(temp_dir, "concat.txt")
    with open(concat_list, "w") as f:
        for sf in segment_files:
            f.write(f"file '{sf}'\n")

    print("\n拼接视频片段...")
    concat_out = os.path.join(temp_dir, "video_only.mp4")
    cmd = [
        FFMPEG, "-y",
        "-f", "concat", "-safe", "0",
        "-i", concat_list,
        "-c", "copy",
        concat_out,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

    # 合并音频
    print("合并音频...")
    with_audio = os.path.join(temp_dir, "with_audio.mp4")
    cmd = [
        FFMPEG, "-y",
        "-i", concat_out,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        with_audio,
    ]
    subprocess.run(cmd, capture_output=True, text=True, check=True)

    # 烧录字幕
    print("烧录字幕...")
    if os.path.exists(srt_path):
        # ffmpeg subtitles filter 需要转义路径中的特殊字符
        srt_escaped = srt_path.replace("'", "'\\''").replace(":", "\\:")
        cmd = [
            FFMPEG, "-y",
            "-i", with_audio,
            "-vf", f"subtitles='{srt_escaped}':force_style="
                   f"'FontName=PingFang SC,FontSize=22,PrimaryColour=&H00FFFFFF,"
                   f"OutlineColour=&H00000000,Outline=2,Shadow=1,MarginV=40'",
            "-c:v", "libx264",
            "-preset", "fast",
            "-c:a", "copy",
            OUTPUT,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"字幕烧录失败，输出无字幕版本: {result.stderr[-300:]}")
            # fallback: 无字幕
            subprocess.run(["cp", with_audio, OUTPUT], check=True)
    else:
        subprocess.run(["cp", with_audio, OUTPUT], check=True)

    # 清理临时文件
    print("清理临时文件...")
    import shutil
    shutil.rmtree(temp_dir, ignore_errors=True)

    size_mb = os.path.getsize(OUTPUT) / 1024 / 1024
    print(f"\n✅ 视频合成完成!")
    print(f"   输出: {OUTPUT}")
    print(f"   大小: {size_mb:.1f} MB")


if __name__ == "__main__":
    main()
