---
name: video-agent-jianying-editor
description: >
  视频团队的剪映剪辑师。将音频、视觉素材、字幕合并为完整时间轴，
  通过 VectCutAPI 生成剪映/CapCut 可直接导入的草稿项目。
  与达芬奇剪辑师（video-agent-editor）并行工作，共享同一套输入文件，
  由制片人（producer）决定调度哪个剪辑师。
  当收到"导出剪映""生成剪映草稿""构建剪映项目"时触发，
  或由制片人调度时自动触发。
---

# video-agent-jianying-editor（剪映剪辑师）

## 与达芬奇剪辑师的关系

两个剪辑师共享完全相同的输入文件，区别仅在输出目标：

| 维度 | 达芬奇剪辑师 (editor) | 剪映剪辑师 (jianying-editor) |
|------|----------------------|------------------------------|
| 输入 | visual-timeline.json + 音频 + 素材 | 相同 |
| 输出 | DaVinci Resolve 项目（API 直连） | 剪映 draft 文件夹（离线生成） |
| 依赖 | 达芬奇 Studio 必须运行 | VectCutAPI 服务必须运行 |
| 导入方式 | 自动创建到达芬奇 | 复制 draft 到剪映目录，重启剪映 |

制片人在调度时通过参数 `output_target` 指定：
- `output_target: "resolve"` → 调达芬奇剪辑师
- `output_target: "jianying"` → 调剪映剪辑师
- `output_target: "both"` → 两个都调，生成两份项目

## 职责边界

- ✅ 读取 visual-timeline.json，通过 VectCutAPI 构建剪映草稿
- ✅ 创建多轨时间轴（视频轨、音频轨、字幕轨）
- ✅ 处理"后期制作"标记的镜头（生成占位素材放入草稿）
- ✅ 为静态图片设置展示时长和基础动画
- ✅ 导入字幕（SRT 格式）
- ✅ 添加基础转场效果
- ❌ 设计画面内容（分镜师负责）
- ❌ 搜索或生成素材（美术师负责）
- ❌ 配音（配音师负责）
- ❌ 视频渲染导出（在剪映中手动完成）

## 输入 → 输出

### 输入（与达芬奇剪辑师完全相同）

- `visual-timeline.json`（美术师产出）
- `audio/voiceover.mp3`
- `audio/subtitles.srt`
- `visuals/*.png`（美术师下载/生成的素材）
- `storyboard.md`（参考，用于后期制作镜头的细节）

### 输出

- `jianying-draft/dfd_<项目名>/` — 剪映草稿文件夹，包含 draft_content.json 和素材引用
- `jianying-editor-report.md` — 剪辑报告（包含导入指南和待手动完成的任务清单）

## 轨道结构

| 轨道 | 类型 | 内容 |
|------|------|------|
| 主视频轨 | 视频 | 图片/视频素材（按 visual-timeline.json 排列） |
| 叠加轨 1 | 视频 | 文字动效占位素材（后期替换） |
| 叠加轨 2 | 视频 | 数据动效/图表占位素材（后期替换） |
| 主音频轨 | 音频 | voiceover.mp3 |
| 音频轨 2 | 音频 | BGM 预留（留空） |
| 字幕轨 | 字幕 | 根据 subtitles.srt 生成 |

## 前置环境

### 1. 安装 VectCutAPI

```bash
git clone https://github.com/sun-guannan/VectCutAPI.git
cd VectCutAPI
python -m venv venv-capcut
source venv-capcut/bin/activate
pip install -r requirements.txt
cp config.json.example config.json
```

### 2. 启动 VectCutAPI 服务

```bash
cd /path/to/VectCutAPI
source venv-capcut/bin/activate
python capcut_server.py
# 服务启动后监听 http://localhost:9001
```

### 3. macOS 剪映草稿目录

剪映专业版（macOS）的草稿目录：

```
/Users/<用户名>/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/
```

如果用户使用 CapCut 国际版：

```
/Users/<用户名>/Movies/CapCut/User Data/Projects/com.lveditor.draft/
```

脚本会自动检测两个路径，优先使用存在的那个。

### 4. 依赖

