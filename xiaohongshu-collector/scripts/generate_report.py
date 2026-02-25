#!/usr/bin/env python3
"""
Generate comprehensive report from Xiaohongshu collection metadata.

Usage:
    python generate_report.py --metadata metadata.json --output ~/Desktop/小红书收集/收集报告.md
"""

import argparse
import json
from pathlib import Path
from datetime import datetime


def format_likes(likes):
    """Format like count with proper units."""
    if isinstance(likes, str):
        return likes
    if likes >= 10000:
        return f"{likes/10000:.1f}万"
    return str(likes)


def generate_report(metadata_file, output_file):
    """
    Generate markdown report from collection metadata.
    
    Args:
        metadata_file: Path to JSON file containing post metadata
        output_file: Output path for markdown report
    """
    # Load metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Group by keyword
    by_keyword = {}
    for entry in metadata:
        keyword = entry['keyword']
        if keyword not in by_keyword:
            by_keyword[keyword] = []
        by_keyword[keyword].append(entry)
    
    # Generate report content
    report_lines = []
    
    # Header
    report_lines.append("# 小红书内容收集报告\n")
    report_lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    report_lines.append("---\n")
    
    # Summary
    total_posts = len(metadata)
    keywords_count = len(by_keyword)
    report_lines.append("## 📊 收集概览\n")
    report_lines.append(f"- **关键词数量**: {keywords_count}\n")
    report_lines.append(f"- **总笔记数**: {total_posts}\n")
    report_lines.append(f"- **搜索关键词**: {', '.join(by_keyword.keys())}\n")
    report_lines.append("\n---\n")
    
    # Detailed section for each keyword
    for keyword, posts in by_keyword.items():
        report_lines.append(f"\n## 🔍 关键词: {keyword}\n")
        report_lines.append(f"\n**收集数量**: {len(posts)} 篇笔记\n")
        
        # Sort by index
        posts.sort(key=lambda x: x.get('index', 0))
        
        # Table header
        report_lines.append("\n| # | 标题 | 作者 | 点赞数 | 链接 |\n")
        report_lines.append("|---|------|------|--------|------|\n")
        
        # Table rows
        for post in posts:
            idx = post.get('index', 0)
            title = post.get('title', '未知标题')
            author = post.get('author', '未知作者')
            likes = format_likes(post.get('likes', 0))
            url = post.get('url', '')
            
            # Truncate title if too long
            if len(title) > 40:
                title = title[:37] + '...'
            
            # Create clickable link
            if url:
                link_text = f"[查看]({url})"
            else:
                link_text = "N/A"
            
            report_lines.append(f"| {idx} | {title} | {author} | {likes} | {link_text} |\n")
        
        # Screenshot preview section
        report_lines.append(f"\n### 截图预览\n")
        
        for post in posts:
            idx = post.get('index', 0)
            title = post.get('title', '未知标题')
            screenshot_path = post.get('organized_path') or post.get('screenshot', '')
            
            if screenshot_path:
                # Convert to relative path if possible
                screenshot_file = Path(screenshot_path).name
                parent_dir = Path(screenshot_path).parent.name
                relative_path = f"{parent_dir}/{screenshot_file}"
                
                report_lines.append(f"\n#### {idx}. {title}\n")
                report_lines.append(f"![{title}]({relative_path})\n")
        
        report_lines.append("\n---\n")
    
    # Footer
    report_lines.append("\n## 📝 备注\n")
    report_lines.append("- 截图已按关键词分类保存在对应文件夹中\n")
    report_lines.append("- 点击表格中的\"查看\"链接可访问原始笔记\n")
    report_lines.append("- 本报告由 Xiaohongshu Collector Skill 自动生成\n")
    
    # Write report
    output_path = Path(output_file).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.writelines(report_lines)
    
    print(f"✅ 报告已生成: {output_path}")
    print(f"📄 总计 {total_posts} 篇笔记，涵盖 {keywords_count} 个关键词")
    
    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description='Generate Xiaohongshu collection report')
    parser.add_argument('--metadata', required=True, help='Path to metadata JSON file')
    parser.add_argument('--output', required=True, help='Output path for markdown report')
    
    args = parser.parse_args()
    
    generate_report(args.metadata, args.output)


if __name__ == '__main__':
    main()
