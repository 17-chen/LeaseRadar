# LeaseRadar（铺讯）新聊天交接

> 更新：2026-10-23，Asia/Shanghai。应用代码基线：92ba1a3；最新已核对交接提交863d24d。本轮材料与演示复核见docs/submission/DEMO_MATERIALS_20261023.md。本文保存项目事实与用户决策，不是全功能完成或正式提交证明。

## 1. 新聊天先读什么

在同一项目目录打开新聊天，明确要求先读本文和 [剩余工作](docs/REMAINING_WORK.md)，再读根目录AGENTS.md、PROJECT_CONTEXT.md、TODO.md。按任务读取README.md、ARCHITECTURE.md、docs/DECISION_LOG.md及对应验收记录。原始需求在docs/handoff/01_TECHNICAL_REPORT.md和02_IMPLEMENTATION_PLAN.md，规格中的勾选/能力不能直接当运行事实。

新聊天不应假定已有本聊天的完整历史、工具变量、进程会话号、浏览器登录或临时权限。本文及仓库是接手入口；private目录只在这台电脑保留，GitHub克隆没有真实数据/账号/本地运行包。先核查现状，不重建项目、不把现有工程覆盖为新脚手架。

## 2. 用户目标、期限与授权

- 产品：发现公开招租公告，自由筛选、比较可核实价格、查看字段依据、及时提醒并跟进。
- 用户希望兼顾实际使用与比赛，当前优先比赛演示；筛选条件应像正常筛选栏一样自行选择，不锁死在咖啡或固定预算。
- 用户明确10月31日前提交。当前内部目标：10月26日核心演示冻结，27–29日录制/修复，30日形成可提交包，31日缓冲。该安排是目标，不代表全规格验收完毕。
- 用户希望持续推进不依赖其操作的工作，不必每轮重新确认；需要用户配置的内容集中在最后补。不要把代码缺口都归为“等用户资料”。
- 已授权本地开发、检查、文档、现有私有GitHub仓库提交/推送；不自动公开仓库、向真实收件人发消息、报名/提交比赛、付费或公网发布。
- 用简明中文说明结果；UI面向非技术用户。保留已有工作与失败样本，不虚构业绩/合作/试用/准确率。

## 3. 仓库与版本

| 项目 | 已核实状态 |
| --- | --- |
| 本机目录 | /Users/chenxin/Documents/瑞幸咖啡 网页检索 |
| GitHub | https://github.com/17-chen/LeaseRadar，私有 |
| 分支 | main；新建开发分支默认codex/前缀 |
| 应用代码基线 | 92ba1a3efbbd21beb93ef92007a646b7a3f304fc |
| API标识版本 | backend/app/main.py：0.1.16；后续材料/会话修复未升版本 |
| 数据库迁移头 | 0011_document_downloads |
| 依赖 | backend/requirements.lock；本机Python3.13，GitHub CI Python3.12 |
| 最新应用CI | https://github.com/17-chen/LeaseRadar/actions/runs/39789625172，2026-10-23查询completed/success，head=92ba1a3 |

交接编写前工作树无已跟踪修改，仅有用户既有未跟踪Un8(1)/、output/ui-refresh.jpg、output/ui-workbench.jpg；不要删除、改写或随手git add全部。本文提交本身会产生后续文档提交，以git log为准，不让交接基线自指。

近期提交定位：92ba1a3演示Cookie隔离；eb430a1分镜视频与媒体验证；f50223e材料刷新/打包版本保护；ccd5a1c提取结果加固；13ce43d收藏/跟进快捷视图；abf2d8a工作台与筛选CSV。

## 4. 当前实现与技术结构

本地模块化单体：FastAPI + SQLAlchemy/Alembic + SQLite + 数据库持久任务/local_worker；前端原生HTML/CSS/JavaScript。Compose提供PostgreSQL16/Redis/Celery部署设计，尚未完成真实生产运行验收。无模型依赖、无AI提取，不要为比赛措辞虚称LLM能力，也不要突然迁移React或重构全栈。

