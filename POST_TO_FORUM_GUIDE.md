# Post to Forum 功能使用指南

## 功能概述

新增的 **Post to Forum** 按钮允许用户直接通过 AI 助手将内容发布到 Moodle 论坛，整个过程通过浏览器自动化完成。

## 架构变更

### 后端变更

1. **工具权限独占** (`course_tools.py`)
   - 将 `fill_moodle_forum` 工具从 `ALL_TOOLS` 移至 `MOODLE_TOOLS`
   - Main Agent 只能访问 `BASIC_TOOLS`，无法直接调用 `fill_moodle_forum`
   - 只有 `moodle_publisher` subagent 可以使用 `fill_moodle_forum`

2. **Subagent 独占配置** (`course_assistant.py`)
   ```python
   # Main Agent 只有基础工具
   tools=BASIC_TOOLS

   # moodle_publisher 独占 MOODLE_TOOLS
   moodle_publisher["tools"] = MOODLE_TOOLS
   ```

### 前端变更

1. **新增按钮** (`ChatInterface.tsx`)
   - 添加 "Post to Forum" 按钮（蓝色，带 MessageSquarePlus 图标）
   - 位置：KB toggle 右侧，与 Cheat Sheet 按钮并列

2. **新增状态**
   - `forumPostMode`: 跟踪是否启用论坛发布模式
   - 两个模式互斥（Cheat Sheet 和 Post to Forum 不能同时激活）

3. **消息格式化**
   - 当 `forumPostMode` 激活时，自动添加特殊标记
   - Agent 会识别标记并委托给 `moodle_publisher` subagent

## 使用流程

### 方式1: 使用 Post to Forum 按钮

```
步骤1: 用户准备好论坛内容
       例如：
       Subject: Understanding RAG Architecture

       ## What I Understand
       - RAG has three components...

       ## My Questions
       - How does the retriever work?

步骤2: 点击 "Post to Forum" 按钮（变为蓝色激活状态）

步骤3: 在输入框粘贴或输入论坛内容

步骤4: 点击 Send 发送

步骤5: Main Agent 检测到 "Forum Post Request" 标记
       ↓
       委托给 moodle-publisher subagent
       ↓
       moodle_publisher 调用 fill_moodle_forum 工具
       ↓
       浏览器自动化执行：
       - 打开 Chrome（如果未打开）
       - 导航到 Moodle 论坛
       - 点击 "Add discussion topic"
       - 填写 Subject 和 Message
       - 等待用户审核

步骤6: 用户在浏览器中审核表单内容

步骤7: 用户手动点击 "Post to forum" 提交
```

### 方式2: 直接对话

用户也可以直接对 AI 说：
```
"请帮我发布这个帖子到 Moodle：

标题：Understanding RAG Architecture

内容：
## What I Understand
...
"
```

Main Agent 会自动识别意图并委托给 `moodle_publisher`。

## 技术细节

### 为什么必须通过 Subagent？

**之前的问题**：
```
Main Agent → 直接调用 fill_moodle_forum 工具
                ↓
         前端显示 "TOOL" 而不是 "SUBAGENT"
```

**解决方案**：
```
Main Agent → 委托给 moodle_publisher subagent
                ↓
         moodle_publisher → 调用 fill_moodle_forum 工具
                ↓
         前端显示 "SUBAGENT: moodle-publisher"
```

**关键改动**：
- `fill_moodle_forum` 不在 Main Agent 的工具列表中
- Main Agent 必须通过 subagent 才能发布到 Moodle
- 确保了职责清晰和架构正确

### 前端标记格式

当用户点击 "Post to Forum" 并发送消息时，前端会自动添加标记：

```
Forum Post Request
Please publish the following forum post to Moodle:

[用户输入的内容]

Instructions:
- Extract the subject (first line or title)
- Use the rest as the message content
- Call the moodle-publisher subagent to fill the Moodle forum form
- Wait for user to review and manually submit
```

**重要**：这些系统指令对用户是隐藏的。用户在聊天界面中只会看到：
```
📮 [他们输入的实际内容]
```

过滤逻辑在 `ChatMessage.tsx:60-64`，使用正则表达式提取用户内容并添加 📮 emoji。

### 与其他按钮的交互

- **KB Toggle**: 独立开关，与 Post to Forum 不冲突
- **Cheat Sheet**: 与 Post to Forum 互斥
  - 点击 Cheat Sheet → 自动关闭 Post to Forum
  - 点击 Post to Forum → 自动关闭 Cheat Sheet

## 环境要求

1. **MCP 依赖**
   ```bash
   pip install mcp markdown
   ```

