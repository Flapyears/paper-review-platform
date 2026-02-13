1. 业务目标与范围
目标

学生把论文上传到平台，形成可送审的固定版本。

管理员把已提交论文分配给评阅教师（按规则回避/数量要求）。

评阅教师在平台上完成下载、填写评阅表、提交评阅结果，并支持管理员退回重评。

范围明确

仅实现以下闭环：

学生上传终稿（含版本管理与锁定）

评阅分配（生成评阅任务，支持替换/取消）

评阅执行（草稿/提交/锁定，退回重评）

不做：开题/中期、查重接口、答辩、成绩发布、归档全套（但需预留字段与扩展点）。

2. 角色与权限（最小集合）
角色

学生：创建论文、上传文件、提交送审、根据退回原因重新上传

评阅教师：查看分配任务、下载论文、填写评阅表、提交/被退回后重提

管理员（学院秘书）：查看提交列表、分配评阅、调整分配、退回评阅、查看进度与导出

权限边界

学生只能访问自己的论文与版本。

评阅教师只能访问分配给自己的评阅任务与该任务绑定的论文版本文件。

管理员可访问批次内全部数据（可按学院/专业做数据范围）。

提交后的版本必须可追溯且用于评阅一致（很多学校要求“送查重版本与送盲审版本一致”的原则可类比到“送审版本一致”）。

3. 端到端流程与状态机（核心约束）
3.1 论文（Thesis）状态

DRAFT：编辑中/未提交

SUBMITTED：学生已提交送审（待分配）

REVIEWING：已分配评阅（评阅中）

REVIEW_DONE：所有评阅任务已提交

退回补交可以做两种：
A) 退回后回到 DRAFT；或 B) 单独状态 RETURNED。建议 A 简化。

3.2 评阅任务（ReviewTask）状态

ASSIGNED：已分配

DRAFTING：评阅表草稿中

SUBMITTED：评阅已提交（锁定）

RETURNED：管理员退回重评

CANCELLED：取消任务（仅未提交可取消）

3.3 关键联动规则

只能对 SUBMITTED 的论文进行分配。

生成任意一条 ReviewTask 后论文进入 REVIEWING。

当该论文所有 ReviewTask 都 SUBMITTED，论文进入 REVIEW_DONE。

每条 ReviewTask 必须绑定论文的一个确定版本（version_id），避免学生之后改文件导致评阅对象变化。

4. 功能需求清单
A. 学生上传论文（MVP）
A1. 论文元信息

标题（必填）

学生身份关联（来自登录账号）

（可选）导师/专业/班级等从教务导入（本期可先不做）

A2. 文件上传

终稿正文（必传，pdf/docx）

（可选）附件（zip、代码等）

校验：

类型白名单

大小限制

上传失败可重试

存储：

本地存储/对象存储均可（MVP 允许本地）

上传记录要可追溯（文件hash、大小、上传人、时间）

FastAPI 处理上传通常用 UploadFile 并建议流式落盘以避免大文件占用内存。

A3. 版本管理（必须）

每次上传终稿创建一个 ThesisVersion

提交送审时将 current_version_id 指向当时版本，并可设置 locked_for_review=true

被管理员退回后，学生重新上传生成新版本；历史版本保留可查

A4. 提交送审

触发条件：存在 current_version

结果：Thesis.status = SUBMITTED，版本记录写 submitted_at

A5. 管理员退回补交

管理员填写退回原因（必填）

论文状态回到 DRAFT（或 RETURNED）

学生看到原因并重新上传再提交

B. 评阅分配（管理员）
B1. 待分配列表

查询 SUBMITTED 论文列表

展示：标题、学生标识（盲审可隐藏/用编码）、当前版本、提交时间、已分配数量

B2. 分配规则（MVP 必须支持）

每篇论文分配评阅人数 N（默认 2，可配置）

回避规则（硬校验）：

评阅教师 ≠ 论文导师（如有导师字段）

（可选增强）均衡规则：

