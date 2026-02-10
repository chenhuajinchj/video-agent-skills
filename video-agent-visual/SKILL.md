---
name: video-agent-visual
description: >
  视频团队的美术师（素材总监）。读取分镜表，为每个镜头判断最佳素材获取方式，
  调度搜索、AI 生成、或标记后期制作，最终产出完整的素材目录和视觉时间轴。
  当收到"准备画面素材""获取视觉素材""根据分镜表找素材"时触发，
  或由制片人（producer）调度时自动触发。
---

# video-agent-visual（美术师 / 素材总监）

## 职责边界

美术师是素材总监，负责判断和调度，确保每个镜头都有对应的视觉素材。

- ✅ 读取分镜表，理解每个镜头的素材需求
- ✅ 判断每个镜头的最佳获取方式（搜索 / AI 生成 / 后期制作）
- ✅ 调度素材库搜索（Pexels/Pixabay/网络搜索）
- ✅ 调度 AI 图片生成（Nano Banana Skill）
- ✅ 标记需要剪辑师后期制作的镜头（文字动效、数据动效）
- ✅ 与字幕时间戳对齐，构建视觉时间轴
- ❌ 设计画面内容（分镜师负责）
- ❌ 构建 FCPXML 时间轴（剪辑师负责）

## 输入 → 输出

- 输入：`storyboard.md`（分镜师产出）+ `audio/subtitles.srt`
- 输出：`visuals/*.png` + `visual-timeline.json` + `visual-report.md`

## 核心决策：素材获取路由

美术师对分镜表中的每个镜头，按素材类型判断获取方式：

| 素材类型 | 获取方式 | 工具 | 说明 |
|----------|----------|------|------|
| 人物 | 网络搜索 | Google/Bing 图片搜索 | 搜真实人物照片，用分镜表的搜索关键词 |
| 书籍 | 网络搜索 | Google/Bing 图片搜索 | 搜真实书籍封面 |
| 场景 | 先搜后生 | Pexels → AI 生成 | 先搜素材库，不满意再用 AI 生成 |
| 数据 | 标记后期 | 剪辑师制作 | 数据图表、统计动画由剪辑师后期制作 |
| 文字 | 标记后期 | 剪辑师制作 | 文字动效、金句卡片由剪辑师后期制作 |
| 对比 | AI 生成 | Nano Banana | 对比画面通常搜不到，直接 AI 生成 |
| 分屏 | 标记后期 | 剪辑师制作 | 多画面分屏由剪辑师后期组合 |
| 隐喻 | AI 生成 | Nano Banana | 隐喻类画面搜不到，AI 生成最合适 |

## 执行步骤

### 步骤 1：解析分镜表

读取 `storyboard.md`，提取每个镜头的信息：
- 镜头编号、时间范围
- 对应逐字稿文字
- 素材类型
- 画面描述
- 搜索关键词
- 情绪/节奏

输出中间文件 `shots.json`：

```json
[
  {
    "shot": "001",
    "time_start": "0:00",
    "time_end": "0:02",
    "script_text": "（开场）",
    "asset_type": "场景",
    "description": "手指快速滑动手机屏幕，通知弹窗不断涌出",
    "search_keywords": "phone scrolling notifications fast",
    "mood": "焦虑、快切",
    "acquire_method": "",
    "file": "",
    "status": "pending"
  }
]
```

### 步骤 2：素材路由决策

遍历 `shots.json`，根据素材类型填充 `acquire_method`：

```
for each shot:
    if asset_type in [数据, 文字, 分屏]:
        acquire_method = "post_production"
        status = "marked_for_editor"
    elif asset_type in [人物, 书籍]:
        acquire_method = "web_search"
        status = "ready_to_search"
    elif asset_type in [对比, 隐喻]:
        acquire_method = "ai_generate"
        status = "ready_to_generate"
    elif asset_type == 场景:
        acquire_method = "search_then_generate"
        status = "ready_to_search"
```

### 步骤 3：执行素材获取

#### 3a. 网络搜索类（人物、书籍）

```bash
python scripts/search_web_images.py \
  --keyword "Cal Newport portrait professor" \
  --output visuals/013.png \
  --min-resolution 1920x1080
```

搜索规则：
- 用分镜表中的英文搜索关键词
- 人物照片：优先选半身照或学者照，避免低清或水印图
- 书籍封面：优先选高清正面封面图
- 下载后验证分辨率 ≥ 1920x1080
- 搜索失败则降级为 AI 生成

#### 3b. 素材库搜索类（场景）

```bash
python scripts/search_stock.py \
  --keyword "phone scrolling notifications fast" \
  --source pexels \
  --output visuals/001.png \
  --min-resolution 1920x1080
```

搜索规则：
- 优先 Pexels，fallback 到 Pixabay
- 如果搜索结果与画面描述匹配度低，转为 AI 生成
- 视频素材优先于静态图片（如果素材库支持）

