# 阶段四：评阅执行、重评与完成联动

## 目标
实现评阅教师任务执行闭环：任务列表、下载绑定版本、评阅草稿与提交、管理员退回重评、论文自动完成。

## 范围
1. 评阅教师任务查询与详情
2. 绑定版本文件下载（鉴权 + 下载统计）
3. 评阅表草稿与最终提交
4. 管理员退回重评
5. 全部提交后的论文状态联动

## 开发任务
1. 实现评阅接口：
   - `GET /api/reviewer/tasks`
   - `GET /api/reviewer/tasks/{task_id}`
   - `GET /api/reviewer/tasks/{task_id}/download`
   - `PUT /api/reviewer/tasks/{task_id}/form`
   - `POST /api/reviewer/tasks/{task_id}/submit`
2. 下载鉴权：仅任务所属评阅教师可下载，记录下载次数与最后下载时间。
3. 评阅表能力：
   - 草稿保存：`ReviewTask -> DRAFTING`
   - 提交：`ReviewTask -> SUBMITTED`，`is_final=true`
   - 提交后不可直接编辑
4. 管理员退回重评：`POST /api/admin/review-tasks/{task_id}/return`
   - 原因必填
   - 任务置 `RETURNED`
   - `ReviewForm.revision_no` 自增保留历史快照
5. 论文完成联动：当同一论文全部非取消任务都 `SUBMITTED`，`Thesis -> REVIEW_DONE`。

## 验收标准
1. 越权评阅教师无法查看/下载他人任务。
2. 提交后不可篡改最终评阅结果。
3. 退回重评有历史留痕，可再次提交。
4. 全部任务提交后论文自动更新为 `REVIEW_DONE`。
