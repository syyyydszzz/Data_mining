#!/bin/bash

# 启动Chrome（调试模式）用于MCP连接
# 这个脚本会启动一个独立的Chrome实例，开启远程调试端口

echo "==================================================================="
echo "🌐 Starting Chrome with Remote Debugging for MCP"
echo "==================================================================="
echo ""

# Chrome profile目录
PROFILE_DIR=~/chrome-mcp-profile

# 检查是否已有Chrome在9222端口运行
if lsof -Pi :9222 -sTCP:LISTEN -t >/dev/null ; then
    echo "⚠️  Port 9222 is already in use!"
    echo ""
    echo "Options:"
    echo "  1. Close the existing Chrome instance and run this script again"
    echo "  2. Or kill the process: kill \$(lsof -t -i:9222)"
    echo ""
    exit 1
fi

# 创建profile目录
mkdir -p "$PROFILE_DIR"

echo "✅ Starting Chrome with:"
echo "   - Remote debugging port: 9222"
echo "   - Profile directory: $PROFILE_DIR"
echo ""
echo "📝 Steps after Chrome opens:"
echo "   1. Navigate to Moodle and login"
echo "   2. Keep this Chrome window open"
echo "   3. Start/restart LangGraph server: langgraph dev"
echo "   4. Use the UI to publish forum posts"
echo ""
echo "⚠️  DO NOT CLOSE this Chrome window while using Moodle automation!"
echo "==================================================================="
echo ""

# 启动Chrome
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir="$PROFILE_DIR" \
  --no-first-run \
  --no-default-browser-check \
  2>&1 &

# 获取进程ID
CHROME_PID=$!

echo "✅ Chrome started (PID: $CHROME_PID)"
echo ""
echo "💡 To check if Chrome is ready:"
echo "   curl http://127.0.0.1:9222/json/version"
echo ""
echo "To stop Chrome:"
echo "   kill $CHROME_PID"
echo ""
echo "==================================================================="

# 等待几秒让Chrome启动
sleep 3

# 检查Chrome是否成功启动
if curl -s http://127.0.0.1:9222/json/version > /dev/null 2>&1; then
    echo "✅ Chrome debugging port is accessible!"
    echo ""
    echo "🎯 Ready to use! You can now:"
    echo "   1. Login to Moodle in this Chrome window"
    echo "   2. Start publishing forum posts from the UI"
else
    echo "❌ Chrome debugging port not accessible yet"
    echo "   Please wait a few seconds and try:"
    echo "   curl http://127.0.0.1:9222/json/version"
fi

echo "==================================================================="
