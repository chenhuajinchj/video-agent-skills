# 模块 4: video-timeline-builder

## 功能概述

生成 DaVinci Resolve 可导入的 FCPXML 时间轴文件。

## 触发条件

- 「生成时间轴」
- 「生成 DaVinci 项目」
- 「导出 FCPXML」

## 目录结构

```
video-timeline-builder/
├── SKILL.md
├── scripts/
│   └── generate_fcpxml.py
└── references/
    └── fcpxml-format.md
```

## 输入文件

### visual-timeline.json

视觉时间轴（来自模块 3）

### audio/voiceover.mp3

语音文件

### audio/subtitles.srt

字幕文件

## 输出文件

### timeline.fcpxml

DaVinci Resolve 可导入的 FCPXML 文件。

## FCPXML 结构

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE fcpxml>
<fcpxml version="1.9">
  <resources>
    <!-- 素材资源定义 -->
    <format id="r1" name="FFVideoFormat1080p30"/>
    <asset id="audio1" src="file:///.../audio/voiceover.mp3"/>
    <asset id="visual1" src="file:///.../visuals/001_xxx.png"/>
    ...
  </resources>

  <library>
    <event name="项目名称">
      <project name="时间轴">
        <sequence>
          <!-- 视频轨 -->
          <spine>
            <clip offset="0s" duration="4.2s">
              <video ref="visual1"/>
            </clip>
            ...
          </spine>

          <!-- 音频轨 -->
          <audio-clip offset="0s" ref="audio1"/>

          <!-- 字幕轨 -->
          <title offset="0s" duration="4.2s">
            <text>字幕内容</text>
          </title>
          ...
        </sequence>
      </project>
    </event>
  </library>
</fcpxml>
```

## 轨道结构

| 轨道 | 内容 | 来源 |
|------|------|------|
| V1 | 视觉素材 | visual-timeline.json |
| A1 | 语音 | voiceover.mp3 |
| A2 | BGM（预留） | 手动添加 |
| 字幕轨 | 字幕 | subtitles.srt |

## 处理流程

1. **读取输入文件**
   - 解析 visual-timeline.json
   - 获取音频时长
   - 解析字幕文件

2. **生成资源定义**
   - 为每个素材创建 asset 节点
   - 设置正确的文件路径

3. **构建时间轴**
   - 按 visual-timeline.json 排列视频片段
   - 添加音频轨
   - 添加字幕轨

4. **输出 FCPXML**
   - 验证 XML 格式
   - 写入 timeline.fcpxml

## 视频规格

| 参数 | 值 |
|------|-----|
| 分辨率 | 1920x1080 |
| 帧率 | 30fps |
| 宽高比 | 16:9 |

## 图片处理

- 静态图片默认添加 Ken Burns 效果（缓慢缩放）
- 持续时间由 visual-timeline.json 指定

## 依赖

无外部 Skill 依赖，纯 Python 脚本生成 XML。

## 在 DaVinci 中的操作

1. 文件 → 导入 → 时间轴 → 选择 timeline.fcpxml
2. 所有素材自动排列在时间轴上
3. 后续操作：
   - 替换不满意的素材
   - 插入出镜片段
   - 添加 BGM
   - 调整字幕样式
   - 调色和渲染

## 使用示例

```
用户：把 visual-timeline.json 转成 DaVinci 时间轴
→ 读取 visual-timeline.json
→ 读取 audio/ 目录文件
→ 生成 timeline.fcpxml
→ 提示用户在 DaVinci 中导入
```
