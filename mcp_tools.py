"""
MCP工具包装 - 将Chrome DevTools MCP工具包装为可调用的异步函数

这个模块将MCP服务器提供的Chrome DevTools工具包装成普通的异步函数。
这些函数可以被其他工具（如fill_moodle_forum）直接调用。

注意：这些函数不是LangChain tools，只是内部辅助函数。
只有fill_moodle_forum是暴露给agent的@tool。
"""

import json
import logging
from typing import Any, Dict, Optional
from mcp_config import mcp_client

logger = logging.getLogger(__name__)


async def mcp_navigate_page(url: str, timeout: int = 30000) -> str:
    """
    Navigate to a URL using Chrome browser via MCP.

    Use this tool to open a web page in the user's Chrome browser.
    The browser must be running for this to work.

    Args:
        url: Target URL to navigate to (e.g., "https://moodle.hku.hk/...")
        timeout: Maximum wait time in milliseconds (default: 30000 = 30 seconds)

    Returns:
        JSON string with navigation result

    Example:
        mcp_navigate_page("https://moodle.hku.hk/mod/forum/view.php?id=3735524")
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__navigate_page",
            {
                "url": url,
                "timeout": timeout,
                "type": "url"
            }
        )
        return json.dumps({"success": True, "result": str(result)}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MCP Tool] navigate_page failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def mcp_take_snapshot(verbose: bool = False) -> str:
    """
    Take a text snapshot of the current page to get element UIDs.

    This tool captures the accessibility tree of the page, which includes
    all interactive elements with unique identifiers (UIDs). Use these UIDs
    with other tools like mcp_click_element or mcp_fill_form.

    Args:
        verbose: If True, include detailed accessibility tree info (default: False)

    Returns:
        String containing page snapshot with element UIDs

    Example usage flow:
        1. Take snapshot to get page structure
        2. Find the UID of the element you want to interact with
        3. Use that UID with mcp_click_element or mcp_fill_form

    Note:
        Always use the latest snapshot. Take a new snapshot after page changes.
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__take_snapshot",
            {"verbose": verbose}
        )
        # result应该已经是字符串格式的snapshot
        if isinstance(result, dict):
            return json.dumps(result, ensure_ascii=False)
        return str(result)
    except Exception as e:
        logger.error(f"[MCP Tool] take_snapshot failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def mcp_click_element(uid: str, dblClick: bool = False) -> str:
    """
    Click an element on the page by its UID.

    Use this tool to click buttons, links, or other clickable elements.
    You must first use mcp_take_snapshot to get the element's UID.

    Args:
        uid: Element UID from the page snapshot (e.g., "element-123")
        dblClick: If True, perform a double-click instead of single-click (default: False)

    Returns:
        JSON string with click result

    Example:
        # First take snapshot to get UIDs
        snapshot = await mcp_take_snapshot()
        # Find "Add discussion topic" button's UID in snapshot
        # Then click it
        mcp_click_element(uid="button-456")
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__click",
            {
                "uid": uid,
                "dblClick": dblClick
            }
        )
        return json.dumps({"success": True, "result": str(result)}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MCP Tool] click_element failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def mcp_fill_form(uid: str, value: str) -> str:
    """
    Fill a form field (input, textarea, select) with a value.

    Use this tool to type text into input fields, text areas, or select
    options from dropdown menus. You must first use mcp_take_snapshot
    to get the element's UID.

    Args:
        uid: Element UID from the page snapshot
        value: The text value to fill in, or option to select

    Returns:
        JSON string with fill result

    Example:
        # Fill a subject field
        mcp_fill_form(uid="input-789", value="Understanding RAG Architecture")

        # Fill a textarea
        mcp_fill_form(uid="textarea-101", value="My question is...")
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__fill",
            {
                "uid": uid,
                "value": value
            }
        )
        return json.dumps({"success": True, "result": str(result)}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MCP Tool] fill_form failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def mcp_evaluate_script(function: str, args: Optional[list] = None) -> str:
    """
    Execute JavaScript code in the current page context.

    Use this tool to run JavaScript for complex interactions that aren't
    possible with standard form filling (e.g., interacting with TinyMCE
    rich text editor).

    Args:
        function: JavaScript function declaration as a string
                 Format: "() => { return document.title; }"
                 or with args: "(el) => { return el.innerText; }"
        args: Optional list of arguments. Each arg should be a dict with "uid" key
              pointing to an element from the snapshot

    Returns:
        JSON string with execution result

    Example:
        # Get page title
        mcp_evaluate_script("() => { return document.title; }")

        # Set TinyMCE content
        mcp_evaluate_script('''
        () => {
            if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
                tinymce.activeEditor.setContent("<p>Hello</p>");
                return { success: true };
            }
            return { success: false };
        }
        ''')
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__evaluate_script",
            {
                "function": function,
                "args": args or []
            }
        )
        return json.dumps({"success": True, "result": result}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MCP Tool] evaluate_script failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


async def mcp_wait_for_text(text: str, timeout: int = 30000) -> str:
    """
    Wait for specific text to appear on the page.

    Use this tool to wait for page content to load before proceeding
    with other actions. This is useful after navigation or clicking buttons.

    Args:
        text: Text string to wait for (case-sensitive)
        timeout: Maximum wait time in milliseconds (default: 30000 = 30 seconds)

    Returns:
        JSON string with wait result

    Example:
        # Wait for forum page to load
        mcp_wait_for_text("Add discussion topic", timeout=10000)

        # Wait for form to appear
        mcp_wait_for_text("Subject", timeout=5000)
    """
    try:
        result = await mcp_client.call_tool(
            "mcp__chrome-devtools__wait_for",
            {
                "text": text,
                "timeout": timeout
            }
        )
        return json.dumps({"success": True, "result": str(result)}, ensure_ascii=False)
    except Exception as e:
        logger.error(f"[MCP Tool] wait_for_text failed: {e}")
        return json.dumps({"success": False, "error": str(e)}, ensure_ascii=False)


# 注意：这些函数已改为普通的异步函数（不再是@tool装饰的LangChain工具）
# 它们是内部辅助函数，可以被其他工具直接调用
# 不需要添加到agent的工具列表中

__all__ = [
    'mcp_navigate_page',
    'mcp_take_snapshot',
    'mcp_click_element',
    'mcp_fill_form',
    'mcp_evaluate_script',
    'mcp_wait_for_text',
]
