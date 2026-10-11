# 运行与部署

## 本地运行

在项目根目录执行（Python3.12/3.13）：

```sh
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/python -m app.cli create-admin
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另一个终端启动后台：

```sh
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

访问 http://127.0.0.1:8000 。后台每15秒处理数据库任务；启用来源后每30分钟扫描第一页。仅本地绑定，浏览器关闭仍运行；终端退出、电脑休眠或关机会影响运行。当前不自动安装开机服务。

可手动核查与采集：

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli source-check nongjy
PYTHONPATH=backend .venv/bin/python -m app.cli crawl-once nongjy --pages 2
PYTHONPATH=backend .venv/bin/python -m app.cli crawl-once wzpt --pages 5
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

## Docker部署包

需常驻Linux服务器或已启动的Docker服务，复制.env.example为.env并填入唯一的URL安全数据库密码，不要把.env入Git。

```sh
docker compose up --build -d
docker compose exec api python -m app.cli create-admin
docker compose logs worker beat
```

Compose启动迁移后再运行API/worker/单实例beat。数据库与Redis不暴露端口；API默认绑定127.0.0.1:8000。正式外网使用需配置HTTPS反向代理、COOKIE_SECURE=true及可信代理；目前没有生产部署或压力测试结论。

网页手动采集加入数据库任务，Celery周期任务和本地worker消费同一队列；不要同时启用多个beat。任务领取与来源锁避免重叠。队列/来源锁超时65/60分钟，崩溃任务在租约过期后可恢复；没有承诺立即恢复。

403时自动停用来源，不绕过访问控制；429当前记录失败，后续轮询间隔30分钟，尚未完整实现Retry-After策略。当前定时仅第一页，深分页补扫需手动CLI；每日游标补扫后续完善。

## 备份与恢复验证

SQLite：

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli backup
```

数据库与快照进入private/backups，均包含私有数据。备份期间暂停worker以确保数据库与文件一致。恢复时复制database.db与snapshots到新的DATA_DIR，设置DATABASE_URL=sqlite:///新目录/database.db，先运行migrate（0006将旧绝对快照路径转为相对路径），核对完整性、记录计数和原文hash再切换服务，禁止直接覆盖运行库。

PostgreSQL：暂停worker/beat；执行docker compose exec -T db pg_dump -U leaseradar -Fc leaseradar，将输出保存到私有备份文件；同时间备份snapshots卷。使用独立新库pg_restore，并核对表计数、附件hash及权限后再切换。当前机器未执行PostgreSQL恢复演练。

## 密钥与通知

管理员密码强哈希；会话Cookie HttpOnly，写操作CSRF验证；本地HTTP仅开发使用。生成的本地管理员信息仅在private/local-admin.txt，文件权限0600。

站内outbox可用，无外部SMTP/Webhook发送实现；UI显示未配置。不要以队列accepted声称邮件已送达。AI、外部通知与云部署将在后续配置完成后验证。

## 分页续扫与恢复（0.1.1）

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli crawl-once nongjy --backfill --pages 1
```

管理员可在来源页面点击“续扫一页”。游标仅在该页全部详情保存后推进；失败重跑可能重复读取已有详情，版本和事件保持幂等。回扫到最后一页后游标重置为1。动态列表会移动，游标覆盖不代表固定时点完整快照，也不能替代活跃详情独立复查。

启用来源后，每30分钟安排首页检查与一次单页回扫，worker持续运行时两者分开执行；默认来源暂停。临时网络错误、408/429和常见5xx最多尝试3次，等待60秒、120秒或更长的Retry-After。其他解析/访问错误停止任务并暂停来源；管理员核查后可重新启用。手动任务也使用同一持久队列。来源页面和`GET /api/v1/jobs/{id}`显示重试时间、次数和状态。

更新代码前停止旧API与worker，执行backup、migrate后再启动。不要将包含账户与原文的备份上传GitHub。多worker长期生产部署的租约竞争和动态分页覆盖仍需专项验证。