| 模块 | 实现/入口 |
| --- | --- |
| 登录/CSRF/角色/接口 | backend/app/main.py、config.py、session_cookies.py |
| 模型/不可变版本/依据/任务 | backend/app/db.py、backend/migrations |
| 来源采集与安全连接 | collectors.py、adapters/wzpt.py、attachments.py |
| 价格/时间/三值规则 | domain.py、lease_terms.py |
| 入库/事件/任务 | service.py、local_worker.py、tasks.py |
| 提醒/摘要/邮件/人工回执 | notifications.py、scheduling.py、email_delivery.py、incident_email.py、delivery_review.py |
| 人工纠正/同挂牌聚合/重挂关系 | review.py、resolution.py、workflows_api.py |
| 来源覆盖/告警 | coverage.py |
| 私有文档上传/审核/下载/提取 | document_jobs.py、document_downloads.py、source_documents.py、document_worker.py |
| 快捷视图 | listing_views.py；列表与CSV共用main.searched_rows |
| 演示与材料 | app/demo.py、scripts/demo.py、scripts/build_recording_bundle.py、docs/submission |

已实现：自由筛选/unknown保留、可核实首年租金换算、字段原文依据、2–5项比较、收藏/跟进/私人笔记、站内提醒、配置式SMTP与摘要、报名截止提醒、来源健康/回扫/退避、事务outbox、人工纠正/冲突/关联撤销、CSV防公式注入、私有附件审核、受控下载、DOCX正文/表格与PDF文字/OCR工作协议。实现不等于所有真实场景已验收，详见下节与剩余工作文档。

## 5. 真实接入范围与不应扩大宣称的内容

- 最近历史核实真实库25条挂牌/41版本：农交云24条，高校1条链接型；本次交接未重查数据库计数，不能叫10月23日实时机会总数。
- 农交云：真实列表/详情、分页、原文快照、6条DOCX价格周期证据。已有真实复查记录；不等于全站/全时段覆盖。
- 高校：独立adapter和fixture已实现，1条历史2025文章全文做过真实GET/字段核对，但未作为当前机会导入。真实库中的链接型记录不算完整第二来源接通。
- 温州产权平台：首页可达历史证据；链接指向未核准zjpse异域，不扩大白名单绕过，不称adapter接通。
- 10月21日已有真实DOCX只读复核：16087字符、233正文段定位、16表行；未自动发布字段，不等于隔离容器或准确率评测。
- 来源默认关闭；最近真实库来源均未启用，自动附件/下载/真实SMTP关闭。交接未访问来源、未发真实邮件、未启动真实采集。
- 无生产部署、真实用户试用、真实邮件最终投递、真实OCR准确率、覆盖/收益/节省耗时指标。禁止用合成数据或系统测试数替代这些结论。

相关证据：docs/SOURCE_AUDIT.md、VERIFICATION.md、WZPT_ADAPTER_VERIFICATION.md、EXTRACTION_VALIDATION_VERIFICATION.md、DOCUMENT_DOWNLOADS_VERIFICATION.md。

## 6. 工程与安全约束

根目录AGENTS.md为完整规范。核心规则：金额Decimal，时间带时区，未知不是0；标题“五年”不能直接把未知价格除60；报名截止优先于竞价截止，披露日期不代替报名时间；经营许可未说明不能当允许。铺位/批次/源公告分离，整体出租不拆价，关键字段保留依据。

数据库为权威，事件/outbox同事务且幂等；外部邮件结果不明不得自动冒险重发，不承诺外部绝对一次。页面变动、再提取、商业变更分开。来源访问白名单、SSRF/DNS固定、拒绝重定向和文件隔离不削弱；blocked保留失败。不把真实公告、数据库、账号、原始文件或私人笔记放入Git/视频。

