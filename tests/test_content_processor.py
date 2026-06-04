"""Tests for utils.content_processor — html_to_markdown"""
import unittest
from utils.content_processor import html_to_markdown


class TestHtmlToMarkdown(unittest.TestCase):
    """HTML → Obsidian 规范 Markdown 转换测试"""

    # ========== 基本标签转换 ==========

    def test_h1_to_h6_atx_headings(self):
        """h1~h6 → # ~ ###### ATX 标题"""
        html = "<h1>一级</h1><h2>二级</h2><h3>三级</h3><h4>四级</h4><h5>五级</h5><h6>六级</h6>"
        md = html_to_markdown(html)
        self.assertIn("# 一级", md)
        self.assertIn("## 二级", md)
        self.assertIn("### 三级", md)
        self.assertIn("#### 四级", md)
        self.assertIn("##### 五级", md)
        self.assertIn("###### 六级", md)

    def test_paragraph(self):
        """<p> → 纯段落文本"""
        md = html_to_markdown("<p>一段普通文字</p>")
        self.assertIn("一段普通文字", md)
        # 不应该包含 HTML 标签
        self.assertNotIn("<p>", md)
        self.assertNotIn("</p>", md)

    def test_strong_and_b_to_bold(self):
        """<strong>/<b> → **粗体**"""
        md = html_to_markdown("<p>前面<strong>加粗</strong>中间<b>也加粗</b>后面</p>")
        self.assertIn("**加粗**", md)
        self.assertIn("**也加粗**", md)
        self.assertNotIn("<strong>", md)
        self.assertNotIn("<b>", md)

    def test_em_and_i_to_italic(self):
        """<em>/<i> → *斜体*"""
        md = html_to_markdown("<p>前面<em>斜体</em>中间<i>也斜体</i>后面</p>")
        self.assertIn("*斜体*", md)
        self.assertIn("*也斜体*", md)
        self.assertNotIn("<em>", md)
        self.assertNotIn("<i>", md)

    def test_link_to_markdown_link(self):
        """<a href="...">text</a> → [text](url)"""
        md = html_to_markdown('<a href="https://example.com">点这里</a>')
        self.assertIn("[点这里](https://example.com)", md)
        self.assertNotIn("<a ", md)

    def test_image_to_markdown_image(self):
        """<img> → ![alt](url)"""
        md = html_to_markdown('<img src="http://mmbiz.qpic.cn/test.jpg" alt="配图"/>')
        self.assertIn("![配图](http://mmbiz.qpic.cn/test.jpg)", md)
        self.assertNotIn("<img", md)

    def test_image_without_alt(self):
        """<img 无 alt → ![](url)"""
        md = html_to_markdown('<img src="http://mmbiz.qpic.cn/test.jpg"/>')
        self.assertIn("![](http://mmbiz.qpic.cn/test.jpg)", md)

    # ========== 列表 ==========

    def test_unordered_list(self):
        """<ul>/<li> → - 列表"""
        md = html_to_markdown("<ul><li>项目A</li><li>项目B</li><li>项目C</li></ul>")
        lines = md.strip().split("\n")
        self.assertTrue(any(line.strip().startswith("- ") for line in lines),
                        f"无序列表应该以 '- ' 开头，实际: {lines}")
        self.assertIn("项目A", md)
        self.assertIn("项目B", md)
        self.assertIn("项目C", md)

    def test_ordered_list(self):
        """<ol>/<li> → 1. 列表"""
        md = html_to_markdown("<ol><li>第一步</li><li>第二步</li><li>第三步</li></ol>")
        lines = md.strip().split("\n")
        self.assertTrue(any(line.strip().startswith("1. ") for line in lines),
                        f"有序列表应该以 '1. ' 开头，实际: {lines}")
        self.assertIn("第一步", md)
        self.assertIn("第二步", md)
        self.assertIn("第三步", md)

    # ========== 表格 ==========

    def test_table_to_pipe_table(self):
        """<table> → Obsidian pipe table"""
        html = """<table>
            <thead><tr><th>姓名</th><th>年龄</th></tr></thead>
            <tbody><tr><td>张三</td><td>28</td></tr><tr><td>李四</td><td>35</td></tr></tbody>
        </table>"""
        md = html_to_markdown(html)
        # Obsidian pipe table: 应有表头分隔行
        self.assertIn("姓名", md)
        self.assertIn("年龄", md)
        self.assertIn("张三", md)
        self.assertIn("28", md)
        self.assertIn("李四", md)
        self.assertIn("35", md)
        # 应有分隔行标记
        self.assertTrue("---" in md or " - " in md,
                        f"表格应该有分隔行，实际: {md}")
        # 不应保留 HTML 表格标签
        self.assertNotIn("<table>", md)
        self.assertNotIn("<thead>", md)

    # ========== 代码 ==========

    def test_inline_code(self):
        """<code> → 行内代码"""
        md = html_to_markdown("<p>用 <code>print()</code> 输出</p>")
        self.assertIn("`print()`", md)
        self.assertNotIn("<code>", md)

    def test_pre_code_block(self):
        """<pre> → 围栏代码块"""
        md = html_to_markdown("<pre>def hello():\n    print('hi')</pre>")
        self.assertIn("```", md)
        self.assertIn("def hello()", md)

    # ========== 引用 ==========

    def test_blockquote(self):
        """<blockquote> → > 引用"""
        md = html_to_markdown("<blockquote>引用文字</blockquote>")
        self.assertTrue(
            "引用文字" in md and md.strip().startswith(">"),
            f"引用应该以 '>' 开头，实际: {md}"
        )

    # ========== 换行 ==========

    def test_br_soft_break(self):
        """<br> → 软换行"""
        md = html_to_markdown("<p>第一行<br>第二行</p>")
        # markdownify 将 <br> 转为 backslash 或两个空格换行
        self.assertIn("第一行", md)
        self.assertIn("第二行", md)
        # 确认不含 <br> 标签
        self.assertNotIn("<br>", md)
        self.assertNotIn("<br/>", md)

    # ========== CSS/属性剥离 ==========

    def test_strips_style_attribute(self):
        """移除 style 属性"""
        md = html_to_markdown('<p style="color: red; font-size: 20px;">红色文字</p>')
        self.assertIn("红色文字", md)
        self.assertNotIn("color: red", md)
        self.assertNotIn("font-size", md)
        self.assertNotIn("style=", md)

    def test_strips_class_attribute(self):
        """移除 class 属性"""
        md = html_to_markdown('<p class="rich_media_content article-body">正文内容</p>')
        self.assertIn("正文内容", md)
        self.assertNotIn("rich_media_content", md)
        self.assertNotIn("article-body", md)
        self.assertNotIn("class=", md)

    def test_strips_script_tags(self):
        """删除 <script> 标签及其内容"""
        md = html_to_markdown('<p>可见</p><script>alert("xss")</script><p>也可见</p>')
        self.assertIn("可见", md)
        self.assertIn("也可见", md)
        self.assertNotIn("alert", md)
        self.assertNotIn("xss", md)

    def test_strips_style_tags(self):
        """删除 <style> 标签及其内容"""
        md = html_to_markdown('<p>可见</p><style>body{color:red;}</style><p>也可见</p>')
        self.assertIn("可见", md)
        self.assertIn("也可见", md)
        self.assertNotIn("body{", md)
        self.assertNotIn("color:red", md)

    # ========== 容器标签剥离 ==========

    def test_strips_span_keeps_text(self):
        """<span> 剥离标签但保留内部文本"""
        md = html_to_markdown('<p>前面<span class="highlight">重点</span>后面</p>')
        self.assertIn("前面", md)
        self.assertIn("重点", md)
        self.assertIn("后面", md)
        self.assertNotIn("<span>", md)

    def test_strips_div_keeps_text(self):
        """<div> 剥离标签但保留内部文本和嵌套内容"""
        md = html_to_markdown('<div class="wrapper"><p>内部段落</p></div>')
        self.assertIn("内部段落", md)
        self.assertNotIn("wrapper", md)

    def test_strips_section_keeps_text(self):
        """<section> 剥离标签但保留内部文本"""
        md = html_to_markdown('<section><h2>章节标题</h2><p>章节内容</p></section>')
        self.assertIn("## 章节标题", md)
        self.assertIn("章节内容", md)
        self.assertNotIn("<section>", md)

    # ========== 边界情况 ==========

    def test_empty_string_returns_empty(self):
        """空字符串返回空"""
        self.assertEqual(html_to_markdown(""), "")

    def test_none_or_whitespace_returns_empty(self):
        """None 或纯空白返回空"""
        self.assertEqual(html_to_markdown(None), "")
        self.assertEqual(html_to_markdown("   \n   "), "")

    def test_preserves_chinese_characters(self):
        """保留中文字符不转换"""
        md = html_to_markdown("<p>你好，世界！今天是一个好天气🎉</p>")
        self.assertIn("你好，世界！", md)
        self.assertIn("🎉", md)

    def test_multiple_blank_lines_compressed(self):
        """连续 3+ 空行压缩为最多 2 个"""
        md = html_to_markdown("<p>A</p><br><br><br><br><p>B</p>")
        self.assertIn("A", md)
        self.assertIn("B", md)
        # 不能有 3 个连续空行
        self.assertFalse("\n\n\n" in md,
                         f"连续空行应被压缩，实际有 3+ 空行: {repr(md)}")

    def test_wechat_article_html_structure(self):
        """模拟微信文章 HTML 结构：多层嵌套 section/div"""
        html = """<section class="article">
            <div class="rich_media_content">
                <h1>文章标题</h1>
                <p class="author">作者：<strong>张三</strong></p>
                <p style="text-indent: 2em;">第一段正文内容，介绍<a href="https://mp.example.com">相关链接</a>的内容。</p>
                <img src="/api/image?url=http%3A%2F%2Fmmbiz.qpic.cn%2Fphoto.jpg" alt="配图" style="width:100%"/>
                <p style="text-indent: 2em;">第二段，包含<em>斜体</em>和<code>代码</code>片段。</p>
                <blockquote>引用资料说明</blockquote>
                <ul><li>要点一</li><li>要点二</li></ul>
            </div>
        </section>"""
        md = html_to_markdown(html)

        # 标题
        self.assertIn("# 文章标题", md)
        # 粗体
        self.assertIn("**张三**", md)
        # 链接
        self.assertIn("[相关链接](https://mp.example.com)", md)
        # 图片
        self.assertIn("![配图](/api/image?url=http%3A%2F%2Fmmbiz.qpic.cn%2Fphoto.jpg)", md)
        # 斜体
        self.assertIn("*斜体*", md)
        # 代码
        self.assertIn("`代码`", md)
        # 引用
        self.assertIn(">", md)
        self.assertIn("引用资料说明", md)
        # 列表
        self.assertIn("要点一", md)
        self.assertIn("要点二", md)
        # 不应包含 CSS
        self.assertNotIn("style=", md)
        self.assertNotIn("text-indent", md)
        self.assertNotIn("width:100%", md)
        # 不应包含容器标签
        self.assertNotIn("<section>", md)
        self.assertNotIn("<div>", md)
        # 不应包含 class
        self.assertNotIn("rich_media_content", md)
        self.assertNotIn("class=\"author\"", md)
