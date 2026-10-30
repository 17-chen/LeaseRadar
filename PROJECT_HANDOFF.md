# LeaseRadar（铺讯）新聊天交接

> 更新：2026-10-29，Asia/Shanghai。长版新增42条字幕、十场景逐段稿及支持实际跳转的本机审阅服务，见docs/submission/CAPTION_REVIEW_20261029.md。API仍标0.1.16，工程材料的历史实现证据仍据ccd5a1c。本文保存项目事实与用户决策，不是全功能完成或正式提交证明。

2026-10-30公开仓库：用户明确要求改为public，已将17-chen/LeaseRadar设置为PUBLIC，并通过不带登录凭据的GitHub API及raw README请求验证公开可读。公开前扫描全部可达历史中的699个小于2MB对象，未发现常见密钥模式，未发现private/、原始快照、数据库或凭据文件被提交；这是模式/路径预检，不是完整安全审计。用户原有未跟踪文件未纳入Git。视频分享链接由用户自行处理。此前“私有/评审访问未确认”是历史状态，现源码访问缺口已解决；10月29日PDF及旧ZIP中的可见性说明仍是当时快照，文件字节未因设置变更自动更新。

用户随后回复确认：已报名并收到组委会确认邮件，以个人方式参赛；按用户说明登记，未读取原邮件，不写入私人联系方式。视频平台未定，消息未附实际评审链接。PDF/对照表和邮件稿已据此更新；剩余重点为源码评审访问、视频链接与最终听审。此前“报名未确认”的当时记录不代表最新用户状态。

据此从`5154540`重建Individual版114文件完整包与258,842字节小包，逐项Git/哈希及确切ZIP独立禁外网恢复通过；最新PDF第6页同步用户确认事实并重做QA。路径/SHA见SUBMISSION_PACKETS_VERIFICATION_20261029.md。旧f9980e3包保留历史，不是最新报名状态。`2427cb0` CI已成功，随后材料提交需按最新head核对。

2026-10-29提交前核查：用户明确明天10月30日交。实时官网和报名弹窗已通过浏览器读取，主体选项**包含学生团队**，更新早先仅凭索引无法确定学生团队资格的记录；本人报名/邮件现已由用户确认，实际姓名等私有资料未写入仓库。三类材料、10月31日24:00、确认邮件流程及原创/授权/赛事展示承诺均已看到，未填写/勾选/提交。对照与明日动作见docs/submission/SUBMISSION_READINESS_20261029.md，未发送邮件稿见SUBMISSION_EMAIL_DRAFT.md。

本轮六页PDF更新到326项/ccb0fb0与eca595e CI、207.6秒有声稿/42条字幕，262项/ccd5a1c历史证据分开；最终六页渲染/文字检查通过，见PDF_REVIEW_20261029.md。完整326项本机回归、1项Poppler、字幕重建、JS/依赖/差异检查通过。源码仍私有、视频仅本机，评审访问和真人逐字听审未签收，因此不能认定已满足全部正式提交条件。新包与GitHub记录另记。

从`f9980e3`生成114文件提交前完整审阅包，113项Git字节一致、确切ZIP独立禁外网合成恢复和字幕检查通过；另生成258,421字节小型核对包，含PDF/对照表/邮件草稿。哈希与范围见docs/submission/SUBMISSION_PACKETS_VERIFICATION_20261029.md。两包仅在private且未正式就绪；本人报名与发布/发送仍未执行。

2026-10-29续作：接续开工时已有的字幕脚本/页面修改，补生成验证、逐段定位及HTTP字节范围服务，修复普通静态服务下跳转停在0秒。326项本机回归、1项Poppler集成、字幕重建/JS/依赖/差异检查通过；1280px和390px分别验证十次实际播放定位及对应字幕，无页面错误或整体横向溢出。首次静态服务及换行失败记录保留private；视频字节未改，未真人逐字听审。README和材料入口已统一到长版及字幕。新包/提交状态另记。

2026-10-29新包：从`ccb0fb0`生成111文件字幕审阅包，110项仓库字节匹配，预解压校验通过；确切ZIP独立禁外网合成恢复、字幕重建检查与回环媒体206请求通过。SHA256及范围见docs/submission/CAPTION_BUNDLE_VERIFICATION_20261029.md。包仅在private，`ready_to_submit=false`；原视频字节、真实接入与外部通道未改。最终GitHub提交/CI以本轮实际核查为准。

2026-10-28新媒体：从`41c9e76`新建合成DEMO录制十场景连续Chrome画面，零裁切原片207.48秒；生成207.6秒有声审阅稿，原片与成片完整解码、十阶段目视和本地Chrome预览元数据检查通过。保留一次错误裁切样本于private；系统合成旁白未经过真人逐字听审。完整293项回归及1项Poppler集成通过，JS语法、依赖和差异检查通过。新包与GitHub状态以随后记录为准。

