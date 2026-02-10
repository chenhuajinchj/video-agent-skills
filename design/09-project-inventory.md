# 认知成长视频制作流水线 - 项目文件汇总

> 生成日期：2026-02-06
> 项目路径：`/Users/chenhuajin/CC视频/video-skills/`

## 架构总览

```
素材收集 → 内容整理 → 逐字稿生成 → 音频制作 → 视觉素材 → 时间轴构建 → 发布准备
   05          06          01          02         03          04          07
   ↓           ↓           ↓           ↓          ↓           ↓           ↓
sources.json outline.md script.md  audio/*   visuals/*  timeline.*  metadata.json
```

主控模块 `08-pipeline` 串联以上所有模块，支持 3 个人工检查点和断点恢复。

---

## 一、设计文档（design/）

| 文件 | 用途 |
|------|------|
| `00-overview.md` | 整体架构、模块关系、目录结构、开发优先级 |
| `01-script-generator.md` | 逐字稿生成模块的输入输出、Prompt 模板、质量标准 |
| `02-audio-producer.md` | 音频制作模块设计，支持自录音/Edge-TTS/ElevenLabs 三种模式 |
| `03-visual-generator.md` | 视觉素材生成，支持 Pexels/Pixabay/AI 生图/YouTube 片段 |
| `04-timeline-builder.md` | FCPXML 时间轴构建，V1 视频轨 + A1 语音轨 + A2 BGM 预留 + 字幕轨 |
| `05-material-collector.md` | 网页搜索 + YouTube 字幕抓取，生成结构化素材库 |
| `06-content-organizer.md` | 素材分析、论点提取、结构化大纲生成 |
| `07-publish-preparer.md` | 发布元数据（标题/描述/标签）和引用出处列表 |
| `08-pipeline.md` | 流水线主控设计，模块编排和状态管理 |
| `09-project-inventory.md` | 本文件，项目文件汇总清单 |

---

## 二、核心模块（8 个）

### 模块 01：video-script-generator（逐字稿生成）

**功能**：根据大纲生成带画面标注的逐字稿，支持反常识/故事/问题 3 种开头模式

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | Claude Code Skill 定义，包含完整的生成指令和质量检查清单 |
| `references/script-template.md` | 参考模板 | 逐字稿格式范例 |
| `references/case-sources.md` | 参考数据 | 案例出处格式规范 |

**输入**：`outline.md` → **输出**：`script.md`

---

### 模块 02：video-audio-producer（音频制作）

**功能**：将逐字稿转为语音 + 字幕，支持 3 种 TTS 引擎

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 音频制作流程指令 |
| `scripts/extract_plain_text.py` | Python | 从 `script.md` 提取纯文本（去除画面标注） |
| `scripts/edge_tts_generate.py` | Python | 调用 Edge-TTS 免费生成语音和字幕 |
| `scripts/elevenlabs_tts.py` | Python | 调用 ElevenLabs API 生成高质量语音 |
| `scripts/generate_subtitles.py` | Python | 使用 Whisper 从音频生成 SRT 字幕 |

**输入**：`script.md` → **输出**：`audio/voiceover.mp3` + `audio/subtitles.srt`

---

### 模块 03：video-visual-generator（视觉素材生成）

**功能**：解析画面标注、匹配时间戳、下载配图素材

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 视觉素材生成流程指令 |
| `scripts/parse_visual_markers.py` | Python | 从 `script.md` 解析 `【画面：...】` 标注 |
| `scripts/match_timestamps.py` | Python | 将画面标注与 SRT 字幕时间戳对齐 |
| `scripts/download_visuals.py` | Python | 从 Pexels/Pixabay 下载素材图片 |

**输入**：`script.md` + `subtitles.srt` → **输出**：`visuals/*.jpg` + `visual-timeline.json`

---

### 模块 04：video-timeline-builder（时间轴构建）

**功能**：生成 DaVinci Resolve 可导入的 FCPXML 时间轴

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 时间轴构建流程指令 |
| `scripts/generate_fcpxml.py` | Python | 将 `visual-timeline.json` 转为 FCPXML 格式 |
| `references/fcpxml-format.md` | 参考文档 | FCPXML 1.11 格式规范说明 |

**输入**：`visual-timeline.json` → **输出**：`timeline.fcpxml`

---

### 模块 05：video-material-collector（素材收集）