#### 3c. AI 生成类（对比、隐喻、搜索失败的场景）

```bash
# 调用 Nano Banana Skill
python scripts/generate_image.py \
  --prompt "完整的时钟玻璃碎裂的动画效果，象征时间被切碎，暗色背景" \
  --output visuals/025.png \
  --aspect-ratio 16:9 \
  --resolution 2K
```

生成规则：
- Prompt 基于分镜表的"画面描述"字段，必要时补充情绪和色调
- 宽高比统一 16:9
- 默认分辨率 2K，封面图用 4K
- 生成后人工检查质量（记录到 visual-report.md）

#### 3d. 标记后期类（数据、文字、分屏）

不下载任何素材，在 `shots.json` 中标记：

```json
{
  "shot": "006",
  "acquire_method": "post_production",
  "status": "marked_for_editor",
  "editor_note": "黑色背景上浮现问号和'时间不够用？'文字动效"
}
```

剪辑师会根据这些标记在后期制作。

### 步骤 4：时间戳对齐

```bash
python scripts/align_timestamps.py \
  <project>/shots.json \
  <project>/audio/subtitles.srt \
  <project>/visual-timeline.json
```

将每个镜头与字幕时间戳对齐：
- 分镜表的时间是估算值，以实际字幕时间为准
- 对齐逻辑：用"对应逐字稿"字段在字幕中定位精确时间

### 步骤 5：质量检查 & 产出报告

生成 `visual-report.md`：

```markdown
# 素材报告 — 视频标题

## 统计

- 总镜头数：99
- 已获取素材：42（搜索 25 + AI 生成 17）
- 标记后期制作：35（文字 27 + 数据 7 + 分屏 1）
- 搜索失败转 AI：5
- 未解决：0

## 素材获取明细

| 镜头 | 素材类型 | 获取方式 | 状态 | 文件 |
|------|----------|----------|------|------|
| 001 | 场景 | pexels | ✅ | visuals/001.png |
| 006 | 文字 | 后期制作 | 📋 | (剪辑师) |
| 025 | 隐喻 | AI 生成 | ✅ | visuals/025.png |

## 需要人工审核的素材

- 013: Cal Newport 照片 — 请确认肖像权
- 019: Gloria Mark 照片 — 请确认肖像权
```

#### 质量检查清单

- [ ] 所有非后期镜头都有对应的素材文件
- [ ] 素材文件名与镜头编号一致（001.png, 002.png...）
- [ ] 所有素材分辨率 ≥ 1920x1080
- [ ] 宽高比统一为 16:9
- [ ] 人物照片无明显水印
- [ ] AI 生成的图片质量可接受（无明显畸变）
- [ ] visual-timeline.json 时间戳与字幕对齐
- [ ] visual-report.md 已生成且无"未解决"项

## visual-timeline.json 格式

```json
{
  "video_specs": {
    "resolution": "1920x1080",
    "fps": 30,
    "aspect_ratio": "16:9"
  },
  "total_duration": 490.0,
  "visuals": [
    {
      "shot": "001",
      "file": "visuals/001.png",
      "description": "手指快速滑动手机屏幕，通知弹窗不断涌出",
      "start_time": 0.0,
      "end_time": 2.0,
      "duration": 2.0,
      "asset_type": "场景",
      "acquire_method": "pexels",
      "mood": "焦虑、快切"
    },
    {
      "shot": "006",
      "file": null,
      "description": "黑色背景上浮现问号和'时间不够用？'文字动效",
      "start_time": 12.0,
      "end_time": 14.0,
      "duration": 2.0,
      "asset_type": "文字",
      "acquire_method": "post_production",
      "mood": "冲击、停顿",
      "editor_note": "黑色背景上浮现问号和'时间不够用？'文字动效"
    }
  ]
}
```

## API 配置

| 环境变量 | 用途 |
|----------|------|
| PEXELS_API_KEY | Pexels 图片/视频搜索和下载 |
| PIXABAY_API_KEY | Pixabay 图片搜索（备选） |
| GEMINI_API_KEY | Nano Banana AI 图片生成 |

## 依赖

- Python 3 标准库
- Pexels/Pixabay API 密钥
- Gemini API 密钥（用于 AI 图片生成）
- Nano Banana Skill（需提前安装）

## 脚本文件

- `scripts/parse_storyboard.py` — 解析分镜表为 shots.json
- `scripts/search_web_images.py` — 网络搜索人物/书籍图片
- `scripts/search_stock.py` — 素材库搜索场景素材
- `scripts/generate_image.py` — 调用 Nano Banana 生成 AI 图片
- `scripts/align_timestamps.py` — 时间戳对齐
- `scripts/generate_report.py` — 生成素材报告
