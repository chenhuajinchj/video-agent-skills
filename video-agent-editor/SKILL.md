---
name: video-agent-editor
description: >
  视频团队的剪辑师。将音频、视觉素材、字幕合并为完整时间轴，
  通过 DaVinci Resolve Studio Python API 直接导入达芬奇项目。
  同时处理美术师标记的"后期制作"镜头（文字动效、数据动效、分屏）。
  当收到"生成时间轴""导入达芬奇""构建项目"时触发，
  或由制片人（producer）调度时自动触发。
---

# video-agent-editor（剪辑师）

## 职责边界

- ✅ 读取视觉时间轴，将所有素材导入达芬奇
- ✅ 创建多轨时间轴（视频轨、音频轨、字幕轨）
- ✅ 处理"后期制作"标记的镜头（生成文字/数据占位素材）
- ✅ 为静态图片添加 Ken Burns 效果
- ✅ 添加字幕和基础转场
- ❌ 设计画面内容（分镜师负责）
- ❌ 搜索或生成素材（美术师负责）
- ❌ 配音（配音师负责）

## 输入 → 输出

- 输入：
  - `visual-timeline.json`（美术师产出）
  - `audio/voiceover.mp3`
  - `audio/subtitles.srt`
  - `visuals/*.png`（美术师下载/生成的素材）
  - `storyboard.md`（参考，用于后期制作镜头的细节）
- 输出：
  - DaVinci Resolve 项目（通过 API 直接创建）
  - `editor-report.md`（剪辑报告）

## 轨道结构

| 轨道 | 类型 | 内容 |
|------|------|------|
| V1 | 视频 | 图片/视频素材（按 visual-timeline.json 排列） |
| V2 | 视频 | 文字动效占位素材（后期替换） |
| V3 | 视频 | 数据动效/图表占位素材（后期替换） |
| A1 | 音频 | voiceover.mp3 |
| A2 | 音频 | BGM 预留轨（留空） |
| Subtitle | 字幕 | 根据 subtitles.srt 生成 |

## 执行步骤

### 步骤 1：预处理后期制作镜头

读取 visual-timeline.json，找出所有 `acquire_method: "post_production"` 的镜头。
为每个后期镜头生成一个占位素材（纯色背景 + 白色文字说明）。

```bash
python scripts/generate_placeholders.py <project>/visual-timeline.json <project>/visuals/
```

占位素材规则：
- 文字动效（文字）：黑色背景，居中白色文字显示画面描述
- 数据动效（数据）：深蓝背景，白色文字显示"数据图表：" + 描述
- 分屏（分屏）：灰色背景，用线条分割区域，标注各区域内容

占位素材命名：`visuals/placeholder_XXX.png`（XXX 为镜头编号）

这些占位素材的作用是让你在达芬奇里能直接看到每个镜头的位置和内容，后续手动替换为正式的动效。

### 步骤 2：导入达芬奇

达芬奇必须处于运行状态。

```bash
python scripts/import_to_resolve.py <project_dir>
```

脚本执行流程：

```python
import DaVinciResolveScript as dvr_script

# 1. 连接达芬奇
resolve = dvr_script.scriptapp("Resolve")
projectManager = resolve.GetProjectManager()

# 2. 创建项目
project = projectManager.CreateProject("视频标题")
project.SetSetting("timelineFrameRate", "30")
project.SetSetting("timelineResolutionWidth", "1920")
project.SetSetting("timelineResolutionHeight", "1080")

# 3. 导入素材到 Media Pool
mediaPool = project.GetMediaPool()
mediaStorage = resolve.GetMediaStorage()

# 导入所有视觉素材
visual_clips = mediaStorage.AddItemsToMediaPool("/path/to/visuals/")

# 导入音频
audio_clips = mediaStorage.AddItemsToMediaPool("/path/to/audio/voiceover.mp3")

# 4. 创建时间轴
timeline = mediaPool.CreateEmptyTimeline("主时间轴")

# 5. 按 visual-timeline.json 顺序添加素材到时间轴
for visual in timeline_data["visuals"]:
    clip_info = {
        "mediaPoolItem": find_clip_by_name(visual["file"]),
        "trackIndex": get_track_index(visual),  # V1/V2/V3
        "startFrame": time_to_frame(visual["start_time"]),
        "endFrame": time_to_frame(visual["end_time"])
    }
    mediaPool.AppendToTimeline([clip_info])

# 6. 添加音频到 A1 轨
# 7. 添加字幕
```

### 步骤 3：轨道分配逻辑

根据素材的获取方式决定放到哪个轨道：