DEMO按数据库URL摘要命名Cookie，LIVE/replay保留lease_session；旧DEMO升级重启需重新登录，不清除LIVE Cookie。该规则减少同主机端口误覆盖，不能隔离恶意同主机服务，多套LIVE仍需不同主机/域名。详见SESSION_ISOLATION_VERIFICATION.md。

## 7. 检查基线与运行状态的区别

10月22日92ba1a3代码：完整275项本机回归通过，41.39秒；另1项真实Poppler工具/合成PDF集成通过，0.56秒；JS语法、依赖一致性、diff检查通过。1条Starlette/AnyIO上游弃用警告保留。10月23日确认上述提交GitHub CI成功，含Linux Python3.12测试、迁移、JS与Poppler集成；不包括macOS媒体编码或生产环境。

本次交接只核查Git、CI、文件和资料，没有重跑全部应用测试。不要将旧测试时长/数量当成新改动已跑过的结果。

进程仅有历史线索，非当前保证：真实API曾在8000（旧版本），多个DEMO曾占8001–8006；最新截图DEMO目录private/demo-runs/366c911e47bd曾在8006，8010曾仅提供output/video预览。接手先检查占用，别把端口猜成最新进程或批量kill。上一轮修复未重启真实/既有演示进程；新聊天宜选择空闲端口新建DEMO。

Docker CLI存在，10月21日docker info曾因无daemon失败；本次未复查。不能把配置文件存在或Poppler宿主集成成功写成Docker隔离worker验收。

## 8. 演示重建与验收路线

```sh
cd '/Users/chenxin/Documents/瑞幸咖啡 网页检索'
git status --short
git log -5 --oneline
.venv/bin/python scripts/demo.py --port 8007
```

8007仅建议，先检查是否空闲。脚本每次创建全新private/demo-runs目录、独立demo.db、随机demo账号及0600指南；终端显示路径，密码只在本机指南，不打印到交接或Git。不覆盖旧目录，不启动worker；强制APP_MODE=demo、独立DB、所有外部通道关闭。只准备数据可加--prepare-only，指定目录必须不存在。

合成6候选/7版本/5站内通知：A年租96000→90000，首年月基准7500；B年租120000，月基准10000；另有超预算、已截止、价格冲突unknown、标题五年但周期未知。面积≥30、月基准≤12000、仅可报名且含unknown→4条，比较ID 1/2/6。七步：筛选→比较→已知依据→未知口径→收件箱→跟进→来源受阻；另核查收藏视图及CSV。所有数字是合成场景，不是真实业绩。七步路线受模式/原管理员/marker/截止时效校验，过期时新建DEMO，不改系统时间或旧数据。

浏览器交互按当前可用CUA工具规范执行，不能依赖旧聊天tab变量或工具会话号。截图工具可能返回JPEG字节，即使目标扩展名写成PNG；媒体构建器会检查真实签名，必须核对扩展名。

## 9. 已有材料与证据版本

| 材料 | 位置与实际状态 |
| --- | --- |
| 介绍PDF | output/pdf/LeaseRadar_Competition_Intro_Draft.pdf；6页，0.1.16，10月21日审阅快照；依据ccd5a1c/262测试，非终稿 |
| PDF构建 | scripts/build_competition_intro.py；独立可选文档依赖，修改须按PDF技能渲染全部页面审阅 |
| 集中材料证据 | docs/submission/RELEASE_EVIDENCE.json；保留旧实现证据，不机械改测试数字 |
| 分镜视频 | output/video/LeaseRadar_Storyboard_Review.mp4；206.9秒，1920×1080，10fps，H.264/AAC |
| 视频性质 | 实际合成UI截图＋本机Tingting合成旁白；持续标识静态分镜/非连续录屏；不是用户声音或真实试用 |
| 视频证据 | 口播依据f50223e/263测试；全片2069帧/573音频缓冲解码、10场景预览及浏览器播放验证；未逐字人工听审 |
| 视频重建 | scripts/build_storyboard_video.py、render_storyboard_video.swift、verify_storyboard_video.swift；macOS原生工具已验证，Linux CI仅验证输入规则 |
| 视频源素材 | docs/submission/VIDEO_STORYBOARD.json、video-assets；边界与失败路径见VIDEO_DRAFT.md |
| 逐镜头稿 | docs/submission/RECORDING_SCRIPT.md；五分钟建议稿与现有3分27秒分镜不是完全同一时间线 |
| 最新本地小运行包 | private/LeaseRadar_Recording_92ba1a3.zip；58个payload文件，57个仓库文件逐字节匹配92ba1a3；另有MANIFEST，未含视频 |