2. **Chrome 浏览器**
   - 需要以远程调试模式启动：
   ```bash
   ./start_chrome_debug.sh
   ```
   或手动：
   ```bash
   /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
     --remote-debugging-port=9222 \
     --user-data-dir=/tmp/chrome-debug
   ```

3. **Moodle 登录**
   - 用户需要在 Chrome 中登录 Moodle
   - 配置 `.env` 文件中的 `MOODLE_FORUM_URL`

4. **环境变量**
   ```bash
   MOODLE_FORUM_URL=https://moodle.hku.hk/mod/forum/view.php?id=YOUR_ID
   ```

## 故障排除

### 问题1: 前端仍显示 "TOOL" 而不是 "SUBAGENT"

**原因**: 后端更改未生效

**解决**:
```bash
# 重启 LangGraph Server
# Ctrl+C 停止当前服务器
langgraph dev
```

### 问题2: 按钮点击无反应

**原因**: 前端未重新编译

**解决**:
```bash
cd deep-agents-ui
npm run dev
```

### 问题3: "Cannot connect to MCP server"

**原因**: Chrome 未启动或 MCP 服务器未运行

**解决**:
```bash
# 1. 启动 Chrome with remote debugging
./start_chrome_debug.sh

# 2. 检查 Chrome 是否在运行
ps aux | grep "remote-debugging-port=9222"

# 3. 确保端口 9222 未被占用
lsof -i :9222
```

### 问题4: "MOODLE_FORUM_URL not configured"

**原因**: 环境变量未配置

**解决**:
```bash
# 编辑 .env 文件
echo 'MOODLE_FORUM_URL=https://moodle.hku.hk/mod/forum/view.php?id=YOUR_ID' >> .env
```

## 测试步骤

### 1. 启动所有服务

```bash
# Terminal 1: 启动 LightRAG
docker-compose up -d

# Terminal 2: 启动 Chrome (远程调试模式)
./start_chrome_debug.sh

# Terminal 3: 启动 LangGraph Server
conda activate course-assistant
langgraph dev

# Terminal 4: 启动前端
cd deep-agents-ui
npm run dev
```

### 2. 测试 Post to Forum 功能

1. 打开浏览器访问 `http://localhost:3000`
2. 在 Chrome 中登录 Moodle
3. 点击 "Post to Forum" 按钮（应该变蓝）
4. 输入测试内容：
   ```
   Test Post from AI Assistant

   This is a test message to verify the forum posting functionality.
   ```
5. 点击 Send
6. 观察前端是否显示 "SUBAGENT: moodle-publisher"
7. 检查 Chrome 是否自动打开 Moodle 并填写表单
8. 在 Chrome 中审核内容
9. 手动点击 "Post to forum" 提交

### 3. 验证工具权限

在 LangGraph Server 终端查看日志：

```
✅ Main Agent Tools: 7        # 不包含 fill_moodle_forum
✅ Total Tools (including subagent exclusive): 8  # 包含 fill_moodle_forum
```

## UI 视觉效果

```
┌─────────────────────────────────────────────────────────┐
│  [KB ON: Use course materials]  [Cheat Sheet] [Post to Forum]  │
│  ↑                                ↑            ↑                │
│  Switch                          Green        Blue              │
│  (独立)                          (互斥)       (互斥)             │
└─────────────────────────────────────────────────────────┘
```

**激活状态**：
- Cheat Sheet 激活：绿色背景 + "Cheat sheet mode active" 提示
- Post to Forum 激活：蓝色背景 + "Forum post mode active" 提示
- 两者不能同时激活

## 架构优势

### 前端职责清晰
- 只负责标记消息类型
- 不处理具体的发布逻辑

### 后端职责清晰
- Main Agent：路由和决策
- moodle_publisher subagent：专门处理 Moodle 发布
- 工具权限独占，防止绕过 subagent

### 用户体验优化
- 一键启用发布模式
- 可视化反馈（蓝色按钮 + 状态提示）
- 保留最终控制权（手动提交）

## 扩展可能

### 未来可以添加的功能

1. **多论坛支持**
   - 让用户选择目标论坛
   - 在 `.env` 中配置多个论坛 URL

2. **草稿保存**
   - 在前端保存未发布的草稿
   - 支持编辑和重新发送

3. **发布历史**
   - 记录已发布的帖子
   - 提供查看和管理功能

4. **模板支持**
   - 预定义论坛帖子模板
   - 快速填充常用格式

## 总结

通过工具权限独占和 subagent 专业化分工，实现了：
- ✅ 清晰的职责划分
- ✅ 正确的架构模式
- ✅ 良好的用户体验
- ✅ 可扩展的设计

用户现在可以通过简单的按钮点击，让 AI 助手自动填写 Moodle 论坛表单，同时保留最终的审核和提交控制权。
