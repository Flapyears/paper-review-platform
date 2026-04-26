---
description: Git 版本控制工作流规范
---

# Git 版本控制最佳实践

本文档定义了少儿编程答题平台的 Git 工作流规范。

## 1. 分支策略 (Git Flow 简化版)

```
main (生产分支)
  │
  ├── develop (开发主分支)
  │     │
  │     ├── feature/xxx (功能分支)
  │     ├── feature/yyy
  │     └── ...
  │
  ├── hotfix/xxx (紧急修复分支)
  └── release/v1.0.0 (发布分支)
```

### 分支说明

| 分支类型 | 命名规范 | 用途 | 合并目标 |
|----------|----------|------|----------|
| `main` | main | 生产环境代码，永远保持可发布状态 | - |
| `develop` | develop | 开发主分支，集成所有已完成功能 | main |
| `feature/*` | feature/题目管理 | 新功能开发 | develop |
| `hotfix/*` | hotfix/登录修复 | 生产环境紧急修复 | main + develop |
| `release/*` | release/v1.0.0 | 发布准备分支 | main + develop |

## 2. 创建分支命令

```bash
# 创建 develop 分支
git checkout -b develop

# 创建功能分支 (基于 develop)
git checkout develop
git checkout -b feature/题目管理完善

# 创建修复分支 (基于 main)
git checkout main
git checkout -b hotfix/修复登录问题
```

## 3. Commit 提交规范

使用**约定式提交 (Conventional Commits)**，中文描述：

```
<类型>(<可选范围>): <描述>

[可选正文]

[可选脚注]
```

### 提交类型

| 类型 | 说明 | 示例 |
|------|------|------|
| `feat` | 新功能 | `feat(题目): 新增题目批量导入功能` |
| `fix` | 修复 Bug | `fix(登录): 修复管理员无法登录问题` |
| `docs` | 文档变更 | `docs: 更新 README 安装说明` |
| `style` | 代码格式 | `style: 统一代码缩进风格` |
| `refactor` | 重构 | `refactor(认证): 重构 JWT 验证逻辑` |
| `perf` | 性能优化 | `perf(查询): 优化题目列表查询性能` |
| `test` | 测试 | `test: 添加题目模块单元测试` |
| `chore` | 构建/工具 | `chore: 升级依赖版本` |
| `ci` | CI/CD | `ci: 添加 GitHub Actions 配置` |

### 提交示例

```bash
# 功能提交
git commit -m "feat(试卷): 实现试卷组卷功能

- 支持从题库拖拽添加题目
- 支持设置每题分值
- 支持试卷预览"

# Bug 修复
git commit -m "fix(学生端): 修复答题页面倒计时不显示问题

修复 ExamView.vue 中计时器初始化逻辑错误
Closes #12"

# 简单提交
git commit -m "docs: 更新数据库 ER 图"
```

## 4. 常用 Git 命令

### 日常开发
// turbo-all
```bash
# 查看状态
git status

# 查看提交历史 (最近10条)
git log --oneline -10

# 添加所有变更
git add .

# 添加特定文件
git add backend/src/questions/

# 提交
git commit -m "feat: 你的提交信息"

# 推送到远程
git push origin feature/你的分支名
```

### 分支操作
```bash
# 查看所有分支
git branch -a

# 切换分支
git checkout develop

# 合并分支 (将 feature 合并到 develop)
git checkout develop
git merge feature/题目管理 --no-ff

# 删除已合并的本地分支
git branch -d feature/题目管理
```

### 撤销操作
```bash
# 撤销工作区修改 (未暂存)
git checkout -- <文件名>

# 撤销暂存 (已 git add)
git reset HEAD <文件名>

# 撤销上一次提交 (保留修改)
git reset --soft HEAD~1

# 修改上一次提交信息
git commit --amend -m "新的提交信息"
```

### 标签发布
```bash
# 创建版本标签
git tag -a v1.0.0 -m "发布 v1.0.0 版本"

# 推送标签到远程
git push origin v1.0.0

# 查看所有标签
git tag -l
```

## 5. 完整开发流程示例

```bash
# 1. 确保 develop 是最新的
git checkout develop
git pull origin develop

# 2. 创建功能分支
git checkout -b feature/题目管理完善

# 3. 开发并提交 (可多次)
git add .
git commit -m "feat(题目): 添加题目编辑弹窗"
git commit -m "feat(题目): 添加题目图片上传"

# 4. 推送功能分支
git push origin feature/题目管理完善

# 5. 创建 Pull Request 或直接合并
git checkout develop
git merge feature/题目管理完善 --no-ff -m "merge: 合并题目管理功能"

# 6. 推送 develop
git push origin develop

# 7. 清理功能分支
git branch -d feature/题目管理完善
git push origin --delete feature/题目管理完善
```

## 6. 远程仓库配置

### GitHub 配置
```bash
# 添加远程仓库
git remote add origin https://github.com/你的用户名/kidcode-exam-platform.git

# 首次推送
git push -u origin main
git push -u origin develop
```

### Gitee 配置 (国内镜像)
```bash
# 添加 Gitee 远程仓库
git remote add gitee https://gitee.com/你的用户名/kidcode-exam-platform.git

# 同时推送到两个仓库
git push origin main && git push gitee main
```

## 7. 代码审查清单

提交 PR 前检查：
- [ ] 代码通过 ESLint 检查 (`npm run lint`)
- [ ] 代码通过 TypeScript 检查 (`npm run type-check`)
- [ ] 新功能有对应的中文注释
- [ ] 敏感信息未被提交 (密码、密钥等)
- [ ] Commit 信息规范
- [ ] 大文件未被提交 (使用 .gitignore)

## 8. 文件大小警告

以下文件不应提交到 Git：
- `node_modules/` (通过 npm install 恢复)
- `.env` (敏感配置)
- `dist/` (构建产物)
- `*.log` (日志文件)
- 大于 10MB 的非代码文件
