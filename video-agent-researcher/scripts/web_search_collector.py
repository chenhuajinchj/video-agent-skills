#!/usr/bin/env python3
"""
网页素材搜集工具。
支持手动 URL 列表模式，抓取网页正文并保存为文本文件。
"""

import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path
from typing import List, Dict
from datetime import datetime


def clean_html(html: str) -> str:
    """简单的 HTML 标签清理，提取正文文本。"""
    # 去除 script 和 style 标签及内容
    html = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<style[^>]*>.*?</style>", "", html, flags=re.DOTALL | re.IGNORECASE)
    # 去除所有 HTML 标签
    text = re.sub(r"<[^>]+>", "", html)
    # 解码常见 HTML 实体
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = text.replace("&lt;", "<").replace("&gt;", ">")
    text = text.replace("&quot;", '"').replace("&#39;", "'")
    # 清理多余空白
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_page(url: str, timeout: int = 15) -> str:
    """抓取网页内容并提取正文。"""
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        charset = resp.headers.get_content_charset() or "utf-8"
        html = resp.read().decode(charset, errors="replace")
    return clean_html(html)


def extract_title(text: str) -> str:
    """从正文前几行提取标题。"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if lines:
        title = lines[0][:80]
        return re.sub(r'[\\/:*?"<>|]', "_", title)
    return "untitled"


def collect_from_urls(urls: List[str], output_dir: str, topic: str) -> List[Dict]:
    """从 URL 列表抓取文章并保存。"""
    output_path = Path(output_dir) / "articles"
    output_path.mkdir(parents=True, exist_ok=True)

    results = []
    for i, url in enumerate(urls, 1):
        url = url.strip()
        if not url:
            continue
        print(f"🔍 [{i}/{len(urls)}] 正在抓取: {url}")
        try:
            text = fetch_page(url)
            if len(text) < 100:
                print(f"   ⚠️ 内容过短，跳过")
                continue

            title = extract_title(text)
            filename = f"article_{i:03d}_{title[:40]}.txt"
            filepath = output_path / filename
            filepath.write_text(f"来源: {url}\n抓取时间: {datetime.now().isoformat()}\n\n{text}", encoding="utf-8")

            results.append({
                "id": f"src_{i:03d}",
                "type": "article",
                "title": title,
                "url": url,
                "file": str(filepath),
                "char_count": len(text)
            })
            print(f"   ✅ 已保存: {filename} ({len(text)} 字)")

        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            print(f"   ❌ 抓取失败: {e}")
            continue

    return results


def load_url_list(topic: str) -> List[str]:
    """提示用户输入 URL 列表（手动模式）。"""
    print(f"\n📋 主题: {topic}")
    print("请输入要抓取的 URL（每行一个，输入空行结束）：")
    urls = []
    while True:
        try:
            line = input().strip()
            if not line:
                break
            if line.startswith("http"):
                urls.append(line)
        except EOFError:
            break
    return urls


def main():
    if len(sys.argv) < 3:
        print("用法: python web_search_collector.py <topic> <output_dir> [url_file]")
        print("示例: python web_search_collector.py '认知偏差' ./materials urls.txt")
        print("\n如果提供 url_file，从文件读取 URL 列表（每行一个）")
        print("如果不提供 url_file，进入交互模式手动输入 URL")
        sys.exit(1)

    topic = sys.argv[1]
    output_dir = sys.argv[2]

    # 从文件或交互模式获取 URL 列表
    if len(sys.argv) > 3:
        url_file = Path(sys.argv[3])
        if not url_file.exists():
            print(f"❌ 错误: 找不到 URL 文件: {url_file}")
            sys.exit(1)
        urls = [l.strip() for l in url_file.read_text(encoding="utf-8").splitlines() if l.strip().startswith("http")]
        print(f"📄 从文件加载了 {len(urls)} 个 URL")
    else:
        urls = load_url_list(topic)

    if not urls:
        print("❌ 没有有效的 URL，退出")
        sys.exit(1)

    print(f"\n🚀 开始抓取 {len(urls)} 个页面...\n")
    results = collect_from_urls(urls, output_dir, topic)

    # 保存搜索结果摘要
    summary = {
        "topic": topic,
        "search_date": datetime.now().strftime("%Y-%m-%d"),
        "total_urls": len(urls),
        "successful": len(results),
        "articles": results
    }
    summary_path = Path(output_dir) / "search_results.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n📊 搜集完成:")
    print(f"   成功: {len(results)}/{len(urls)}")
    print(f"   结果: {summary_path}")


if __name__ == "__main__":
    main()
