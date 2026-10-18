# LeaseRadar · 铺讯

面向门店拓展的招租公告发现、筛选与跟进工作空间。比赛优先，兼顾真实使用；筛选条件由用户选择，未选项不限。

**状态：0.1.11-dev，高校公告字段可靠性版本。** 不是完整规格验收或生产上线版本。GitHub仓库目前私有。

## 已实现

- 登录、HttpOnly会话、CSRF、服务端admin/member权限与个人订阅/笔记隔离。
- 关键词、城市/区县、面积、月租基准、物业类型、环境、经营用途和状态自由筛选；未知条件可保留待确认。
- 农交云实际列表/详情分页采集、原文快照、版本和字段依据；DOCX表格精确标的身份与金额核对后识别首年租金。
- 保存订阅、三值匹配、首次历史摘要、事务事件/outbox和站内收件箱；可配置报名截止提醒，延期/关闭/放弃/暂停后作废旧提醒。
- 收藏、跟进状态/笔记、2–5条比较、CSV公式注入防护；人工纠正/源更新冲突审核、同挂牌出处聚合及可撤销重挂关联。
- 每日摘要/静默/催办例外、完整历史分页、来源覆盖预算与持久告警、核准链接导入、独立DEMO回放与字段评测工具。
- 来源健康、分页续扫、活跃/关注详情复查、403/429退避、数据库持久任务、本地worker；部署包提供PostgreSQL/Redis/Celery。

## 运行

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/python -m app.cli create-admin
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开终端运行后台：

```sh
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

打开 http://127.0.0.1:8000 。来源默认关闭，管理员可手动采集或启用30分钟轮询；本机休眠/关机影响运行。生产常驻部署请看[部署手册](docs/DEPLOYMENT.md)。

## 验证与限制

2026-10-13：161项本机测试通过；通知摘要/静默、完整历史、人工纠正与可撤销关联、租约归属、DNS连接固定、回放/评测工具及0007恢复已验证。浏览器桌面与390px手机验收使用隔离DEMO数据，未混入真实库。见[本阶段验收](docs/WORKFLOWS_VERIFICATION.md)。

农交云采集2页24条记录，随后第一页12条DOCX增强复查，6条价格周期得到附件证据。高校扫描5页仅发现1条链接型公告，其关键字段未覆盖，不计作完整第二来源接通。温州产权平台只验证首页可访问，适配器未实现。本阶段又完成2条农交云详情及1条高校已入库详情复查，均为提取更新，未扩大独立第二来源关键字段覆盖。具体见[审计](docs/SOURCE_AUDIT.md)与[验证报告](docs/VERIFICATION.md)。

未验证/未实现：Docker实际运行、生产部署、真实外部邮件投递、完整第二来源字段、完整覆盖保证、真实PDF/OCR样本、复杂条款自动提取、来源告警真实投递/服务商回执验收及真实评测指标。不能宣称全网覆盖、确定允许咖啡经营、最低总成本或已开展完整试用。详见[路线图](ROADMAP.md)。

## 项目资料

[项目上下文](PROJECT_CONTEXT.md) · [任务清单](TODO.md) · [架构](ARCHITECTURE.md) · [技术决策](docs/DECISION_LOG.md) · [原始交接](docs/handoff/README_FIRST.md) · [比赛要求](docs/COMPETITION_REQUIREMENTS.md)

## English

LeaseRadar helps retail expansion teams discover public leasing announcements, filter candidates, inspect field evidence, compare rent on verified bases, and track follow-ups. This initial local development release includes a FastAPI backend, a responsive HTML/JavaScript frontend, deterministic HTML/DOCX extraction and a durable database job queue. It does not yet satisfy the full production specification. Unknown terms remain unknown; sample replay and live data must stay separate. See the deployment guide and roadmap for setup and current limitations.

Code license: MIT. Public source content and original handoff material are not relicensed by this repository; see[数据政策](docs/DATA_POLICY.md)。

SMTP通知与来源异常：可配置单用户邮件通道与摘要已通过本地协议/注入发送测试，真实邮件默认关闭。邮件回执与站内通知分别显示；来源页提供管理员当前异常及恢复历史。启用与状态语义见 [运行与部署](docs/DEPLOYMENT.md)。

历史阶段：0.1.7-dev，161项本机回归、0009恢复及DEMO发送审核验证。见[告警与发送审核验收](docs/DELIVERY_REVIEW_VERIFICATION.md)。升级先备份、migrate至0009，再重启API/worker。外部资料可以最后统一补齐，见[最后配置清单](docs/FINAL_SETUP_CHECKLIST.md)。

条款与附件：网页支持有依据的租金递增/免租/分段计算；PDF/DOCX上传进入私有审核队列，OCR文字不自动改字段。PDF/OCR需独立隔离提取worker，本机工具缺失/容器未启动仍保持待处理，见本阶段验收。

来源告警邮件默认单独关闭，启用后只向已配置管理员发异常/恢复通知。结果不明须服务商依据才能审核重试；关闭保留历史且不自动恢复。备份现包含上传附件队列。

最新附件能力：DOCX正文段落与表格按文档顺序进入私有审核，保留段/表/行依据，删除修订不计入文字；损坏请求保留失败结果，不阻塞后续附件。未自动提取业务条款，未扩大真实来源。见[正文与队列验收](docs/DOCX_BODY_VERIFICATION.md)。

来源附件审核：启用SOURCE_DOCUMENTS_ENABLED并指定SOURCE_DOCUMENTS_USER_ID管理员后，采集/详情复查会将已保存且带SHA256的来源附件复制到私有审核队列；默认关闭。仅启用此审核开关不会自动下载未缓存附件；受控下载有单独开关。需先备份、迁移0010并重启API/worker；见[来源附件验收](docs/SOURCE_DOCUMENTS_VERIFICATION.md)。

受控下载：SOURCE_DOCUMENT_DOWNLOADS_ENABLED默认false，同时要求来源附件审核开关和有效管理员。支持核准HTTPS地址的.pdf/.docx，5MB、最多3次、Retry-After与共享来源租约；401/403保留blocked，不跳转或绕过。页面显示下载和审核的独立状态。213项回归及一份真实DOCX下载已验证；不是完整第二来源接通或PDF/OCR准确率验收。升级至0011后使用，见[下载验收](docs/DOCUMENT_DOWNLOADS_VERIFICATION.md)。

0.1.11：高校独立适配器增强价格/面积冲突、日期语义与原文条款依据；已核对1条历史全文，不等于当前第二来源完整接通。见[验收记录](docs/WZPT_ADAPTER_VERIFICATION.md)。剩余范围与估算见[交付计划](docs/DELIVERY_PLAN.md)：比赛核心5–8个、完整可独立开发范围15–25个有效开发日，外部配置等待另计。
