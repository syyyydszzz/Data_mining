# 🎓 智能课程助手 (Intelligent Course Assistant)

基于 LangChain DeepAgents 框架构建的智能课程助手，集成 LightRAG 知识库，支持动态 KB 切换。

## ✨ 核心功能

1. **智能知识问答** - 支持 KB 动态切换
   - KB ON: 从课程材料检索，提供精确引用
   - KB OFF: 纯 LLM 推理，开放式讨论

2. **论坛帖子生成** - 一键生成结构化论坛帖子
   - 自动分析对话历史
   - 提取理解部分和困惑点
   - 生成可编辑的 Markdown 草稿

3. **学习报告生成** - 个性化复习材料
   - 按主题生成结构化报告
   - 包含定义、流程、示例、对比表
   - 支持速查表 (Cheat Sheet) 生成

## 🏗️ 技术架构

### 核心技术栈
- **框架**: LangChain 1.0 + DeepAgents 0.2.6
- **LLM**: Claude API (Anthropic)
- **RAG**: LightRAG (Docker 部署)
- **UI**: Deep Agents UI (Next.js)

### 系统组件
```
用户 → Deep Agents UI → LangGraph Server → Course Assistant Agent
                                              ├─ Knowledge Retriever
                                              ├─ Content Synthesizer
                                              ├─ Forum Composer
                                              └─ Study Material Generator
                                                      ↓
                                              LightRAG Server
```

## 🚀 快速开始

### 前置要求

- Python 3.10+
- Node.js 18+
- Docker & Docker Compose
- Claude API Key

### 步骤 1: 启动 LightRAG 服务

```bash
# 确保 LightRAG Docker 已配置
docker-compose up -d

# 验证服务
curl http://localhost:9621/health
```

### 步骤 2: 配置后端

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，设置你的 ANTHROPIC_API_KEY
```

### 步骤 3: 启动后端 LangGraph Server

```bash
langgraph dev
```

服务将在 `http://localhost:2024` 启动。

### 步骤 4: 配置和启动前端 UI

```bash
# 克隆 Deep Agents UI (如果还没有)
cd ..
git clone https://github.com/langchain-ai/deep-agents-ui.git
cd deep-agents-ui

# 配置环境变量
cat > .env.local << EOF
NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024"
NEXT_PUBLIC_AGENT_ID=course-assistant
EOF

# 安装依赖并启动
npm install
npm run dev
```

前端将在 `http://localhost:3000` 启动。

## 📁 项目结构

```
deep-research-agents-v3/
├── course_assistant.py          # 主程序 (Agent 定义)
├── course_tools.py               # 工具函数 (RAG、论坛、报告)
├── course_subagents.json         # 子智能体配置
├── course_instructions.md        # 系统提示词
├── lightrag_client.py            # LightRAG 客户端
├── state.py                      # 状态定义
├── langgraph.json                # LangGraph 配置
├── requirements.txt              # Python 依赖
├── .env.example                  # 环境变量模板
└── docker-compose.yml            # LightRAG Docker 配置
```

## 🔧 配置说明

### 环境变量 (.env)

```env
# 必需
ANTHROPIC_API_KEY=your_api_key_here

# 可选配置
CLAUDE_MODEL=claude-sonnet-4-20250514    # 模型选择
LIGHTRAG_BASE_URL=http://localhost:9621  # LightRAG 地址
LIGHTRAG_API_KEY=                       # 如果 LightRAG 开启鉴权，则在此填写
RECURSION_LIMIT=30                        # 最大递归深度
```

### ⚠️ LightRAG API 集成说明

`lightrag_client.py` 已对齐官方 API（OpenAPI v0249）：
- `/query` 支持 `mode`, `include_references`, `only_need_context`, `top_k`, `chunk_top_k`, `enable_rerank` 等全部参数
- 支持通过 `.env` 配置 `LIGHTRAG_BASE_URL`、`LIGHTRAG_API_KEY`
- `_parse_result()` 解析返回的 `references` 并生成 citation 结构
- `_extract_source_info()` 根据文件名提取讲义/考试编号

## 🎯 使用示例

### 1. 知识查询 (KB ON)

**输入**:
```
用户: "什么是 Transformer 架构？"
KB Toggle: ON
```

**输出**:
```
Transformer 是一种基于自注意力机制的神经网络架构[1]...

**引用**:
[1] 数据挖掘 第9讲，幻灯片15-18
[2] 2023年考试试卷，第5题
```

### 2. 开放讨论 (KB OFF)

**输入**:
```
用户: "AI 在医疗领域的应用有哪些？"
KB Toggle: OFF
```

**输出**:
```
基于通用知识回答（未检索课程材料）：

AI 在医疗领域有多种应用：
1. 医学影像分析
2. 疾病预测
...

💡 提示：开启 KB 开关可查看课程标准答案。
```

### 3. 生成论坛帖子

**输入**:
```
用户: "帮我生成论坛帖子"
```

**输出**:
```markdown
# 关于 Transformer 自注意力机制的理解与困惑

## 我理解的部分
1. Transformer 使用自注意力机制...
2. 通过 Query、Key、Value 计算...

## 我的困惑点
1. 自注意力的计算复杂度如何优化？
2. 位置编码的具体作用是什么？

## AI 回答摘要
...

**来源**: 数据挖掘 第9讲，幻灯片15-18
```

### 4. 生成学习报告

**输入**:
```
用户: "生成关于 RAG 架构的复习报告，涵盖第7-9讲"
```

**输出**: 结构化 Markdown 报告（包含定义、流程、对比表、速查表）

## 🛠️ 开发指南

### 添加新工具

在 `course_tools.py` 中添加:

```python
@tool
def my_new_tool(param: str) -> str:
    """工具描述"""
    # 实现逻辑
    return result
```

### 添加新子智能体

在 `course_subagents.json` 中添加:

```json
{
  "my_subagent": {
    "name": "my-subagent",
    "description": "子智能体描述",
    "prompt": "系统提示词...",
    "tools": ["tool1", "tool2"]
  }
}
```

在 `course_assistant.py` 中注册:

```python
my_subagent = subagents_config["my_subagent"]
subagents=[..., my_subagent]
```

### 本地测试

```bash
# 直接运行主程序进行本地测试
python course_assistant.py
```

## 📊 系统监控

### 使用 LangSmith 追踪

在 `.env` 中添加:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=course-assistant
```

访问 [smith.langchain.com](https://smith.langchain.com) 查看完整的执行轨迹。

## ❓ 常见问题

### Q1: LightRAG 连接失败
**A**: 检查 Docker 容器状态
```bash
docker ps
# 如果未运行
docker-compose up -d
```

### Q2: Claude API 错误
**A**: 检查 API Key 是否正确设置
```bash
echo $ANTHROPIC_API_KEY
```

### Q3: 前端无法连接后端
**A**: 确保 `.env.local` 中的 URL 正确
```
NEXT_PUBLIC_DEPLOYMENT_URL="http://127.0.0.1:2024"
```

### Q4: Agent 不调用子智能体
**A**: 检查系统提示词和子智能体描述是否清晰

## 📝 待办事项

- [ ] 完善 LightRAG API 集成（需要实际 API 文档）
- [ ] 添加 UI 自定义组件（KB Toggle 开关）
- [ ] 实现课程材料导入流程
- [ ] 添加单元测试
- [ ] 添加性能监控
- [ ] 支持多语言（中英文切换）

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

---

**注意**: 这是项目的初始版本，LightRAG 集成部分需要根据实际 API 调整。请提供 LightRAG 的 API 文档以完善集成。
