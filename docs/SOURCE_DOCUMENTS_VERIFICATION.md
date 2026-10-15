# 0.1.9 已缓存来源附件自动审核

2026-10-15（Asia/Shanghai）。Python3.13本机，Python3.12 CI；Python锁依赖不变。

## 完成范围

采集/详情复查可自动将已保存且带SHA256的来源附件放入指定管理员私有审核队列；不重复下载、没有任意URL访问能力。默认关闭，只有SOURCE_DOCUMENTS_ENABLED=true及SOURCE_DOCUMENTS_USER_ID对应有效admin才工作，未配置/无效配置在setup-readiness明确展示；配置无效不阻塞挂牌入库。

0010增加来源版本、原地址与挂牌+URL+SHA256唯一键。人工上传历史来源信息留NULL；同附件跨挂牌版本不重复，同址新内容生成新审核，旧失败不删。不改变原版本/事件/匹配身份或虚构商业变化；审核记录与ingest同事务，提交前不发布文件worker请求。切换管理员不转移旧审核。

每次观察最多新增5份、只检查前20个附件、管理员待提取最多20份；排满后下次同公告观察可续入。缺失、哈希不符、软链接、超5MB等保留failed及来源，修复后需人工重新上传，不自动无限重试。无哈希或未下载的文件不会入队；并非全来源附件抓取完成。

页面继续用“条款与附件”的管理员私有列表，展示来源版本与原地址，文本经过HTML转义。提取仍需独立隔离worker，内容仍须人工核验，不自动改挂牌。

## 验证

- 整合远端c0b2131（DOCX价格表排除删除/移出修订）后，185项完整本机回归通过。此前183项完整回归及15项来源附件/迁移专项复核也通过；未覆盖或替换远端改动。
- 合成来源parser/快照→真实ingest→提交后请求→文件worker→数据库review→管理员API，重复观察/新版本幂等、同址新内容、rollback不发布请求、无效配置/成员拒绝、丢失/损坏/超限/软链接、20份背压恢复、唯一键拒绝重复均通过。没有真实网络或邮件。
- 已有0003有数据升级测试新增0009手工附件记录，再升级0010，来源字段为NULL、review保留、外键/完整性通过。
- 真实SQLite通过backup API复制到临时异目录，0009→0010：25挂牌/41版本/0附件记录不变，integrity ok，外键错误0。原库未改，proof见private/source-documents-restore-proof.json；原库仍0009，本阶段常驻进程未重启。
- node语法、pip check、Compose配置和git diff检查通过；没有Docker实际运行或生产压力验收。

## 命令

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
# 部署前先停止API/worker并备份，再升级；重启命令同README
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

可选配置示例：SOURCE_DOCUMENTS_ENABLED=true、SOURCE_DOCUMENTS_USER_ID=管理员ID；不是实际用户ID。保持现有private/runtime.json不变，外部配置最后统一补齐。

## 真实接入与下一步

无新源网络采集、原库无写入、真实邮件与自动入队均保持关闭。本阶段只有合成闭环与真实库副本升级。下一步仍为未缓存PDF等来源附件获取、独立第二来源关键字段、真实PDF/OCR准确率及生产容器验收；不能将这次功能视为全部来源自动附件支持。
