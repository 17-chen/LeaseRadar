# 项目上下文

> 最后更新：2026-10-12（Asia/Shanghai）

## 项目基本信息

- 名称：LeaseRadar（铺讯）
- 目标：招租公告及时发现、可核查筛选、比较与跟进。
- 用户：门店拓展团队；当前比赛优先，筛选条件自由选择。
- 仓库：https://github.com/17-chen/LeaseRadar（私有）。

## 产品愿景

公开公告分散且关键信息在附件；以持续采集、字段依据、可靠规则减少逐站人工刷信息。参加2026开源行业解决方案创新赛，提交截止10月31日24:00。

## 技术架构

- Python：FastAPI、SQLAlchemy/Alembic、httpx、BeautifulSoup、标准库DOCX。
- 前端：原生HTML/CSS/JavaScript；React迁移尚未实施。
- 数据库：本机SQLite；Compose设计PostgreSQL16。
- 任务：数据库队列，本机local_worker；部署Celery/Redis。
- AI：无模型依赖；未使用AI提取。
- 锁依赖：backend/requirements.lock；本机Python3.13验证。

## 当前状态

- 核心实现与148项测试完成；已补可续扫游标、活跃/关注详情复查、有限重试与可配置站内报名提醒；尚未满足交接包全部P0。
- 真实库25条：农交云24，高校链接型1。6条DOCX价格周期核实；本阶段真实复查3条，审查后41个版本（本次新增1个为纠正reprocessing，保留原核验时间）。
- API与本地worker当前启动；来源enabled默认false，不自动长期采集。
- Docker CLI存在，但Docker服务/桌面应用不可用；只做配置校验。
- 可配置SMTP发送与独立回执已实现并在本地合成接收端验证；当前真实外部通道关闭。没有公网部署、真实邮件发送、参赛报名或试用业绩。

## 重要设计决策

参见docs/DECISION_LOG.md；保守关联、unknown不推断、价格Decimal、原文和私人数据不入Git。

## 约束条件

- 不覆盖外部项目，不泄露private目录及密钥。
- 不绕过访问控制，不将搜索缓存视为适配成功。
- 公开仓库发布、服务器与真实通知目标需用户授权；当前仓库创建/源码推送已由用户授权。
- 用户最新“开始吧”允许正式开发，不需每个可逆步骤再次询问。

## 已知问题

第二来源正文覆盖不足；真实SMTP服务商未配置；有依据条款计算和附件审核队列已实现；本机PDF/OCR工具未配置，真实样本准确率、容器运行、自动附件/复杂条款候选提取及比赛材料未完成；回扫预算与持久告警不保证动态列表完整性；来源/任务token归属与DNS连接固定已本地验证，生产多worker、大规模压力和PostgreSQL恢复仍需验收。来源告警外发与管理员死信重放仍未实现。

## 下一步任务

继续PDF/OCR及完整条款/第二来源适配，生产与真实评测条件最后统一补齐。通知节奏、完整分页、人工纠正/撤销/冲突、人工关联聚合与重挂、预算/告警、导入/回放/评测工具已实现。0007有数据升级与异目录恢复验证；docs/WORKFLOWS_VERIFICATION.md记录范围，docs/FINAL_SETUP_CHECKLIST.md集中外部配置。

## 证据来源

backend/app、backend/tests/test_core.py、docs/VERIFICATION.md、docs/SOURCE_AUDIT.md、private/verification_counts.json（私有本地计数）。

0.1.6：0008附件表迁移与独立恢复通过；网页条款计算只读，合成DOCX上传/独立worker/审核闭环在DEMO通过。详细边界见docs/TERMS_ATTACHMENTS_VERIFICATION.md。
