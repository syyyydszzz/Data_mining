"""
LightRAG 客户端
基于真实的 LightRAG Server API 实现
API 文档: http://localhost:9621/docs
"""

import os
import requests
import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)

# LightRAG 服务配置来自环境变量，方便部署在不同地址
DEFAULT_LIGHTRAG_BASE_URL = os.getenv("LIGHTRAG_BASE_URL", "http://localhost:9621")
DEFAULT_LIGHTRAG_API_KEY = os.getenv("LIGHTRAG_API_KEY")


class LightRAGClient:
    """LightRAG API 客户端（基于真实 API v0249）"""

    def __init__(self, base_url: str = DEFAULT_LIGHTRAG_BASE_URL, api_key: Optional[str] = DEFAULT_LIGHTRAG_API_KEY):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        logger.info(f"✅ LightRAG Client initialized: {self.base_url}")

    def query(
        self,
        query: str,
        mode: str = "mix",
        include_references: bool = True,
        response_type: Optional[str] = None,
        top_k: Optional[int] = None,
        chunk_top_k: Optional[int] = None,
        enable_rerank: Optional[bool] = None,
        hl_keywords: Optional[List[str]] = None,
        ll_keywords: Optional[List[str]] = None,
        only_need_context: Optional[bool] = None,
        only_need_prompt: Optional[bool] = None,
        max_total_tokens: Optional[int] = None,
        max_entity_tokens: Optional[int] = None,
        max_relation_tokens: Optional[int] = None,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        user_prompt: Optional[str] = None,
        stream: Optional[bool] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        查询 LightRAG 知识库（基于真实 API）

        Args:
            query: 查询问题（最少 3 个字符）
            mode: 查询模式
            include_references: 是否包含来源引用
            response_type: 响应格式偏好（如 "Multiple Paragraphs"）
            top_k: 检索的顶部实体/关系数量
            chunk_top_k: 从向量检索初步获取的 chunk 数量
            enable_rerank: 是否开启重排
            hl_keywords: 高层关键词
            ll_keywords: 低层关键词
            only_need_context: 是否只需要检索上下文
            only_need_prompt: 是否只返回 prompt
            max_total_tokens / max_entity_tokens / max_relation_tokens: Token 管控
            conversation_history: 对话历史（只发送给 LLM，不影响检索）
            user_prompt: 自定义 prompt 模板
            stream: 是否请求流式（仅 /query/stream 实际使用）
            timeout: 超时时间（秒）

        Returns:
            {
                "response": "RAG生成的答案",
                "references": [...],  # 来源引用（如果 include_references=True）
                "sources": [...],  # 解析后的来源信息（用于生成引用）
                "status": "success"
            }
        """
        try:
            if len(query) < 3:
                return {
                    "error": "Query text must be at least 3 characters long",
                    "status": "bad_request"
                }

            logger.info(f"[LightRAG] Querying: {query[:50]}... (mode={mode})")

            request_params: Dict[str, Any] = {
                "query": query,
                "mode": mode,
                "include_references": include_references
            }

            optional_params = {
                "response_type": response_type,
                "top_k": top_k,
                "chunk_top_k": chunk_top_k,
                "enable_rerank": enable_rerank,
                "hl_keywords": hl_keywords,
                "ll_keywords": ll_keywords,
                "only_need_context": only_need_context,
                "only_need_prompt": only_need_prompt,
                "max_total_tokens": max_total_tokens,
                "max_entity_tokens": max_entity_tokens,
                "max_relation_tokens": max_relation_tokens,
                "conversation_history": conversation_history,
                "user_prompt": user_prompt,
                "stream": stream,
            }

            for key, value in optional_params.items():
                if value is not None and value != []:
                    request_params[key] = value

            url_params = {}
            if self.api_key:
                url_params["api_key_header_value"] = self.api_key

            response = requests.post(
                f"{self.base_url}/query",
                json=request_params,
                params=url_params,
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                parsed_result = self._parse_result(result)
                logger.info(
                    f"[LightRAG] Query successful, found {len(parsed_result.get('sources', []))} sources"
                )
                return parsed_result

            if response.status_code in (400, 422):
                error_detail = response.json().get("detail", "Bad request")
                logger.error(f"[LightRAG] Bad request: {error_detail}")
                return {
                    "error": error_detail,
                    "status": "bad_request"
                }

            if response.status_code >= 500:
                error_detail = response.json().get("detail", "Internal server error")
                logger.error(f"[LightRAG] Server error: {error_detail}")
                return {
                    "error": error_detail,
                    "status": "server_error"
                }

            logger.error(f"[LightRAG] Query failed: {response.status_code}")
            return {
                "error": f"API returned status {response.status_code}",
                "status": "error"
            }

        except requests.exceptions.Timeout:
            logger.error("[LightRAG] Query timeout")
            return {
                "error": "Request timeout - query took too long to process",
                "status": "timeout"
            }
        except requests.exceptions.ConnectionError:
            logger.error("[LightRAG] Connection error - is LightRAG server running?")
            return {
                "error": "Cannot connect to LightRAG server. Please ensure Docker container is running (docker-compose up -d).",
                "status": "connection_error"
            }
        except Exception as e:
            logger.exception(f"[LightRAG] Unexpected error: {e}")
            return {
                "error": str(e),
                "status": "error"
            }

    def _parse_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        解析 LightRAG 返回结果，提取来源信息

        真实的 LightRAG API 返回格式:
        {
            "response": "生成的答案文本",
            "references": [
                {
                    "reference_id": "1",
                    "file_path": "/documents/lecture_8.pdf"
                },
                ...
            ]
        }
        """
        parsed = {
            "response": result.get("response", ""),
            "references": result.get("references", []),
            "sources": [],
            "status": "success",
            "raw_response": result
        }

        # 从 references 中提取来源信息
        for ref in result.get("references", []):
            source_info = self._extract_source_info(ref)
            if source_info:
                parsed["sources"].append(source_info)

        return parsed

    def _extract_source_info(self, reference: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        从 reference 中提取来源信息

        LightRAG reference 格式:
        {
            "reference_id": "1",
            "file_path": "Slides-20251022_副本.pdf"  # 实际格式
        }

        我们需要从 file_path 中解析出:
        - lecture_id (讲义编号)
        - slide_range (幻灯片范围)
        - exam_year (考试年份)
        - question_num (题号)
        """
        file_path = reference.get("file_path", "")
        reference_id = reference.get("reference_id", "")

        if not file_path:
            return None

        import re

        # 获取文件名（去掉路径）
        file_name = file_path.split('/')[-1]

        # 尝试匹配各种讲义格式
        lecture_patterns = [
            # 标准格式: lecture_8_slides_26-27.pdf
            r'lecture[_\s-]*(\d+)[_\s-]*slides?[_\s-]*([\d\-]+)',
            # 中文格式: 第8讲_幻灯片26-27.pdf
            r'第(\d+)讲[_\s-]*幻灯片([\d\-]+)',
            # Slides 格式: Slides-20251022.pdf（从日期提取）
            r'slides?[_\s-]*(\d{8})',
            # Lecture 格式: Lecture8_slides26-27.pdf
            r'lecture(\d+)[_\s-]*slide[_\s-]*([\d\-]+)',
            # 数据挖掘格式: 数据挖掘_Lecture_8.pdf
            r'lecture[_\s-]*(\d+)',
        ]

        for pattern in lecture_patterns:
            match = re.search(pattern, file_name, re.IGNORECASE)
            if match:
                # 有两个捕获组：讲义编号 + 幻灯片范围
                if len(match.groups()) >= 2:
                    lecture_id = int(match.group(1))
                    slide_range = match.group(2)
                    return {
                        "type": "lecture",
                        "reference_id": reference_id,
                        "file_path": file_path,
                        "lecture_id": lecture_id,
                        "slide_range": slide_range,
                        "citation": f"Lecture {lecture_id}, Slides {slide_range}"
                    }
                # 只有一个捕获组：讲义编号或日期
                elif len(match.groups()) == 1:
                    value = match.group(1)
                    # 如果是8位数字，可能是日期格式
                    if len(value) == 8:
                        return {
                            "type": "lecture",
                            "reference_id": reference_id,
                            "file_path": file_path,
                            "date": value,
                            "citation": f"Course Slides ({value[:4]}-{value[4:6]}-{value[6:]})"
                        }
                    # 否则是讲义编号
                    else:
                        lecture_id = int(value)
                        return {
                            "type": "lecture",
                            "reference_id": reference_id,
                            "file_path": file_path,
                            "lecture_id": lecture_id,
                            "citation": f"Lecture {lecture_id}"
                        }

        # 尝试匹配考试格式
        exam_patterns = [
            r'exam[_\s-]*(\d{4})[_\s-]*q(\d+)',  # exam_2023_q5.pdf
            r'(\d{4})[年_\s-]*考试[_\s-]*第?(\d+)题?',  # 2023年考试_第5题.pdf
            r'exam[_\s-]*(\d{4})[_\s-]*question[_\s-]*(\d+)',  # exam_2023_question_5.pdf
            r'test[_\s-]*(\d{4})[_\s-]*(\d+)',  # test_2023_5.pdf
        ]

        for pattern in exam_patterns:
            match = re.search(pattern, file_name, re.IGNORECASE)
            if match:
                exam_year = match.group(1)
                question_num = int(match.group(2))
                return {
                    "type": "exam",
                    "reference_id": reference_id,
                    "file_path": file_path,
                    "exam_year": exam_year,
                    "question_num": question_num,
                    "citation": f"{exam_year} Exam, Question {question_num}"
                }

        # 如果无法解析具体格式，返回通用文档引用
        logger.debug(f"[LightRAG] Using generic citation for: {file_path}")
        return {
            "type": "document",
            "reference_id": reference_id,
            "file_path": file_path,
            "citation": f"Reference Document [{reference_id}]: {file_name}"
        }

    def insert_text(
        self,
        text: str,
        description: Optional[str] = None,
        timeout: int = 60
    ) -> Dict[str, Any]:
        """
        插入单个文本到 LightRAG

        Args:
            text: 要插入的文本内容
            description: 文本描述（可选）
            timeout: 超时时间

        Returns:
            {
                "status": "success" | "duplicated",
                "message": "...",
                "track_id": "..."
            }
        """
        try:
            logger.info(f"[LightRAG] Inserting text: {text[:50]}...")

            request_data = {"text": text}
            if description:
                request_data["description"] = description

            url_params = {}
            if self.api_key:
                url_params["api_key_header_value"] = self.api_key

            response = requests.post(
                f"{self.base_url}/documents/text",
                json=request_data,
                params=url_params,
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[LightRAG] Text inserted: {result.get('status')}")
                return result
            else:
                logger.error(f"[LightRAG] Insert failed: {response.status_code}")
                return {
                    "error": f"Insert failed with status {response.status_code}",
                    "status": "error"
                }

        except Exception as e:
            logger.exception(f"[LightRAG] Insert error: {e}")
            return {"error": str(e), "status": "error"}

    def insert_texts(
        self,
        texts: List[str],
        timeout: int = 120
    ) -> Dict[str, Any]:
        """
        批量插入多个文本到 LightRAG

        Args:
            texts: 文本列表
            timeout: 超时时间

        Returns:
            插入结果
        """
        try:
            logger.info(f"[LightRAG] Inserting {len(texts)} texts")

            url_params = {}
            if self.api_key:
                url_params["api_key_header_value"] = self.api_key

            response = requests.post(
                f"{self.base_url}/documents/texts",
                json={"texts": texts},
                params=url_params,
                timeout=timeout
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"[LightRAG] Texts inserted: {result.get('status')}")
                return result
            else:
                logger.error(f"[LightRAG] Bulk insert failed: {response.status_code}")
                return {
                    "error": f"Bulk insert failed with status {response.status_code}",
                    "status": "error"
                }

        except Exception as e:
            logger.exception(f"[LightRAG] Bulk insert error: {e}")
            return {"error": str(e), "status": "error"}

    def get_pipeline_status(self) -> Dict[str, Any]:
        """
        获取文档处理管道的状态

        Returns:
            {
                "busy": bool,
                "job_name": str,
                "docs": int,
                "cur_batch": int,
                ...
            }
        """
        try:
            url_params = {}
            if self.api_key:
                url_params["api_key_header_value"] = self.api_key

            response = requests.get(
                f"{self.base_url}/documents/pipeline_status",
                params=url_params,
                timeout=10
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"Failed with status {response.status_code}"}

        except Exception as e:
            logger.exception(f"[LightRAG] Get pipeline status error: {e}")
            return {"error": str(e)}

    def health_check(self) -> bool:
        """
        检查 LightRAG 服务是否可用

        Returns:
            True if service is running, False otherwise
        """
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            if response.status_code == 200:
                return True
        except Exception:
            pass

        try:
            response = requests.get(
                f"{self.base_url}/documents/pipeline_status",
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False


# 全局客户端实例，按需创建（读取最新环境变量）
_lightrag_client: Optional[LightRAGClient] = None


def get_lightrag_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> LightRAGClient:
    """
    获取（或创建）LightRAG 客户端实例

    Args:
        base_url: 自定义 LightRAG 地址
        api_key: 可选 API Key（等同于 api_key_header_value）
    """
    global _lightrag_client

    if base_url or api_key:
        _lightrag_client = LightRAGClient(
            base_url=base_url or DEFAULT_LIGHTRAG_BASE_URL,
            api_key=api_key if api_key is not None else DEFAULT_LIGHTRAG_API_KEY
        )
        return _lightrag_client

    if _lightrag_client is None:
        _lightrag_client = LightRAGClient()

    return _lightrag_client
