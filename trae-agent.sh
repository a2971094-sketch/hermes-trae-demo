#!/bin/bash
# ============================================================
# trae-agent.sh — Hermes 主控 × Trae 云端被控 任务助手
# 在 Trae 云端终端中运行
#
# 用法:
#   bash trae-agent.sh poll      查看待处理任务
#   bash trae-agent.sh pick [N]  领取任务 (编号 N 或最新的)
#   bash trae-agent.sh submit    提交当前分支并创建 PR
#   bash trae-agent.sh status    查看当前工作状态
# ============================================================
set -e

ACTION="${1:-help}"

case "$ACTION" in
  poll)
    echo "═══════════════════════════════════════"
    echo "  🔍 检查待处理 Trae 任务..."
    echo "═══════════════════════════════════════"
    gh issue list --label "trae-task" --state open \
      --json number,title,createdAt,updatedAt \
      --limit 10 | python3 -c "
import sys, json
tasks = json.load(sys.stdin)
if not tasks:
    print('🎉 没有待处理的任务，好清闲！')
    sys.exit(0)
print(f'📋 找到 {len(tasks)} 个待处理任务:\n')
for t in tasks:
    print(f'  #{t[\"number\"]}: {t[\"title\"]}')
    print(f'    创建: {t[\"createdAt\"][:19]}')
    print(f'    更新: {t[\"updatedAt\"][:19]}')
    print()
"
    ;;

  pick)
    ISSUE="${2:-$(gh issue list --label trae-task --state open --limit 1 --json number | python3 -c "import sys,json; tasks=json.load(sys.stdin); print(tasks[0]['number'] if tasks else '')")}"
    if [ -z "$ISSUE" ]; then
      echo "❌ 没有待处理的任务可领取"
      exit 0
    fi

    echo "═══════════════════════════════════════"
    echo "  📦 领取任务 #$ISSUE ..."
    echo "═══════════════════════════════════════"

    # 获取 Issue 详情和分支名
    TITLE=$(gh issue view "$ISSUE" --json title --jq '.title')
    BODY=$(gh issue view "$ISSUE" --json body --jq '.body')

    # 从 Issue 体中提取分支名
    BRANCH=$(echo "$BODY" | grep -oP '(?<=### 分支\n|## 分支)[\s\n]*feat/[^\s\n]+|feat/[a-zA-Z0-9_-]+' | head -1 | tr -d '[:space:]')

    # 如果没找到，尝试从标题推断
    if [ -z "$BRANCH" ]; then
      SLUG=$(echo "$TITLE" | sed 's/.*://' | tr '[:upper:]' '[:lower:]' | sed 's/ /-/g' | tr -cd 'a-z0-9_-')
      BRANCH="feat/$SLUG"
    fi

    echo "  任务: $TITLE"
    echo "  分支: $BRANCH"

    # 拉取并切换分支
    git fetch origin "$BRANCH" 2>/dev/null || echo "  分支 $BRANCH 可能还不存在，将在本地创建"
    if git checkout "$BRANCH" 2>/dev/null; then
      echo "  ✅ 已切换到已有分支 $BRANCH"
    else
      git checkout -b "$BRANCH"
      echo "  ✅ 已创建并切换到分支 $BRANCH"
    fi

    # 显示任务内容
    if [ -f .trae-task.md ]; then
      echo ""
      echo "╔══════════════════════════════════════════╗"
      echo "║           📋 任务内容                    ║"
      echo "╚══════════════════════════════════════════╝"
      cat .trae-task.md
    else
      echo ""
      echo "╔══════════════════════════════════════════╗"
      echo "║           📋 任务内容 (来自 Issue)       ║"
      echo "╚══════════════════════════════════════════╝"
      gh issue view "$ISSUE"
    fi

    # 标记为进行中
    gh issue edit "$ISSUE" --add-label "in-progress" --remove-label "trae-task" 2>/dev/null || true

    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  🚀 已就绪！在 Trae 中用 AI 完成编码后运行:"
    echo ""
    echo "     bash trae-agent.sh submit"
    echo "══════════════════════════════════════════════════"
    ;;

  submit)
    BRANCH=$(git branch --show-current)
    if [ "$BRANCH" = "main" ] || [ "$BRANCH" = "master" ]; then
      echo "❌ 当前在 $BRANCH 分支，请先切换到任务分支"
      exit 1
    fi

    echo "═══════════════════════════════════════"
    echo "  📤 提交分支 $BRANCH 的成果..."
    echo "═══════════════════════════════════════"

    # 检查是否有未提交的更改
    if [ -n "$(git status --porcelain)" ]; then
      CHANGED=$(git status --porcelain | wc -l)
      echo "  有 $CHANGED 个未提交的文件"
      git add -A
      BRANCH_DESC=$(echo "$BRANCH" | sed 's|^feat/||;s|^fix/||;s|^refactor/||;s|-| |g;s|_| |g')
      git commit -m "feat: $BRANCH_DESC"
      echo "  ✅ 已提交"
    else
      echo "  没有新更改，使用已有提交"
    fi

    # 推送
    echo ""
    echo "  📤 推送到远程..."
    git push -u origin HEAD
    echo "  ✅ 已推送"

    # 创建 Pull Request
    echo ""
    echo "  📝 创建 PR..."

    # 查找关联的 Issue
    ISSUE_REF=$(gh issue list --label "in-progress" --state open --limit 1 --json number --jq '.[0].number' 2>/dev/null || echo "")

    PR_TITLE=$(echo "$BRANCH" | sed 's|^feat/|feat: |;s|^fix/|fix: |;s|^refactor/|refactor: |;s|^docs/|docs: |;s|-| |g;s|_| |g')

    if [ -n "$ISSUE_REF" ]; then
      # 有关联 Issue：创建 PR 并关联
      CHANGES=$(git log --oneline main..HEAD 2>/dev/null || git log --oneline master..HEAD 2>/dev/null || echo "")

      cat > /tmp/pr-body.md << PRBODY
