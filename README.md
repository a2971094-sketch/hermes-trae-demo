# Hermes x Trae 工作流 — 快速参考

## 概念
```
Hermes (主控/大脑) → GitHub Issues + PRs → Trae 云端 (被控/双手)
  规划任务                   中转通道                   编码执行
```

## Hermes 端 (主控)

```bash
cd /c/Users/Administrator/hermes-trae-demo

# 1. 分发任务
python ~/AppData/Local/hermes/scripts/hermes-dispatch.py dispatch \
  "用户认证模块" feat/user-auth \
  "实现 JWT 登录/注册/刷新三个接口"

# 2. 查看状态
python ~/AppData/Local/hermes/scripts/hermes-dispatch.py list

# 3. 审查合并
python ~/AppData/Local/hermes/scripts/hermes-dispatch.py review 42
```

## Trae 端 (被控 — 在 Trae 云端终端)

```bash
cd /path/to/project

# 1. 查看任务
bash trae-agent.sh poll

# 2. 领取任务
bash trae-agent.sh pick 42

# 3. 用 Trae AI 完成编码后提交
bash trae-agent.sh submit
```

## 前提条件
- GitHub 仓库 (https://github.com/你的用户名/hermes-trae-demo)
- gh CLI 已登录 (`gh auth login`)
- Git 配置完毕
