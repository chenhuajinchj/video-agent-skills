# 模块 7: video-publish-preparer

## 功能概述

准备发布所需的封面、标题、描述、标签和 BGM 推荐。

## 触发条件

- 「准备发布素材」
- 「生成封面和标题」
- 「准备上传」

## 目录结构

```
video-publish-preparer/
├── SKILL.md
└── scripts/
    └── generate_metadata.py
```

## 输入文件

### script.md

逐字稿（用于生成标题和描述）

### outline.md

大纲（用于提取核心主题）

## 输出文件

### publish/thumbnail.png

封面图（16:9，1280x720）

### publish/metadata.json

```json
{
  "titles": [
    "巴菲特：为什么别人恐惧时，你应该贪婪？",
    "2008 年金融危机，巴菲特做了什么？",
    "90 岁巴菲特的投资秘诀，99% 的人做不到"
  ],
  "description": "视频描述文案...",
  "hashtags": ["#巴菲特", "#投资", "#个人成长", "#财富自由"],
  "recommended_bgm": [
    {
      "name": "Inspiring Corporate",
      "mood": "励志",
      "source": "pixabay",
      "url": "https://..."
    },
    {
      "name": "Calm Piano",
      "mood": "沉思",
      "source": "pixabay",
      "url": "https://..."
    }
  ]
}
```

### publish/sources.md

案例出处列表：

```markdown
# 视频引用出处

## 案例来源

1. **2008 年投资高盛**
   - 来源：《滚雪球》第 23 章
   - 类型：书籍

2. **Buy American 文章**
   - 来源：纽约时报，2008 年 10 月 17 日
   - 类型：新闻报道

3. **持有可口可乐 30 年**
   - 来源：伯克希尔年度股东信 1996
   - 类型：官方文件
```

## 处理流程

1. **生成标题候选**
   - 分析视频核心主题
   - 生成 3-5 个标题选项
   - 考虑平台特点（抖音/小红书）

2. **生成描述**
   - 简短概括视频内容
   - 包含关键词

3. **生成标签**
   - 提取主题相关标签
   - 添加平台热门标签

4. **推荐 BGM**
   - 根据视频情绪推荐背景音乐
   - 提供 Pixabay 等免费音乐源链接

5. **生成封面图**
   - 使用 AI 生成封面
   - 或从视频素材中选取关键帧

6. **整理出处**
   - 从 script.md 提取所有【出处：...】
   - 生成 sources.md

## 标题生成策略

| 类型 | 示例 |
|------|------|
| 疑问式 | 为什么别人恐惧时，你应该贪婪？ |
| 数字式 | 90 岁巴菲特的 3 个投资秘诀 |
| 反常识 | 巴菲特：远离华尔街才能赚钱 |
| 故事式 | 2008 年金融危机，巴菲特做了什么？ |

## BGM 推荐规则

| 视频情绪 | 推荐风格 |
|----------|----------|
| 励志 | Inspiring, Uplifting |
| 沉思 | Piano, Ambient |
| 紧张 | Dramatic, Cinematic |
| 轻松 | Acoustic, Happy |

## 依赖的外部 Skill

| Skill | 用途 |
|-------|------|
| document-illustrator-skill | 生成封面图 |

## 使用示例

```
用户：准备发布素材
→ 读取 script.md 和 outline.md
→ 生成标题、描述、标签
→ 推荐 BGM
→ 生成封面图
→ 整理出处列表
→ 输出到 publish/ 目录
```