```
for each visual in timeline_data["visuals"]:
    if acquire_method in ["pexels", "pixabay", "web_search", "ai_generate"]:
        → V1（正式素材轨）
    elif asset_type == "文字":
        → V2（文字动效占位轨）
    elif asset_type in ["数据", "分屏"]:
        → V3（数据/图表占位轨）
```

这样你在达芬奇里一眼就能看出哪些镜头是正式素材，哪些需要后期替换。

### 步骤 4：图片处理

静态图片在时间轴上的处理：
- 默认添加 Ken Burns 效果（缓慢缩放 ZoomX/ZoomY 从 1.0 到 1.05）
- 持续时间由 visual-timeline.json 的 duration 字段决定
- 图片自动缩放适配 1920x1080（通过 SetProperty ZoomX/ZoomY）

```python
# Ken Burns 效果设置
clip.SetProperty("ZoomX", 1.0)   # 起始缩放
clip.SetProperty("ZoomY", 1.0)
# 注意：达芬奇 API 不直接支持关键帧动画
# Ken Burns 需要通过 Fusion 页面的 Transform 节点实现
# 或在导入后由用户手动添加
```

如果达芬奇 API 无法直接设置关键帧动画，Ken Burns 效果标记在 editor-report.md 中提醒用户手动添加。

### 步骤 5：字幕处理

```bash
python scripts/import_subtitles.py <project_dir>
```

字幕导入方式：
- 读取 subtitles.srt
- 通过达芬奇 API 创建字幕轨
- 或导入 SRT 文件到字幕轨

字幕样式：
- 字体：PingFang SC
- 大小：48px
- 颜色：白色
- 阴影：黑色，2px 偏移
- 位置：画面底部居中

### 步骤 6：生成剪辑报告

输出 `editor-report.md`：

```markdown
# 剪辑报告 — 视频标题

## 项目信息

- 达芬奇项目名：XXX
- 分辨率：1920x1080
- 帧率：30fps
- 总时长：8 分 10 秒

## 轨道统计

| 轨道 | 片段数 | 说明 |
|------|--------|------|
| V1 | 42 | 正式素材 |
| V2 | 27 | 文字动效占位（需替换） |
| V3 | 8 | 数据/图表占位（需替换） |
| A1 | 1 | 配音 |
| A2 | 0 | BGM（待添加） |
| Subtitle | 108 条 | 字幕 |

## 需要手动完成的工作

### 文字动效（V2 轨，27 个镜头）
- 镜头 006：黑色背景上浮现问号和"时间不够用？"文字
- 镜头 008："工具""方法论""意志力"三个词依次出现又被划掉
- ...

### 数据动效（V3 轨，7 个镜头）
- 镜头 020：数据可视化动画，"每 11 分钟被打断一次"统计图
- 镜头 021：时间轴动画，11 分钟标记被打断，25 分钟恢复区间
- ...

### Ken Burns 效果
- V1 轨所有静态图片需添加缓慢缩放动画

### BGM
- A2 轨预留，需手动添加背景音乐
```

### 步骤 7：质量检查

- [ ] 达芬奇项目已创建且可打开
- [ ] V1 轨素材顺序与 visual-timeline.json 一致
- [ ] V2/V3 轨占位素材已就位
- [ ] A1 轨音频已导入且时长正确
- [ ] 字幕已导入且与音频同步
- [ ] editor-report.md 已生成
- [ ] 所有需要手动完成的工作已列出

## 达芬奇环境配置

### macOS 环境变量

```bash
export RESOLVE_SCRIPT_API="/Library/Application Support/Blackmagic Design/DaVinci Resolve/Developer/Scripting/"
export RESOLVE_SCRIPT_LIB="/Applications/DaVinci Resolve/DaVinci Resolve.app/Contents/Libraries/Fusion/fusionscript.so"
export PYTHONPATH="$PYTHONPATH:$RESOLVE_SCRIPT_API/Modules/"
```

### 前置条件

- DaVinci Resolve Studio 必须处于运行状态
- Resolve Preferences 中需开启外部脚本访问权限：
  Preferences → System → General → External scripting using: 选择 "Local"

## 视频规格

| 参数 | 值 |
|------|-----|
| 分辨率 | 1920x1080 |
| 帧率 | 30fps |
| 宽高比 | 16:9 |

## 依赖

- Python 3
- DaVinciResolveScript 模块（达芬奇自带）
- ffprobe（获取音频时长）
- Pillow（生成占位素材）

## 脚本文件

- `scripts/generate_placeholders.py` — 生成后期制作占位素材
- `scripts/import_to_resolve.py` — 达芬奇 API 导入主脚本
- `scripts/import_subtitles.py` — 字幕导入
