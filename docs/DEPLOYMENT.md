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

数据库与快照进入private/backups，均包含私有数据。备份期间暂停worker以确保数据库与文件一致。恢复时复制database.db与snapshots到新的DATA_DIR，设置DATABASE_URL=sqlite:///新目录/database.db，先运行完整性检查与记录计数再切换服务，禁止直接覆盖运行库。

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

延期、关闭、暂停订阅、取消提醒配置、放弃/已成交、过期后，旧提醒在收件箱标为作废并保留历史，作废项不计入未读数。尚未被站内接受的提醒恢复条件后复用原outbox；已接受过或回执未知的旧提醒不自动重发。同一期限回退到已有身份也遵循此规则。无静默/每日摘要及外部SMTP/Webhook实现。生成依赖本地worker轮询；长采集任务、电脑休眠和暂停监测可能造成延迟。

升级前停止旧API和worker，备份后执行migrate。0004增加提醒表及outbox二选一来源约束，旧crawl_runs类型无法可靠恢复，标为legacy。只验证SQLite旧库和新库迁移，PostgreSQL仍需部署演练。
