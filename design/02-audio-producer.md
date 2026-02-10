# 模块 2: video-audio-producer

## 功能概述

处理语音和生成字幕，支持自录音和 AI 语音两种模式。

## 触发条件

- 「生成语音」
- 「我录好音了，生成字幕」
- 「处理音频」

## 目录结构

```
video-audio-producer/
├── SKILL.md
└── scripts/
    ├── extract_plain_text.py   # 提取纯文字供录音
    └── generate_subtitles.py   # Whisper 生成字幕
```

## 两种工作模式

```
开始时询问用户：
├── 模式 A：「我自己录音」
│   ├── 1. 导出 script-plain.txt（去除画面标注）
│   ├── 2. 等待用户上传 voiceover.mp3
│   └── 3. 使用 Whisper 生成 subtitles.srt
│
└── 模式 B：「使用 AI 语音」
    ├── 1. 调用 ElevenLabs 生成 voiceover.mp3
    └── 2. 使用 Whisper 生成 subtitles.srt
```

## 输入文件

### script.md

带画面标注的逐字稿（来自模块 1）

### voiceover.mp3（模式 A）

用户自行录制的语音文件

## 输出文件

### script-plain.txt

去除画面标注的纯文字，供录音参考：

```
1956 年，26 岁的巴菲特做了一个让所有人不解的决定。

当时华尔街正处于黄金年代，所有人都想挤进曼哈顿的投行。

但巴菲特选择回到家乡奥马哈，一个人口不到 30 万的小城市。
他说：「我在这里能更好地思考。」
...
```

### audio/voiceover.mp3

- 模式 A：用户上传
- 模式 B：AI 生成

### audio/subtitles.srt

```srt
1
00:00:00,000 --> 00:00:04,200
1956 年，26 岁的巴菲特做了一个让所有人不解的决定。

2
00:00:04,200 --> 00:00:09,800
当时华尔街正处于黄金年代，所有人都想挤进曼哈顿的投行。

3
00:00:09,800 --> 00:00:15,500
但巴菲特选择回到家乡奥马哈，一个人口不到 30 万的小城市。
```

## 处理流程

### 模式 A（自录音）

1. 从 script.md 提取纯文字 → script-plain.txt
2. 提示用户录音并上传到 audio/voiceover.mp3
3. 使用 Whisper 转写 → audio/subtitles.srt
4. 校验字幕与原文的对应关系

### 模式 B（AI 语音）

1. 从 script.md 提取纯文字
2. 调用 ElevenLabs API 生成语音 → audio/voiceover.mp3
3. 使用 Whisper 转写 → audio/subtitles.srt

## 依赖的外部 Skill

| Skill | 用途 | 必需 |
|-------|------|------|
| whisper | 语音转字幕 | 是 |
| video-toolkit/elevenlabs | AI 语音生成 | 模式 B |

## 技术要点

### Whisper 参数

- 语言：zh（中文）
- 输出格式：srt
- 时间戳精度：毫秒

### 字幕分段规则

- 每条字幕不超过 2 行
- 每行不超过 20 个中文字符
- 按自然语句断句

## 使用示例

```
用户：我录好音了，生成字幕
→ 检查 audio/voiceover.mp3 是否存在
→ 调用 Whisper 生成字幕
→ 输出 audio/subtitles.srt
```
