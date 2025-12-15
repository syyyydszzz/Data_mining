"""
Moodle辅助函数 - 提供Moodle相关的工具函数

包括：
1. Snapshot解析：从MCP返回的页面快照中查找元素UID
2. Markdown转HTML：将Markdown格式转换为Moodle兼容的HTML
3. 元素定位：智能查找表单元素
"""

import re
import json
import logging
from typing import Optional, Dict, List

logger = logging.getLogger(__name__)


def parse_snapshot_for_text(
    snapshot: str,
    text: str,
    element_type: Optional[str] = None,
    case_sensitive: bool = False
) -> Optional[str]:
    """
    从snapshot中查找包含指定文本的元素UID（增强版）

    Args:
        snapshot: MCP返回的页面快照字符串
        text: 要查找的文本内容
        element_type: 可选的元素类型过滤（如 "button", "link"）
        case_sensitive: 是否大小写敏感（默认False）

    Returns:
        Optional[str]: 找到的元素UID，如果没找到返回None

    Example:
        uid = parse_snapshot_for_text(snapshot, "Add discussion topic", element_type="button")
    """
    try:
        search_text = text if case_sensitive else text.lower()
        lines = snapshot.split('\n')

        logger.debug(f"[Moodle Helper] Searching for text '{text}' in {len(lines)} lines")

        for i, line in enumerate(lines):
            line_to_search = line if case_sensitive else line.lower()

            # 检查是否包含目标文本
            if search_text in line_to_search:
                # 如果指定了元素类型，检查类型是否匹配
                if element_type:
                    if element_type.lower() not in line.lower():
                        continue

                logger.debug(f"[Moodle Helper] Found text at line {i}: {line[:100]}")

                # 提取UID - MCP使用 uid=xxx 格式
                uid_match = re.search(r'uid=(\S+)', line)
                if uid_match:
                    uid = uid_match.group(1)
                    logger.info(f"[Moodle Helper] Found element '{text}' with UID: {uid}")
                    return uid

                # 也尝试旧格式: [uid: xxx] 或 uid: xxx
                uid_match = re.search(r'\[?uid[:\s]+([^\]\s,]+)', line, re.IGNORECASE)
                if uid_match:
                    uid = uid_match.group(1)
                    logger.info(f"[Moodle Helper] Found element '{text}' with UID (old format): {uid}")
                    return uid

        logger.warning(f"[Moodle Helper] Could not find element with text '{text}'")
        logger.debug(f"[Moodle Helper] Snapshot preview (first 500 chars): {snapshot[:500]}")
        return None

    except Exception as e:
        logger.error(f"[Moodle Helper] Error parsing snapshot: {e}")
        return None


