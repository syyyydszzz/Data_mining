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


@tool
def get_lecture_content(
    lecture_id: int,
    slide_range: str,
) -> str:
    """
    Get specific slide content from a lecture

    Use case: When precise location of content from a specific lecture is needed (only call when [KB_STATUS:ON])

    Args:
        lecture_id: Lecture number (1-12, depending on course)
        slide_range: Slide range (e.g., "26-27" or "15")

    Returns:
        JSON-formatted lecture content and source information

    Example:
        get_lecture_content(8, "26-27")
        → Returns content from Lecture 8, slides 26-27
    """
    logger.info(f"[TOOL] get_lecture_content: Lecture {lecture_id}, Slides {slide_range}")

    query = f"Content of Lecture {lecture_id}, Slides {slide_range}"

    try:
        # 使用 local 模式进行精确检索
        result = lightrag.query(
            query=query,
            mode="local",
            include_references=True
        )

        return json.dumps({
            "lecture_id": lecture_id,
            "slide_range": slide_range,
            "response": result.get("response", ""),
            "references": result.get("references", []),
            "sources": result.get("sources", []),
            "citation": f"Data Mining Lecture {lecture_id}, Slides {slide_range}"
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] get_lecture_content error: {e}")
        return json.dumps({
            "error": str(e),
            "lecture_id": lecture_id,
            "slide_range": slide_range
        }, ensure_ascii=False, indent=2)


@tool
def search_exam_papers(
    topic: str,
    year: Optional[str] = None,
) -> str:
    """
    Search past exam papers for related questions

    Use case: Find exam questions and answers about a topic from past exams (only call when [KB_STATUS:ON])

    Args:
        topic: Topic (e.g., "RAG architecture", "Transformer")
        year: Optional year filter (e.g., "2023")

    Returns:
        JSON-formatted exam questions and source information

    Example:
        search_exam_papers("RAG architecture", "2023")
        → Returns questions about RAG from 2023 exam
    """
    logger.info(f"[TOOL] search_exam_papers: topic={topic}, year={year}")

    query = f"Past exam questions about {topic}"
    if year:
        query += f" (year {year})"

    try:
        result = lightrag.query(
            query=query,
            mode="hybrid",
            include_references=True
        )

        return json.dumps({
            "topic": topic,
            "year": year,
            "response": result.get("response", ""),
            "references": result.get("references", []),
            "sources": result.get("sources", [])
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] search_exam_papers error: {e}")
        return json.dumps({
            "error": str(e),
            "topic": topic
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

        logger.info("[TOOL] Parsing snapshot for button UID...")
        button_uid = parse_snapshot_for_text(snapshot, "Add discussion topic", element_type="button")

        if not button_uid:
            return json.dumps({
                "success": False,
                "error": "Could not find 'Add discussion topic' button",
                "message": "Please make sure you're on the Moodle forum page and try again",
                "troubleshooting": [
                    "Check if you're logged into Moodle",
                    "Verify the forum URL is correct",
                    "Make sure the page has fully loaded"
                ]
            }, ensure_ascii=False, indent=2)

        logger.info(f"[TOOL] Clicking button with UID: {button_uid}")
        await mcp_click_element(button_uid)

        # Step 3: 等待表单加载
        logger.info("[TOOL] Waiting for form to load...")
        await mcp_wait_for_text("Subject", timeout=10000)

        # Step 4: 填充Subject字段
        logger.info("[TOOL] Taking snapshot to find form fields...")
        snapshot = await mcp_take_snapshot(verbose=False)

        logger.info("[TOOL] Finding Subject input field...")
        subject_uid = parse_snapshot_for_input(snapshot, "Subject")

        if not subject_uid:
            return json.dumps({
                "success": False,
                "error": "Could not find Subject input field",
                "message": "The form structure may have changed. Please fill the form manually.",
                "debug_info": "Subject field UID not found in snapshot"
            }, ensure_ascii=False, indent=2)

        logger.info(f"[TOOL] Filling Subject field with UID: {subject_uid}")
        await mcp_fill_form(subject_uid, subject)

        # Step 5: 填充Message字段（TinyMCE富文本编辑器）
        logger.info("[TOOL] Converting Markdown to HTML...")
        message_html = markdown_to_moodle_html(message)

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

@tool
def generate_study_report(
    topic: str,
    lectures: str,  # JSON list as string, e.g., "[7, 8, 9]"
    include_examples: bool = True
) -> str:
    """
    Generate personalized study report

    Use case: When user requests review materials for a topic

    Args:
        topic: Topic (e.g., "RAG architecture")
        lectures: Lecture range (JSON list string, e.g., "[7, 8, 9]")
        include_examples: Whether to include examples

    Returns:
        Structured study report metadata (actual report generated by Study Material Generator Agent)

    Note: This tool is called by the Study Material Generator Agent
    """
    logger.info(f"[TOOL] generate_study_report: topic={topic}, lectures={lectures}")

    try:
        lectures_list = json.loads(lectures) if isinstance(lectures, str) else lectures

        return json.dumps({
            "tool": "generate_study_report",
            "status": "delegating_to_subagent",
            "subagent": "study-material-generator",
            "topic": topic,
            "lectures": lectures_list,
            "include_examples": include_examples
        }, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.exception(f"[TOOL] generate_study_report error: {e}")
        return json.dumps({
            "error": str(e),
            "topic": topic
        }, ensure_ascii=False, indent=2)


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

# 所有可用工具
ALL_TOOLS = [
    # RAG tools
    lightrag_query,
    get_lecture_content,
    search_exam_papers,
    # Forum tools
    generate_forum_draft,
    format_forum_post,
    fill_moodle_forum,  # Moodle发布工具
    # Report tools
    generate_study_report,
    create_cheat_sheet,
]


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
            get_lecture_content,
            search_exam_papers,
        ]
    elif mode == "forum":
        return [
            generate_forum_draft,
            format_forum_post,
        ]
    elif mode == "report":
        return [
            lightrag_query,  # 报告生成也需要检索
            generate_study_report,
            create_cheat_sheet,
        ]
    else:
        return ALL_TOOLS
