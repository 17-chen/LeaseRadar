# 项目上下文

> 最后更新：2026-10-18（Asia/Shanghai）

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

- 核心实现与213项完整本机回归通过；已补可续扫游标、活跃/关注详情复查、有限重试与可配置站内报名提醒；尚未满足交接包全部P0。
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

第二来源正文覆盖不足；真实SMTP服务商未配置；有依据条款计算和附件审核队列已实现；本机PDF/OCR工具未配置，真实样本准确率、容器运行、自动附件/复杂条款候选提取及比赛材料未完成；回扫预算与持久告警不保证动态列表完整性；来源/任务token归属与DNS连接固定已本地验证，生产多worker、大规模压力和PostgreSQL恢复仍需验收。来源告警SMTP与管理员发送审核/一次重试已实现，真实外部通道仍关闭。

## 下一步任务

继续PDF/OCR及完整条款/第二来源适配，生产与真实评测条件最后统一补齐。通知节奏、完整分页、人工纠正/撤销/冲突、人工关联聚合与重挂、预算/告警、导入/回放/评测工具已实现。0007有数据升级与异目录恢复验证；docs/WORKFLOWS_VERIFICATION.md记录范围，docs/FINAL_SETUP_CHECKLIST.md集中外部配置。

## 证据来源

backend/app、backend/tests/test_core.py、docs/VERIFICATION.md、docs/SOURCE_AUDIT.md、private/verification_counts.json（私有本地计数）。

0.1.6：0008附件表迁移与独立恢复通过；网页条款计算只读，合成DOCX上传/独立worker/审核闭环在DEMO通过。详细边界见docs/TERMS_ATTACHMENTS_VERIFICATION.md。

0.1.7：来源告警/恢复独立回执、管理员依据审核/一次重试/关闭终态、持久Message-ID与原地址保护；补附件队列备份。0009独立恢复和161项本机回归通过，详情docs/DELIVERY_REVIEW_VERIFICATION.md。

0.1.8：DOCX正文/表格按顺序提取并保留位置、删除修订排除；损坏请求生成失败结果而不终止worker。合成上传/提取/审核及备份回归通过；无新数据库迁移或依赖，真实源范围不变。API/worker重启后加载新版本，本文不代表本次已重启。见docs/DOCX_BODY_VERIFICATION.md。

0.1.9：采集/详情复查可将已缓存带哈希的来源附件自动送指定管理员私有审核，默认关闭；来源版本/URL与内容唯一身份、每观察5份及待处理20份限制、失败留存。0010副本升级/完整性及旧附件记录迁移通过，真实原库仍0009，常驻进程未重启。未下载附件的获取、完整第二来源和真实PDF/OCR评测未实现；见docs/SOURCE_DOCUMENTS_VERIFICATION.md。

0.1.10：未缓存PDF/DOCX下载独立持久队列、token/来源租约、有限重试/blocked、原始版本与管理员归属、状态分页。213项完整本机回归、一份公开DOCX真实GET（1,461,321字节）与隔离DEMO页面通过。真实库先备份再0009→0011，25挂牌/41版本/0下载/0审核，API0.1.10和本地worker已启动；来源/自动下载/邮件均关闭。真实PDF/OCR、生产与第二来源完整字段仍未验收。详情docs/DOCUMENT_DOWNLOADS_VERIFICATION.md。

0.1.11：高校独立适配器、合成fixture及18项测试，冲突unknown/明确日期时区/用途条款原文/正文附件安全元数据；真实历史全文1条核对，原库未导入历史样本。无新依赖/迁移。剩余比赛核心5–8、完整当前可独立开发范围15–25有效开发日（估算，见docs/DELIVERY_PLAN.md），用户配置与观察等待单列。

用户最新优先级（2026-10-18）：10月31日前提交、演示优先；按docs/COMPETITION_DEMO.md倒排，26日核心冻结/30日可提交包。0.1.12新增scripts/demo.py和app.demo，全新隔离目录合成6候选/7版本/5提醒，随机账号指南；拒绝覆盖与继承真实DB，强制关闭外部通道。完整功能估算保留作后续计划，不再作为演示提交前置。

0.1.12本机236项完整回归通过；实际隔离DEMO在127.0.0.1:8001启动，当前指南private/demo-runs/647be7504b4e/DEMO_GUIDE.md。最终录屏/介绍PDF/公开提交尚未执行，后续按倒排优先处理。
