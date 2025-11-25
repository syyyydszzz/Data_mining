# 快速开始 - Moodle 自动填写

## 🚀 一键启动（推荐）

使用统一启动脚本，自动启动MCP Chrome + LangGraph服务器：

```bash
cd /Users/suyongyuan/Desktop/deepagents-main/deep-research-agents-v3
./start_with_chrome.sh
```

### 脚本会自动完成：

1. ✅ **启动MCP专用Chrome**
   - 使用独立profile：`~/chrome-mcp-profile`
   - 开启调试端口：9222
   - 不影响你的正常Chrome

2. ⏸️ **等待你登录Moodle**
   - 脚本会暂停，等你按Enter
   - 在打开的Chrome窗口中登录Moodle
   - 登录session会保存，下次不用重新登录

3. ✅ **启动LangGraph服务器**
   - 自动连接到Chrome
   - 开始监听请求

### 工作流程图：

```
运行 ./start_with_chrome.sh
    ↓
检查Chrome是否运行
    ├─ 已运行 → 跳过启动
    └─ 未运行 → 后台启动Chrome
    ↓
等待你登录Moodle
    ↓
按 Enter 继续
    ↓
验证Chrome连接
    ↓
启动 langgraph dev
    ↓
✅ 可以使用UI发布帖子了！
```

---

## 📝 第一次使用

### 步骤：

1. **运行启动脚本**：
   ```bash
   ./start_with_chrome.sh
   ```

2. **看到Chrome窗口打开**：
   - 这是MCP专用Chrome（独立profile）
   - 地址栏会显示"remote debugging port: 9222"

3. **在这个Chrome中登录Moodle**：
   - 导航到：https://moodle.hku.hk
   - 输入用户名和密码
   - 完成双因素认证（如果需要）

4. **回到终端，按Enter**：
   - LangGraph服务器会启动
   - 看到日志输出

5. **打开UI开始使用**：
   - 打开：http://localhost:3000
   - 生成论坛帖子
   - 点击"Publish to Moodle"

---

## 🔄 第二次及之后使用

### 情况1：Chrome还在运行

如果Chrome没有关闭（推荐保持运行）：

```bash
./start_with_chrome.sh
```

脚本会检测到Chrome已运行，直接启动服务器，**不需要重新登录**！

### 情况2：Chrome已关闭

如果你关闭了Chrome：

```bash
./start_with_chrome.sh
```

脚本会重新启动Chrome，但**login session仍然保存**在profile中，通常不需要重新登录（除非session过期）。

---

## 🛑 停止服务

### 停止LangGraph服务器：

在终端中按 `Ctrl+C`

### 停止Chrome：

**选项1：保持运行（推荐）**
- 不做任何操作
- Chrome会继续在后台运行
- 下次启动脚本时自动检测到

**选项2：完全停止**
```bash
pkill -f 'remote-debugging-port=9222'
```

---

## 💡 常见问题

### Q: Chrome窗口在哪里？

A: 启动脚本后，应该会自动打开一个新的Chrome窗口。如果没看到：
- 检查Dock中是否有Chrome图标
- 或者Command+Tab切换应用

### Q: 如何区分MCP Chrome和普通Chrome？

A: MCP Chrome的特征：
- ✅ 地址栏下方显示："Chrome is being controlled by automated test software"
- ✅ 使用独立profile（`~/chrome-mcp-profile`）
- ✅ 开启了远程调试端口9222

### Q: 可以同时运行两个Chrome吗？

A: 可以！MCP Chrome和你的正常Chrome可以同时运行，互不影响。

### Q: 端口9222已被占用怎么办？

A: 说明MCP Chrome已经在运行了，直接运行脚本即可（会跳过Chrome启动）。

如果需要重启Chrome：
```bash
# 停止现有Chrome
pkill -f 'remote-debugging-port=9222'

# 重新运行脚本
./start_with_chrome.sh
```

### Q: 登录session多久过期？

A: 取决于Moodle的session策略，通常几小时到几天。过期后重新登录即可。

---

## 📁 相关文件

| 文件 | 说明 |
|------|------|
| `start_with_chrome.sh` | **推荐使用** - 统一启动脚本 |
| `start_chrome_debug.sh` | 单独启动Chrome（备用） |
| `mcp_config.py` | MCP连接配置 |
| `course_tools.py` | Moodle表单填写工具 |
| `~/chrome-mcp-profile/` | Chrome profile目录（存储登录session）|

---

## 🎯 完整流程总结

```bash
# 1. 第一次使用
./start_with_chrome.sh
# → Chrome打开 → 登录Moodle → 按Enter → 服务器启动

# 2. 使用UI发布帖子
# 打开 http://localhost:3000
# 生成帖子 → 点击"Publish to Moodle"

# 3. 停止服务器
# 按 Ctrl+C

# 4. 下次使用（Chrome保持运行）
./start_with_chrome.sh
# → 直接启动服务器（不需要重新登录！）
```

---

**就这么简单！享受自动化发帖的便利吧 🎉**