- Python 3.10+
- VectCutAPI 服务（运行中）
- FFprobe（获取音频/视频时长）
- Pillow（生成占位素材）
- requests（调用 VectCutAPI）

## 执行步骤

### 步骤 1：预处理后期制作镜头

与达芬奇剪辑师共用同一个脚本，生成占位素材。

```bash
python scripts/generate_placeholders.py <project>/visual-timeline.json <project>/visuals/
```

占位素材规则（与达芬奇剪辑师一致）：
- 文字动效：黑色背景 + 白色文字描述
- 数据动效：深蓝背景 + 白色文字标注
- 分屏：灰色背景 + 区域分割线

### 步骤 2：通过 VectCutAPI 构建剪映草稿

```bash
python scripts/import_to_jianying.py <project_dir>
```

脚本执行流程：

```python
import requests
import json
import subprocess
import os

CAPCUT_API = "http://localhost:9001"

# ── 1. 读取项目数据 ──
with open(f"{project_dir}/visual-timeline.json") as f:
    timeline = json.load(f)

# 获取语音时长
result = subprocess.run(
    ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
     "-of", "csv=p=0", f"{project_dir}/audio/voiceover.mp3"],
    capture_output=True, text=True
)
total_duration = float(result.stdout.strip())

# ── 2. 创建草稿 ──
resp = requests.post(f"{CAPCUT_API}/create_draft", json={
    "width": 1920,
    "height": 1080
})
draft_id = resp.json()["draft_id"]

# ── 3. 添加语音到主音频轨 ──
voiceover_path = os.path.abspath(f"{project_dir}/audio/voiceover.mp3")
requests.post(f"{CAPCUT_API}/add_audio", json={
    "draft_id": draft_id,
    "audio_url": voiceover_path,
    "start": 0,
    "end": total_duration,
    "volume": 1.0
})

# ── 4. 按 visual-timeline.json 添加视觉素材 ──
for shot in timeline["shots"]:
    shot_number = shot["shot_number"]
    start_time = shot["start_time"]
    end_time = shot["end_time"]
    acquire_method = shot.get("acquire_method", "search")

    # 确定素材文件路径
    if acquire_method == "post_production":
        img_path = os.path.abspath(
            f"{project_dir}/visuals/placeholder_{shot_number:03d}.png"
        )
    else:
        img_path = os.path.abspath(
            f"{project_dir}/visuals/{shot_number:03d}.png"
        )

    if not os.path.exists(img_path):
        print(f"⚠️  镜头 {shot_number} 素材缺失: {img_path}")
        continue

    # 添加到主视频轨
    requests.post(f"{CAPCUT_API}/add_video", json={
        "draft_id": draft_id,
        "video_url": img_path,
        "start": start_time,
        "end": end_time,
        "transition": "fade_in"
    })

# ── 5. 导入字幕 ──
srt_path = os.path.abspath(f"{project_dir}/audio/subtitles.srt")
if os.path.exists(srt_path):
    subtitles = parse_srt(srt_path)
    for sub in subtitles:
        requests.post(f"{CAPCUT_API}/add_subtitle", json={
            "draft_id": draft_id,
            "text": sub["text"],
            "start": sub["start"],
            "end": sub["end"],
            "font_size": 36,
            "font_color": "#FFFFFF",
            "shadow_enabled": True,
            "background_alpha": 0.6
        })

# ── 6. 保存草稿 ──
resp = requests.post(f"{CAPCUT_API}/save_draft", json={
    "draft_id": draft_id
})
draft_folder = resp.json()["local_path"]
print(f"✅ 草稿已保存: {draft_folder}")
```

### 步骤 3：部署草稿到剪映

脚本保存草稿后，自动将 `dfd_xxx` 文件夹复制到剪映的 drafts 目录：