## 变更内容

$(echo "$CHANGES" | head -10 | sed 's/^/- /' || echo "- 实现功能编码")

- [x] 代码已完成
- [x] 单元测试已添加
- [ ] 所有测试通过
- [ ] 代码风格符合规范

Closes #${ISSUE_REF}
PRBODY

      gh pr create \
        --title "$PR_TITLE" \
        --body "$(cat /tmp/pr-body.md)" \
        --label "trae-done"

      gh issue edit "$ISSUE_REF" --remove-label "in-progress" --add-label "trae-done" 2>/dev/null || true

      echo "  ✅ PR 已创建，关联 Issue #$ISSUE_REF"
    else
      CHANGES=$(git log --oneline main..HEAD 2>/dev/null || git log --oneline master..HEAD 2>/dev/null || echo "")

      cat > /tmp/pr-body.md << PRBODY
## 变更内容

$(echo "$CHANGES" | head -10 | sed 's/^/- /' || echo "- 实现功能编码")

- [x] 代码已完成
- [x] 单元测试已添加
- [ ] 所有测试通过
- [ ] 代码风格符合规范
PRBODY

      gh pr create \
        --title "$PR_TITLE" \
        --body "$(cat /tmp/pr-body.md)" \
        --label "trae-done"

      echo "  ✅ PR 已创建"
    fi

    # 切回 main
    git checkout main 2>/dev/null || git checkout master 2>/dev/null || true

    echo ""
    echo "══════════════════════════════════════════════════"
    echo "  ✅ 提交完成！现在切换到 Hermes 去审查合并 PR"
    echo "══════════════════════════════════════════════════"
    ;;

  status)
    echo "═══════════════════════════════════════"
    echo "  📊 当前工作状态"
    echo "═══════════════════════════════════════"
    echo ""
    echo "【本地】"
    echo "  分支: $(git branch --show-current)"
    echo "  未提交: $(git status --porcelain | wc -l) 个文件"
    echo "  未推送: $(git log --oneline @{u}..HEAD 2>/dev/null | wc -l) 个提交"
    echo ""
    echo "【待处理任务】"
    gh issue list --label "trae-task" --state open --limit 5 \
      --json number,title --jq '.[] | "  #\(.number): \(.title)"' 2>/dev/null \
      || echo "  (gh 未登录或无权限)"
    echo ""
    echo "【进行中任务】"
    gh issue list --label "in-progress" --state open --limit 5 \
      --json number,title --jq '.[] | "  #\(.number): \(.title)"' 2>/dev/null \
      || echo "  (无)"
    echo ""
    echo "【待审查 PR】"
    gh pr list --state open --label "trae-done" --limit 5 \
      --json number,title,headRefName --jq '.[] | "  #\(.number): \(.title) [\(.headRefName)]"' 2>/dev/null \
      || echo "  (无)"
    ;;

  help|*)
    echo "╔══════════════════════════════════════════╗"
    echo "║   Hermes 主控 × Trae 云端被控 任务助手   ║"
    echo "╚══════════════════════════════════════════╝"
    echo ""
    echo "用法: bash trae-agent.sh <命令>"
    echo ""
    echo "命令:"
    echo "  poll            查看待处理任务列表"
    echo "  pick [编号]     领取任务 (指定 Issue 编号或最新的)"
    echo "  submit          提交当前分支代码并创建 PR"
    echo "  status          查看当前工作状态"
    echo "  help            显示此帮助"
    echo ""
    echo "完整工作流:"
    echo "  1. bash trae-agent.sh poll      # 查看任务"
    echo "  2. bash trae-agent.sh pick 42   # 领取任务"
    echo "  3. (在 Trae 中用 AI 完成编码)   # 编写代码"
    echo "  4. bash trae-agent.sh submit    # 提交并创建 PR"
    echo "  5. (切换到 Hermes 审查合并)     # 最终验收"
    ;;
esac