## 活跃详情与报名提醒（0.1.2）

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli refresh-details nongjy --limit 2
PYTHONPATH=backend .venv/bin/python -m app.cli remind-once
```

启用来源后，调度按首页检查、详情复查、分页回扫各自到期时间安排任务；同来源已有不同类型任务时手动接口返回409，不把已有首页任务伪称为详情任务。详情复查每15分钟安排一批，最多5条，从最久未核验的记录开始；活跃记录至少间隔30分钟，已关闭/长期过期但仍被收藏或跟进的记录至少间隔24小时。普通过期公告有72小时宽限以核验关闭状态；日期型披露使用3日宽限，期限未知的普通公告仅在首次入库30日内轮转。放弃/已成交跟进不作为关注依据。单批上限和积压会增加单条核验间隔，不承诺全库每30分钟完成。

用户在保存订阅或“编辑设置”中配置提前小时数，默认72/24；允许1–168小时，最多3个不重复值，留空关闭。只使用有时区的明确报名截止，不用竞价时间或日期型披露推算。最近核验超过24小时不生成/接受新的催办提醒；worker恢复后只生成当前最近的提醒窗口，例如仅剩10小时且设置72/24时生成24小时提醒，不补发72小时消息。已有一般字段更新不会重发同一截止窗口。

延期、关闭、暂停订阅、取消提醒配置、放弃/已成交、过期后，旧提醒在收件箱标为作废并保留历史，作废项不计入未读数。尚未被站内接受的提醒恢复条件后复用原outbox；已接受过或回执未知的旧提醒不自动重发。同一期限回退到已有身份也遵循此规则。静默/每日摘要及Webhook未实现；SMTP单用户通道自0.1.3提供，默认关闭，见后文。生成依赖本地worker轮询；长采集任务、电脑休眠和暂停监测可能造成延迟。

升级前停止旧API和worker，备份后执行migrate。0004增加提醒表及outbox二选一来源约束，旧crawl_runs类型无法可靠恢复，标为legacy。只验证SQLite旧库和新库迁移，PostgreSQL仍需部署演练。

## 邮件通道（0.1.3开发版）

默认 `EMAIL_ENABLED=false`。仅在已授权接收地址上启用；本阶段只有本地合成SMTP接收验证，没有真实外部邮件。管理员通过环境变量指定一个 `EMAIL_USER_ID` 与该用户的 `EMAIL_RECIPIENT`，不会发送其他用户通知。配置 `EMAIL_START_AT` 为启用时间的带时区ISO时间，之前的历史通知不补发。配置示例字段见 `.env.example`；本地启动不会自动读取该文件，需在API和worker启动环境中导出相同配置。SMTP_PASSWORD只进入私有环境，不进入Git或日志。

生产通道要求 `SMTP_SECURITY=starttls` 或 `ssl`，默认端口587需按服务商调整；`local`只允许127.0.0.1/::1的合成接收端。设置 SMTP_HOST、SMTP_PORT、SMTP_FROM；服务商要求认证时设置SMTP_USERNAME/SMTP_PASSWORD。配置错误在ready接口显示invalid_configuration，站内通知仍可用。

worker自动处理邮件；手动单轮执行 `PYTHONPATH=backend .venv/bin/python -m app.cli email-once`。每轮最多20条，网络超时15秒；暂时错误最多3次，退避60/120秒，永久错误进入dead_letter。DATA阶段断连或发送租约超时进入ambiguous，不自动重发，需先核验服务商回执。稳定Message-ID有助查找，不保证SMTP外部绝对一次；accepted仅表示SMTP服务器接受，不证明最终邮箱投递。

发送记录引用原站内outbox，按outbox唯一键去重；发送前复核订阅启用、报名提醒有效性和接收用户/地址。暂停、作废或地址改变的待发记录取消；已接受记录不会撤回。邮件不包含私人跟进笔记。当前一个配置对应一个用户地址，尚无自助邮箱验证、批量订阅摘要、静默时间或失败记录人工重发入口。未知条件提醒目前逐条发送，不是每日合并摘要。

`/api/v1/email-deliveries`只返回当前用户回执，不暴露地址；管理员 `/api/v1/source-alerts` 返回当前来源异常，页面按来源显示告警，恢复后移除。它是当前状态视图，尚无持久告警历史、过久未检查告警或外部来源告警邮件。

## 0.1.4审查修复升级

停止旧API/worker，backup后migrate到0006，再启动新进程。快照路径按DATA_DIR解析；import-html新增必填 --observed-at（原抓取带时区ISO时间）。保持单worker，过期来源/任务租约的多进程归属校验仍待补强。完整审查、独立恢复与界面证据见docs/CODE_STATE_AUDIT.md。


## 0.1.5通知、审核与集中配置

升级先停止旧API/worker，backup，migrate至0007，再启动。私有DATA_DIR/runtime.json加载集中SMTP/应用配置，环境变量优先；模板config.runtime.example.json，权限0600，勿提交Git。readiness-check仅报告状态，详见FINAL_SETUP_CHECKLIST.md。

网页“我的订阅→通知节奏”保存每日/即时、时区、摘要时间、静默和报名催办例外；旧用户未保存时沿用原即时行为。保存后待确认每日汇总，每批最多100条。静默期间延后站内接受与SMTP，恢复worker汇总已到期事件，保留发现时间。摘要来源状态是组批时快照，不是全站覆盖保证。提醒/邮件/摘要全部历史可分页查询。

管理员从详情创建有依据的纠正和挂牌关系，人工审核处理冲突或撤销；API要求当前版本，过时写入409。同挂牌聚合保留独立原始观察，冲突unknown；重挂和整体成员关系不拆价格、不合并私人笔记。来源页配置预算不会自动启用；告警有恢复历史但没有外发。

核准详情/imports进入持久队列；只允许已适配两个来源，未适配外链不跟随。DEMO回放仅允许独立空库；evaluate接受私有人工标注JSONL，模板是合成示例，不能当真实效果。WORKFLOWS_VERIFICATION.md含实际命令和范围。Docker/PostgreSQL/Celery运行和真实SMTP投递仍待统一配置与验收。
