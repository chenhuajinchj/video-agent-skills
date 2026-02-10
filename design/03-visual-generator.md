# 模块 3: video-visual-generator

## 功能概述

生成或搜索视觉素材，构建视觉时间轴，是连接文案和剪辑的关键模块。

## 触发条件

- 「生成视觉素材」
- 「准备画面素材」
- 「根据逐字稿生成配图」

## 目录结构

```
video-visual-generator/
├── SKILL.md
└── scripts/
    ├── parse_visual_markers.py   # 解析画面标注
    ├── match_timestamps.py       # 匹配时间戳
    └── download_visuals.py       # 下载素材
```

## 输入文件

### script.md

带 `[画面#XXX：描述]` 标注的逐字稿

### audio/subtitles.srt

字幕文件，用于获取时间戳

## 输出文件

### visuals/ 目录

按编号命名的素材文件：

```
visuals/
├── 001_buffett-young.png
├── 002_wall-street.mp4
├── 003_omaha-street.png
└── ...
```

### visual-timeline.json

```json
{
  "video_specs": {
    "resolution": "1920x1080",
    "fps": 30,
    "aspect_ratio": "16:9"
  },
  "total_duration": 600.5,
  "visuals": [
    {
      "index": 1,
      "id": "画面#001",
      "file": "visuals/001_buffett-young.png",
      "description": "巴菲特年轻时在办公室看报纸的老照片",
      "start_time": 0.0,
      "end_time": 4.2,
      "duration": 4.2,
      "type": "image",
      "source": "ai-generated"
    },
    {
      "index": 2,
      "id": "画面#002",
      "file": "visuals/002_wall-street.mp4",
      "description": "纽约华尔街街景，车水马龙",
      "start_time": 4.2,
      "end_time": 9.8,
      "duration": 5.6,
      "type": "video",
      "source": "pexels"
    }
  ]
}
```

## 时间计算规则

| 字段 | 计算方式 |
|------|----------|
| start_time | 该画面对应文字在字幕中的开始时间 |
| end_time | 下一个画面的 start_time |
| 最后一个 end_time | 音频总时长 |
| 无标注段落 | 延续上一个画面 |

## 处理流程

1. **解析画面标注**
   - 从 script.md 提取所有 `[画面#XXX：描述]`
   - 建立编号 → 描述的映射

2. **匹配时间戳**
   - 解析 subtitles.srt 获取每句话的时间
   - 将画面标注与对应文字的时间戳关联

3. **生成素材计划**
   - 为每个画面选择素材来源
   - 展示计划，等待用户确认

4. **获取素材**
   - AI 生图 / 素材库下载 / YouTube 片段
   - 按编号命名保存到 visuals/

5. **构建时间轴**
   - 生成 visual-timeline.json

## 素材来源优先级

| 优先级 | 来源 | 适用场景 |
|--------|------|----------|
| 1 | Pexels/Pixabay | 通用场景、风景、城市 |
| 2 | AI 生图 | 特定人物、历史场景 |
| 3 | YouTube 片段 | 新闻画面、演讲片段 |

## 检查点

### 生成前

展示「素材计划」：
```
画面#001: AI 生图 - 巴菲特年轻时...
画面#002: Pexels 搜索 - Wall Street traffic
画面#003: Pexels 搜索 - small town street
...
确认开始生成？[Y/n]
```

### 生成后

展示素材预览，用户可标记需要替换的画面。

## 依赖的外部 Skill

| Skill | 用途 |
|-------|------|
| document-illustrator-skill | AI 生图 |
| media-downloader | Pexels/Pixabay 素材 |
| yt-dlp | YouTube 片段下载 |

## 使用示例

```
用户：根据逐字稿生成配图
→ 解析 script.md 中的画面标注
→ 读取 subtitles.srt 获取时间戳
→ 展示素材计划，等待确认
→ 生成/下载素材到 visuals/
→ 输出 visual-timeline.json
→ 展示预览
```