```python
import shutil

# 检测剪映草稿目录
jianying_paths = [
    os.path.expanduser(
        "~/Movies/JianyingPro/User Data/Projects/com.lveditor.draft/"
    ),
    os.path.expanduser(
        "~/Movies/CapCut/User Data/Projects/com.lveditor.draft/"
    ),
]

target_dir = None
for p in jianying_paths:
    if os.path.exists(p):
        target_dir = p
        break

if target_dir:
    dest = os.path.join(target_dir, os.path.basename(draft_folder))
    shutil.copytree(draft_folder, dest)
    print(f"✅ 草稿已复制到剪映目录: {dest}")
    print("⚠️  请重启剪映或切换一下草稿列表即可看到新项目")
else:
    print("⚠️  未找到剪映草稿目录，请手动复制:")
    print(f"   {draft_folder}")
    print("   → 到剪映的 Projects/com.lveditor.draft/ 目录下")
```

### 步骤 4：生成剪辑报告

输出 `jianying-editor-report.md`，内容包括：

```markdown
# 剪映剪辑报告

## 项目信息
- 草稿名称: dfd_xxx
- 总时长: X 分 X 秒
- 镜头数: N 个
- 分辨率: 1920x1080

## 草稿位置
- VectCutAPI 输出: /path/to/dfd_xxx/
- 剪映目录: ~/Movies/JianyingPro/.../dfd_xxx/

## 导入指南
1. 确保剪映已关闭
2. 草稿已自动复制到剪映目录（如果检测到）
3. 打开剪映，在草稿列表中找到项目
4. 如果看不到，请重启剪映

## 待手动完成的工作

### 后期制作镜头（需替换占位素材）
- [ ] 镜头 003: 文字动效 — "..."
- [ ] 镜头 007: 数据图表 — "..."

### BGM
- [ ] 添加背景音乐到音频轨 2

### 字幕样式
- [ ] 调整字幕字体和位置（当前为默认白色 36px）

### 转场
- [ ] 检查各镜头间的转场效果，按需调整

### 最终导出
- [ ] 在剪映中预览并导出最终视频
```

## VectCutAPI 接口速查

| 接口 | 用途 | 关键参数 |
|------|------|----------|
| POST /create_draft | 创建新草稿 | width, height |
| POST /add_video | 添加视频/图片到视频轨 | draft_id, video_url, start, end, transition, volume |
| POST /add_audio | 添加音频 | draft_id, audio_url, start, end, volume |
| POST /add_text | 添加文字 | draft_id, text, start, end, font_size, font_color, shadow_enabled |
| POST /add_subtitle | 添加字幕 | draft_id, text, start, end, font_size, font_color |
| POST /add_image | 添加图片叠加 | draft_id, image_url, start, end |
| POST /add_video_keyframe | 添加关键帧动画 | draft_id, track_name, property_types, times, values |
| POST /add_effect | 添加特效 | draft_id, effect_name, start, end |
| POST /add_sticker | 添加贴纸 | draft_id, sticker_url, start, end |
| POST /save_draft | 保存草稿到本地 | draft_id |
| POST /get_duration | 获取媒体时长 | media_url |

## MCP 集成（可选）

如果在 Claude Code 中使用，可以配置 VectCutAPI 的 MCP 服务器：

```json
{
  "mcpServers": {
    "capcut-api": {
      "command": "python3",
      "args": ["mcp_server.py"],
      "cwd": "/path/to/VectCutAPI",
      "env": {
        "PYTHONPATH": "/path/to/VectCutAPI",
        "DEBUG": "0"
      }
    }
  }
}
```

配置后 Claude Code 可以直接调用 VectCutAPI 的工具，无需通过 HTTP。

## 注意事项

- VectCutAPI 服务必须在运行状态（`python capcut_server.py`），否则脚本无法工作
- 素材路径必须使用绝对路径，VectCutAPI 需要能访问到文件
- 剪映版本兼容性：VectCutAPI 生成的草稿格式兼容剪映专业版和 CapCut 国际版
- 草稿复制到剪映目录后需要重启剪映才能看到
- 如果素材文件很大，save_draft 可能需要较长时间（会复制素材到草稿文件夹内）
- 字幕样式在剪映中可以二次调整，脚本只设置基础样式

## 脚本文件

- `scripts/generate_placeholders.py` — 生成后期制作占位素材（与达芬奇剪辑师共用）
- `scripts/import_to_jianying.py` — VectCutAPI 导入主脚本
- `scripts/parse_srt.py` — SRT 字幕解析工具
- `scripts/deploy_to_jianying.py` — 自动复制草稿到剪映目录
