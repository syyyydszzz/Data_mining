#!/bin/bash

# 启动LangGraph服务器 + MCP Chrome（自动化启动）
# 这个脚本会：
# 1. 启动MCP专用Chrome（独立profile，调试模式）
# 2. 等待你登录Moodle
# 3. 启动LangGraph服务器

echo "==================================================================="
echo "🚀 Starting Course Assistant with MCP Chrome"
echo "==================================================================="
echo ""

# Chrome profile目录（MCP专用）
PROFILE_DIR=~/chrome-mcp-profile
DEBUG_PORT=9222

# ============================================================
# Step 1: 检查并启动Chrome
# ============================================================

echo "📋 Step 1: Checking Chrome status..."

# 检查9222端口是否已被占用
if lsof -Pi :$DEBUG_PORT -sTCP:LISTEN -t >/dev/null 2>&1 ; then
    echo "✅ Chrome is already running on port $DEBUG_PORT"
    echo ""
else
    echo "🌐 Starting MCP Chrome (independent profile)..."
    echo "   Profile: $PROFILE_DIR"
    echo "   Debug port: $DEBUG_PORT"
    echo ""

    # 创建profile目录
    mkdir -p "$PROFILE_DIR"

    # 在后台启动Chrome
    /Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
      --remote-debugging-port=$DEBUG_PORT \
      --user-data-dir="$PROFILE_DIR" \
      --no-first-run \
      --no-default-browser-check \
      > /dev/null 2>&1 &

    CHROME_PID=$!
    echo "✅ Chrome started (PID: $CHROME_PID)"
    echo ""

    # 等待Chrome启动
    echo "⏳ Waiting for Chrome to be ready..."
    for i in {1..10}; do
        if curl -s http://127.0.0.1:$DEBUG_PORT/json/version > /dev/null 2>&1; then
            echo "✅ Chrome debugging port is accessible!"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    echo ""
fi

# ============================================================
# Step 2: 提示用户登录Moodle
# ============================================================

echo "==================================================================="
echo "⚠️  IMPORTANT: Please login to Moodle now"
echo "==================================================================="
echo ""
echo "📍 A Chrome window should be open (or switch to it)"
echo "   This is your MCP Chrome with independent profile"
echo ""
echo "🔑 Please:"
echo "   1. Navigate to: https://moodle.hku.hk"
echo "   2. Login with your credentials"
echo "   3. Keep this Chrome window open"
echo ""
echo "💡 This login session will be saved in: $PROFILE_DIR"
echo "   You only need to login once (unless session expires)"
echo ""
echo "==================================================================="
echo ""
read -p "Press ENTER after you've logged into Moodle..."
echo ""

# ============================================================
# Step 3: 验证Chrome连接
# ============================================================

echo "🔍 Verifying Chrome connection..."
if curl -s http://127.0.0.1:$DEBUG_PORT/json/version > /dev/null 2>&1; then
    echo "✅ Chrome debugging port is working!"
    echo ""
else
    echo "❌ Cannot connect to Chrome debugging port"
    echo "   Please check if Chrome is running"
    echo ""
    exit 1
fi

# ============================================================
# Step 4: 启动LangGraph服务器
# ============================================================

echo "==================================================================="
echo "🚀 Starting LangGraph Server"
echo "==================================================================="
echo ""
echo "ℹ️  LangGraph will connect to Chrome at: http://127.0.0.1:$DEBUG_PORT"
echo "ℹ️  Your Moodle login session is preserved"
echo ""
echo "📝 Server logs will appear below..."
echo "   Press Ctrl+C to stop the server"
echo ""
echo "==================================================================="
echo ""

# 启动LangGraph服务器（前台运行）
langgraph dev

# 服务器停止后的清理提示
echo ""
echo "==================================================================="
echo "⚠️  LangGraph Server stopped"
echo "==================================================================="
echo ""
echo "💡 Chrome is still running in the background"
echo "   To stop Chrome: pkill -f 'remote-debugging-port=$DEBUG_PORT'"
echo ""
echo "   Or keep it running for next time (recommended)"
echo "==================================================================="
