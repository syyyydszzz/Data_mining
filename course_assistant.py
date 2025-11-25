"""
智能课程助手 - 主程序
基于 DeepAgents 框架构建
"""

import os
import json
import logging
from dotenv import load_dotenv

# LangChain imports
from langchain_anthropic import ChatAnthropic

# DeepAgents
from deepagents import create_deep_agent

# Local imports
from course_tools import (
    BASIC_TOOLS,
    MOODLE_TOOLS,
    lightrag_query,
    create_cheat_sheet,
    generate_forum_draft,
    format_forum_post,
    fill_moodle_forum,  # Moodle发布工具
)
from lightrag_client import get_lightrag_client

# MCP imports (可选，如果未安装不影响其他功能)
# 注意：mcp_tools中的函数现在是内部辅助函数，不再暴露给agent
# 只有fill_moodle_forum是暴露给agent的工具
try:
    from mcp_config import mcp_client, initialize_mcp
    MCP_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️  MCP tools not available: {e}")
    logger.warning("⚠️  Moodle forum publishing feature will not be available")
    MCP_AVAILABLE = False

# 创建工具名称到工具对象的映射
TOOL_MAP = {
    # RAG工具
    "lightrag_query": lightrag_query,
    "create_cheat_sheet": create_cheat_sheet,
    # 论坛工具
    "generate_forum_draft": generate_forum_draft,
    "format_forum_post": format_forum_post,
    "fill_moodle_forum": fill_moodle_forum,  # Moodle发布
}

# 注意：MCP wrapper functions (mcp_navigate_page等) 不再是独立工具
# 它们是内部辅助函数，只被fill_moodle_forum使用
# fill_moodle_forum已经包含在上面的TOOL_MAP中

# === 配置日志 ===
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# === 加载环境变量 ===
load_dotenv()

# === 配置参数 ===
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")  # 中转 API URL（可选）
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")
RECURSION_LIMIT = int(os.getenv("RECURSION_LIMIT", 30))
LIGHTRAG_BASE_URL = os.getenv("LIGHTRAG_BASE_URL", "http://localhost:9621")
LIGHTRAG_API_KEY = os.getenv("LIGHTRAG_API_KEY")

# === 验证配置 ===
if not ANTHROPIC_API_KEY:
    logger.warning("⚠️  ANTHROPIC_API_KEY not found in .env file")
    logger.warning("⚠️  Please set your Claude API key to use the assistant")

# === 加载系统指令 ===
logger.info("📖 Loading system instructions...")
with open("course_instructions.md", "r", encoding="utf-8") as f:
    SYSTEM_INSTRUCTIONS = f.read()
logger.info("✅ System instructions loaded")

# === 加载子智能体配置 ===
logger.info("🤖 Loading subagent configurations...")
with open("course_subagents.json", "r", encoding="utf-8") as f:
    subagents_config = json.load(f)

# 将工具名称转换为工具对象
def convert_tools(tool_names: list) -> list:
    """将工具名称列表转换为工具对象列表"""
    return [TOOL_MAP[name] for name in tool_names if name in TOOL_MAP]

# 提取子智能体并转换工具
knowledge_retriever = subagents_config["knowledge_retriever"].copy()
knowledge_retriever["tools"] = convert_tools(knowledge_retriever.get("tools", []))

forum_composer = subagents_config["forum_composer"].copy()
forum_composer["tools"] = convert_tools(forum_composer.get("tools", []))

cheat_sheet_generator = subagents_config["cheat_sheet_generator"].copy()
cheat_sheet_generator["tools"] = convert_tools(cheat_sheet_generator.get("tools", []))

moodle_publisher = subagents_config["moodle_publisher"].copy()
# moodle_publisher 使用独占的 MOODLE_TOOLS（fill_moodle_forum）
moodle_publisher["tools"] = MOODLE_TOOLS

logger.info(f"✅ Loaded {len(subagents_config)} subagents:")
for name in subagents_config.keys():
    logger.info(f"   - {name}")

# === 检查 LightRAG 连接 ===
logger.info("🔍 Checking LightRAG connection...")
lightrag_client = get_lightrag_client(
    base_url=LIGHTRAG_BASE_URL,
    api_key=LIGHTRAG_API_KEY,
)
if lightrag_client.health_check():
    logger.info(f"✅ LightRAG is running at {LIGHTRAG_BASE_URL}")
else:
    logger.warning(f"⚠️  Cannot connect to LightRAG at {LIGHTRAG_BASE_URL}")
    logger.warning("⚠️  Please ensure Docker container is running:")
    logger.warning("     cd lightrag && docker-compose up -d")

# === 初始化 MCP (Chrome DevTools) ===
# 注意：MCP 初始化是异步的，但 LangGraph Server 会在需要时自动处理
# 这里只记录可用性，实际连接在首次工具调用时进行
if MCP_AVAILABLE:
    logger.info("🌐 MCP (Chrome DevTools) is available")
    logger.info("ℹ️  MCP will auto-connect when publishing to Moodle")
    logger.info("ℹ️  Chrome will be started automatically by MCP")
else:
    logger.info("ℹ️  MCP not available - Install with: pip install mcp markdown")

# === 初始化 Claude 模型 ===
logger.info(f"🧠 Initializing Claude model: {CLAUDE_MODEL}...")
if ANTHROPIC_BASE_URL:
    logger.info(f"🔀 Using custom API endpoint: {ANTHROPIC_BASE_URL}")

