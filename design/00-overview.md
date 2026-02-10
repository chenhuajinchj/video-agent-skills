# 认知成长视频制作流程 - 整体概览

## 项目目标

创建一套模块化的 Claude Code Skills，用于自动化「认知成长/个人成长」类视频的前期制作流程，最终输出 DaVinci Resolve 可导入的时间轴文件和所有素材。

## 视频规格

- 时长：8-15 分钟
- 风格：口播配画面，案例驱动
- 平台：抖音、TikTok、小红书
- 分辨率：16:9，1920x1080，30fps
- 要求：每个观点必须有案例背书

## 模块架构

```
┌─────────────────────────────────────────────────────────────┐
│                      video-pipeline（主控）                   │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 01-script    │→ │ 02-audio     │→ │ 03-visual    │       │
│  │ generator    │  │ producer     │  │ generator    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         ↓                                    ↓              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ 04-timeline  │← │ 05-material  │  │ 06-content   │       │
│  │ builder      │  │ collector    │  │ organizer    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         ↓                                                   │
│  ┌──────────────┐                                           │
│  │ 07-publish   │                                           │
│  │ preparer     │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
```

## 开发顺序

| 优先级 | 模块 | 文档 | 原因 |
|--------|------|------|------|
| P0-1 | script-generator | 01 | 最独立，可单独测试 |
| P0-2 | audio-producer | 02 | 依赖 script.md |
| P0-3 | visual-generator | 03 | 依赖 script.md + subtitles.srt |
| P0-4 | timeline-builder | 04 | 依赖 visual-timeline.json |
| P1-1 | material-collector | 05 | 素材搜集 |
| P1-2 | content-organizer | 06 | NotebookLM 整理 |
| P1-3 | publish-preparer | 07 | 发布准备 |
| P2 | pipeline | 08 | 串联所有模块 |

## 项目目录结构

```
project-name/
├── materials/                 # 模块 5 输出
│   ├── sources.json
│   ├── articles/
│   └── transcripts/
├── outline.md                 # 模块 6 输出
├── script.md                  # 模块 1 输出
├── audio/                     # 模块 2 输出
│   ├── voiceover.mp3
│   └── subtitles.srt
├── visuals/                   # 模块 3 输出
│   ├── 001_xxx.png
│   └── 002_xxx.mp4
├── visual-timeline.json       # 模块 3 输出
├── timeline.fcpxml            # 模块 4 输出
├── publish/                   # 模块 7 输出
│   ├── thumbnail.png
│   ├── metadata.json
│   └── sources.md
└── project.json               # 项目状态
```

## 标准文件格式

### project.json

```json
{
  "name": "project-slug",
  "created_at": "2026-01-29T10:00:00Z",
  "topic": "视频主题",
  "status": {
    "script-generator": "completed|in-progress|pending",
    "audio-producer": "pending",
    "visual-generator": "pending",
    "timeline-builder": "pending"
  },
  "checkpoints": {
    "outline_confirmed": false,
    "script_confirmed": false,
    "visuals_confirmed": false
  }
}
```

### 检查点说明

| 检查点 | 位置 | 说明 |
|--------|------|------|
| 大纲确认 | content-organizer 后 | 确认论点结构 |
| 逐字稿确认 | script-generator 后 | 确认文案内容 |
| 素材预览 | visual-generator 后 | 确认画面素材 |

## 核心设计原则

1. **模块化**：每个模块独立，可单独使用
2. **标准接口**：模块间通过标准文件格式通信
3. **自由组合**：可跳过、替换、单独调用任意模块
4. **半自动化**：自动化繁琐工作，保留人工精修空间