**功能**：围绕主题搜集网页文章和 YouTube 字幕

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 素材搜集流程指令 |
| `scripts/web_search_collector.py` | Python | 网页文章搜集和保存 |
| `scripts/youtube_transcript_collector.py` | Python | YouTube 视频字幕下载 |
| `scripts/compile_sources.py` | Python | 汇总所有素材生成 `sources.json` 索引 |

**输入**：主题关键词 → **输出**：`materials/sources.json` + `materials/articles/` + `materials/transcripts/`

---

### 模块 06：video-content-organizer（内容整理）

**功能**：分析素材，提取核心论点，生成结构化大纲

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 内容整理和大纲生成指令 |
| `scripts/generate_outline.py` | Python | 大纲 Markdown 模板生成工具 |

**输入**：`materials/` → **输出**：`outline.md`

---

### 模块 07：video-publish-preparer（发布准备）

**功能**：生成各平台发布所需的元数据和引用出处

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 发布准备流程指令 |
| `scripts/generate_metadata.py` | Python | 生成标题、描述、标签等元数据 |
| `scripts/compile_sources_list.py` | Python | 整理引用出处列表 |

**输入**：`script.md` + `materials/` → **输出**：`publish/metadata.json` + `publish/sources.md`

---

### 模块 08：video-pipeline（流水线主控）

**功能**：串联所有模块，管理项目状态和检查点

| 文件 | 类型 | 核心功能 |
|------|------|----------|
| `SKILL.md` | Prompt 模板 | 流水线编排指令，定义模块执行顺序和检查点 |
| `scripts/pipeline_manager.py` | Python | 项目状态管理（读写 `project.json`），支持断点恢复 |

**检查点**：大纲确认 → 逐字稿确认 → 素材预览

---

## 三、测试项目（test-project/）

以「巴菲特的逆向思维」为主题的端到端测试数据：

| 文件 | 类型 | 说明 |
|------|------|------|
| `project.json` | JSON | 项目状态配置 |
| `outline.md` | Markdown | 生成的视频大纲 |
| `script.md` | Markdown | 生成的逐字稿（含画面标注） |
| `script-plain.txt` | Text | 纯文本逐字稿（TTS 输入） |
| `markers.json` | JSON | 解析出的画面标注列表 |
| `markers-timed.json` | JSON | 带时间戳的画面标注 |
| `visual-timeline.json` | JSON | 完整视觉时间轴（18 个画面段） |
| `timeline.fcpxml` | XML | DaVinci Resolve FCPXML 时间轴 |
| `import_to_resolve.py` | Python | DaVinci Resolve API 导入脚本 |
| `compose_video.py` | Python | FFmpeg 视频合成脚本 |
| `audio/voiceover.mp3` | Audio | Edge-TTS 生成的语音 |
| `audio/subtitles.srt` | SRT | Whisper 生成的字幕 |
| `visuals/visuals/*.jpg` | Image | 14 张配图素材（4 张缺失待补） |
| `materials/sources.json` | JSON | 素材索引 |
| `materials/transcripts/` | SRT | 3 个 YouTube 字幕文件 |
| `publish/metadata.json` | JSON | 发布元数据 |
| `publish/sources.md` | Markdown | 引用出处列表 |

---

## 四、辅助工具文件

| 文件 | 位置 | 说明 |
|------|------|------|
| `CLAUDE.md` | 项目根目录 | 项目级 Claude Code 配置 |
| `video-pipeline-design-v2.md` | 项目根目录 | 流水线设计 v2 版本文档 |

---

## 五、统计

| 类别 | 数量 |
|------|------|
| 核心模块 | 8 个（7 功能 + 1 主控） |
| SKILL.md（Prompt 模板） | 8 个 |
| Python 脚本 | 16 个 |
| 设计文档 | 10 个 |
| 参考文档 | 3 个 |
| 测试项目数据文件 | 17+ 个 |

---

## 六、已知问题和待改进

1. **`download_visuals.py` 扩展名问题**：下载图片时统一用 `.png` 扩展名，但实际可能是 JPEG 格式，导致达芬奇显示离线媒体。需要检测实际格式后用正确扩展名保存。
2. **4 个缺失素材**：002、003、013、017 四张图片在测试项目中缺失，需要补充生成。
3. **FCPXML 兼容性**：达芬奇对 FCPXML 导入支持有限，已改用 `import_to_resolve.py` 通过 Python API 直接导入。
