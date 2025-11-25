# MCP Integration Guide - Moodle Forum Publishing

This document explains how to use the **MCP (Model Context Protocol) integration** for automated Moodle forum posting.

---

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [How It Works](#how-it-works)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [Architecture](#architecture)
- [FAQ](#faq)

---

## Overview

The Course Assistant integrates with **Chrome DevTools MCP** to automate filling Moodle forum post forms. This feature:

✅ **Navigates** to your Moodle forum page
✅ **Clicks** the "Add discussion topic" button
✅ **Fills** Subject and Message fields automatically
✅ **Converts** Markdown to HTML for TinyMCE editor
✅ **Leaves** final submission to the user for review

**Important**: This tool only **fills** the form - it never submits automatically. You always have control over the final post.

---

## Prerequisites

### 1. System Requirements

- **Node.js** (v20.19 or higher LTS)
- **Chrome browser** (current stable version or newer)
- **Python 3.11+**
- **Active Moodle session** (logged in)

### 2. Required Dependencies

```bash
# Python packages
pip install mcp markdown

# Node.js package (for MCP server)
# Option A: Global installation
npm install -g chrome-devtools-mcp

# Option B: Use npx (no installation needed)
# The server will be auto-downloaded when first used
```

---

## Setup Instructions

### Step 1: Install Python Dependencies

```bash
# In your project directory
pip install -r requirements.txt
```

This will install:
- `mcp>=1.0.0` - Model Context Protocol client
- `markdown>=3.5.0` - Markdown to HTML converter

### Step 2: Configure Environment Variables

Edit your `.env` file:

```bash
# Copy example if you don't have .env yet
cp .env.example .env

# Add your Moodle forum URL
nano .env
```

Add these lines to `.env`:

```env
# Moodle Forum Configuration
MOODLE_FORUM_URL=https://moodle.hku.hk/mod/forum/view.php?id=3735524
MOODLE_DEFAULT_FORUM=Default course forum
```

**How to get your forum URL**:
1. Log into Moodle
2. Navigate to your course forum
3. Copy the complete URL from the browser address bar

### Step 3: Start MCP Server

**Note**: The MCP server will automatically start when the Course Assistant first uses a browser automation tool. You can also pre-start it manually:

**Option A: Auto-start (recommended)**
```bash
# No manual start needed - server launches automatically
# when Course Assistant calls MCP tools
```

**Option B: Manual pre-start** (optional)

```bash
# In a separate terminal window
npx -y chrome-devtools-mcp@latest
```

**Verification**: Check Chrome DevTools MCP is available:
```bash
npx chrome-devtools-mcp@latest --version
```

### Step 4: Start Chrome with Remote Debugging

**IMPORTANT**: Chrome must be started with remote debugging enabled for MCP to work.

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile &

# Linux
google-chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile &

# Windows (PowerShell)
Start-Process "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir=C:\temp\chrome-debug-profile
```

**Why `--user-data-dir` is required**: Chrome requires a separate user data directory for security when enabling remote debugging. This creates an isolated Chrome instance.

**Verify debugging port is open**:
```bash
curl http://localhost:9222/json/version
```

You should see JSON output with Chrome version information.

**Create a convenient alias** (optional, macOS/Linux):
```bash
# Add to ~/.zshrc or ~/.bashrc
alias chrome-mcp='/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --remote-debugging-port=9222 \
  --user-data-dir=/tmp/chrome-debug-profile &'

# Then just run:
chrome-mcp
```

### Step 5: Start Course Assistant

```bash
# Start LangGraph server
langgraph dev
```

Look for this confirmation in the logs:

```
✅ MCP connected - Moodle forum publishing available
```

If you see a warning instead:
```
⚠️  MCP connection failed - Forum publishing will not work
```
→ **This is normal on first run**. The server will auto-start when you use the forum publishing feature.

→ If it still fails after trying to publish, go to [Troubleshooting](#troubleshooting)

---

## How It Works

### Architecture Flow

```
User Request
    ↓
Main Agent detects "publish to Moodle"
    ↓
Delegates to forum-composer → Generates post
    ↓
Delegates to moodle-publisher subagent
    ↓
Calls fill_moodle_forum tool
    ↓
┌─────────────────────────────────────┐
│ MCP Tool Execution (Automated)      │
├─────────────────────────────────────┤
│ 1. Navigate to forum URL            │
│ 2. Wait for page load               │
│ 3. Take snapshot (get element UIDs) │
│ 4. Click "Add discussion topic"     │
│ 5. Wait for form load               │
│ 6. Take snapshot (get form UIDs)    │
│ 7. Fill Subject field               │
│ 8. Fill Message field (Markdown→HTML)│
│ 9. Return success message           │
└─────────────────────────────────────┘
    ↓
User sees form filled in Chrome
    ↓
User reviews and clicks "Post to forum" manually
```

### Security Design

**Why manual submission?**
- Prevents accidental posts
- Allows final review and editing
- Gives user complete control
- Ensures content accuracy before publishing

---

## Usage Guide

### Basic Usage

**Step 1: Have a conversation**

```
User: What is RAG architecture?
Assistant: [Provides detailed explanation with citations]
```

**Step 2: Generate and publish**

```
User: Generate a forum post based on our discussion and publish it to Moodle
```

**Step 3: Wait for automation**

The system will:
1. Generate a structured forum post (with "What I Understand" and "My Questions" sections)
2. Open Moodle in Chrome
3. Fill the Subject and Message fields
4. Show confirmation message

**Step 4: Review and submit**

1. Check Chrome - the form should be filled
2. Review the content
3. Make any edits if needed
4. Click "Post to forum" button

### Example Workflow

```
You: I'm confused about how RAG retriever works. Can you explain?