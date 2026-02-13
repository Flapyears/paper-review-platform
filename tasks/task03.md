# 阶段三：管理员评阅分配与调整

## 目标
实现管理员完成待分配列表、评阅任务生成、替换/取消、进度查看与审计留痕。

## 范围
1. SUBMITTED 论文列表
2. 分配评阅（支持批量）
3. 替换/取消未提交任务
4. 评阅进度汇总

## 开发任务
1. 实现管理员接口：
   - `GET /api/admin/thesis?status=SUBMITTED`
   - `POST /api/admin/review-tasks/assign`
   - `POST /api/admin/review-tasks/{task_id}/replace`
   - `POST /api/admin/review-tasks/{task_id}/cancel`
   - `GET /api/admin/review-progress`
2. 分配规则：
   - 仅允许对 `SUBMITTED` 论文分配
   - 默认每篇论文分配2人（请求可覆盖）
   - 回避校验：评阅教师不能是论文导师
3. 分配后联动：
   - 创建 `ReviewTask(ASSIGNED)`，绑定 `version_id`
   - 论文状态转为 `REVIEWING`
4. 替换限制：仅 `ASSIGNED/DRAFTING/RETURNED` 可替换。
5. 取消限制：仅未提交任务可取消（状态置 `CANCELLED`）。
6. 所有关键操作写入 `AuditLog`。

## 验收标准
1. `SUBMITTED` 之外状态论文不可分配。
2. 分配与替换都遵守回避规则。
3. 审计日志完整记录操作人与目标对象。
4. 进度接口可返回每篇论文任务完成率。
