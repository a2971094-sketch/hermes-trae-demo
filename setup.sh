#!/bin/bash
# ============================================================
# setup.sh — 沙箱环境一键初始化
# 用法: source setup.sh <GH_TOKEN>
# ============================================================
set -e

GH_TOKEN="${1:-$HERMES_GH_TOKEN}"

# ── 1. 安装 gh CLI（如未安装）──────────────────────────────
if ! command -v gh &>/dev/null; then
  echo "[setup] 安装 gh CLI..."
  (type -p wget >/dev/null || apt-get update && apt-get install -y wget) >/dev/null 2>&1
  mkdir -p /etc/apt/keyrings
  wget -qO- https://cli.github.com/packages/githubcli-archive-keyring.gpg | tee /etc/apt/keyrings/githubcli-archive-keyring.gpg >/dev/null
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  apt-get update -qq && apt-get install -y gh -qq
  echo "[setup] gh CLI 安装完成"
else
  echo "[setup] gh CLI 已存在，跳过安装"
fi

# ── 2. gh 登录 ─────────────────────────────────────────────
if [ -n "$GH_TOKEN" ]; then
  echo "$GH_TOKEN" | gh auth login --with-token 2>/dev/null
  echo "[setup] gh 已登录: $(gh api user --jq .login 2>/dev/null || echo '未知')"
else
  echo "[setup] ⚠️ 未提供 GH_TOKEN，跳过 gh 登录"
  echo "  用法: source setup.sh ghp_xxxx"
fi

# ── 3. Python 依赖 ────────────────────────────────────────
echo "[setup] 安装 Python 依赖..."
pip install -e ".[dev]" --break-system-packages -q 2>/dev/null

# ── 4. Git 配置 ───────────────────────────────────────────
git config user.email "trae-agent@hermes.demo" 2>/dev/null || true
git config user.name "Trae Agent" 2>/dev/null || true

# ── 5. git remote 使用 token 认证（避免 push 时弹交互）───
if [ -n "$GH_TOKEN" ]; then
  REMOTE_URL=$(git remote get-url origin 2>/dev/null || true)
  if echo "$REMOTE_URL" | grep -q "^https://github.com" && ! echo "$REMOTE_URL" | grep -q "@"; then
    OWNER=$(echo "$REMOTE_URL" | sed 's|https://github.com/||;s|/.*||')
    REPO=$(echo "$REMOTE_URL" | sed 's|https://github.com/||;s|.git||;s|.*/||')
    git remote set-url origin "https://${OWNER}:${GH_TOKEN}@github.com/${OWNER}/${REPO}.git"
    echo "[setup] git remote 已配置 token 认证"
  fi
fi

echo ""
echo "[setup] ✅ 环境就绪！可以执行:"
echo "  bash trae-agent.sh poll"