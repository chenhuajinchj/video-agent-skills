---
name: video-agent-storyboarder
description: >
  视频团队的分镜师。将编剧的逐字稿拆解为逐句分镜表，为每句话设计具体的画面镜头。
  通过 Python 脚本调用 Gemini Flash API 批量生成分镜，低成本高效率。
  产出 storyboard.json（结构化数据）+ storyboard.md（可读版本）。
  当收到"生成分镜表""设计画面""拆分镜头"时触发，
  或由制片人（producer）调度时自动触发。
---

# video-agent-storyboarder（分镜师）

## 职责边界

分镜师是文字世界和画面世界的桥梁。通过 Gemini Flash API 自动生成分镜：
- ✅ 调用 `generate_storyboard.py` 脚本自动拆稿和设计画面
- ✅ 审核生成的分镜质量（格式、覆盖度、节奏）
- ✅ 必要时手动调整个别镜头
- ❌ 写逐字稿（编剧负责）
- ❌ 搜索下载素材文件（美术负责）
- ❌ 构建时间轴（剪辑师负责）

## 输入 → 输出

- 输入：`script.md`（编剧产出的逐字稿）
- 输出：`storyboard.json`（结构化数据）+ `storyboard.md`（可读版本）

## 执行方式

### 运行脚本

```bash
python scripts/generate_storyboard.py <project_dir> [--style <风格>] [--duration <时长>]
```

参数：
- `project_dir` — 项目目录（包含 script.md）
- `--style` — 视频风格描述（默认："AI科技/知识分享"）
- `--duration` — 目标时长（默认："6-10分钟"）

脚本会：
1. 读取 `script.md`
2. 用 prompt 模板 + 变量替换构建 prompt
3. 调用 Gemini Flash API（`gemini-2.5-flash`，低成本纯文本模型）
4. 解析 JSON 响应
5. 输出 `storyboard.json` + `storyboard.md`
6. 失败自动重试 1 次

## storyboard.json 格式

```json
[
  {
    "shot_number": 1,
    "time_range": "0:00-0:04",
    "script_text": "你有没有想过一个问题",
    "asset_type": "场景",
    "image_prompt": "A person scrolling through a phone with countless notification pop-ups flooding the screen, warm office lighting, close-up shot",
    "mood": "焦虑、快切",
    "is_post_production": false
  }
]
```

## storyboard.md 格式

```markdown
# 分镜表 — 视频标题

> 总镜头数：XX 个

---

| 镜头 | 时间 | 对应逐字稿 | 素材类型 | 图片生成 Prompt | 情绪/节奏 | 后期 |
|------|------|-----------|---------|----------------|----------|------|
| 001 | 0:00-0:04 | 你有没有想过一个问题 | 场景 | A person scrolling... | 焦虑、快切 | |
```

## 核心规则

### 素材类型分类

| 类型 | 说明 | 后期制作 |
|------|------|---------|
| 场景 | 实拍或 AI 生成的场景画面 | 否 |
| 人物 | 提到的人物形象 | 否 |
| 书籍 | 提到的书籍/论文 | 否 |
| 数据 | 数据图表、统计动画 | ✅ 是 |
| 文字 | 关键概念/金句文字排版 | ✅ 是 |
| 对比 | 前后对比、A vs B | 否 |
| 分屏 | 多画面同时展示 | ✅ 是 |
| 隐喻 | 视觉比喻/象征 | 否 |

### 镜头时长

- 标准节奏：3-5 秒/镜头
- 快节奏段落（开头钩子、数据冲击、情绪高潮）：2-3 秒/镜头
- 慢节奏段落（故事展开、情感共鸣、结尾沉淀）：5-8 秒/镜头
- 绝对上限：单镜头不超过 10 秒

### image_prompt 规则

- 必须用英文
- 描述具体、可视化的画面，直接给 Nano Banana（Gemini Image API）使用
- 包含画面构图、光线、色调、氛围
- 15-50 个英文单词

### 情绪标注

常用情绪词：
- 紧张、焦虑、压迫、冲击（问题呈现）
- 权威、可信、平稳（引用专家/数据）
- 共鸣、温暖、日常（贴近观众）
- 震惊、醒悟、反思（关键转折）
- 希望、力量、行动（解决方案和结尾）
- 讽刺、荒诞、反差（揭示问题本质）

## 质量检查清单

脚本生成后，人工或 Claude 审核以下项目：

#### 镜头检查
- [ ] 镜头编号从 1 开始且连续
- [ ] 每个镜头 2-10 秒，平均 4-5 秒
- [ ] 总镜头时长之和 ≈ 视频总时长（±5 秒）
- [ ] 无连续 3 个以上同类型素材

#### 覆盖检查
- [ ] 逐字稿中每句话都有对应镜头
- [ ] 所有提到的人名都有对应镜头
- [ ] 所有提到的书籍都有对应镜头
- [ ] 所有数据/统计都有数据动效镜头（is_post_production: true）

#### Prompt 检查
- [ ] 全部为英文
- [ ] 画面描述具体可生成（非抽象概念）
- [ ] 人物和书籍描述准确

#### 情绪曲线检查
- [ ] 开头有紧张/好奇感
- [ ] 中间有起伏
- [ ] 关键转折处有情绪变化
- [ ] 结尾有收束感

## Prompt 模板

模板文件位于 `prompts/storyboard_prompt.txt`，包含：
- 角色设定和任务描述
- 模板变量：`{script_content}`, `{video_style}`, `{total_duration}`
- 输出格式规范（JSON 数组）
- 字段说明和规则

## API 配置

| 环境变量 | 用途 |
|----------|------|
| GEMINI_API_KEY | Gemini Flash API 调用 |

## 依赖

- Python 3.10+
- 标准库：json, pathlib, argparse, urllib
- Gemini API 密钥

## 脚本文件

- `scripts/generate_storyboard.py` — 分镜生成主脚本
- `prompts/storyboard_prompt.txt` — Prompt 模板