def parse_snapshot_for_input(
    snapshot: str,
    label: str,
    input_type: Optional[str] = None
) -> Optional[str]:
    """
    查找与label关联的输入框元素UID（增强版）

    Args:
        snapshot: MCP返回的页面快照字符串
        label: 输入框的label文本（如 "Subject", "Message"）
        input_type: 可选的输入框类型（如 "text", "textarea"）

    Returns:
        Optional[str]: 找到的输入框UID，如果没找到返回None

    Example:
        uid = parse_snapshot_for_input(snapshot, "Subject")
    """
    try:
        label_lower = label.lower()
        lines = snapshot.split('\n')

        logger.debug(f"[Moodle Helper] Searching for '{label}' field in {len(lines)} lines")

        # 方法1: 查找label后面的input
        for i, line in enumerate(lines):
            if label_lower in line.lower():
                logger.debug(f"[Moodle Helper] Found '{label}' at line {i}: {line[:100]}")

                # 检查当前行是否包含input
                if 'textbox' in line.lower() or 'entry' in line.lower():
                    # MCP snapshot中，textbox/entry 通常表示输入框
                    uid_match = re.search(r'uid=(\S+)', line)
                    if uid_match:
                        uid = uid_match.group(1)
                        logger.info(f"[Moodle Helper] Found input in same line with UID: {uid}")
                        return uid

                # 检查接下来的10行（增加搜索范围）
                for j in range(i + 1, min(i + 11, len(lines))):
                    next_line = lines[j]

                    # 查找textbox或entry（MCP使用的术语）
                    if 'textbox' in next_line.lower() or 'entry' in next_line.lower():
                        # 检查类型是否匹配
                        if input_type:
                            if input_type.lower() not in next_line.lower():
                                continue

                        # 提取UID
                        uid_match = re.search(r'uid=(\S+)', next_line)
                        if uid_match:
                            uid = uid_match.group(1)
                            logger.info(f"[Moodle Helper] Found input at line {j} with UID: {uid}")
                            return uid

        # 方法2: 如果方法1失败，尝试查找任何包含label关键词的textbox
        logger.debug(f"[Moodle Helper] Method 1 failed, trying method 2: search for textbox with '{label}'")
        for i, line in enumerate(lines):
            if 'textbox' in line.lower() and label_lower in line.lower():
                uid_match = re.search(r'uid=(\S+)', line)
                if uid_match:
                    uid = uid_match.group(1)
                    logger.info(f"[Moodle Helper] Found textbox with '{label}' in text, UID: {uid}")
                    return uid

        # 方法3: 查找input[name="subject"]这样的模式
        logger.debug(f"[Moodle Helper] Method 2 failed, trying method 3: search by name attribute")
        name_pattern = label_lower
        for line in lines:
            if f'name="{name_pattern}"' in line.lower() or f"name='{name_pattern}'" in line.lower():
                uid_match = re.search(r'uid=(\S+)', line)
                if uid_match:
                    uid = uid_match.group(1)
                    logger.info(f"[Moodle Helper] Found input by name attribute, UID: {uid}")
                    return uid

        logger.warning(f"[Moodle Helper] Could not find input for label '{label}' using any method")
        # 输出部分快照用于调试
        logger.debug(f"[Moodle Helper] Snapshot preview (first 500 chars): {snapshot[:500]}")
        return None

    except Exception as e:
        logger.error(f"[Moodle Helper] Error finding input: {e}")
        return None


async def markdown_to_moodle_html(markdown_text: str) -> str:
    """
    将Markdown格式转换为Moodle兼容的HTML (异步版本)

    Moodle的TinyMCE编辑器支持标准HTML。
    这个函数将Markdown转换为干净的HTML。

    Args:
        markdown_text: Markdown格式的文本

    Returns:
        str: HTML格式的文本

    Example:
        html = await markdown_to_moodle_html("## Title\\n- Item 1\\n- Item 2")
    """
    try:
        # 尝试导入markdown库
        try:
            import markdown
            from markdown.extensions import extra, nl2br, tables
        except ImportError:
            logger.warning("[Moodle Helper] markdown library not installed, using simple conversion")
            # 简单的Markdown转换（如果没有安装markdown库）
            return simple_markdown_to_html(markdown_text)

        # 使用asyncio.to_thread将同步的markdown转换移到线程池
        # 这样可以避免LangGraph的blocking I/O检测
        import asyncio
        html = await asyncio.to_thread(
            markdown.markdown,
            markdown_text,
            extensions=['extra', 'nl2br', 'tables']
        )

        logger.debug(f"[Moodle Helper] Converted Markdown to HTML ({len(html)} chars)")
        return html

    except Exception as e:
        logger.error(f"[Moodle Helper] Error converting Markdown: {e}")
        # 出错时使用简单转换而不是返回原始文本
        logger.info("[Moodle Helper] Falling back to simple conversion")
        return simple_markdown_to_html(markdown_text)


