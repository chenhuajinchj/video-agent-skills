# 模块 5: video-material-collector

## 功能概述

搜索和下载与主题相关的素材，为后续内容整理提供原始资料。

## 触发条件

- 「搜索关于 [主题] 的素材」
- 「收集 [主题] 的资料」
- 「发现本周热门个人成长话题」

## 目录结构

```
video-material-collector/
├── SKILL.md
└── scripts/
    └── download_materials.py
```

## 输入

- 主题关键词
- 或「自动发现趋势」指令

## 输出文件

### materials/sources.json

```json
{
  "topic": "巴菲特的逆向思维",
  "search_date": "2026-01-29",
  "sources": [
    {
      "id": "src_001",
      "type": "article",
      "title": "Warren Buffett's Contrarian Strategy",
      "url": "https://...",
      "file": "materials/articles/buffett-strategy.txt",
      "summary": "介绍巴菲特在市场恐慌时买入的策略..."
    },
    {
      "id": "src_002",
      "type": "youtube",
      "title": "Buffett Explains His Investment Philosophy",
      "url": "https://youtube.com/...",
      "file": "materials/transcripts/buffett-interview.txt",
      "summary": "巴菲特本人解释他的投资哲学..."
    }
  ]
}
```

### materials/articles/

下载的文章文本文件

### materials/transcripts/

YouTube 视频字幕文本

## 素材类型

| 类型 | 来源 | 输出 |
|------|------|------|
| article | Web 搜索 | .txt 文件 |
| youtube | YouTube | 字幕 .txt |
| podcast | 播客平台 | 字幕 .txt |
| book | 书籍摘录 | .txt 文件 |

## 处理流程

1. **搜索素材**
   - Web 搜索相关文章
   - YouTube 搜索相关视频
   - 识别权威来源

2. **下载内容**
   - 提取文章正文
   - 下载 YouTube 字幕
   - 保存到 materials/ 目录

3. **生成摘要**
   - 为每个素材生成简短摘要
   - 记录到 sources.json

4. **输出报告**
   - 展示找到的素材列表
   - 提示用户上传到 NotebookLM

## 依赖的外部 Skill

| Skill | 用途 |
|-------|------|
| youtube-transcript | 下载 YouTube 字幕 |
| tapestry-skills | 文章提取 |
| Web Search | 搜索相关内容 |

## 后续步骤

素材收集完成后：
1. 用户手动将 materials/ 中的文件上传到 NotebookLM
2. 调用 video-content-organizer 生成大纲

## 使用示例

```
用户：搜索关于巴菲特投资哲学的素材
→ Web 搜索相关文章
→ YouTube 搜索相关视频
→ 下载内容到 materials/
→ 生成 sources.json
→ 提示用户上传到 NotebookLM
```
