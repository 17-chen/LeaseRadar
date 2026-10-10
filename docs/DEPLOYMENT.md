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
