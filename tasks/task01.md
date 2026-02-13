# 阶段一：基础架构与核心模型

## 目标
建立可运行的 FastAPI 服务、数据库模型、统一鉴权上下文与状态机基础，为后续业务接口提供稳定底座。

## 范围
1. 项目初始化
2. 数据库与ORM模型（User/Thesis/ThesisVersion/FileRecord/ReviewTask/ReviewForm/AuditLog）
3. 枚举状态定义与关键约束
4. 通用异常与响应结构
5. 简化鉴权（基于请求头注入当前用户）

## 开发任务
1. 初始化项目结构（`app/`、`tests/`、`storage/`）。
2. 配置 SQLite + SQLAlchemy（同步模式，便于MVP落地）。
3. 建立模型与外键关系，落实：
   - `ReviewTask.version_id` 强绑定论文版本
   - `Thesis.current_version_id` 指向当前送审版本
   - `ReviewForm` 支持 `revision_no`
4. 提供基础依赖：DB Session、当前用户、角色权限校验。
5. 实现审计日志写入工具函数（后续接口复用）。
6. 增加健康检查接口与应用启动脚本。

## 验收标准
1. `uvicorn app.main:app` 可启动。
2. 自动建表成功。
3. 模型关系可在测试中完成基本CRUD。
4. 角色鉴权依赖可正确拒绝越权访问。