try:
    model_kwargs = {
        "model": CLAUDE_MODEL,
        "anthropic_api_key": ANTHROPIC_API_KEY,
        "temperature": 0,
        "max_tokens": 4096
    }

    # 如果配置了中转 API，添加 base_url 参数
    if ANTHROPIC_BASE_URL:
        model_kwargs["base_url"] = ANTHROPIC_BASE_URL

    model = ChatAnthropic(**model_kwargs)
    logger.info("✅ Claude model initialized")
except Exception as e:
    logger.error(f"❌ Failed to initialize Claude model: {e}")
    raise

# === 创建 Deep Agent ===
logger.info("🚀 Creating Course Assistant Agent with DeepAgents framework...")

course_agent = create_deep_agent(
    model=model,
    tools=BASIC_TOOLS,  # Main Agent 只使用基础工具，不包含 fill_moodle_forum
    system_prompt=SYSTEM_INSTRUCTIONS,
    subagents=[
        knowledge_retriever,
        forum_composer,
        cheat_sheet_generator,
        moodle_publisher  # Moodle发布子智能体（独占 fill_moodle_forum 工具）
    ]
).with_config({"recursion_limit": RECURSION_LIMIT})

# === 导出供 LangGraph Server 使用 ===
# LangGraph Server 要求导出的必须是 Graph 对象（不能用 RunnableLambda 包装）
# KB 状态检查逻辑在工具层通过 config 读取 state["kb_enabled"]
agent = course_agent

logger.info("✅ Course Assistant Agent created successfully")

logger.info("=" * 80)
logger.info("🎓 Intelligent Course Assistant - Ready!")
logger.info("=" * 80)
logger.info("")
logger.info("Configuration:")
logger.info(f"  - Model: {CLAUDE_MODEL}")
logger.info(f"  - LightRAG: {LIGHTRAG_BASE_URL}")
logger.info(f"  - Recursion Limit: {RECURSION_LIMIT}")
logger.info(f"  - Main Agent Tools: {len(BASIC_TOOLS)}")
logger.info(f"  - Total Tools (including subagent exclusive): {len(BASIC_TOOLS + MOODLE_TOOLS)}")
logger.info(f"  - Subagents: {len(subagents_config)}")
logger.info("")
logger.info("To start the server:")
logger.info("  langgraph dev")
logger.info("")
logger.info("=" * 80)


# === 测试函数（仅用于本地测试） ===
if __name__ == "__main__":
    logger.info("\n" + "=" * 80)
    logger.info("🧪 Running local tests...")
    logger.info("=" * 80)

    # 测试会话 ID
    test_thread_id = "test_session_001"

    # 测试 1: KB ON 查询
    print("\n" + "=" * 80)
    print("Test 1: KB ON - Query about RAG Architecture")
    print("=" * 80)

    try:
        result = agent.invoke(
            {
                "messages": [{"role": "user", "content": "什么是RAG架构？"}],
                "kb_enabled": True,
                "current_mode": "qa",
                "retrieved_documents": [],
                "citations": [],
                "conversation_summary": "",
                "user_preferences": {}
            },
            config={"configurable": {"thread_id": test_thread_id}}
        )

        print("\n📤 Assistant Response:")
        print(result["messages"][-1].content)

    except Exception as e:
        logger.error(f"❌ Test 1 failed: {e}")
        logger.exception(e)

    # 测试 2: KB OFF 查询
    print("\n" + "=" * 80)
    print("Test 2: KB OFF - Open-ended Discussion")
    print("=" * 80)

    try:
        result = agent.invoke(
            {
                "messages": [{"role": "user", "content": "AI 在医疗领域的应用有哪些？"}],
                "kb_enabled": False,
                "current_mode": "qa",
                "retrieved_documents": [],
                "citations": [],
                "conversation_summary": "",
                "user_preferences": {}
            },
            config={"configurable": {"thread_id": test_thread_id + "_2"}}
        )

        print("\n📤 Assistant Response:")
        print(result["messages"][-1].content)

    except Exception as e:
        logger.error(f"❌ Test 2 failed: {e}")
        logger.exception(e)

    # 测试 3: 检查对话历史
    print("\n" + "=" * 80)
    print("Test 3: Conversation History (Follow-up Question)")
    print("=" * 80)

    try:
        result = agent.invoke(
            {
                "messages": [{"role": "user", "content": "能详细解释一下检索器的工作原理吗？"}],
                "kb_enabled": True,
                "current_mode": "qa",
                "retrieved_documents": [],
                "citations": [],
                "conversation_summary": "",
                "user_preferences": {}
            },
            config={"configurable": {"thread_id": test_thread_id}}  # 使用相同 thread_id
        )

        print("\n📤 Assistant Response:")
        print(result["messages"][-1].content)

    except Exception as e:
        logger.error(f"❌ Test 3 failed: {e}")
        logger.exception(e)

    print("\n" + "=" * 80)
    print("✅ Local tests completed!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Ensure LightRAG is running: cd lightrag && docker-compose up -d")
    print("2. Start LangGraph Server: langgraph dev")
    print("3. Start Deep Agents UI: cd deep-agents-ui && npm run dev")
    print("=" * 80)
