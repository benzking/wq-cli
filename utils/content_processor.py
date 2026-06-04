#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
图文内容处理器 - 完美还原微信文章的图文混合内容
"""

import re
import logging
from typing import Dict, List
from urllib.parse import quote

logger = logging.getLogger(__name__)


def process_article_content(html: str, proxy_base_url: str = None) -> Dict:
    """
    处理文章内容，保持图文顺序并代理图片
    
    Args:
        html: 原始 HTML
        proxy_base_url: 图片代理基础 URL（例如：https://你的域名.com）
        
    Returns:
        {
            'content': '处理后的 HTML（图片已代理）',
            'plain_content': '纯文本',
            'images': ['图片URL列表'],
            'has_images': True/False
        }
    """
    
    # 1. 提取正文内容（保持原始 HTML 结构）
    content = extract_content(html)
    
    if not content:
        return {
            'content': '',
            'plain_content': '',
            'images': [],
            'has_images': False
        }
    
    # 2. 提取所有图片 URL（按顺序）
    images = extract_images_in_order(content)
    
    # 3. 代理图片 URL（保持 HTML 中的图片顺序）
    if proxy_base_url:
        content = proxy_all_images(content, proxy_base_url)
    
    # 4. 清理和优化 HTML
    content = clean_html(content)
    
    # 5. 生成纯文本
    plain_content = html_to_text(content)
    
    # 6. 纯图片文章处理：如果没有文字但有图片，生成图片描述
    if not plain_content.strip() and images:
        plain_content = f"[纯图片文章，共 {len(images)} 张图片]"
        logger.info(f"检测到纯图片文章: {len(images)} 张图片，无文字内容")
    
    return {
        'content': content,
        'plain_content': plain_content,
        'images': images,
        'has_images': len(images) > 0
    }


def _extract_div_inner(html: str, open_tag_pattern: str) -> str:
    """
    Extract the inner HTML of a <div> matched by open_tag_pattern,
    correctly handling nested <div> tags by counting open/close depth.
    """
    m = re.search(open_tag_pattern, html, re.DOTALL | re.IGNORECASE)
    if not m:
        return ""

    start = m.end()
    depth = 1
    pos = start
    open_re = re.compile(r'<div[\s>/]', re.IGNORECASE)
    close_re = re.compile(r'</div\s*>', re.IGNORECASE)

    while depth > 0 and pos < len(html):
        next_open = open_re.search(html, pos)
        next_close = close_re.search(html, pos)

        if next_close is None:
            break

        if next_open and next_open.start() < next_close.start():
            depth += 1
            pos = next_open.end()
        else:
            depth -= 1
            if depth == 0:
                return html[start:next_close.start()].strip()
            pos = next_close.end()

    return html[start:].strip()


def extract_content(html: str) -> str:
    """
    Extract article body, trying multiple container patterns.
    Different WeChat account types (government, media, personal) use
    different HTML structures. We try them in order of specificity.
    For image-text messages (item_show_type=8), short posts (item_show_type=10),
    and audio share pages (item_show_type=7), delegates to helpers.
    """
    from utils.helpers import (
        is_image_text_message, _extract_image_text_content,
        is_short_content_message, _extract_short_content,
        is_audio_message, _extract_audio_content,
        get_item_show_type, _extract_audio_share_content,
    )

    # [2026-05-25] 3 个特殊分支返回空时 fallthrough 到下面通用 Pattern,
    # 防御 WeChat HTML 模板变化 (新版 type-10 用 js_article 容器而非 JsDecode pattern)
    # Check for audio/video share pages (item_show_type=7) FIRST
    # These pages use Vue apps and have no js_content div
    if get_item_show_type(html) == '7':
        result = _extract_audio_share_content(html)
        content = result.get('content', '')
        if content:
            return content
        logger.info("type=7 audio_share returned empty, fallthrough to standard patterns")

    if is_image_text_message(html):
        result = _extract_image_text_content(html)
        content = result.get('content', '')
        if content:
            return content
        logger.info("type=8 image_text returned empty, fallthrough to standard patterns")

    if is_short_content_message(html):
        result = _extract_short_content(html)
        content = result.get('content', '')
        if content:
            return content
        logger.info("type=10 short_content returned empty, fallthrough to standard patterns")

    if is_audio_message(html):
        result = _extract_audio_content(html)
        content = result.get('content', '')
        if content:
            return content
        logger.info("audio extract returned empty, fallthrough to standard patterns")

    # Pattern 1: id="js_content" (most common)
    content = _extract_div_inner(html, r'<div[^>]*\bid=["\']js_content["\'][^>]*>')
    if content:
        return content

    # Pattern 2: class contains rich_media_content
    content = _extract_div_inner(html, r'<div[^>]*\bclass=["\'][^"\']*rich_media_content[^"\']*["\'][^>]*>')
    if content:
        return content

    # Pattern 3: id="page-content" (government/institutional accounts)
    content = _extract_div_inner(html, r'<div[^>]*\bid=["\']page-content["\'][^>]*>')
    if content:
        return content

    # Pattern 4: class contains rich_media_area_primary_inner
    content = _extract_div_inner(html, r'<div[^>]*\bclass=["\'][^"\']*rich_media_area_primary_inner[^"\']*["\'][^>]*>')
    if content:
        return content

    # Pattern 5: id="js_article" (alternative article container)
    content = _extract_div_inner(html, r'<div[^>]*\bid=["\']js_article["\'][^>]*>')
    if content:
        return content

    # [2026-05-25] Pattern 6: id="page_content" (underscore variant,
    # was matched by has_article_content but missed by extract_content)
    content = _extract_div_inner(html, r'<div[^>]*\bid=["\']page_content["\'][^>]*>')
    if content:
        return content

    # [2026-05-25] Pattern 7: class="rich_media_area_primary" (no _inner suffix)
    content = _extract_div_inner(html, r'<div[^>]*\bclass=["\'][^"\']*rich_media_area_primary[^"\']*["\'][^>]*>')
    if content:
        return content

    logger.warning("Failed to extract article body from any known container")
    return ""


def extract_images_in_order(content: str) -> List[str]:
    """
    按顺序提取所有图片 URL
    
    微信文章的图片有两种属性：
    1. data-src（主要）- 懒加载图片
    2. src（备用）- 直接加载图片
    """
    images = []
    
    # 提取所有 <img> 标签（按 HTML 中的顺序）
    img_pattern = re.compile(r'<img[^>]*>', re.IGNORECASE)
    
    for img_tag in img_pattern.finditer(content):
        img_html = img_tag.group(0)
        
        # 优先提取 data-src
        data_src_match = re.search(r'data-src="([^"]+)"', img_html)
        if data_src_match:
            img_url = data_src_match.group(1)
            if is_valid_image_url(img_url) and img_url not in images:
                images.append(img_url)
            continue
        
        # 备用：提取 src
        src_match = re.search(r'src="([^"]+)"', img_html)
        if src_match:
            img_url = src_match.group(1)
            if is_valid_image_url(img_url) and img_url not in images:
                images.append(img_url)
    
    logger.info(f"提取到 {len(images)} 张图片（按顺序）")
    return images


def proxy_all_images(content: str, proxy_base_url: str) -> str:
    """
    代理所有图片 URL（保持 HTML 中的图片顺序）
    
    替换策略：
    1. 提取图片URL（data-src 或 src）
    2. 替换为代理URL
    3. 确保同时有 data-src 和 src 属性（RSS阅读器需要src）
    
    重要: RSS 阅读器需要 src 属性才能显示图片!
    """
    
    def replace_img_tag(match):
        """替换单个 <img> 标签"""
        img_html = match.group(0)
        
        # 提取原始图片 URL（优先data-src，其次src）
        data_src_match = re.search(r'data-src="([^"]+)"', img_html, re.IGNORECASE)
        src_match = re.search(r'\ssrc="([^"]+)"', img_html, re.IGNORECASE)
        
        original_url = None
        if data_src_match:
            original_url = data_src_match.group(1)
        elif src_match:
            original_url = src_match.group(1)
        
        if not original_url or not is_valid_image_url(original_url):
            return img_html
        
        # 生成代理 URL
        proxy_url = f"{proxy_base_url}/api/image?url={quote(original_url, safe='')}"
        
        new_html = img_html
        
        # 第一步：替换 data-src（如果有）
        if data_src_match:
            new_html = re.sub(
                r'data-src="[^"]+"',
                f'data-src="{proxy_url}"',
                new_html,
                count=1,
                flags=re.IGNORECASE
            )
        
        # 第二步：处理 src 属性
        if src_match:
            # 已有 src，直接替换
            new_html = re.sub(
                r'\ssrc="[^"]+"',
                f' src="{proxy_url}"',
                new_html,
                count=1,
                flags=re.IGNORECASE
            )
        else:
            # 没有 src，必须添加（使用最简单可靠的方法）
            new_html = new_html.replace('<img', f'<img src="{proxy_url}"', 1)
            # 处理大写
            if 'src=' not in new_html:
                new_html = new_html.replace('<IMG', f'<IMG src="{proxy_url}"', 1)
        
        return new_html
    
    # 替换所有 <img> 标签
    content = re.sub(
        r'<img[^>]*>',
        replace_img_tag,
        content,
        flags=re.IGNORECASE
    )
    
    logger.info("图片 URL 已代理")
    return content


def is_valid_image_url(url: str) -> bool:
    """判断是否为有效的图片 URL"""
    if not url:
        return False
    
    # 排除 base64 和无效 URL
    if url.startswith('data:'):
        return False
    
    # 只保留微信 CDN 图片
    wechat_cdn_domains = [
        'mmbiz.qpic.cn',
        'mmbiz.qlogo.cn',
        'wx.qlogo.cn'
    ]
    
    return any(domain in url for domain in wechat_cdn_domains)


def clean_html(content: str) -> str:
    """
    清理和优化 HTML
    
    1. 移除 script 标签
    2. 移除 style 标签（可选）
    3. 移除空白标签
    """
    
    # 移除 <script> 标签
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除 <style> 标签（可选，保留可以保持样式）
    # content = re.sub(r'<style[^>]*>.*?</style>', '', content, flags=re.DOTALL | re.IGNORECASE)
    
    # 移除空段落
    content = re.sub(r'<p[^>]*>\s*</p>', '', content, flags=re.IGNORECASE)
    
    # 移除多余空白
    content = re.sub(r'\n\s*\n', '\n', content)
    
    return content.strip()


def html_to_text(html: str) -> str:
    """将 HTML 转为纯文本（移除图片，只保留文字）"""
    import html as html_module
    
    # 移除图片标签
    text = re.sub(r'<img[^>]*>', '', html, flags=re.IGNORECASE)
    
    # 移除其他标签
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'</(?:p|div|section|h[1-6])>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<[^>]+>', '', text)
    
    # HTML 实体解码
    text = html_module.unescape(text)
    
    # 清理空白
    text = re.sub(r'[ \t]+', ' ', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


def html_to_markdown(html_content: str) -> str:
    """
    将 HTML 转为 Obsidian 规范的纯净 Markdown。

    基于 BeautifulSoup 手写解析完成转换（零额外依赖）。转换规则：
    - <h1>~<h6> → # ~ ###### ATX 标题
    - <a> → [text](url)
    - <img> → ![alt](url)
    - <strong>/<b> → **粗体**
    - <em>/<i> → *斜体*
    - <table>/<tr>/<td>/<th> → Obsidian pipe table
    - <ul>/<ol>/<li> → Markdown 缩进列表
    - <blockquote> → > 引用
    - <code> / <pre> → 行内代码 / 围栏代码块
    - <br> → 软换行
    - style/class 属性全部移除
    - <script>/<style> 标签连带内容删除
    - <span>/<div>/<section> 仅保留内部文本
    - 连续空行压缩为单个空行
    """
    import html as _html
    from bs4 import BeautifulSoup, NavigableString

    if not html_content or not html_content.strip():
        return ""

    soup = BeautifulSoup(html_content, "html.parser")

    # 1. 移除 script / style 标签（含内容）
    for tag in soup(["script", "style"]):
        tag.decompose()

    # 2. 移除 style / class / id 等展示属性，保留 href/src/alt 等功能属性
    _keep_attrs = {"href", "src", "alt", "title"}
    for tag in soup.find_all(True):
        for attr in list(tag.attrs):
            if attr not in _keep_attrs:
                tag.attrs.pop(attr, None)

    # 3. 深度遍历，将 HTML 转为 Markdown
    lines = []  # 行级输出的各行
    _inline_buf: list[str] = []  # 当前正在构建的行内片段

    def _flush_inline():
        """将行内缓冲区的内容合并为一行，压入 lines"""
        text = "".join(_inline_buf).strip()
        if text:
            # 压缩连续空格
            text = re.sub(r'  +', ' ', text)
            lines.append(text)
        _inline_buf.clear()

    def _block_sep():
        """在块级元素之间插入空行分隔"""
        if lines and lines[-1] != "":
            lines.append("")

    def _process(node, list_depth=0):
        """递归处理 DOM 节点"""
        if isinstance(node, NavigableString):
            t = _html.unescape(str(node))
            # 规范化空白
            t = re.sub(r'\s+', ' ', t)
            _inline_buf.append(t)
            return

        tag = node.name
        if tag is None:
            # 根节点 / 匿名块
            for child in node.children:
                _process(child, list_depth)
            return

        # ── 块级元素（先 flush 当前行，输出后 flush）──
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            _flush_inline()
            _block_sep()
            level = int(tag[1])
            prefix = "#" * level + " "
            for child in node.children:
                _process(child, list_depth)
            content = "".join(_inline_buf).strip()
            _inline_buf.clear()
            if content:
                lines.append(prefix + content)
            return

        if tag == "p":
            _flush_inline()
            _block_sep()
            for child in node.children:
                _process(child, list_depth)
            _flush_inline()
            return

        if tag == "br":
            # 换行：flush 当前行内为一行，不追加空行
            _flush_inline()
            return

        if tag in ("div", "section", "article", "header", "footer", "main", "aside", "figure", "figcaption"):
            _flush_inline()
            _block_sep()
            for child in node.children:
                _process(child, list_depth)
            _flush_inline()
            return

        if tag == "hr":
            _flush_inline()
            _block_sep()
            lines.append("---")
            return

        # ── 引用 ──
        if tag == "blockquote":
            _flush_inline()
            _block_sep()
            before = len(lines)
            for child in node.children:
                _process(child, list_depth)
            _flush_inline()
            # 给 blockquote 内产生的行加 "> " 前缀
            for i in range(before, len(lines)):
                lines[i] = "> " + lines[i]
            return

        # ── 表格 ──
        if tag == "table":
            _flush_inline()
            _block_sep()
            rows = node.find_all("tr")
            table_lines = []
            for ri, row in enumerate(rows):
                cells = row.find_all(["td", "th"])
                cell_texts = []
                for cell in cells:
                    _inline_buf.clear()
                    for child in cell.children:
                        _process(child, list_depth)
                    cell_texts.append("".join(_inline_buf).strip())
                table_lines.append("| " + " | ".join(cell_texts) + " |")
                if ri == 0 and row.find("th"):
                    # 表头分隔行
                    sep = "| " + " | ".join("---" for _ in cells) + " |"
                    table_lines.append(sep)
            lines.extend(table_lines)
            _inline_buf.clear()
            return

        # ── 列表 ──
        if tag in ("ul", "ol"):
            _flush_inline()
            is_ordered = tag == "ol"
            idx = 0
            for li in node.find_all("li", recursive=False):
                _inline_buf.clear()
                for child in li.children:
                    _process(child, list_depth + 1)
                text = "".join(_inline_buf).strip()
                _inline_buf.clear()
                if text:
                    indent = "  " * list_depth
                    if is_ordered:
                        idx += 1
                        lines.append(f"{indent}{idx}. {text}")
                    else:
                        lines.append(f"{indent}- {text}")
            return

        # ── 代码块 ──
        if tag == "pre":
            _flush_inline()
            code_tag = node.find("code")
            code_text = code_tag.get_text() if code_tag else node.get_text()
            lines.append("```")
            for cl in code_text.splitlines():
                lines.append(cl)
            lines.append("```")
            return

        # ── 行内元素 ──
        if tag in ("strong", "b"):
            _inline_buf.append("**")
            for child in node.children:
                _process(child, list_depth)
            _inline_buf.append("**")
            return

        if tag in ("em", "i"):
            _inline_buf.append("*")
            for child in node.children:
                _process(child, list_depth)
            _inline_buf.append("*")
            return

        if tag == "code":
            _inline_buf.append("`")
            for child in node.children:
                _process(child, list_depth)
            _inline_buf.append("`")
            return

        if tag == "a":
            href = node.get("href", "")
            _inline_buf.append("[")
            for child in node.children:
                _process(child, list_depth)
            _inline_buf.append(f"]({href})")
            return

        if tag == "img":
            src = node.get("src", "")
            alt = node.get("alt", "")
            _inline_buf.append(f"![{alt}]({src})")
            return

        if tag == "span":
            # 剥离标签，保留文本
            for child in node.children:
                _process(child, list_depth)
            return

        # ── 未知标签：当作块级容器处理 ──
        _flush_inline()
        for child in node.children:
            _process(child, list_depth)
        _flush_inline()

    _process(soup)

    # blockquote 后处理：查找 blockquote 产生的行并加前缀
    # 由于上面流程 blockquote 已经被处理为嵌套行，这里用正则标记后处理
    # 简化方案：blockquote 在 _process 中已将子内容输出到 lines
    # 但需要加 "> " 前缀 — 采用先标记后处理的策略
    # 实际采用原始 HTML 正则预处理 blockquote 更简单

    # 最终合并
    result = "\n".join(lines)

    # 清理：连续 3+ 空行压缩为 2 个
    result = re.sub(r'\n{3,}', '\n\n', result)
    # 清理行尾空白
    result = re.sub(r'[ \t]+$', '', result, flags=re.MULTILINE)

    return result.strip()


# ==================== 使用示例 ====================

def example_usage():
    """使用示例"""
    
    # 假设这是从微信获取的原始 HTML
    original_html = """
    <html>
    <body>
    <div id="js_content">
        <p>这是第一段文字</p>
        <p><img data-src="https://mmbiz.qpic.cn/image1.jpg" /></p>
        <p>这是第二段文字</p>
        <p><img data-src="https://mmbiz.qpic.cn/image2.jpg" /></p>
        <p>这是第三段文字</p>
    </div>
    </body>
    </html>
    """
    
    # 处理内容
    result = process_article_content(
        html=original_html,
        proxy_base_url="https://wechatrss.waytomaster.com"
    )
    
    print("处理后的 HTML:")
    print(result['content'])
    print("\n图片列表（按顺序）:")
    for i, img in enumerate(result['images'], 1):
        print(f"  {i}. {img}")
    
    print("\n纯文本:")
    print(result['plain_content'])


if __name__ == "__main__":
    example_usage()
