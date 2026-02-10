# Agent Team 重构报告

> 日期：2026-02-06
> Commit：`279b516` on `main`
> 基于：`agent-team-architecture.md` 架构文档

---

## 一、重构概述

将 `video-skills/` 下原有的 **8 个独立模块**重构为 **7 个 Agent Skill**，
从"流水线模式"升级为"Agent 团队协作模式"，支持并行调度和断点恢复。

### 核心变化

| 变化 | 说明 |
|------|------|
| 8 → 7 | 合并 material-collector + content-organizer 为 researcher |
| 模块 → 角色 | 每个 Agent 有明确的团队角色（制片人、编剧、配音师等） |
| 串行 → 并行 | voice 和 visual 可并行执行 |
| 状态管理升级 | project.json 字段从旧模块名更新为 Agent 名 |

---

## 二、新旧模块映射

| 新 Agent | 角色 | 原模块 | 变化说明 |
|----------|------|--------|----------|
| `video-agent-producer` | 制片人 | video-pipeline (08) | 更新状态管理逻辑 |
| `video-agent-researcher` | 调研员 | video-material-collector (05) + video-content-organizer (06) | **合并两个模块** |
| `video-agent-writer` | 编剧 | video-script-generator (01) | 纯 Skill，无脚本 |
| `video-agent-voice` | 配音师 | video-audio-producer (02) | 脚本不变 |
| `video-agent-visual` | 美术 | video-visual-generator (03) | 脚本不变 |
| `video-agent-editor` | 剪辑师 | video-timeline-builder (04) | 新增 import_to_resolve.py |
| `video-agent-publisher` | 运营 | video-publish-preparer (07) | 脚本不变 |

---

## 三、新目录结构

```
video-skills/
├── video-agent-producer/          # 制片人（总调度）
│   ├── SKILL.md
│   ├── scripts/pipeline_manager.py
│   └── references/quality-checklist.md
│
├── video-agent-researcher/        # 调研员（素材+大纲）
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── web_search_collector.py
│   │   ├── youtube_transcript_collector.py
│   │   ├── compile_sources.py
│   │   └── generate_outline.py
│   └── references/outline-template.md
│
├── video-agent-writer/            # 编剧（逐字稿）
│   ├── SKILL.md
│   └── references/
│       ├── script-template.md
│       └── case-sources.md
│
├── video-agent-voice/             # 配音师（语音+字幕）
│   ├── SKILL.md
│   └── scripts/
│       ├── extract_plain_text.py
│       ├── edge_tts_generate.py
│       ├── elevenlabs_tts.py
│       └── generate_subtitles.py
│
├── video-agent-visual/            # 美术（视觉素材）
│   ├── SKILL.md
│   └── scripts/
│       ├── parse_visual_markers.py
│       ├── match_timestamps.py
│       └── download_visuals.py
│
├── video-agent-editor/            # 剪辑师（时间轴）
│   ├── SKILL.md
│   ├── scripts/
│   │   ├── generate_fcpxml.py
│   │   └── import_to_resolve.py
│   └── references/fcpxml-format.md
│
├── video-agent-publisher/         # 运营（发布准备）
│   ├── SKILL.md
│   └── scripts/
│       ├── generate_metadata.py
│       └── compile_sources_list.py
│
├── *_legacy/                      # 8 个旧模块备份
└── test-project/                  # 端到端测试数据
```

---

## 四、协作流程

```
用户输入主题
    │
    ▼
[producer] 接收主题，创建 project.json
    │
    ▼
[researcher] 搜集素材 → 生成 outline.md
    │
    ▼
[producer] ⏸ 检查点 1：大纲确认（outline_approved）
    │
    ▼
[writer] 根据大纲生成 script.md
    │
    ▼
[producer] ⏸ 检查点 2：逐字稿确认（script_approved）
    │
    ├──────────────────┐
    ▼                  ▼
[voice]            [visual]          ← 可并行
生成语音+字幕      搜索匹配素材
    │                  │
    └────────┬─────────┘
             ▼
[editor] 合并 → 生成 timeline.fcpxml
    │
    ▼
[producer] ⏸ 检查点 3：素材预览（preview_approved）
    │
    ▼
[publisher] 生成发布元数据
    │
    ▼
[producer] 交付完整项目包
```

---

## 五、project.json 新格式

```json
{
  "topic": "视频主题",
  "created_at": "2026-02-06T10:00:00Z",
  "current_stage": "writer",
  "stages": {
    "researcher": { "status": "completed" },
    "writer": { "status": "in_progress" },
    "voice": { "status": "pending" },
    "visual": { "status": "pending" },
    "editor": { "status": "pending" },
    "publisher": { "status": "pending" }
  },
  "checkpoints": {
    "outline_approved": true,
    "script_approved": false,
    "preview_approved": false
  },
  "config": {
    "tts_engine": "edge-tts",
    "target_duration": "6-10min",
    "platforms": ["douyin", "bilibili", "youtube"]
  }
}
```

---

## 六、端到端验证结果

使用"巴菲特的逆向思维"测试项目验证：

```
📋 项目: test-project
📝 主题: 巴菲特的逆向思维
────────────────────────────────────────
  ✅ researcher (completed)
     ☑️  检查点: 大纲已确认
  ✅ writer (completed)
     ☑️  检查点: 逐字稿已确认
  ✅ voice (completed)
  ✅ visual (completed)
     ☑️  检查点: 素材已确认
  ✅ editor (completed)
  ✅ publisher (completed)
────────────────────────────────────────
🎉 所有模块已完成！
```

新项目创建测试也通过，流程正确从 `researcher` 开始。

---

## 七、pipeline_manager.py 变更

| 字段 | 旧值 | 新值 |
|------|------|------|
| MODULE_ORDER | 7 个旧模块名 | 6 个 Agent 名 |
| CHECKPOINTS | outline_confirmed → content-organizer | outline_approved → researcher |
| CHECKPOINTS | script_confirmed → script-generator | script_approved → writer |
| CHECKPOINTS | visuals_confirmed → visual-generator | preview_approved → visual |
| current_step 初始值 | material-collector | researcher |

---

## 八、备份说明

原 8 个模块已重命名为 `_legacy` 后缀保留：

- `video-audio-producer_legacy/`
- `video-content-organizer_legacy/`
- `video-material-collector_legacy/`
- `video-pipeline_legacy/`
- `video-publish-preparer_legacy/`
- `video-script-generator_legacy/`
- `video-timeline-builder_legacy/`
- `video-visual-generator_legacy/`

确认新架构稳定运行后，可安全删除这些备份目录。

---

## 九、后续建议

1. **删除 _legacy 目录**：确认新架构稳定后执行
2. **添加 .gitignore**：排除 `__pycache__/`、`*.pyc`、`output.mp4` 等
3. **扩展角色**：按架构文档第五章，可增加音效师、配乐师、翻译等角色
4. **CI 集成**：为 pipeline_manager.py 添加单元测试
