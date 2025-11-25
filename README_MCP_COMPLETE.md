# MCP Integration Guide - Moodle Forum Publishing

This document explains how to use the MCP (Model Context Protocol) integration for automated Moodle forum posting.

## 📋 Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Setup Instructions](#setup-instructions)
- [How It Works](#how-it-works)
- [Usage Guide](#usage-guide)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Overview

The Course Assistant integrates with **Chrome DevTools MCP** to automate filling Moodle forum post forms.

✅ Navigates to your Moodle forum page  
✅ Clicks the "Add discussion topic" button  
✅ Fills Subject and Message fields automatically  
✅ Converts Markdown to HTML for TinyMCE editor  
✅ Leaves final submission to the user for review  

**Important**: This tool only **fills** the form - it never submits automatically.

---

## Prerequisites

### System Requirements

- Node.js (v18+)
- Chrome browser (running)
- Python 3.11+
- Active Moodle session (logged in)

### Required Dependencies

```bash
# Python
pip install mcp markdown

# Node.js (MCP server)
npm install -g @modelcontextprotocol/server-chrome-devtools
```

---

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env`:

```env
MOODLE_FORUM_URL=https://moodle.hku.hk/mod/forum/view.php?id=3735524
MOODLE_DEFAULT_FORUM=Default course forum
```

### 3. Start MCP Server

```bash
npx -y @modelcontextprotocol/server-chrome-devtools &
```

### 4. Start Course Assistant

```bash
langgraph dev
```

Look for: `✅ MCP connected - Moodle forum publishing available`

---

## Usage Guide

**Example:**

```
User: What is RAG architecture?
Assistant: [Explains with citations]

User: Generate a forum post and publish it to Moodle