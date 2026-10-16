# 架构说明

> 最后更新：2026-10-10

## 系统概览

模块化单体API+后台worker。领域规则共享，数据库为权威；本地SQLite运行方式与PostgreSQL Compose共用模型。

## 组件与职责

| 组件 | 路径 | 职责 | 依赖 |
|---|---|---|---|
| API/认证 | backend/app/main.py | 会话、CSRF、权限、筛选与用户操作 | FastAPI/Argon2 |
| 数据 | backend/app/db.py、migrations | 资产/挂牌/源记录/版本/证据/任务/outbox | SQLAlchemy/Alembic |
| 来源 | backend/app/collectors.py | 已验证HTML选择器、网络边界与分页 | httpx/BeautifulSoup |
| 附件 | backend/app/attachments.py | 限额DOCX、精确标的表格价据 | zipfile/XML |
| 领域 | backend/app/domain.py | Decimal换算和pass/fail/unknown | Python |
| 流水线 | backend/app/service.py | 版本/事件/匹配同事务、任务领取 | 数据库 |
| 通知规则 | backend/app/notifications.py | 变更信息、报名提醒身份/作废与事务outbox | 数据库/领域 |
| worker | backend/app/local_worker.py、tasks.py | 本地队列/Celery轮询 | 数据库/Redis |
| 界面 | frontend | 自由筛选、证据、比较与跟进 | 同域API |

## 数据流

来源列表→详情/附件→私有快照→规则字段/证据→保守资产和挂牌→不可变版本→订阅三值匹配→事务outbox→站内收件箱。

列表查新、分页回扫与已存详情复查为三种同源互斥任务。详情复查按最后核验时间轮转，单批最多5条，成功记录逐条提交。提醒独立于商业变更事件：deadline_reminders保存订阅/挂牌/UTC截止/提前小时数唯一身份；outbox检查约束要求恰好关联一个事件或提醒。版本更新不重发同一截止窗口提醒。

## 外部服务

公开候选来源；GitHub源码仓库。无AI/真实邮件投递/云托管实际接入。SMTP模块与合成协议验证已实现。

## 构建、测试与部署

backend/requirements.lock锁定依赖；PYTHONPATH=backend pytest -q backend/tests；Dockerfile+Compose待运行验证。

## 架构约束与风险

未知不当0；报名和竞价分开；价格性质分组；不拆整体出租价；模型和页面不能赋予执行权限。当前跨源身份审核、完整每日覆盖、关键PDF/OCR与生产安全仍是后续工作。

SMTP邮件回执独立引用站内outbox，一条outbox最多一条email_deliveries；按接收用户、地址与启用时间配置，由worker有界处理。SMTP结果不明不自动重发，所有邮件默认关闭。来源告警现在有持久事件及恢复时间，告警SMTP模块已实现，默认独立关闭；真实投递未验收。

0006将hash命名HTML快照存为DATA_DIR下相对路径，保证换目录恢复；离线import-html须传明确观测时间，不冒充新核验。高校记录ID取公告编号而非page.htm，按同URL兼容旧ID。SQLite每连接启用外键；浏览器区分应用条件与草稿、对过期会话清理缓存并丢弃旧请求。

0007新增用户通知偏好、摘要/成员、纠正/关联/审计和来源告警/页观测。摘要不新增伪商业事件，成员仍对应原outbox；代表记录沿用独立SMTP回执，外部接受不等于最终投递。人工纠正发布不可变版本，无市场事件，源更新产生冲突保留人工值并进入unknown；same_round关系图合并检索展示并保留原来源字段，重挂是独立Listing。search批量加载后在内存三值匹配，大库数据库下推尚待基准。来源/任务token通过条件UPDATE取得归属，旧owner不能继续续租/入库/完成；DNS解析后连接IP并使用原Host/SNI。仍只宣称合成归属测试与有限真实GET，未做生产多worker/网络压力验收。

0008 document_reviews为私有附件审核权威，独立worker通过限额文件协议通信、不连接DB/SMTP。结果需哈希/格式/结构校验；PDF/OCR采用独立禁网络容器和资源上限。lease_terms为有依据的只读Decimal算式，不改来源字段，不认为租金序列是实际付款计划。真实文档准确率与容器运行仍待验收。

0009 incident_emails以异常/阶段唯一，独立于挂牌事件/outbox。EmailDelivery和IncidentEmail记录持久Message-ID、发件地址及manual_retry。依据审核与AuditAction同事务，状态CAS防重复审核；closed不自动恢复，人工排队仅再尝试一次。备份复制document_queue，附件worker/API须同时暂停。

0.1.8 DOCX共用有界XML入口；审核提取正文段落和表格的顺序文字，docx_text与旧docx_table同时被结果验证器接纳。字段增强仍只走原精确表格规则，不从审核文字自动改挂牌。文件worker将请求解析错误写成终态失败结果，DB身份校验继续独立执行，坏请求保留不阻塞后续任务。

0010 document_reviews增加origin_version_id/origin_url及挂牌+来源地址+SHA256唯一键，手动上传为NULL保持原行为。source_documents在ingest事务内复用document_jobs，结果请求仍在提交后由reconcile发布。仅读取白名单地址对应的已有hash快照，不发网络请求；指定管理员归属与单次/总待提取上限，默认关闭。

0011 document_downloads以版本+URL唯一，记录原管理员/来源、尝试、token租约、退避及审核引用；入队与ingest同事务。下载worker每poll最多一份，使用已核准IP连接、原Host/SNI、禁止重定向，和HTML采集共用Source租约。领取后不持DB事务做GET，结束时同时验证任务和来源token再发布审核。内容写入哈希命名的document_queue/inputs并随现有备份保留；不修改原公告字段或创建商业事件。
