# Skill 目录统一维护方案

##  问题

当前存在两个独立的 skill 存储位置：

1. **CC (Claude Code)**: `~/.claude/skills/`
2. **工作区**: `/opt/personal-agent-workspace/`

这导致：
- CC 和 Codex 可能访问不同版本的代码
- Skill 更新需要同步到两个位置
- 版本控制混乱

##  解决方案

### 方案 A：软链接（推荐）

将 CC 的 skill 目录软链接到工作区：

```bash
# 1. 在工作区创建 skills 目录
mkdir -p /opt/personal-agent-workspace/skills/ai-quiz

# 2. 复制现有 SKILL.md 到工作区
cp ~/.claude/skills/ai-quiz/SKILL.md /opt/personal-agent-workspace/skills/ai-quiz/

# 3. 删除 CC 的 skill 目录
rm -rf ~/.claude/skills/ai-quiz

# 4. 创建软链接
ln -s /opt/personal-agent-workspace/skills/ai-quiz ~/.claude/skills/ai-quiz
```

**优点**：
- CC 和 Codex 访问同一份代码
- 所有更改自动同步
- 版本控制统一管理

**注意**：需要手动执行一次设置（权限限制）

### 方案 B：同步脚本

使用 `sync-skills.sh` 脚本定期同步：

```bash
# 同步所有 skills
./sync-skills.sh

# 同步指定 skill
./sync-skills.sh ai-quiz
```

**优点**：
- 不需要特殊权限
- 可以控制同步时机

**缺点**：
- 需要手动运行
- 可能存在版本不一致窗口

### 方案 C：Git Submodule

将 skills 作为 git submodule 管理：

```bash
# 在工作区创建 skills 仓库
cd /opt/personal-agent-workspace
git submodule add <skills-repo-url> skills

# CC 读取
ln -s /opt/personal-agent-workspace/skills/ai-quiz ~/.claude/skills/ai-quiz
```

##  推荐架构

```
/opt/personal-agent-workspace/
├── skills/                    # ← 统一的 Skill 目录
│   ├── ai-quiz/
│   │   ├── SKILL.md          # Skill 定义
│   │   └── ...
│   ├── weekend-lunch/
│   └── ...
├── ai-quiz-codex-package/    # 项目代码
│   ├── engine/
│   ├── tools/
│   └── data/
└── sync-skills.sh            # 同步脚本

~/.claude/skills/ai-quiz -> /opt/personal-agent-workspace/skills/ai-quiz
                                 ↑
                            软链接，CC 通过此链接访问
```

##  执行步骤

### 立即执行（手动）

由于权限限制，需要用户手动执行以下命令：

```bash
# 1. 设置软链接
rm -rf ~/.claude/skills/ai-quiz
ln -s /opt/personal-agent-workspace/skills/ai-quiz ~/.claude/skills/ai-quiz

# 2. 验证
ls -la ~/.claude/skills/ | grep ai-quiz
# 应显示: ai-quiz -> /opt/personal-agent-workspace/skills/ai-quiz
```

### 后续维护

1. **新增 Skill**：在工作区 `skills/` 创建，然后设置软链接
2. **更新 Skill**：直接在工作区修改，CC 自动看到更新
3. **版本控制**：`skills/` 目录纳入 git 管理

##  其他项目的 Skill

对于其他项目（如 weekend-lunch）：

```bash
# 1. 在工作区创建
mkdir -p /opt/personal-agent-workspace/skills/weekend-lunch

# 2. 创建 SKILL.md
cat > /opt/personal-agent-workspace/skills/weekend-lunch/SKILL.md << 'EOF'
# 周末午餐推荐 Skill
...
EOF

# 3. 设置软链接
ln -s /opt/personal-agent-workspace/skills/weekend-lunch ~/.claude/skills/weekend-lunch
```

##  验证

```bash
# 检查软链接
ls -la ~/.claude/skills/

# 检查内容一致性
diff -r ~/.claude/skills/ai-quiz /opt/personal-agent-workspace/skills/ai-quiz
# 应无输出（内容一致）
```