def simple_markdown_to_html(text: str) -> str:
    """
    简单的Markdown到HTML转换（不依赖markdown库）

    只支持基本的Markdown语法：
    - ## 标题 -> <h2>
    - **粗体** -> <strong>
    - *斜体* -> <em>
    - - 列表 -> <ul><li>
    - 段落分隔

    Args:
        text: Markdown文本

    Returns:
        str: 简单转换后的HTML
    """
    html_lines = []
    in_list = False

    for line in text.split('\n'):
        line = line.strip()

        if not line:
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append('<br>')
            continue

        # 标题
        if line.startswith('## '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h2>{line[3:]}</h2>')
        elif line.startswith('# '):
            if in_list:
                html_lines.append('</ul>')
                in_list = False
            html_lines.append(f'<h1>{line[2:]}</h1>')

        # 列表项
        elif line.startswith('- ') or line.startswith('* '):
            if not in_list:
                html_lines.append('<ul>')
                in_list = True
            html_lines.append(f'<li>{line[2:]}</li>')

        # 普通段落
        else:
            if in_list:
                html_lines.append('</ul>')
                in_list = False

            # 处理粗体和斜体
            line = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', line)
            line = re.sub(r'\*(.+?)\*', r'<em>\1</em>', line)

            html_lines.append(f'<p>{line}</p>')

    if in_list:
        html_lines.append('</ul>')

    return '\n'.join(html_lines)


def extract_forum_post_from_draft(draft: str) -> Dict[str, str]:
    """
    从forum draft中提取subject和message

    支持两种格式：
    1. JSON格式：{"title": "...", "understood": "...", ...}
    2. Markdown格式：# Title\\n## What I Understand\\n...

    Args:
        draft: Forum draft字符串（JSON或Markdown）

    Returns:
        Dict[str, str]: 包含 "subject" 和 "message" 的字典

    Example:
        result = extract_forum_post_from_draft(draft_json)
        # {"subject": "Understanding RAG", "message": "## What I Understand..."}
    """
    try:
        # 尝试解析为JSON
        try:
            data = json.loads(draft)
            subject = data.get("title", "Forum Post")

            # 组合message部分
            message_parts = []
            if "understood" in data and data["understood"]:
                message_parts.append(f"## What I Understand\n{data['understood']}")
            if "confused" in data and data["confused"]:
                message_parts.append(f"\n\n## My Confusion Points\n{data['confused']}")
            if "ai_summary" in data and data["ai_summary"]:
                message_parts.append(f"\n\n## AI Assistant Summary\n{data['ai_summary']}")

            message = "\n".join(message_parts)

            return {"subject": subject, "message": message}

        except json.JSONDecodeError:
            # 不是JSON，尝试从Markdown中提取
            lines = draft.split('\n')
            subject = "Forum Post"
            message = draft

            # 查找第一个 # 标题作为subject
            for line in lines:
                if line.startswith('# '):
                    subject = line[2:].strip()
                    # 从这一行之后开始作为message
                    idx = draft.find(line)
                    if idx >= 0:
                        message = draft[idx + len(line):].strip()
                    break

            return {"subject": subject, "message": message}

    except Exception as e:
        logger.error(f"[Moodle Helper] Error extracting forum post: {e}")
        return {"subject": "Forum Post", "message": draft}


def validate_moodle_url(url: str) -> bool:
    """
    验证URL是否是有效的Moodle论坛URL

    Args:
        url: 要验证的URL

    Returns:
        bool: 如果是有效的Moodle URL返回True

    Example:
        is_valid = validate_moodle_url("https://moodle.hku.hk/mod/forum/view.php?id=123")
    """
    if not url:
        return False

    # 检查是否包含moodle域名
    if 'moodle' not in url.lower():
        logger.warning(f"[Moodle Helper] URL does not contain 'moodle': {url}")
        return False

    # 检查是否是HTTPS
    if not url.startswith('https://'):
        logger.warning(f"[Moodle Helper] URL is not HTTPS: {url}")
        return False

    # 检查是否是论坛相关URL
    if '/mod/forum/' not in url and '/forum/' not in url:
        logger.warning(f"[Moodle Helper] URL does not appear to be a forum URL: {url}")
        return False

    return True


def escape_javascript_string(text: str) -> str:
    """
    转义字符串以便在JavaScript中安全使用

    Args:
        text: 要转义的字符串

    Returns:
        str: 转义后的字符串

    Example:
        safe_text = escape_javascript_string("It's a \"test\"")
    """
    # 转义反斜杠
    text = text.replace('\\', '\\\\')
    # 转义引号
    text = text.replace('"', '\\"')
    text = text.replace("'", "\\'")
    # 转义换行符
    text = text.replace('\n', '\\n')
    text = text.replace('\r', '\\r')
    # 转义反引号（用于模板字符串）
    text = text.replace('`', '\\`')
    # 转义$（用于模板字符串）
    text = text.replace('$', '\\$')

    return text
