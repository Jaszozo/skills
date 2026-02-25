#!/usr/bin/env python3
"""
Xiaohongshu Post Collector v2.0
收集小红书笔记截图和元数据（改进版）

改进内容：
1. 点赞阈值筛选 (≥N)
2. 内容相关性校验（必须包含指定关键词）
3. 优化登录流程

Usage:
    python collect_posts.py --keyword "她研社春日小懒裤" --count 20 --min-likes 100 --must-contain "她研社,小懒裤"
"""

import argparse
import json
import os
import re
import sys
import time
import random
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
except ImportError:
    print("Error: Playwright not installed. Run: pip install playwright && playwright install chromium")
    sys.exit(1)


class XiaohongshuCollector:
    def __init__(self, headless=False, slow_mo=50):
        self.headless = headless
        self.slow_mo = slow_mo
        self.browser = None
        self.page = None
        self.collected_posts = []
        self.skipped_reasons = {
            'low_likes': 0,
            'irrelevant': 0,
            'load_failed': 0
        }

    def __enter__(self):
        self.playwright = sync_playwright().start()
        user_data_dir = os.path.expanduser('~/.xiaohongshu-browser-data')
        os.makedirs(user_data_dir, exist_ok=True)

        self.context = self.playwright.chromium.launch_persistent_context(
            user_data_dir,
            headless=self.headless,
            slow_mo=self.slow_mo,
            viewport={'width': 1400, 'height': 900},
            args=['--disable-blink-features=AutomationControlled'],
            timeout=60000  # 60秒超时
        )
        self.browser = self.context
        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def random_delay(self, min_sec=1.0, max_sec=2.0):
        """随机延迟"""
        time.sleep(random.uniform(min_sec, max_sec))

    def ensure_logged_in(self):
        """确保已登录（改进版：更可靠的检测）"""
        print("🔐 检查登录状态...")
        self.page.goto('https://www.xiaohongshu.com', timeout=60000)
        self.random_delay(2, 3)

        # 方法1：检查是否有登录弹窗
        try:
            login_modal = self.page.locator('text=登录后查看').first
            if login_modal.is_visible(timeout=2000):
                return self._wait_for_manual_login()
        except:
            pass

        # 方法2：尝试访问搜索页，看是否被拦截
        self.page.goto('https://www.xiaohongshu.com/search_result?keyword=test', timeout=60000)
        self.random_delay(2, 3)

        try:
            login_required = self.page.locator('text=登录后查看搜索结果').first
            if login_required.is_visible(timeout=3000):
                return self._wait_for_manual_login()
        except:
            pass

        print("✅ 已登录")
        return True

    def _wait_for_manual_login(self):
        """等待用户手动登录"""
        print("\n" + "="*60)
        print("⚠️  需要登录！请在浏览器中完成登录：")
        print("   - 使用小红书APP扫码")
        print("   - 或使用手机号+验证码")
        print("="*60)

        # 回到首页方便登录
        self.page.goto('https://www.xiaohongshu.com', timeout=60000)
        self.random_delay(1, 2)

        max_wait = 180  # 3分钟
        start = time.time()

        while time.time() - start < max_wait:
            self.random_delay(3, 5)

            # 检查是否已登录成功
            try:
                # 尝试访问搜索页
                self.page.goto('https://www.xiaohongshu.com/search_result?keyword=test', timeout=60000)
                self.random_delay(2, 3)

                login_required = self.page.locator('text=登录后查看搜索结果')
                if not login_required.is_visible(timeout=2000):
                    print("\n✅ 登录成功！")
                    return True
            except:
                pass

            remaining = int(max_wait - (time.time() - start))
            print(f"⏳ 等待登录... 剩余 {remaining} 秒")

        print("❌ 登录超时")
        return False

    def search(self, keyword):
        """搜索关键词"""
        encoded_keyword = quote(keyword)
        search_url = f'https://www.xiaohongshu.com/search_result?keyword={encoded_keyword}&source=web_search_result_notes'

        print(f"\n🔍 搜索: {keyword}")
        self.page.goto(search_url, timeout=60000)
        self.random_delay(3, 4)

        # 等待搜索结果
        try:
            self.page.wait_for_selector('section, [class*="note"], [class*="feed"]', timeout=10000)
            print("✅ 搜索结果已加载")
            return True
        except PlaywrightTimeout:
            print("❌ 搜索结果加载超时")
            return False

    def extract_like_count(self, text):
        """解析点赞数"""
        if not text:
            return 0
        text = str(text).strip().lower()

        # 匹配 X.X万 或 X万
        match = re.search(r'([\d.]+)\s*[万w]', text)
        if match:
            return int(float(match.group(1)) * 10000)

        # 匹配纯数字
        match = re.search(r'(\d+)', text)
        if match:
            return int(match.group(1))

        return 0

    def check_content_relevance(self, text, must_contain_all):
        """检查内容是否包含所有必需关键词"""
        if not must_contain_all:
            return True

        text_lower = text.lower()
        for keyword in must_contain_all:
            if keyword.lower() not in text_lower:
                return False
        return True

    def get_all_post_elements(self):
        """获取页面上所有帖子元素"""
        # 小红书的帖子通常在 section 标签中
        selectors = [
            'section[class*="note"]',
            'section',
            '[class*="note-item"]',
            'a[href*="/explore/"]'
        ]

        for selector in selectors:
            elements = self.page.locator(selector).all()
            # 过滤掉太小的元素（可能是其他UI组件）
            valid_elements = []
            for el in elements:
                try:
                    box = el.bounding_box()
                    if box and box['width'] > 100 and box['height'] > 100:
                        valid_elements.append(el)
                except:
                    continue

            if len(valid_elements) >= 3:  # 至少找到3个帖子才认为选择器正确
                return valid_elements

        return []

    def scroll_and_collect_candidates(self, min_likes, must_contain_all, max_candidates=100):
        """滚动页面并收集符合条件的候选帖子"""
        candidates = []
        seen_urls = set()
        scroll_count = 0
        max_scrolls = 30
        no_new_count = 0

        print(f"📊 筛选条件: 点赞≥{min_likes}, 必须包含: {must_contain_all}")

        while scroll_count < max_scrolls and len(candidates) < max_candidates:
            # 获取当前页面的帖子
            posts = self.get_all_post_elements()

            new_found = 0
            for post in posts:
                try:
                    # 获取帖子链接作为唯一标识
                    href = post.get_attribute('href') or ''
                    if not href:
                        link = post.locator('a[href*="/explore/"]').first
                        href = link.get_attribute('href') if link else ''

                    if href in seen_urls:
                        continue
                    seen_urls.add(href)

                    # 获取帖子标题/描述
                    title_text = ''
                    try:
                        title_el = post.locator('[class*="title"], [class*="desc"], span').first
                        title_text = title_el.inner_text() if title_el else ''
                    except:
                        pass

                    # 获取点赞数
                    likes = 0
                    try:
                        like_el = post.locator('[class*="like"], [class*="count"]').first
                        likes = self.extract_like_count(like_el.inner_text() if like_el else '0')
                    except:
                        pass

                    # 检查点赞数
                    if likes < min_likes:
                        self.skipped_reasons['low_likes'] += 1
                        continue

                    # 检查内容相关性（在标题中）
                    if must_contain_all and not self.check_content_relevance(title_text, must_contain_all):
                        # 先不排除，等打开详情后再次检查
                        pass

                    candidates.append({
                        'element': post,
                        'href': href,
                        'title_preview': title_text[:50],
                        'likes_preview': likes
                    })
                    new_found += 1
                    print(f"  📌 候选: {title_text[:30]}... 👍{likes}")

                except Exception as e:
                    continue

            if new_found == 0:
                no_new_count += 1
                if no_new_count >= 3:
                    print("⚠️ 没有更多新帖子")
                    break
            else:
                no_new_count = 0

            # 滚动加载更多
            self.page.evaluate('window.scrollBy(0, 600)')
            self.random_delay(1.5, 2.5)
            scroll_count += 1

            if scroll_count % 5 == 0:
                print(f"📜 已滚动 {scroll_count} 次，找到 {len(candidates)} 个候选")

        print(f"\n📋 共找到 {len(candidates)} 个候选帖子")
        return candidates

    def collect_post_detail(self, candidate, index, keyword, must_contain_all, output_dir):
        """收集单个帖子详情"""
        try:
            element = candidate['element']

            # 点击打开详情
            element.click()
            self.random_delay(2, 3)

            # 等待详情加载
            detail_modal = None
            for selector in ['[class*="note-detail"]', '[class*="detail"]', '[role="dialog"]', '.modal']:
                try:
                    modal = self.page.locator(selector).first
                    if modal.is_visible(timeout=3000):
                        detail_modal = modal
                        break
                except:
                    continue

            if not detail_modal:
                self.skipped_reasons['load_failed'] += 1
                self._close_any_modal()
                return None

            # 提取完整内容
            full_text = ''
            title = ''
            description = ''

            try:
                # 获取标题
                title_el = self.page.locator('[class*="title"], h1').first
                title = title_el.inner_text() if title_el.is_visible(timeout=1000) else ''
            except:
                pass

            try:
                # 获取描述/正文
                desc_el = self.page.locator('[class*="desc"], [class*="content"], [class*="note-text"]').first
                description = desc_el.inner_text() if desc_el.is_visible(timeout=1000) else ''
            except:
                pass

            full_text = f"{title} {description}"

            # 🔍 关键检查：内容相关性验证
            if must_contain_all and not self.check_content_relevance(full_text, must_contain_all):
                print(f"  ⏭️ 跳过(内容不相关): {title[:30]}...")
                self.skipped_reasons['irrelevant'] += 1
                self._close_any_modal()
                return None

            # 获取点赞数
            likes = 0
            try:
                like_el = self.page.locator('[class*="like"] [class*="count"], [data-type="like"]').first
                likes = self.extract_like_count(like_el.inner_text() if like_el.is_visible(timeout=1000) else '0')
            except:
                likes = candidate.get('likes_preview', 0)

            # 获取作者
            author = ''
            try:
                author_el = self.page.locator('[class*="author"], [class*="user"] [class*="name"]').first
                author = author_el.inner_text() if author_el.is_visible(timeout=1000) else ''
            except:
                pass

            # 截图
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', title[:30]) or f'post_{index}'
            filename = f"{index:02d}_{safe_title}_{timestamp}.png"
            filepath = os.path.join(output_dir, filename)

            detail_modal.screenshot(path=filepath)

            metadata = {
                'index': index,
                'keyword': keyword,
                'title': title[:200],
                'description': description[:500],
                'author': author,
                'likes': likes,
                'url': self.page.url,
                'screenshot': filename,
                'collected_at': datetime.now().isoformat()
            }

            print(f"  ✅ #{index}: {title[:35]}... 👍{likes}")

            self._close_any_modal()
            self.random_delay(1, 2)
            return metadata

        except Exception as e:
            print(f"  ❌ 收集失败: {e}")
            self.skipped_reasons['load_failed'] += 1
            self._close_any_modal()
            return None

    def _close_any_modal(self):
        """关闭任何打开的弹窗"""
        try:
            # 先尝试ESC
            self.page.keyboard.press('Escape')
            self.random_delay(0.3, 0.5)
        except:
            pass

        try:
            close_btn = self.page.locator('[class*="close"], button:has-text("×"), [aria-label*="关闭"]').first
            if close_btn.is_visible(timeout=500):
                close_btn.click()
        except:
            pass

    def collect(self, keyword, count=20, min_likes=100, must_contain_all=None, output_dir=None):
        """主收集流程（改进版）"""
        if not output_dir:
            output_dir = os.path.expanduser(f'~/Desktop/小红书收集/{keyword}')
        os.makedirs(output_dir, exist_ok=True)

        print(f"\n📁 输出目录: {output_dir}")
        print(f"🎯 目标: 收集 {count} 篇笔记")
        print(f"📊 条件: 点赞≥{min_likes}")
        if must_contain_all:
            print(f"🔍 必须包含: {' 且 '.join(must_contain_all)}")

        # 搜索
        if not self.search(keyword):
            return []

        # 收集候选帖子
        candidates = self.scroll_and_collect_candidates(
            min_likes=min_likes,
            must_contain_all=must_contain_all,
            max_candidates=count * 3  # 多收集一些候选
        )

        if not candidates:
            print("❌ 未找到符合条件的帖子")
            return []

        # 逐个收集详情
        print(f"\n📥 开始收集详情...")
        collected = []

        for i, candidate in enumerate(candidates):
            if len(collected) >= count:
                break

            # 需要重新回到搜索页
            if i > 0 and i % 5 == 0:
                self.search(keyword)
                self.random_delay(1, 2)
                # 滚动到之前的位置
                for _ in range(i // 4):
                    self.page.evaluate('window.scrollBy(0, 600)')
                    self.random_delay(0.5, 1)

            # 重新获取元素（因为DOM可能已变化）
            posts = self.get_all_post_elements()
            if i < len(posts):
                candidate['element'] = posts[i]

            metadata = self.collect_post_detail(
                candidate=candidate,
                index=len(collected) + 1,
                keyword=keyword,
                must_contain_all=must_contain_all,
                output_dir=output_dir
            )

            if metadata:
                collected.append(metadata)

            # 进度报告
            if len(collected) % 5 == 0 and len(collected) > 0:
                print(f"\n📥 进度: {len(collected)}/{count}")

        # 保存结果
        metadata_file = os.path.join(output_dir, 'metadata.json')
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(collected, f, ensure_ascii=False, indent=2)

        # 打印统计
        print(f"\n" + "="*60)
        print(f"✅ 收集完成!")
        print(f"   成功收集: {len(collected)} 篇")
        print(f"   跳过(点赞不足): {self.skipped_reasons['low_likes']}")
        print(f"   跳过(内容不相关): {self.skipped_reasons['irrelevant']}")
        print(f"   跳过(加载失败): {self.skipped_reasons['load_failed']}")
        print(f"📄 元数据: {metadata_file}")
        print("="*60)

        return collected


def main():
    parser = argparse.ArgumentParser(description='小红书帖子收集器 v2.0')
    parser.add_argument('--keyword', '-k', required=True, help='搜索关键词')
    parser.add_argument('--count', '-c', type=int, default=20, help='收集数量 (默认: 20)')
    parser.add_argument('--min-likes', '-l', type=int, default=100, help='最低点赞数 (默认: 100)')
    parser.add_argument('--must-contain', '-m', type=str, help='必须包含的关键词，逗号分隔 (如: 她研社,小懒裤)')
    parser.add_argument('--output', '-o', help='输出目录')
    parser.add_argument('--headless', action='store_true', help='无头模式')

    args = parser.parse_args()

    # 解析必须包含的关键词
    must_contain_all = None
    if args.must_contain:
        must_contain_all = [k.strip() for k in args.must_contain.split(',') if k.strip()]

    with XiaohongshuCollector(headless=args.headless) as collector:
        if not collector.ensure_logged_in():
            print("登录失败，退出")
            sys.exit(1)

        results = collector.collect(
            keyword=args.keyword,
            count=args.count,
            min_likes=args.min_likes,
            must_contain_all=must_contain_all,
            output_dir=args.output
        )

        print(f"\n最终结果: {len(results)} 篇笔记")


if __name__ == '__main__':
    main()
