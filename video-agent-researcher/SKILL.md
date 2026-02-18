---
name: video-agent-researcher
description: >
  视频团队的通用调研员。围绕任意主题搜集网页文章和 YouTube 字幕，
  分析素材提取核心论点，生成结构化大纲。
  触发条件："搜索关于[主题]的素材"、"收集资料"、"帮我找文章和视频"
---

# video-agent-researcher

视频团队的通用调研员。负责围绕任意主题搜集网页文章和 YouTube 字幕，分析素材提取核心论点，生成结构化大纲。

## 触发条件

- 「搜索关于 [主题] 的素材」
- 「收集 [主题] 的资料」
- 「帮我找一些关于 [主题] 的文章和视频」
- 「整理素材生成大纲」
- 由制片人（producer）调度时自动触发

## 输入 → 输出

- 输入：主题关键词（由制片人传入）
- 输出：`materials/sources.json` + `materials/articles/` + `materials/transcripts/` + `outline.md`

## 工作流程

1. 接收主题关键词
2. **搜集素材**（优先使用 WebSearch/WebFetch 工具，脚本作为离线备选）
   - 用英文关键词搜索 5-8 篇高质量文章（英文源优先，中文源补充）
   - 用 WebFetch 抓取关键文章的详细内容
3. **（可选）YouTube 字幕**：如需参考同类视频的讲述方式，搜集 1-3 个相关视频字幕
4. 汇总素材，生成 `sources.json` 索引
5. 分析所有素材，提取核心论点和案例
6. **数据验证**：搜索各关键实体（模型、公司、产品）的官方发布页，确认版本号、发布日期、基准数据为最新
7. 生成结构化大纲，须包含：主题定位、目标观众、3-5 个核心论点、每个论点的支撑案例、开头模式建议
8. 返回 `outline.md` 给制片人

## 素材搜集详细步骤

### 方式一：WebSearch/WebFetch（推荐，Claude Code 环境）

1. 用 WebSearch 搜索 3-4 组关键词（英文优先），每组获取 10 条结果
2. 从结果中筛选 5-8 篇高质量文章（优先选择：权威媒体、研究机构、行业分析）
3. 用 WebFetch 抓取关键文章的详细内容
4. 将抓取结果整理为 `materials/research-report.md`

### 方式二：Python 脚本（离线备选）

#### 网页文章搜集

```bash
python scripts/web_search_collector.py <topic> <output_dir> [url_file]
```

- 支持从 URL 文件批量导入
- 支持交互模式手动输入 URL
- 自动抓取网页正文，去除 HTML 标签
- 保存到 `materials/articles/` 目录

### YouTube 字幕下载

```bash
python scripts/youtube_transcript_collector.py <video_url> <output_dir>
```

- 使用 yt-dlp 下载自动字幕（中文优先，英文备选）
- 将 VTT/SRT 字幕转为纯文本
- 保存到 `materials/transcripts/` 目录

### 素材汇总

```bash
python scripts/compile_sources.py <materials_dir> <topic>
```

- 扫描 articles/ 和 transcripts/ 目录
- 为每个文件生成摘要（前 200 字）
- 输出 `sources.json` 索引文件

### 大纲生成

```bash
python scripts/generate_outline.py <sources.json> [output.md]
```

- 读取 sources.json 和素材文件
- 提取关键信息
- 生成预填充的 outline.md 模板

## 大纲质量标准

| 指标 | 要求 |
|------|------|
| 核心主题 | 一句话清晰概括 |
| 论点数量 | 3-5 个为宜 |
| 论点逻辑 | 递进或并列，结构清晰 |
| 案例支撑 | 每个论点至少 1 个案例 |
| 出处标注 | 每个案例标注来源 |
| 时长合理 | 5-15 分钟范围内 |

## 素材质量标准

| 指标 | 要求 |
|------|------|
| 素材数量 | 至少 3-5 篇文章或字幕 |
| 内容长度 | 每篇至少 500 字 |
| 来源多样性 | 至少 2 种不同来源类型 |
| 内容相关性 | 与主题直接相关 |
| 语言 | 英文源优先（质量更高），中文源补充 |

## 依赖

- **yt-dlp**：YouTube 字幕下载
- **Python 3**：标准库（urllib, json, re, subprocess）
- **网络连接**：抓取网页和下载字幕

## 脚本文件

- `scripts/web_search_collector.py` - 网页文章搜集
- `scripts/youtube_transcript_collector.py` - YouTube 字幕下载
- `scripts/compile_sources.py` - 素材汇总索引
- `scripts/generate_outline.py` - 大纲模板生成
