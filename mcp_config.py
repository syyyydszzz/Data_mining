"""
MCP客户端配置 - 连接到Chrome DevTools MCP服务器

这个模块提供了与Chrome DevTools MCP服务器的连接管理。
MCP (Model Context Protocol) 允许通过标准协议与外部工具通信。
"""

import os
import sys

import asyncio
import logging
from typing import Dict, Any, Optional


# 尝试导入MCP相关库，如果不存在则提供友好的错误提示
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    print("[MCP] ⚠️ Warning: MCP library not installed. Run: pip install mcp")

logger = logging.getLogger(__name__)


class MCPClient:
    """
    MCP客户端封装类

    负责管理与Chrome DevTools MCP服务器的连接，
    并提供工具调用接口。

    注意：这个类必须保持 stdio_client 和 ClientSession 的上下文活跃，
    直到显式调用 disconnect()
    """

    def __init__(self):
        """初始化MCP客户端"""
        self.session: Optional[ClientSession] = None
        self.tools: Dict[str, Any] = {}
        self._initialized: bool = False
        self._connection_error: Optional[str] = None
        self._cleanup_task: Optional[asyncio.Task] = None  # 后台清理任务

    async def connect(self, timeout: int = 120) -> Dict[str, Any]:
        """
        连接到Chrome DevTools MCP服务器 (官方推荐方式)

        注意：首次运行时 npx 需要下载包，Chrome 需要启动，所以超时设置为 120 秒
        """
        if self._initialized:
            return self.tools

        try:
            logger.info("[MCP] Connecting to Chrome DevTools MCP server...")

            # 1. 使用 npx 方式（官方推荐）
            # 优先使用 npx，如果不存在则使用绝对路径
            use_npx = True

            # 2. 环境变量
            env = os.environ.copy()
            env["NODE_OPTIONS"] = "--dns-result-order=ipv4first"

            # 确保 PATH 包含 node 和 npm
            node_bin_dir = "/Users/suyongyuan/.nvm/versions/node/v24.11.0/bin"
            env["PATH"] = f"{node_bin_dir}:{env.get('PATH', '')}"

            if use_npx:
                command = "npx"
                args = [
                    "-y",  # 自动确认
                    "chrome-devtools-mcp@latest",
                    "--browserUrl=http://127.0.0.1:9222",  # 连接到手动启动的Chrome
                ]
                logger.info(f"🔍 [DEBUG] Executing: npx -y chrome-devtools-mcp@latest --browserUrl=http://127.0.0.1:9222")
                logger.info("ℹ️  Connecting to manually started Chrome with remote debugging")
                logger.info("ℹ️  Please ensure Chrome is running with: --remote-debugging-port=9222")
            else:
                # 备用方案：使用绝对路径
                command = "/Users/suyongyuan/.nvm/versions/node/v24.11.0/bin/chrome-devtools-mcp"
                args = ["--browserUrl=http://127.0.0.1:9222"]  # 连接到手动启动的Chrome
                logger.info(f"🔍 [DEBUG] Executing: {command} --browserUrl=http://127.0.0.1:9222")

            # 3. 启动参数
            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )

            # 4. 创建持久连接（不使用 async with，保持 context 活跃）
            async def _maintain_connection():
                """
                维持MCP连接的后台任务
                这个函数会一直运行，直到连接断开或被主动关闭
                """
                stdio_context = stdio_client(server_params)
                read_stream, write_stream = await stdio_context.__aenter__()

                try:
                    self.session = ClientSession(read_stream, write_stream)
                    await self.session.__aenter__()

                    # 初始化
                    await self.session.initialize()
                    tools_response = await self.session.list_tools()
                    self.tools = {tool.name: tool for tool in tools_response.tools}
                    self._initialized = True

                    logger.info(f"[MCP] ✅ Connected! Available tools: {len(self.tools)}")

                    # 保持连接活跃（等待断开信号）
                    await asyncio.Event().wait()  # 永远等待，直到任务被取消

                except asyncio.CancelledError:
                    logger.info("[MCP] Connection task cancelled, cleaning up...")
                    raise
                finally:
                    # 清理资源
                    if self.session:
                        try:
                            await self.session.__aexit__(None, None, None)
                        except:
                            pass
                    try:
                        await stdio_context.__aexit__(None, None, None)
                    except:
                        pass

            # 启动后台连接任务
            self._cleanup_task = asyncio.create_task(_maintain_connection())

            # 等待初始化完成（带超时）
            start_time = asyncio.get_event_loop().time()
            check_count = 0
            while not self._initialized:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    if self._cleanup_task:
                        self._cleanup_task.cancel()
                    raise asyncio.TimeoutError(
                        f"Connection initialization timeout after {timeout}s. "
                        f"This may happen if:\n"
                        f"  1. npx is downloading chrome-devtools-mcp (first run)\n"
                        f"  2. Chrome is slow to start\n"
                        f"  3. Network issues\n"
                        f"Try running manually: npx -y chrome-devtools-mcp@latest"
                    )

                # 每 5 秒打印一次进度
                check_count += 1
                if check_count % 50 == 0:  # 0.1s * 50 = 5s
                    logger.info(f"[MCP] Still connecting... ({elapsed:.1f}s / {timeout}s)")

                await asyncio.sleep(0.1)

            return self.tools

        except asyncio.TimeoutError:
            logger.error(f"[MCP] ❌ Connection timeout after {timeout}s")
            self._initialized = False
            raise
        except Exception as e:
            logger.error(f"[MCP] ❌ Connection failed: {e}")
            self._initialized = False
            raise

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """
        调用MCP工具

        Args:
            tool_name: 工具名称（如 "mcp__chrome-devtools__navigate_page"）
            arguments: 工具参数字典

        Returns:
            Any: 工具执行结果

        Raises:
            RuntimeError: 如果未初始化或工具不存在
            Exception: 如果工具调用失败
        """
        # 如果未初始化，先尝试连接
        if not self._initialized:
            try:
                await self.connect()
            except Exception as e:
                raise RuntimeError(f"Cannot call tool: MCP not initialized. {e}")

        # 检查工具是否存在
        if tool_name not in self.tools:
            available_tools = ", ".join(list(self.tools.keys())[:5])
            raise ValueError(
                f"Tool '{tool_name}' not found. "
                f"Available tools: {available_tools}..."
            )

        try:
            logger.debug(f"[MCP] Calling tool: {tool_name} with args: {arguments}")

            # 调用工具
            result = await self.session.call_tool(tool_name, arguments)

            logger.debug(f"[MCP] Tool '{tool_name}' completed successfully")
            return result

        except Exception as e:
            logger.error(f"[MCP] Tool '{tool_name}' failed: {e}")
            raise Exception(f"MCP tool call failed: {e}")

    def is_connected(self) -> bool:
        """
        检查是否已成功连接

        Returns:
            bool: 如果已连接返回True，否则返回False
        """
        return self._initialized and self.session is not None

    def get_connection_error(self) -> Optional[str]:
        """
        获取连接错误信息（如果有）

        Returns:
            Optional[str]: 错误信息，如果没有错误则返回None
        """
        return self._connection_error

    async def disconnect(self):
        """断开与MCP服务器的连接"""
        try:
            logger.info("[MCP] Disconnecting from server...")

            # 取消后台连接任务（会触发清理逻辑）
            if self._cleanup_task and not self._cleanup_task.done():
                self._cleanup_task.cancel()
                try:
                    await self._cleanup_task
                except asyncio.CancelledError:
                    pass  # 预期的取消

            self._initialized = False
            self.session = None
            self.tools = {}
            self._cleanup_task = None

            logger.info("[MCP] Disconnected successfully")
        except Exception as e:
            logger.error(f"[MCP] Error during disconnect: {e}")


# 全局MCP客户端实例
# 在整个应用中共享这个单例
mcp_client = MCPClient()


async def initialize_mcp() -> bool:
    """
    初始化全局MCP客户端

    这个函数会在应用启动时被调用。
    如果连接失败，不会抛出异常，只会记录警告。

    Returns:
        bool: 如果连接成功返回True，否则返回False
    """
    try:
        await mcp_client.connect()
        return True
    except Exception as e:
        logger.warning(f"[MCP] Could not initialize MCP client: {e}")
        logger.warning("[MCP] Forum publishing feature will not be available")
        return False


# 提供便捷的检查函数
def is_mcp_available() -> bool:
    """
    检查MCP功能是否可用

    Returns:
        bool: 如果MCP已连接且可用返回True
    """
    return mcp_client.is_connected()
