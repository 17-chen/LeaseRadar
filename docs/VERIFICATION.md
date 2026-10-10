# 首轮验证报告

日期：2026-10-10（Asia/Shanghai），版本0.1.0-dev。

## 已通过

- PYTHONPATH=backend .venv/bin/pytest -q backend/tests：24 passed，1个Starlette/AnyIO弃用提示；隔离demo测试库，无真实消息。
- node --check frontend/app.js；pip check：依赖兼容检查通过。
- Alembic新库升级0002且3个来源种子存在；既有开发库迁移未清空数据。
- Compose以占位密码校验配置通过；没有Docker服务，因此没有容器实际运行结果。
- 农交云适配器source-check实际返回12详情/142页；crawl-once两页24条，第一页DOCX增强复查12条；6条首年租金口径核实。
- 高校实际5/470页发现1条链接型公告；正文只提供交易平台链接，关键字段unknown，不计作完整独立第二源。
- 浏览器登录、面积上限100㎡、包含/排除未知切换、详情证据和2条比较通过。
- 390px手机截图与DOM宽度检查未见横向溢出。
- SQLite备份恢复到独立文件，PRAGMA integrity_check=ok；25挂牌、37版本、37原文记录。没有覆盖原数据库。
- 持久任务回收过期租约、排队幂等、失败记录及站内通知状态有测试。

## 未验证与缺口

Docker/PostgreSQL/Celery实际运行、生产HTTPS、外部通知、自动分页补扫、严格DNS重绑定防御、关键PDF/OCR与完整第二来源。没有匹配召回/准确率、延迟P95、真实用户耗时或试用业绩。

来源扫描一次/有限分页不等于长期覆盖；6条价据成功不是关键字段正确率指标。代码测试数量不代表生产就绪。

GitHub首次CI在Python3.12上通过23项测试与新库迁移；随后补充未知价格性质排序的回归测试，最新提交CI另行核查。