每位评阅老师最大任务数 K

任务量均衡分配

B3. 分配操作

手动分配：管理员选择论文 + 评阅教师，生成 N 条 ReviewTask

批量分配：一次选择多篇论文并分配

分配后：

Thesis.status → REVIEWING

记录审计日志（谁分配的、分配给谁、时间、理由）

B4. 调整分配

ASSIGNED/DRAFTING 状态下可替换评阅教师

SUBMITTED 状态不允许直接替换：必须走“退回重评/新增任务”的受控流程（本期可先做退回重评）

可取消任务（仅未提交）

B5. 催办与进度（本期可做简版）

管理员可查看每篇论文评阅完成情况

（可选）一键催办/提醒（站内消息即可）

C. 评阅执行（评阅教师）
C1. 我的任务列表

仅显示分配给我的 ReviewTask

字段：论文标题（盲审时可显示“论文编号”）、截止时间、状态、是否逾期

C2. 任务详情与文件下载

可下载该任务绑定的论文版本文件

下载鉴权（必须校验 reviewer_id）

记录下载次数与最后下载时间（用于审计）

C3. 评阅表（ReviewForm）

评阅表字段（MVP 建议最少）：

分数（0-100）

等级（优秀/良好/中等/及格/不及格 或 A/B/C/D/E）

是否同意答辩（YES/NO/REVISE）

评语（给学生）

内部评语（给管理员/学院）

支持：

保存草稿（ReviewTask → DRAFTING）

提交（ReviewTask → SUBMITTED，ReviewForm.is_final=true）

提交后锁定不可改

C4. 管理员退回重评

管理员填写退回原因（必填），ReviewTask → RETURNED

教师收到提示后可修改并重新提交

需保留历史（最简方式：ReviewFormHistory 或 revision_no + 快照）

C5. 评阅完成联动

当一篇论文所有 ReviewTask 都 SUBMITTED，Thesis → REVIEW_DONE

5. 数据对象（概念模型）

User：id、role、name、email…

Thesis：id、student_id、advisor_id(可选)、title、status、current_version_id…

ThesisVersion：id、thesis_id、stage、file_id、locked_for_review、submitted_at…

File：id、storage_path、sha256、mime、size、uploaded_by、uploaded_at

ReviewTask：id、thesis_id、version_id、reviewer_id、status、assigned_at、due_at、download_count…

ReviewForm：task_id、score、grade、comments、allow_defense、is_final、revision_no…

AuditLog：actor_id、action、target、payload、created_at

6. 接口清单（按模块）
学生

GET /api/thesis/my

POST /api/thesis/my（创建）

PUT /api/thesis/{id}（改标题）

POST /api/thesis/{id}/upload-final（multipart）

POST /api/thesis/{id}/submit-final

GET /api/files/{file_id}/download（鉴权）

管理员

GET /api/admin/thesis?status=SUBMITTED

POST /api/admin/thesis/{id}/return（退回补交）

POST /api/admin/review-tasks/assign（批量分配）

POST /api/admin/review-tasks/{task_id}/replace

POST /api/admin/review-tasks/{task_id}/cancel

POST /api/admin/review-tasks/{task_id}/return（退回重评）

（可选）GET /api/admin/review-progress

评阅教师

GET /api/reviewer/tasks

GET /api/reviewer/tasks/{task_id}

GET /api/reviewer/tasks/{task_id}/download

PUT /api/reviewer/tasks/{task_id}/form（草稿）

POST /api/reviewer/tasks/{task_id}/submit

7. 非功能需求（必须写进需求，避免后期返工）

安全与权限：所有下载/评阅接口必须鉴权与授权；短链或流式下载；日志记录。

审计留痕：分配、替换、取消、提交、退回、下载都要记 AuditLog。

一致性：评阅对象版本固定（version_id 绑定），历史版本可追溯。

性能：文件上传下载要考虑大文件；避免一次性读入内存。

可用性：草稿保存、防误提交、明确错误提示（回避冲突/状态不允许）。