视频SHA256：833ffa946aaa5c7b75fffbcfbf62dce25bb0f54fc7de6148ab8c15d36b9c5806。
最新运行包SHA256：13ab7863a15be7d59cde7c6c369dd793a3dd1ba0fe80a85ad2a682eaed48717e。proof在同名.proof.json；manifest的working_tree_dirty=true来自既有未跟踪文件，不等于包内源码有未提交修改，已有逐文件匹配证明。

打包：`.venv/bin/python scripts/build_recording_bundle.py --output private/新的录制包.zip`；显式清单、拒绝覆盖和符号链接、不含private原始数据，API版本与RELEASE_EVIDENCE版本不同会拒绝。不要通过简单篡改证据JSON绕过保护。小包是本地运行交接，ready_to_submit=false，非最终参赛材料全包。

macOS媒体构建曾遇沙箱原生编码服务不可用、AIFF直接合成失败；改AAC、保留源asset、真实时长与直封装后最终端到端成功，失败保留在private。若重建需本地原生编码服务权限，不能误称需要录屏/麦克风权限。视频旁media.json/proof.json只是完整性记录，不是可信签名。

## 10. 比赛要求与尚待确认

官网：https://www.oschina.net/oa2026/。历史核验与限制见docs/COMPETITION_REQUIREMENTS.md。10月22日直接网页读取为通用社区页，官网检索索引约三周前；不能把索引当当日表单/资格已确认。资料列代码仓库链接、作品介绍（推荐PDF）、核心功能/流程视频链接；个人/普通学生团队参赛主体资格、报名审核、材料访问与实际提交尚未确认/执行。

建议赛道一是项目建议，并非用户已报名事实。3–5分钟明确属于赛道三，不能当赛道一硬时长。已知资料中的日期矛盾不擅自修正；最终以正式报名/审核指引为准。无向组委会发邮件或报名记录。

## 11. 恢复与验证命令

2026-10-23接手补充：新建8008/8009两套隔离合成DEMO，最新源码浏览器七步、收藏/跟进、筛选CSV四行、双端口退出隔离通过；8008指南在`private/demo-runs/f1746b395fb7/DEMO_GUIDE.md`，8009在`private/demo-runs/e418dc2de39c/DEMO_GUIDE.md`。PDF审阅稿已修正静态分镜视频状态并逐页渲染检查。275项本机回归及1项Poppler集成通过；首次受限沙箱中本机SMTP绑定失败，获本机监听权限后全通过。390px最新页面、自然过期提示、最终视频听审与正式提交仍待核验。详见docs/submission/DEMO_MATERIALS_20261023.md；Git同步状态以本轮最终记录为准。

以下从仓库根目录运行。新机器先建venv并用backend/requirements.lock安装，不随意升级依赖。

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

本机Poppler集成需将工具目录加入PATH，不是应用依赖已全局配置：

```sh
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
```

测试会使用独立临时DB、合成本地SMTP；不要对真实DB运行破坏式测试。迁移/备份/真实服务恢复按DEPLOYMENT.md审查后执行，别为了看界面先对默认LIVE库创建账号/清库/导入。配置、源开关与真实收件人更改都不属于“接手读资料”步骤。

下一轮优先顺序：新建最新DEMO→完整七步与多端口浏览器彩排→提交材料内容/口播终审与PDF更新→最终视频/源码/文档包一致性与失败恢复检查。具体验收门槛、用户事项及生产后续在docs/REMAINING_WORK.md。
