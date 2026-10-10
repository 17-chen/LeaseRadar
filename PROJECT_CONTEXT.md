# 项目上下文

> 最后更新：2026-10-10（Asia/Shanghai）

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

- 首轮核心实现与24项测试完成；尚未满足交接包全部P0。
- 真实库25条：农交云24，高校链接型1。6条DOCX价格周期核实。
- API与本地worker当前启动；来源enabled默认false，不自动长期采集。
- Docker CLI存在，但Docker服务/桌面应用不可用；只做配置校验。
- 没有公网部署、外部通知、参赛报名/邮件发送或试用业绩。

## 重要设计决策

参见docs/DECISION_LOG.md；保守关联、unknown不推断、价格Decimal、原文和私人数据不入Git。

## 约束条件

- 不覆盖外部项目，不泄露private目录及密钥。
- 不绕过访问控制，不将搜索缓存视为适配成功。
- 公开仓库发布、服务器与真实通知目标需用户授权；当前仓库创建/源码推送已由用户授权。
- 用户最新“开始吧”允许正式开发，不需每个可逆步骤再次询问。

## 已知问题

第二来源正文覆盖不足；自动回扫/通知细节/人工审核未实现；真实量化目标待评测；安全与生产运行待验证。

## 下一步任务

先补第二来源关键字段、自动回扫与外部测试通道，再做人工纠正和跨源关联；保持运行版本可回放。

## 证据来源

backend/app、backend/tests/test_core.py、docs/VERIFICATION.md、docs/SOURCE_AUDIT.md、private/verification_counts.json（私有本地计数）。
