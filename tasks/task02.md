# 阶段二：学生端流程（论文与版本）

## 目标
实现学生可完成“创建论文 -> 上传终稿 -> 提交送审 -> 被退回后重传”的闭环。

## 范围
1. 我的论文查询/创建/修改标题
2. 终稿上传（白名单、大小限制、哈希追溯）
3. 版本管理与送审锁定
4. 管理员退回补交

## 开发任务
1. 实现学生接口：
   - `GET /api/thesis/my`
   - `POST /api/thesis/my`
   - `PUT /api/thesis/{id}`
   - `POST /api/thesis/{id}/upload-final`
   - `POST /api/thesis/{id}/submit-final`
2. 上传实现要求：
   - 使用流式写入本地存储目录
   - 限制 `pdf/docx`，可配置大小上限
   - 记录 `sha256`、`mime`、`size`、`uploaded_at`
3. 每次上传创建 `ThesisVersion`。
4. 提交送审时：
   - 校验存在当前版本
   - `Thesis.status = SUBMITTED`
   - 当前版本 `locked_for_review = true` 并记录 `submitted_at`
5. 管理员退回补交接口：`POST /api/admin/thesis/{id}/return`
   - 原因必填
   - 论文回到 `DRAFT`

## 验收标准
1. 学生无法访问他人论文。
2. 上传失败可重试，不产生脏数据。
3. 提交后状态正确流转为 `SUBMITTED`。
4. 退回后学生能看到原因并继续上传新版本。
