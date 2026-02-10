#!/usr/bin/env python3
"""
通过 DaVinci Resolve Python API 手动构建时间线。
ImportTimelineFromFile 对 FCPXML 不兼容，改用 API 直接构建。
"""

import sys
import json
from pathlib import Path

sys.path.append("/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/Modules/")
import DaVinciResolveScript as dvr_script

PROJECT_DIR = Path(__file__).resolve().parent
TIMELINE_JSON = PROJECT_DIR / "visual-timeline.json"
AUDIO_FILE = PROJECT_DIR / "audio" / "voiceover.mp3"
VISUALS_DIR = PROJECT_DIR / "visuals" / "visuals"
TIMELINE_NAME = "巴菲特的逆向思维"


def find_visual_file(file_field: str) -> str:
    """根据 JSON 中的 file 字段找到实际文件路径，自动尝试 .png/.jpg 互换"""
    filename = Path(file_field).name
    stem = Path(filename).stem
    candidate = VISUALS_DIR / filename
    if candidate.exists():
        return str(candidate)
    # 尝试替换扩展名（.png <-> .jpg）
    for ext in [".jpg", ".jpeg", ".png"]:
        alt = VISUALS_DIR / (stem + ext)
        if alt.exists():
            return str(alt)
    # 回退到项目目录
    candidate2 = PROJECT_DIR / file_field
    if candidate2.exists():
        return str(candidate2)
    return None


def main():
    resolve = dvr_script.scriptapp("Resolve")
    if not resolve:
        print("❌ 无法连接 DaVinci Resolve")
        sys.exit(1)

    print(f"✅ 已连接 DaVinci Resolve {resolve.GetVersionString()}")

    pm = resolve.GetProjectManager()
    project = pm.GetCurrentProject()
    print(f"📁 当前项目: {project.GetName()}")

    mp = project.GetMediaPool()
    root_folder = mp.GetRootFolder()

    # 读取时间线数据
    data = json.loads(TIMELINE_JSON.read_text(encoding="utf-8"))
    visuals = data["visuals"]
    fps = data["video_specs"]["fps"]

    # 收集所有需要导入的文件
    files_to_import = []
    visual_paths = {}

    for v in visuals:
        path = find_visual_file(v["file"])
        if path:
            files_to_import.append(path)
            visual_paths[v["index"]] = path
        else:
            print(f"  ⚠️ 素材缺失: {v['file']}")

    # 添加音频
    if AUDIO_FILE.exists():
        files_to_import.append(str(AUDIO_FILE))

    # 导入所有媒体到媒体池
    print(f"\n📥 导入 {len(files_to_import)} 个媒体文件...")
    imported = mp.ImportMedia(files_to_import)
    if not imported:
        print("❌ 媒体导入失败")
        sys.exit(1)
    print(f"✅ 成功导入 {len(imported)} 个文件")

    # 建立文件名到 MediaPoolItem 的映射
    clip_map = {}
    for item in imported:
        clip_map[item.GetName()] = item

    # 创建空时间线
    timeline = mp.CreateEmptyTimeline(TIMELINE_NAME)
    if not timeline:
        print("❌ 无法创建时间线")
        sys.exit(1)
    print(f"\n🎬 已创建时间线: {TIMELINE_NAME}")

    # 设置当前时间线
    project.SetCurrentTimeline(timeline)

    # 按顺序添加视觉素材到视频轨
    print("\n📎 添加视觉素材到时间线...")
    added_count = 0
    for v in visuals:
        filename = Path(v["file"]).name
        stem = Path(filename).stem
        clip = clip_map.get(filename)
        # 尝试替换扩展名匹配
        if not clip:
            for ext in [".jpg", ".jpeg", ".png"]:
                clip = clip_map.get(stem + ext)
                if clip:
                    break
        if not clip:
            print(f"  ⚠️ 跳过 {v['id']}: 媒体池中未找到 {filename}")
            continue

        duration_sec = v["end_time"] - v["start_time"]
        duration_frames = int(duration_sec * fps)

        # AppendToTimeline 添加到末尾
        result = mp.AppendToTimeline([{
            "mediaPoolItem": clip,
            "startFrame": 0,
            "endFrame": duration_frames,
        }])

        if result:
            added_count += 1
            print(f"  ✅ {v['id']}: {duration_sec:.1f}s ({duration_frames} frames)")
        else:
            print(f"  ❌ {v['id']}: 添加失败")

    # 添加音频到音频轨
    print("\n🔊 添加音频...")
    audio_clip = clip_map.get("voiceover.mp3")
    if audio_clip:
        result = mp.AppendToTimeline([{
            "mediaPoolItem": audio_clip,
            "startFrame": 0,
            "endFrame": int(data["total_duration"] * fps),
            "trackIndex": 1,
            "mediaType": 2,  # 2 = audio
        }])
        if result:
            print("  ✅ 音频已添加")
        else:
            print("  ❌ 音频添加失败")

    print(f"\n🎉 完成! 共添加 {added_count}/{len(visuals)} 个视觉素材")
    print(f"   视频轨道数: {timeline.GetTrackCount('video')}")
    print(f"   音频轨道数: {timeline.GetTrackCount('audio')}")
    print("\n请在 DaVinci Resolve 中查看时间线。")


if __name__ == "__main__":
    main()
