#!/usr/bin/env python3
"""
视频制作流水线管理器。
管理视频项目的创建、状态跟踪、模块更新和检查点确认。
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

# 模块执行顺序（新 Agent 命名）
MODULE_ORDER = [
    "researcher",
    "writer",
    "storyboarder",
    "voice",
    "visual",
    "editor",
    "publisher",
]

# 检查点与前置模块的映射
CHECKPOINTS = {
    "outline_approved": "researcher",
    "script_approved": "writer",
    "preview_approved": "visual",
}

# 检查点中文名称
CHECKPOINT_NAMES = {
    "outline_approved": "大纲已确认",
    "script_approved": "逐字稿已确认",
    "preview_approved": "素材已确认",
}

# 状态 emoji
STATUS_EMOJI = {
    "completed": "✅",
    "in-progress": "🔄",
    "pending": "⏳",
    "skipped": "⏭️",
}


def load_project(project_dir: str) -> Dict:
    """读取项目 project.json。"""
    path = Path(project_dir) / "project.json"
    if not path.exists():
        raise FileNotFoundError(f"找不到项目文件: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def save_project(project_dir: str, data: Dict) -> None:
    """保存项目 project.json。"""
    data["updated_at"] = datetime.now().isoformat(timespec="seconds")
    path = Path(project_dir) / "project.json"
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_next_step(project_data: Dict) -> str:
    """根据当前状态返回下一步应执行的模块名。"""
    status = project_data["status"]
    checkpoints = project_data["checkpoints"]

    for module in MODULE_ORDER:
        if status[module] in ("completed", "skipped"):
            # 检查该模块完成后是否有未确认的检查点
            for cp_name, cp_module in CHECKPOINTS.items():
                if cp_module == module and not checkpoints.get(cp_name, False):
                    return f"等待检查点: {CHECKPOINT_NAMES[cp_name]}"
            continue
        return module

    return "all-completed"


def create_project(name: str, topic: str, base_dir: str = ".") -> None:
    """创建新的视频项目。"""
    project_dir = Path(base_dir) / name
    if project_dir.exists():
        print(f"❌ 错误: 项目目录已存在: {project_dir}")
        sys.exit(1)

    # 创建目录结构
    dirs = [
        "materials/articles",
        "materials/transcripts",
        "audio",
        "visuals",
        "publish",
    ]
    for d in dirs:
        (project_dir / d).mkdir(parents=True, exist_ok=True)

    # 初始化 project.json
    now = datetime.now().isoformat(timespec="seconds")
    project_data = {
        "name": name,
        "topic": topic,
        "created_at": now,
        "updated_at": now,
        "status": {module: "pending" for module in MODULE_ORDER},
        "checkpoints": {
            "outline_approved": False,
            "script_approved": False,
            "preview_approved": False,
        },
        "current_step": "researcher",
    }

    (project_dir / "project.json").write_text(
        json.dumps(project_data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"✅ 项目已创建: {project_dir.resolve()}")
    print(f"📝 主题: {topic}")
    print(f"📁 目录结构:")
    print(f"   {name}/")
    print(f"   ├── materials/articles/")
    print(f"   ├── materials/transcripts/")
    print(f"   ├── audio/")
    print(f"   ├── visuals/")
    print(f"   ├── publish/")
    print(f"   └── project.json")
    print(f"👉 下一步: 开始 researcher（素材搜集+大纲生成）")


def show_status(project_dir: str) -> None:
    """显示项目状态。"""
    data = load_project(project_dir)
    status = data["status"]
    checkpoints = data["checkpoints"]

    print(f"📋 项目: {data['name']}")
    print(f"📝 主题: {data['topic']}")
    print(f"🕐 创建: {data['created_at']}")
    print(f"🕐 更新: {data['updated_at']}")
    print("─" * 40)

    # 检查点插入位置
    checkpoint_after = {
        "researcher": "outline_approved",
        "writer": "script_approved",
        "visual": "preview_approved",
    }

    for module in MODULE_ORDER:
        s = status.get(module, "pending")
        emoji = STATUS_EMOJI.get(s, "❓")
        print(f"  {emoji} {module} ({s})")

        # 显示检查点
        if module in checkpoint_after:
            cp = checkpoint_after[module]
            if checkpoints.get(cp, False):
                print(f"     ☑️  检查点: {CHECKPOINT_NAMES[cp]}")
            elif status.get(module) == "completed":
                print(f"     ⬜ 检查点: {CHECKPOINT_NAMES[cp]}（未确认）")

    print("─" * 40)

    next_step = get_next_step(data)
    if next_step == "all-completed":
        print("🎉 所有模块已完成！")
    else:
        print(f"👉 下一步: {next_step}")


def update_module_status(project_dir: str, module: str, new_status: str) -> None:
    """更新模块状态。"""
    if module not in MODULE_ORDER:
        print(f"❌ 错误: 未知模块 '{module}'")
        print(f"   可用模块: {', '.join(MODULE_ORDER)}")
        sys.exit(1)

    valid_statuses = ("pending", "in-progress", "completed", "skipped")
    if new_status not in valid_statuses:
        print(f"❌ 错误: 无效状态 '{new_status}'")
        print(f"   可用状态: {', '.join(valid_statuses)}")
        sys.exit(1)

    data = load_project(project_dir)
    data["status"][module] = new_status
    data["current_step"] = get_next_step(data)
    save_project(project_dir, data)

    emoji = STATUS_EMOJI.get(new_status, "❓")
    print(f"{emoji} {module} → {new_status}")


def mark_checkpoint(project_dir: str, checkpoint: str) -> None:
    """标记检查点为已确认。"""
    if checkpoint not in CHECKPOINTS:
        print(f"❌ 错误: 未知检查点 '{checkpoint}'")
        print(f"   可用检查点: {', '.join(CHECKPOINTS.keys())}")
        sys.exit(1)

    data = load_project(project_dir)

    # 检查前置模块是否已完成
    required_module = CHECKPOINTS[checkpoint]
    if data["status"].get(required_module) != "completed":
        print(f"⚠️  警告: 前置模块 {required_module} 尚未完成")

    data["checkpoints"][checkpoint] = True
    data["current_step"] = get_next_step(data)
    save_project(project_dir, data)

    print(f"☑️  检查点已确认: {CHECKPOINT_NAMES[checkpoint]}")
    next_step = data["current_step"]
    if next_step != "all-completed":
        print(f"👉 下一步: {next_step}")
    else:
        print("🎉 所有模块已完成！")


def print_usage() -> None:
    """打印使用说明。"""
    print("视频制作流水线管理器")
    print()
    print("用法:")
    print("  python pipeline_manager.py new <project_name> <topic>       创建新项目")
    print("  python pipeline_manager.py status <project_dir>             查看项目状态")
    print("  python pipeline_manager.py update <project_dir> <module> <status>  更新模块状态")
    print("  python pipeline_manager.py checkpoint <project_dir> <name>  标记检查点")
    print()
    print("模块: " + ", ".join(MODULE_ORDER))
    print("状态: pending, in-progress, completed, skipped")
    print("检查点: " + ", ".join(CHECKPOINTS.keys()))


def main():
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    try:
        if command == "new":
            if len(sys.argv) < 4:
                print("用法: python pipeline_manager.py new <project_name> <topic>")
                sys.exit(1)
            create_project(sys.argv[2], sys.argv[3])

        elif command == "status":
            if len(sys.argv) < 3:
                print("用法: python pipeline_manager.py status <project_dir>")
                sys.exit(1)
            show_status(sys.argv[2])

        elif command == "update":
            if len(sys.argv) < 5:
                print("用法: python pipeline_manager.py update <project_dir> <module> <status>")
                sys.exit(1)
            update_module_status(sys.argv[2], sys.argv[3], sys.argv[4])

        elif command == "checkpoint":
            if len(sys.argv) < 4:
                print("用法: python pipeline_manager.py checkpoint <project_dir> <checkpoint_name>")
                sys.exit(1)
            mark_checkpoint(sys.argv[2], sys.argv[3])

        else:
            print(f"❌ 未知命令: {command}")
            print_usage()
            sys.exit(1)

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ 错误: project.json 格式错误: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
