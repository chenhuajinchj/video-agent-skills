#!/usr/bin/env python3
"""
从 script.md 提取纯文字，去除画面标注和出处标注。
输出 script-plain.txt 供录音参考。
"""

import re
import sys
from pathlib import Path


def extract_plain_text(script_path: str) -> str:
    """
    从逐字稿中提取纯文字。

    去除：
    - [画面#XXX：描述] 标注
    - 【出处：...】标注
    - 元信息部分（## 元信息 到 ---）
    """
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"找不到文件: {script_path}")

    content = script_path.read_text(encoding="utf-8")

    # 去除元信息部分
    content = re.sub(r"## 元信息.*?---", "", content, flags=re.DOTALL)

    # 去除标题
    content = re.sub(r"^# 逐字稿：.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"^## 正文\s*$", "", content, flags=re.MULTILINE)

    # 去除画面标注 [画面#XXX：描述]
    content = re.sub(r"\[画面#\d{3}：[^\]]+\]\s*\n?", "", content)

    # 去除出处标注 【出处：...】
    content = re.sub(r"【出处：[^】]+】\s*", "", content)

    # 清理多余空行
    content = re.sub(r"\n{3,}", "\n\n", content)

    # 去除首尾空白
    content = content.strip()

    return content


def main():
    if len(sys.argv) < 2:
        print("用法: python extract_plain_text.py <script.md> [output.txt]")
        print("示例: python extract_plain_text.py ./script.md ./script-plain.txt")
        sys.exit(1)

    script_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else "script-plain.txt"

    try:
        plain_text = extract_plain_text(script_path)

        # 统计信息
        char_count = len(plain_text.replace(" ", "").replace("\n", ""))
        line_count = len([l for l in plain_text.split("\n") if l.strip()])

        # 写入文件
        Path(output_path).write_text(plain_text, encoding="utf-8")

        print(f"✅ 已导出录音稿: {output_path}")
        print(f"   字数: {char_count}")
        print(f"   段落: {line_count}")
        print(f"   预估时长: {char_count // 220} 分钟")

    except FileNotFoundError as e:
        print(f"❌ 错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
