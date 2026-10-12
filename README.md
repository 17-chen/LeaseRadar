# LeaseRadar · 铺讯

面向门店拓展的招租公告发现、筛选与跟进工作空间。比赛优先，兼顾真实使用；筛选条件由用户选择，未选项不限。

**状态：0.1.6-dev，本地条款与附件审核版本。** 不是完整规格验收或生产上线版本。GitHub仓库目前私有。

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

2026-10-11：148项本机测试通过；通知摘要/静默、完整历史、人工纠正与可撤销关联、租约归属、DNS连接固定、回放/评测工具及0007恢复已验证。浏览器桌面与390px手机验收使用隔离DEMO数据，未混入真实库。见[本阶段验收](docs/WORKFLOWS_VERIFICATION.md)。

农交云采集2页24条记录，随后第一页12条DOCX增强复查，6条价格周期得到附件证据。高校扫描5页仅发现1条链接型公告，其关键字段未覆盖，不计作完整第二来源接通。温州产权平台只验证首页可访问，适配器未实现。本阶段又完成2条农交云详情及1条高校已入库详情复查，均为提取更新，未扩大独立第二来源关键字段覆盖。具体见[审计](docs/SOURCE_AUDIT.md)与[验证报告](docs/VERIFICATION.md)。

未验证/未实现：Docker实际运行、生产部署、真实外部邮件投递、完整第二来源字段、完整覆盖保证、PDF/OCR、完整条款计算、来源告警外发/死信重放及真实评测指标。不能宣称全网覆盖、确定允许咖啡经营、最低总成本或已开展完整试用。详见[路线图](ROADMAP.md)。

## 项目资料

[项目上下文](PROJECT_CONTEXT.md) · [任务清单](TODO.md) · [架构](ARCHITECTURE.md) · [技术决策](docs/DECISION_LOG.md) · [原始交接](docs/handoff/README_FIRST.md) · [比赛要求](docs/COMPETITION_REQUIREMENTS.md)

## English

LeaseRadar helps retail expansion teams discover public leasing announcements, filter candidates, inspect field evidence, compare rent on verified bases, and track follow-ups. This initial local development release includes a FastAPI backend, a responsive HTML/JavaScript frontend, deterministic HTML/DOCX extraction and a durable database job queue. It does not yet satisfy the full production specification. Unknown terms remain unknown; sample replay and live data must stay separate. See the deployment guide and roadmap for setup and current limitations.

Code license: MIT. Public source content and original handoff material are not relicensed by this repository; see[数据政策](docs/DATA_POLICY.md)。

SMTP通知与来源异常：可配置单用户邮件通道与摘要已通过本地协议/注入发送测试，真实邮件默认关闭。邮件回执与站内通知分别显示；来源页提供管理员当前异常及恢复历史。启用与状态语义见 [运行与部署](docs/DEPLOYMENT.md)。

最新阶段：0.1.6-dev，148项本机回归、0008异目录恢复、条款算式和DEMO附件闭环验证。新增[条款与附件验收](docs/TERMS_ATTACHMENTS_VERIFICATION.md)。升级先备份、migrate至0008，再重启API/worker。外部资料可以最后统一补齐，见[最后配置清单](docs/FINAL_SETUP_CHECKLIST.md)。

条款与附件：网页支持有依据的租金递增/免租/分段计算；PDF/DOCX上传进入私有审核队列，OCR文字不自动改字段。PDF/OCR需独立隔离提取worker，本机工具缺失/容器未启动仍保持待处理，见本阶段验收。
