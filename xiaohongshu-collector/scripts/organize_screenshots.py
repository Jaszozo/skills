#!/usr/bin/env python3
"""
Organize Xiaohongshu screenshots into keyword-based folder structure.

Usage:
    python organize_screenshots.py --metadata metadata.json --screenshots /tmp/screenshots --output ~/Desktop/小红书收集
"""

import argparse
import json
import os
import shutil
from pathlib import Path
from datetime import datetime


def sanitize_filename(name):
    """Remove or replace invalid characters in filename."""
    invalid_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    for char in invalid_chars:
        name = name.replace(char, '_')
    # Limit length to 100 characters
    if len(name) > 100:
        name = name[:97] + '...'
    return name


def organize_screenshots(metadata_file, screenshots_dir, output_dir):
    """
    Organize screenshots into keyword-based folders.
    
    Args:
        metadata_file: Path to JSON file containing post metadata
        screenshots_dir: Directory containing temporary screenshot files
        output_dir: Output directory for organized structure
    """
    # Load metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    # Create output directory
    output_path = Path(output_dir).expanduser()
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Group by keyword
    by_keyword = {}
    for entry in metadata:
        keyword = entry['keyword']
        if keyword not in by_keyword:
            by_keyword[keyword] = []
        by_keyword[keyword].append(entry)
    
    # Process each keyword group
    stats = {
        'total_files': 0,
        'by_keyword': {}
    }
    
    for keyword, posts in by_keyword.items():
        # Create keyword folder
        keyword_folder = output_path / sanitize_filename(keyword)
        keyword_folder.mkdir(exist_ok=True)
        
        # Sort by index
        posts.sort(key=lambda x: x.get('index', 0))
        
        # Move and rename screenshots
        moved_count = 0
        for idx, post in enumerate(posts, 1):
            old_filename = post.get('screenshot')
            if not old_filename:
                continue
                
            old_path = Path(screenshots_dir) / old_filename
            if not old_path.exists():
                print(f"⚠️  Warning: Screenshot not found: {old_filename}")
                continue
            
            # Create new filename with title
            title = post.get('title', f'post_{idx}')
            title_safe = sanitize_filename(title)
            ext = old_path.suffix
            new_filename = f"{idx:02d}_{title_safe}{ext}"
            new_path = keyword_folder / new_filename
            
            # Move file
            shutil.copy2(old_path, new_path)
            moved_count += 1
            
            # Update metadata with new path
            post['organized_path'] = str(new_path)
        
        stats['by_keyword'][keyword] = moved_count
        stats['total_files'] += moved_count
        
        print(f"✅ {keyword}: {moved_count} 个文件")
    
    # Save updated metadata
    updated_metadata_path = output_path / 'metadata.json'
    with open(updated_metadata_path, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)
    
    # Print summary
    print(f"\n📊 整理完成！")
    print(f"总文件数: {stats['total_files']}")
    print(f"保存位置: {output_path}")
    
    return stats


def main():
    parser = argparse.ArgumentParser(description='Organize Xiaohongshu screenshots')
    parser.add_argument('--metadata', required=True, help='Path to metadata JSON file')
    parser.add_argument('--screenshots', required=True, help='Directory containing screenshots')
    parser.add_argument('--output', required=True, help='Output directory for organized files')
    
    args = parser.parse_args()
    
    organize_screenshots(args.metadata, args.screenshots, args.output)


if __name__ == '__main__':
    main()
