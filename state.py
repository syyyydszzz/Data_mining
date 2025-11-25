"""
课程助手 Agent 的状态定义
"""

from typing import TypedDict, Annotated, List, Dict, Any, Literal
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class CourseAssistantState(TypedDict):
    """
    课程助手的状态定义

    这个状态会在整个对话过程中维护，并在每轮对话中更新
    """

    # 消息历史（自动追加）
    messages: Annotated[List[BaseMessage], add_messages]

    # KB 开关状态（核心！）
    # True = 从课程材料检索（带引用）
    # False = 纯 LLM 推理（不检索）
    kb_enabled: bool

    # 当前模式
    # "qa" = 知识问答
    # "forum" = 论坛帖子生成
    # "report" = 学习报告生成
    current_mode: Literal["qa", "forum", "report"]

    # 检索结果缓存
    retrieved_documents: List[Dict[str, Any]]

    # 引用信息
    citations: List[Dict[str, Any]]

    # 对话摘要（用于论坛生成）
    conversation_summary: str

    # 用户偏好（扩展功能）
    user_preferences: Dict[str, Any]


# 默认状态
def create_initial_state(
    kb_enabled: bool = True,
    current_mode: Literal["qa", "forum", "report"] = "qa"
) -> CourseAssistantState:
    """创建初始状态"""
    return {
        "messages": [],
        "kb_enabled": kb_enabled,
        "current_mode": current_mode,
        "retrieved_documents": [],
        "citations": [],
        "conversation_summary": "",
        "user_preferences": {}
    }
