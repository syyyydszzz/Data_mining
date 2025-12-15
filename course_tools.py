"""
课程助手的工具函数
集成 LightRAG 和其他功能
"""

from langchain_core.tools import tool
import json
import logging
import os
from typing import Optional, List
from lightrag_client import get_lightrag_client

# 初始化logger（必须在使用前定义）
logger = logging.getLogger(__name__)

# 导入MCP相关工具和辅助函数
try:
    from mcp_tools import (
        mcp_navigate_page,
        mcp_take_snapshot,
        mcp_click_element,
        mcp_fill_form,
        mcp_evaluate_script,
        mcp_wait_for_text
    )
    from moodle_helpers import (
        parse_snapshot_for_text,
        parse_snapshot_for_input,
        markdown_to_moodle_html,
        validate_moodle_url,
        escape_javascript_string
    )
    MCP_TOOLS_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[TOOL] MCP tools not available: {e}")
    MCP_TOOLS_AVAILABLE = False

# 获取 LightRAG 客户端
lightrag = get_lightrag_client()

# ==================== RAG 工具 ====================

@tool
def lightrag_query(
    query: str,
    mode: str = "mix",
    include_references: bool = True,
    only_need_context: bool = False,
    response_type: str = None,
    top_k: int = None,
    chunk_top_k: int = None,
    enable_rerank: bool = None,
    hl_keywords: List[str] = None,
    ll_keywords: List[str] = None,
) -> str:
    """
    Query LightRAG knowledge base (core retrieval tool)

    Use case: When user message contains [KB_STATUS:ON] marker, retrieve relevant information from course materials

    Args:
        query: Query question (e.g., "What is RAG architecture?")
        mode: Query mode
            - "mix": Integrates knowledge graph + vector retrieval (recommended) ⭐
            - "hybrid": Combines local and global approaches
            - "local": Focuses on specific entities and direct relationships
            - "global": Analyzes broad patterns in knowledge graph
            - "naive": Simple vector similarity search
        include_references: Whether to include source references
        only_need_context: Whether to return only retrieval context (without generated answer)
        response_type: Response format preference (e.g., "Multiple Paragraphs")
        top_k / chunk_top_k / enable_rerank / hl_keywords / ll_keywords: Advanced query options

    Returns:
        JSON-formatted retrieval results containing:
        - response: RAG-generated answer (may be empty if only_need_context=True)
        - references: Source reference list
        - sources: Parsed source information list
            [{
                "type": "lecture",
                "lecture_id": 8,
                "slide_range": "26-27",
                "citation": "Data Mining Lecture 8, Slides 26-27"
            }]

    Important notes:
    - This tool should only be called when [KB_STATUS:ON] marker is detected
    - Call only once per query, do not repeat calls
    - Returns results with precise source references
    """
    logger.info(f"[TOOL] lightrag_query called: {query[:50]}... (mode={mode})")

    try:
        # 调用 LightRAG 客户端
        result = lightrag.query(
            query=query,
            mode=mode,
            include_references=include_references,
            response_type=response_type,
            top_k=top_k,
            chunk_top_k=chunk_top_k,
            enable_rerank=enable_rerank,
            hl_keywords=hl_keywords,
            ll_keywords=ll_keywords,
            only_need_context=only_need_context
        )

        # 检查是否有错误
        if result.get("status") == "error":
            return json.dumps({
                "error": result.get("error"),
                "suggestion": "Please check if LightRAG service is running (docker ps)"
            }, ensure_ascii=False, indent=2)

        if result.get("status") == "connection_error":
            return json.dumps({
                "error": "Cannot connect to LightRAG service",
                "suggestion": "Please run: cd lightrag && docker-compose up -d"
            }, ensure_ascii=False, indent=2)

        # 返回成功结果（使用正确的字段名）
        return json.dumps({
            "response": result.get("response", ""),
            "references": result.get("references", []),
            "sources": result.get("sources", []),
            "query": query,
            "mode": mode
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] lightrag_query error: {e}")
        return json.dumps({
            "error": str(e),
            "query": query
        }, ensure_ascii=False, indent=2)


# ==================== 论坛工具 ====================

@tool
def generate_forum_draft(conversation_history: str) -> str:
    """
    Generate forum post draft based on conversation history

    Use case: When user clicks "Generate Forum Post" button

    Args:
        conversation_history: Complete conversation history (JSON format)

    Returns:
        Structured forum post draft
        {
            "title": "Questions about XXX",
            "understood": "What I understand",
            "confused": "My confusion points",
            "ai_summary": "AI response summary"
        }

    Note: This tool is called by the Forum Composer Agent, do not call directly
    """
    logger.info("[TOOL] generate_forum_draft called")

    # 这个工具实际上是委托给 Forum Composer Agent 处理
    # 返回一个标记，告诉主 Agent 需要调用子智能体
    return json.dumps({
        "tool": "generate_forum_draft",
        "status": "delegating_to_subagent",
        "subagent": "forum-composer",
        "input": conversation_history
    }, ensure_ascii=False, indent=2)


@tool
def format_forum_post(draft: str) -> str:
    """
    Format forum draft as Markdown

    Args:
        draft: Forum draft (JSON string)

    Returns:
        Formatted Markdown text
    """
    logger.info("[TOOL] format_forum_post called")

    try:
        draft_dict = json.loads(draft) if isinstance(draft, str) else draft

        template = f"""# {draft_dict.get('title', 'Untitled Question')}

## What I Understand
{draft_dict.get('understood', '')}

## My Confusion Points
{draft_dict.get('confused', '')}

## AI Assistant Summary
{draft_dict.get('ai_summary', '')}

---
*This post was generated with assistance from the AI Course Assistant*
"""
        return template

    except Exception as e:
        logger.exception(f"[TOOL] format_forum_post error: {e}")
        return f"Error formatting post: {str(e)}"


@tool
async def fill_moodle_forum(
    subject: str,
    message: str,
    forum_url: Optional[str] = None
) -> str:
    """
    Fill Moodle forum post form with subject and message using Chrome DevTools MCP.
    User will review and manually submit the post.

    This tool automates the following steps:
    1. Navigate to Moodle forum page
    2. Click "Add discussion topic" button
    3. Fill Subject field with the title
    4. Fill Message field with the content (supports TinyMCE rich text editor)
    5. Leave final submission for user review

    Args:
        subject: Forum post title/subject
        message: Forum post content (Markdown format, will be converted to HTML)
        forum_url: Moodle forum URL (optional, uses MOODLE_FORUM_URL env variable if not provided)

    Returns:
        Success message with instructions, or error details

    Example:
        fill_moodle_forum(
            subject="Understanding RAG Architecture",
            message="## What I Understand\\n- RAG has three components...\\n\\n## My Questions\\n- How does..."
        )

    Note:
        - Requires Chrome browser to be open
        - User must be logged into Moodle
        - MCP server must be running (npx -y @modelcontextprotocol/server-chrome-devtools)
    """
    logger.info(f"[TOOL] fill_moodle_forum called: subject='{subject[:50]}...'")

    # 智能提取 subject：如果提供的 subject 看起来不像一个合适的标题，
    # 就从 message 中提取第一个 Markdown 标题
    import re

    should_extract_title = (
        # subject 包含指令词
        any(word in subject.lower() for word in ["post a", "write a", "create a", "about"]) or
        # subject 太短
        len(subject.strip()) < 15 or
        # subject 全是小写且没有标点
        (subject.islower() and not any(c in subject for c in ".,!?;:"))
    )

    if should_extract_title and message:
        # 从 message 中提取第一个标题
        # 支持 # Title 或 ## Title 格式
        title_match = re.search(r'^(#+\s+.+?)(\n|$)', message, re.MULTILINE)
        if title_match:
            # 提取标题文本（去掉 # 符号）
            full_heading = title_match.group(1)
            extracted_title = re.sub(r'^#+\s+', '', full_heading).strip()
            logger.info(f"[TOOL] Auto-extracted subject from message: '{extracted_title}'")
            subject = extracted_title

            # 从 message 中移除这个标题行（避免重复）
            message = message[title_match.end():].lstrip('\n')
            logger.info(f"[TOOL] Removed title heading from message to avoid duplication")
        else:
            # 如果没有 Markdown 标题，使用 message 的第一行（最多100个字符）
            first_line = message.split('\n')[0].strip()
            if len(first_line) > 100:
                first_line = first_line[:97] + "..."
            if first_line:
                logger.info(f"[TOOL] Using first line as subject: '{first_line}'")
                subject = first_line
                # 也从 message 中移除第一行
                message_lines = message.split('\n', 1)
                if len(message_lines) > 1:
                    message = message_lines[1].lstrip('\n')
                    logger.info(f"[TOOL] Removed first line from message to avoid duplication")

    logger.info(f"[TOOL] Final subject: '{subject}'")

    # 检查MCP工具是否可用
    if not MCP_TOOLS_AVAILABLE:
        return json.dumps({
            "success": False,
            "error": "MCP tools not available",
            "message": "Please install MCP dependencies: pip install mcp markdown"
        }, ensure_ascii=False, indent=2)

    # 获取论坛URL
    if not forum_url:
        forum_url = os.getenv("MOODLE_FORUM_URL", "")

    if not forum_url:
        return json.dumps({
            "success": False,
            "error": "MOODLE_FORUM_URL not configured",
            "message": "Please set MOODLE_FORUM_URL in your .env file"
        }, ensure_ascii=False, indent=2)

    # 验证URL
    if not validate_moodle_url(forum_url):
        return json.dumps({
            "success": False,
            "error": "Invalid Moodle URL",
            "message": f"The URL does not appear to be a valid Moodle forum URL: {forum_url}"
        }, ensure_ascii=False, indent=2)

    try:
        # Step 1: 导航到论坛页面
        logger.info(f"[TOOL] Navigating to forum: {forum_url}")
        nav_result = await mcp_navigate_page(forum_url, timeout=30000)
        logger.debug(f"[TOOL] Navigation result: {nav_result}")

        # Step 2: 等待并点击"Add discussion topic"按钮
        logger.info("[TOOL] Waiting for 'Add discussion topic' button...")
        await mcp_wait_for_text("Add discussion topic", timeout=10000)

        logger.info("[TOOL] Taking snapshot to find button...")
        snapshot = await mcp_take_snapshot(verbose=False)

        # 保存论坛页面快照用于调试（使用异步I/O）
        try:
            from pathlib import Path
            import asyncio
            forum_snapshot_file = Path("debug_forum_snapshot.txt")
            # 使用 asyncio.to_thread 避免 blocking I/O
            await asyncio.to_thread(forum_snapshot_file.write_text, str(snapshot), encoding='utf-8')
            logger.info(f"[TOOL] Forum snapshot saved to: {forum_snapshot_file}")
            logger.debug(f"[TOOL] Forum snapshot length: {len(str(snapshot))} chars")
        except Exception as e:
            logger.warning(f"[TOOL] Could not save forum snapshot: {e}")

        logger.info("[TOOL] Parsing snapshot for button UID...")
        logger.debug(f"[TOOL] Forum snapshot preview (first 1000 chars): {str(snapshot)[:1000]}")

        # 确保 snapshot 是字符串
        snapshot_str = str(snapshot)
        button_uid = parse_snapshot_for_text(snapshot_str, "Add discussion topic", element_type=None)

        if not button_uid:
            return json.dumps({
                "success": False,
                "error": "Could not find 'Add discussion topic' button",
                "message": "Please check the debug_forum_snapshot.txt file to see the page structure",
                "troubleshooting": [
                    "Check if you're logged into Moodle",
                    "Verify the forum URL is correct",
                    "Make sure the page has fully loaded",
                    "Review debug_forum_snapshot.txt to find the actual button text"
                ],
                "debug_files": ["debug_forum_snapshot.txt"]
            }, ensure_ascii=False, indent=2)

        logger.info(f"[TOOL] Clicking button with UID: {button_uid}")
        await mcp_click_element(button_uid)

        # Step 3: 等待表单加载并使用 JavaScript 填充
        logger.info("[TOOL] Waiting for form to load...")
        import asyncio
        await asyncio.sleep(2)  # 等待展开动画完成

        # Step 4: 使用 JavaScript 直接填充 Subject 字段（更可靠）
        logger.info("[TOOL] Filling Subject field with JavaScript...")
        escaped_subject = json.dumps(subject)

        subject_script = f"""
() => {{
    // 查找 Subject 输入框
    const subjectInput = document.querySelector('#id_subject') ||
                        document.querySelector('input[name="subject"]') ||
                        document.querySelector('input[type="text"][required]');

    if (subjectInput) {{
        subjectInput.value = {escaped_subject};
        // 触发 change 事件确保 Moodle 检测到输入
        subjectInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
        subjectInput.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return {{ success: true, method: 'direct-js' }};
    }}

    return {{ success: false, error: 'Subject input not found' }};
}}
"""

        subject_result = await mcp_evaluate_script(subject_script)
        logger.info(f"[TOOL] Subject fill result: {subject_result}")

        # Step 5: 填充Message字段（TinyMCE富文本编辑器）
        logger.info("[TOOL] Converting Markdown to HTML...")
        message_html = await markdown_to_moodle_html(message)

        logger.info("[TOOL] Preparing JavaScript to set TinyMCE content...")
        # 使用JSON转义来安全地处理HTML内容
        escaped_html = json.dumps(message_html)

        # 执行JavaScript设置编辑器内容
        script = f"""
() => {{
    // 尝试方法1: 使用TinyMCE API
    if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {{
        tinymce.activeEditor.setContent({escaped_html});
        return {{ success: true, method: 'tinymce' }};
    }}

    // 尝试方法2: 查找所有TinyMCE编辑器实例
    if (typeof tinymce !== 'undefined' && tinymce.editors && tinymce.editors.length > 0) {{
        // 找到message相关的编辑器
        for (let editor of tinymce.editors) {{
            if (editor.id && (editor.id.includes('message') || editor.id.includes('advancededitor'))) {{
                editor.setContent({escaped_html});
                return {{ success: true, method: 'tinymce-byid', id: editor.id }};
            }}
        }}
        // 如果没找到特定的，使用第一个
        tinymce.editors[0].setContent({escaped_html});
        return {{ success: true, method: 'tinymce-first' }};
    }}

    // 尝试方法3: 直接设置textarea
    const textarea = document.querySelector('textarea[name="message"]') ||
                     document.querySelector('textarea[name="message[text]"]') ||
                     document.querySelector('#id_message');
    if (textarea) {{
        textarea.value = {escaped_html};
        // 触发change事件
        textarea.dispatchEvent(new Event('change', {{ bubbles: true }}));
        return {{ success: true, method: 'textarea' }};
    }}

    return {{ success: false, error: 'No editor found' }};
}}
"""

        logger.info("[TOOL] Executing JavaScript to fill message...")
        result = await mcp_evaluate_script(script)
        logger.debug(f"[TOOL] JavaScript execution result: {result}")

        # 解析结果
        try:
            result_data = json.loads(result)
            if not result_data.get("success"):
                logger.warning(f"[TOOL] Message filling might have failed: {result}")
        except:
            pass

        # 成功完成
        logger.info("[TOOL] ✅ Form filled successfully!")
        return json.dumps({
            "success": True,
            "message": "✅ **Moodle forum post filled successfully!**\n\n" +
                       "**Next steps:**\n" +
                       "1. Review the Subject and Message in your browser\n" +
                       "2. Make any edits if needed\n" +
                       "3. Click the **'Post to forum'** button to publish\n\n" +
                       "The form is ready for your final review and submission.",
            "filled_data": {
                "subject": subject,
                "message_length": len(message),
                "message_html_length": len(message_html)
            }
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] fill_moodle_forum error: {e}")
        return json.dumps({
            "success": False,
            "error": str(e),
            "message": "❌ **Error filling Moodle forum:**\n\n" +
                       f"{str(e)}\n\n" +
                       "**Troubleshooting:**\n" +
                       "1. Make sure Chrome browser is open\n" +
                       "2. Check if you're logged into Moodle\n" +
                       "3. Verify MOODLE_FORUM_URL is correct in .env\n" +
                       "4. Try manually navigating to the forum first\n" +
                       "5. Check if MCP server is running: npx -y @modelcontextprotocol/server-chrome-devtools"
        }, ensure_ascii=False, indent=2)


# ==================== 报告生成工具 ====================

# ==================== Cheat Sheet 工具 ====================

@tool
def create_cheat_sheet(
    concept: str,
) -> str:
    """
    Create concept cheat sheet

    Use case: Quickly generate definition, workflow, advantages, challenges, etc. for a concept (only call when [KB_STATUS:ON])

    Args:
        concept: Concept name (e.g., "Transformer architecture")

    Returns:
        Cheat sheet retrieval results

    Example output:
        | Dimension | Content |
        |-----------|---------|
        | Definition | ... |
        | Workflow | ... |
        | Advantages | ... |
        | Challenges | ... |
    """
    logger.info(f"[TOOL] create_cheat_sheet: concept={concept}")

    query = f"Definition, workflow, advantages, challenges, and use cases of {concept}"

    try:
        result = lightrag.query(
            query=query,
            mode="hybrid",
            include_references=True
        )

        return json.dumps({
            "concept": concept,
            "response": result.get("response", ""),
            "references": result.get("references", []),
            "sources": result.get("sources", []),
            "format": "cheat_sheet"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] create_cheat_sheet error: {e}")
        return json.dumps({
            "error": str(e),
            "concept": concept
        }, ensure_ascii=False, indent=2)


# ==================== 工具列表导出 ====================

# ==================== 工具分组 ====================
# Main Agent 的基础工具（不包含专用工具）
BASIC_TOOLS = [
    # RAG tools
    lightrag_query,
    create_cheat_sheet,
    # Forum generation tools (内容生成，但不发布)
    generate_forum_draft,
    format_forum_post,
]

# Moodle Publisher 专用工具（只有这个subagent能用）
MOODLE_TOOLS = [
    fill_moodle_forum,  # 浏览器自动化发布
]

# 所有可用工具（兼容性保留，供需要的地方使用）
ALL_TOOLS = BASIC_TOOLS + MOODLE_TOOLS


def get_tools_by_mode(mode: str) -> List:
    """
    根据模式返回对应的工具集

    Args:
        mode: "qa" | "forum" | "report"

    Returns:
        工具列表
    """
    if mode == "qa":
        return [
            lightrag_query,
        ]
    elif mode == "forum":
        return [
            generate_forum_draft,
            format_forum_post,
        ]
    elif mode == "report":
        return [
            lightrag_query,  # 报告生成也需要检索
            create_cheat_sheet,  # Cheat sheet 生成
        ]
    else:
        return ALL_TOOLS
