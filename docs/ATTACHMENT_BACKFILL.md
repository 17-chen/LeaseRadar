# 历史当前版本附件补扫

2026-11-03新增CLI入口。沿用现有数据库下载队列与私有审核流程，无新增依赖或迁移；API版本仍0.1.16。它补齐历史记录的**有界下载入队**，不是全网附件发现、历史所有版本扫描或自动字段纠正。

## 前提

按[部署说明](DEPLOYMENT.md)在私有runtime配置中启用`SOURCE_DOCUMENTS_ENABLED`、`SOURCE_DOCUMENT_DOWNLOADS_ENABLED`，并将`SOURCE_DOCUMENTS_USER_ID`设为有效管理员ID。缺配置或成员账号会拒绝执行；默认开关未改。不需要配置SMTP。

以下命令须在安装了锁定依赖、完成迁移的项目根目录运行。使用目标数据库对应的DATA_DIR/DATABASE_URL；不要把合成测试误指向真实库。命令不联网，但`--apply`写入的任务可能立即被已运行的local_worker领取并联网，因此应先预览，再按来源授权与运行配置决定入队。

## 预览、入队、续扫

```bash
# 默认只读预览，最多检查25个挂牌的当前版本
PYTHONPATH=backend .venv/bin/python -m app.cli backfill-attachments nongjy --limit 25

# 明确入队；成功提交数据库事务后才输出游标
PYTHONPATH=backend .venv/bin/python -m app.cli backfill-attachments nongjy --limit 25 --apply

# 将上一轮apply输出的next_after_listing值填入；这里的123仅为示例
PYTHONPATH=backend .venv/bin/python -m app.cli backfill-attachments nongjy --after-listing 123 --limit 25 --apply
```

另一个可选来源是`wzpt`。来源之间分别保存游标，不要共用。`--limit`范围1–100，`--after-listing`为非负挂牌ID。命令每次处理一批，不会自动循环或自动启用来源。

输出字段：

| 字段 | 含义 |
| --- | --- |
| mode / source | preview或apply，以及来源 |
| scanned | 本批已检查的挂牌数，包含暂时未能全部入队的末条 |
| planned | 本次容量允许计划新增的任务数；预览不创建任务 |
| queued | 实际新增任务数，preview恒为0 |
| after_listing / next_after_listing | 输入游标及可续扫游标；**只用成功apply的输出推进实际入队游标** |
| has_more / stop | 是否需要续扫；complete、batch_limit、listing_limit或queue_capacity |

`listing_limit`表示本挂牌尚有符合条件的附件未入队；`queue_capacity`表示待处理下载已到限额。二者均不会把游标推进到尚未完整处理的挂牌。待worker消化队列后，使用相同返回游标再执行。游标由操作者或调用脚本保存，不是数据库后台定时任务；丢失游标时从0重新扫描，唯一键会跳过已有任务。

`complete`只表示本轮当前数据库视图中、受检查预算约束的入队遍历结束，不代表附件已下载、审核通过或覆盖完整。扫描期间新增/更新的较早挂牌可能需要从0再做一轮。

## 边界与恢复

- 只检查指定来源挂牌的当前展示版本，避免重新下载已过时版本。每挂牌最多查看前20项附件元数据，每次最多新增5个下载任务；超出前20项不在此补扫覆盖范围。
- 仅处理缺少sha256的PDF/DOCX链接；已有哈希的本地快照仍走原有采集/复查审核入口，不在此历史补扫内。
- URL仍按HTTPS、核准域名、443端口、无用户信息/fragment及后缀过滤；实际下载沿用DNS公网校验、连接固定、5MB、60秒和来源租约限制。
- 下载执行前再次核对任务来源与原始公告来源；此前已入队但归属错误的任务会取消，且不会发起网络请求。
- 同管理员最多20个queued/retry_wait/downloading下载任务。保持现有本地容量预算，不宣称已经完成生产多worker容量/并发验收。
- 同源同URL的blocked状态阻止重新入队；同版本同URL已有任意状态的任务均跳过，failed/cancelled也不自动重试或清除。错误历史保留。
- 每批写入与游标结果以同一次调用事务为边界，SQLite显式开启外层事务，防止嵌套保存点提前提交；异常由调用侧回滚。跨会话重跑依赖数据库唯一键保持幂等。
- 下载后创建私有DocumentReview，提取/人工审核流程保持原样；不发布新商业版本、不修改挂牌字段、不生成市场变更或向外发消息。

## 本轮证据与剩余工作

新增合成测试覆盖预览、显式提交、跨会话重复运行、部分挂牌/满队列续扫、批次/来源筛选、当前版本、blocked/failed保留、非法元数据、禁用/管理员校验、回滚及CLI入口；另用合成DOCX与本地传输替身走完“历史入队→下载→私有提取→待审核”。首次测试暴露SQLite保存点提前提交问题，已修复并保留回滚断言；没有删除失败样本或降低限制。

运行命令：

```bash
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_attachment_backfill.py backend/tests/test_document_downloads.py backend/tests/test_source_documents.py
```

本轮最终核验：Python3.13本机完整应用回归345项通过（56.76秒），真实Poppler工具/合成PDF集成1项通过（0.47秒），前端与审阅页JS语法、pip依赖一致性、89处文档相对链接/围栏及git diff --check通过。首次受限沙箱完整回归343过/2失败，均为本机SMTP/HTTP监听被拒；允许回环监听后完整重跑通过，原失败日志保留。存在原有Starlette/AnyIO弃用警告，未改锁依赖。GitHub同步与CI以本轮实际提交为准。

本轮未扫描真实库、未启用真实下载、未配置真实消息目标。真实附件覆盖、复杂格式/PDF准确率、生产PostgreSQL与多worker恢复仍需独立验收。