2026-10-28新包：从`e58d268`生成105文件私有审阅包，104个仓库文件与提交逐字节一致，预解压校验与确切ZIP独立禁外网合成恢复通过；SHA256与边界见docs/submission/FULL_BROWSER_BUNDLE_VERIFICATION_20261028.md。`ready_to_submit=false`，真实接入范围不变。GitHub状态以随后记录为准。

2026-10-28 GitHub：`90029b4`已推送私有`origin/main`；[Tests运行40633005440](https://github.com/17-chen/LeaseRadar/actions/runs/40633005440) completed/success，覆盖Linux应用测试、迁移、JS与Poppler集成。macOS视频编码、真人听审及正式提交不在CI中。若本交接本身随后单独提交，最新head的CI需另核。

2026-10-27新包：96项许可文件中95项与`5fd845a`逐字节一致，另1项为生成的入口指南；预解压校验及确切ZIP独立禁外网合成登录/筛选恢复通过。ZIP SHA256 `9b0748eee40a46cfce4e2538160bae8a20a68c8913940ca25f285f3767a2ace0`，仅在private；原89文件包保留。三种媒体各自标注，`ready_to_submit=false`。GitHub同步及CI以随后记录为准。

2026-10-27 GitHub：`b5f5b83`已推送私有`origin/main`，对应[Tests运行40429647203](https://github.com/17-chen/LeaseRadar/actions/runs/40429647203) completed/success；Linux应用回归、迁移、JS和Poppler集成均通过。macOS媒体编码/真人听审不在CI中。之后若仅更新交接文档，最新CI仍应按新head复查。

2026-10-27视频续作：用已验证的55.68秒合成七步Chrome连续录屏，生成55.8秒1280×840/10fps H.264有声剪辑稿；上沿全程标明自动化浏览器操作与系统合成旁白。完整558帧和145音频缓冲解码、峰值0.723及八阶段抽帧通过；末段原先提前进入旁白已修正，失败与早版保留在private。成片/旁白稿/proof和边界见docs/submission/BROWSER_REVIEW_VIDEO_20261027.md。尚未真人逐字听审，不称最终投稿视频；真实来源、邮件与生产范围未变化。打包器已补三类媒体核验，完整289项回归及1项Poppler集成通过；新包/CI以随后记录为准。

2026-10-26演示续作：从当前a9e6981代码新建8015隔离合成DEMO，Chrome/Playwright连续走完七步，录成55.68秒无音轨WebM，剔除原始捕获首0.8秒空白登录表单；最终首帧为合成候选页。浏览器脚本已通用化并复跑七步，输出SHA和录制方式证明；关键镜头抽帧目视、成品完整解码通过。它是自动化连续浏览器操作，**不是带讲解的最终投稿视频**，原静态分镜逐字听审仍待完成。17项包专项、285项完整回归及1项Poppler集成通过。见docs/submission/BROWSER_WALKTHROUGH_20261026.md。真实来源/邮件未启用，8015已停止，原8001 SSH未触碰。本轮新包与GitHub状态以随后记录为准。

2026-10-26新包：从512678b生成89文件完整审阅包，88项仓库字节匹配，预解压校验及确切ZIP独立禁外网合成登录/筛选/比较/CSV恢复通过。静态分镜与无音轨连续操作片段均在包中并分别标识；SHA256和边界见docs/submission/BROWSER_WALKTHROUGH_BUNDLE_VERIFICATION_20261026.md。`ready_to_submit=false`，GitHub同步/CI以本轮后续记录为准。

2026-10-25材料续作：六页PDF已按新DEMO七步/390px彩排重建并逐页渲染目视，材料日期更新；完整PDF QA见docs/submission/PDF_REVIEW_20261025.md。为现有207.5秒静态分镜新增逐段人工听审清单，十段文字/音频文件与时长自动核对通过，但**没有完成真人逐字听审**；见docs/submission/VIDEO_LISTENING_CHECKLIST_20261025.md。旧82文件包不含新版PDF。完整回归首次因沙箱禁止本机SMTP监听为281过/1失败，允许回环监听后282项全过；Poppler集成、JS语法、依赖一致性和差异检查通过。新包与GitHub状态以本轮后续记录为准。

2026-10-25新包：从f7f1fc7生成85文件本地完整审阅包，84仓库文件逐字节匹配，预解压校验与确切ZIP独立禁外网合成登录/筛选/比较/CSV恢复通过；SHA256与限制见docs/submission/PDF_REVIEW_BUNDLE_VERIFICATION_20261025.md。`ready_to_submit=false`，GitHub同步与CI以本轮后续记录为准。

2026-10-23续作：含视频的80文件本地完整审阅包已基于`d306277`生成，独立解压/逐文件Git匹配/无外网DEMO恢复通过；SHA256和边界见docs/submission/FULL_REVIEW_BUNDLE_VERIFICATION.md。这是历史包，不能代表10月24日PDF字节。此包仍非最终参赛提交包，视频为静态分镜草稿、PDF为审阅稿。新增包专项测试后完整280项回归通过；真实来源和外部通道未操作。GitHub同步与CI以最新提交状态为准。

2026-10-24续作：从`e369687`生成新版80文件含视频审阅包，79个仓库文件与提交逐字节匹配，ZIP哈希/CRC和无外网独立DEMO初始化通过；PDF为10月24日材料，视频仍是原静态分镜草稿，`ready_to_submit=false`。完整280项本机回归、1项Poppler集成及材料逐页QA通过。范围与哈希见docs/submission/FULL_REVIEW_BUNDLE_VERIFICATION_20261024.md；新包仅在private。

2026-10-24后续：新建8011隔离合成DEMO，在窄屏复核详情与三项比较；模拟服务端会话到期触发401后，修复登录页持续提示。基于`234918c`重新生成80文件包，79项Git字节匹配、哈希/CRC及独立无外网DEMO初始化通过；完整280项回归和1项Poppler集成通过。见docs/submission/MOBILE_SESSION_VERIFICATION_20261024.md及FULL_REVIEW_BUNDLE_VERIFICATION_20261024_MOBILE.md。视频/正式提交仍未完成。

2026-10-24本轮：新增标准库ZIP预解压校验器及损坏/恶意条目专项测试，从`b5132b9`生成81文件新审阅包；80项Git字节匹配、逐项哈希/CRC通过。独立解压后在禁外网条件下完成DEMO初始化、登录、筛选4条、比较、CSV和静态资源HTTP链路。完整281项回归、1项Poppler集成通过；首轮本地SMTP因沙箱端口绑定受阻，获准本机监听后重跑通过。视频10场景时间线/图片哈希一致，但未人工逐字听审；PDF与视频内容未改。见docs/submission/VERIFIED_REVIEW_BUNDLE_20261024.md。

2026-10-24续作：旧视频末镜头“当前263项”会被误解为现时状态，改为指向截图对应源码阶段并重建207.5秒静态分镜；视频proof增加分镜稿哈希，打包器拒绝口播稿与视频证据不一致。PDF第6页同步约3分28秒并渲染检查。从`0b1d266`生成81文件包，80项Git字节匹配、独立禁外网HTTP恢复通过；完整282项回归、1项Poppler集成通过。旧视频/包及首次沙箱AAC失败保留。没有人工逐字听审或正式提交。见docs/submission/VIDEO_REFRESH_BUNDLE_VERIFICATION_20261024.md。

2026-10-25续作：从最新e67da58新建隔离合成DEMO，原生浏览器重新走完七步；390px来源页及三候选比较可读，页面无整体横向溢出，截图与受限沙箱失败现场留在private。录制建议稿纠正历史测试数/真实样本“当前”的歧义。尚未逐字听审视频或签收演示冻结；完整记录见docs/submission/DEMO_FREEZE_REHEARSAL_20261025.md。本轮最终测试、审阅包和GitHub状态以随后记录为准。

2026-10-25包续作：从`1fbeef2`生成82文件完整审阅包，81项仓库字节匹配、预解压校验及独立禁外网合成登录/筛选/比较/CSV恢复通过。282项完整应用回归、1项Poppler集成及14项包专项测试通过。包在private，`ready_to_submit=false`；详见docs/submission/REHEARSAL_BUNDLE_VERIFICATION_20261025.md。

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
| GitHub | https://github.com/17-chen/LeaseRadar，公开；2026-10-30已核验匿名读取 |
| 分支 | main；新建开发分支默认codex/前缀 |
| 本轮开始源码提交 | eca595e；前端业务逻辑仍为234918c，PDF在10月29日提交前更新，10月28日长版视频/10月29日字幕已具备，API/数据库业务代码基线仍为92ba1a3；最新提交以git log为准 |
| API标识版本 | backend/app/main.py：0.1.16；后续材料/会话修复未升版本 |
| 数据库迁移头 | 0011_document_downloads |
| 依赖 | backend/requirements.lock；本机Python3.13，GitHub CI Python3.12 |
| 本轮开始已核实CI | https://github.com/17-chen/LeaseRadar/actions/runs/40834936441，head=eca595e，completed/success；含Linux Python3.12应用测试、迁移、JS及Poppler集成。后续提交仍须另核 |

10月29日开工已有output/video/index.html修改、未跟踪review.js及build_browser_captions.py，本轮接续并验证；另有长期用户未跟踪Un8(1)/、output/ui-refresh.jpg、output/ui-workbench.jpg，继续保留且不纳入提交。本文提交本身会产生后续文档提交，以git log为准，不让交接基线自指。

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

2026-10-23初次交接只核查Git、CI、文件和资料，没有重跑全部应用测试；后续检查已按日期另记。不要将旧测试时长/数量当成新改动已跑过的结果。

进程仅有历史线索，非当前保证：真实API曾在8000（旧版本），多个DEMO曾占8001–8006；最新截图DEMO目录private/demo-runs/366c911e47bd曾在8006，8010曾仅提供output/video预览。接手先检查占用，别把端口猜成最新进程或批量kill。上一轮修复未重启真实/既有演示进程；新聊天宜选择空闲端口新建DEMO。

2026-10-24本轮`lsof`复核8000–8019监听：仅SSH进程75651监听8001，没有识别到LeaseRadar API/DEMO进程；未触碰该SSH进程。`docker info`仍因daemon socket不可用失败，未做容器验收。之后的运行状态需重新核查。

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
| 介绍PDF | output/pdf/LeaseRadar_Competition_Intro_Draft.pdf；6页，0.1.16，10月29日审阅版；326项/ccb0fb0与262项/ccd5a1c分开，长版/字幕/正式缺口已更新；见PDF_REVIEW_20261029.md |
| PDF构建 | scripts/build_competition_intro.py；独立可选文档依赖，修改须按PDF技能渲染全部页面审阅 |
| 集中材料证据 | docs/submission/RELEASE_EVIDENCE.json；保留旧实现证据，不机械改测试数字 |
| 分镜视频 | output/video/LeaseRadar_Storyboard_Review_20261024.mp4；207.5秒，1920×1080，10fps，H.264/AAC |
| 浏览器操作补充片段 | output/video/LeaseRadar_Browser_Walkthrough_20261026.webm；55.68秒，1280×800，25fps，VP8无音轨；合成DEMO自动七步连续录制，非正式投稿视频 |
| 视频性质 | 实际合成UI截图＋本机Tingting合成旁白；持续标识静态分镜/非连续录屏；不是用户声音或真实试用 |
| 视频证据 | 截图依据f50223e；修订口播不再称263项为当前，分镜哈希绑定；全片2075帧/574音频缓冲解码、10场景预览（与旧版相同）；十段自动核对及听审清单已备，未逐字人工听审 |
| 视频重建 | scripts/build_storyboard_video.py、render_storyboard_video.swift、verify_storyboard_video.swift；macOS原生工具已验证，Linux CI仅验证输入规则 |
| 视频源素材 | docs/submission/VIDEO_STORYBOARD.json、video-assets；边界与失败路径见VIDEO_DRAFT.md |
| 逐镜头稿 | docs/submission/RECORDING_SCRIPT.md；五分钟建议稿与现有约3分28秒分镜不是完全同一时间线 |
| 最新本地小运行包 | private/LeaseRadar_Recording_92ba1a3.zip；58个payload文件，57个仓库文件逐字节匹配92ba1a3；另有MANIFEST，未含视频 |
| 10月28日本地完整审阅包 | private/LeaseRadar_Review_20261028_FullBrowser.zip；105个payload文件，五类媒体与PDF，独立恢复通过；不含10月29日字幕，详见FULL_BROWSER_BUNDLE_VERIFICATION_20261028.md；后续新包另记 |
| 最新本地完整审阅包 | private/LeaseRadar_Review_20261029_Individual.zip；114个payload文件，基于5154540，PDF/对照/邮件稿含用户确认报名及个人参赛状态，独立恢复通过；见SUBMISSION_PACKETS_VERIFICATION_20261029.md |
| 提交核对小包 | private/LeaseRadar_Submission_Individual_20261029.zip；258,842字节，含PDF/对照/邮件稿；报名已由用户确认，待补实际署名/访问链接和听审，未正式发送 |
| 长版字幕审阅 | output/video中的VTT、captions.json和review.js；运行python3 scripts/serve_video_review.py，只监听回环且支持分段跳转；句内时码为估算，未真人听审 |

当前视频SHA256：01f296ea063f1178614fc712b03a62a3375b89237e6924979e426754c516ff54；旧版SHA256见VIDEO_DRAFT.md。
当前完整审阅包SHA256：5653880185dd98b6be1f9107f8f46c36b57bdc069f8bf79006c3f69bd2a7f30f；只在private，未公开发布。
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

下一轮优先顺序：视频逐字听审/最终形式→PDF与包终审→访问方式及正式提交。10月29日111文件字幕包已独立恢复合成应用与分段审阅服务；七步和390px已在10月25日新建DEMO复核，10月26日又连续录下桌面七步；多端口隔离、模拟会话到期分别有10月23/24日记录，未等待12小时自然过期。具体验收门槛、用户事项及生产后续在docs/REMAINING_WORK.md。
