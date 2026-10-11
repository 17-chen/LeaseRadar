# 首轮验证报告

日期：2026-10-10（Asia/Shanghai），版本0.1.0-dev。

## 已通过

- PYTHONPATH=backend .venv/bin/pytest -q backend/tests：25 passed，1个Starlette/AnyIO弃用提示；隔离demo测试库，无真实消息。
- node --check frontend/app.js；pip check：依赖兼容检查通过。
- Alembic新库升级0002且3个来源种子存在；既有开发库迁移未清空数据。
- Compose以占位密码校验配置通过；没有Docker服务，因此没有容器实际运行结果。
- 农交云适配器source-check实际返回12详情/142页；crawl-once两页24条，第一页DOCX增强复查12条；6条首年租金口径核实。
- 高校实际5/470页发现1条链接型公告；正文只提供交易平台链接，关键字段unknown，不计作完整独立第二源。
- 浏览器登录、面积上限100㎡、包含/排除未知切换、详情证据和2条比较通过。
- 390px手机截图与DOM宽度检查未见横向溢出。
- SQLite备份恢复到独立文件，PRAGMA integrity_check=ok；25挂牌、37版本、37原文记录。没有覆盖原数据库。
- 持久任务回收过期租约、排队幂等、失败记录及站内通知状态有测试。

## 首轮未验证与缺口（后续变化见迭代记录）

Docker/PostgreSQL/Celery实际运行、生产HTTPS、外部通知、自动分页补扫、严格DNS重绑定防御、关键PDF/OCR与完整第二来源。没有匹配召回/准确率、延迟P95、真实用户耗时或试用业绩。

来源扫描一次/有限分页不等于长期覆盖；6条价据成功不是关键字段正确率指标。代码测试数量不代表生产就绪。

GitHub首次CI在Python3.12上通过23项测试与新库迁移；随后补充未知价格性质排序的回归测试，最新提交CI另行核查。

## 2026-10-10 分页恢复迭代

- `PYTHONPATH=backend .venv/bin/pytest -q`：30 passed；一个上游Starlette/AnyIO弃用提示。新增页中失败后恢复、429等待与3次失败停止、HTTP日期Retry-After、API任务类型、首页/回扫调度测试。
- `node --check frontend/app.js`及`git diff --check`通过。
- 本地旧库备份后升级0003成功；独立SQLite空库从0001迁移至0003成功。
- 高校公开栏目真实CLI回扫第1页成功，游标2；持久job 2由实际worker续扫第2页成功，游标3，两页租赁详情均为0。保留25条原有挂牌记录，未声称扩大第二来源关键字段覆盖。
- 本轮未运行Docker/PostgreSQL、长时间多worker或真实外部通知；前端新按钮通过语法和接口测试，本轮未重做浏览器视觉审查。

## 2026-10-10 详情与报名提醒迭代

- 58项测试通过；覆盖部分详情失败恢复、同源锁、无目标不伪报源站新鲜数据、关闭/失配信息通知、72/24窗口、恢复后的最近窗口、延期作废、暂停/放弃/过期/配置取消、旧核验不催办、版本无关去重、两并发周期唯一outbox、订阅与收件箱权限、恢复未接受提醒且不重发已接受提醒、不同任务409、未知周期不伪报明确降价。
- 迁移测试从有用户/版本/已接受outbox的0003合成库升级到0004，原记录与72/24默认设置保留，完整性和foreign_key_check通过；本机真实库备份后升级成功，新空库升级成功。
- 农交云CLI真实详情复查2条（crawl_run 7）成功；高校持久job 3经本地worker真实复查已入库详情1条（crawl_run 8）成功。新增3个版本均为reprocessing；现有25挂牌、40版本、6条价格周期核实。高校仍是链接型公告，未算完整独立第二来源接通。
- 独立DEMO库验证订阅48/12小时设置保存、自定义12小时窗口入箱、关闭信息与延期/作废显示；所有合成公告标题带“合成演示”，桌面与手机均有DEMO标识。390px页面scrollWidth=375，无横向溢出；浏览器error/warn为空。截图留在私有screenshots目录，不上传源公告或账户数据。
- node语法与git diff检查通过；未新增依赖。仍有上游Starlette/AnyIO弃用提示。
- 本轮不验证真实外部发送、Docker/PostgreSQL/Celery部署、长时间多worker/大规模记录量、每日全量覆盖、P95或用户业绩；本地SQL查询与单worker长任务对提醒延迟的影响仍需后续专项检查。

## 2026-10-11：SMTP发送记录与当前来源告警

- 76项pytest通过（Python3.13），含本地127.0.0.1真实SMTP协议接收、发送去重、用户隔离、三次退避后dead_letter、MAIL/RCPT/DATA返回码、DATA断连ambiguous、过期发送租约不重发、旧消息启用时间排除、关闭公告与暂停订阅不发送；node语法与diff检查通过。
- 新迁移0005及已有0003至head升级回归通过。真实库先备份到private/backups/20261011T050513Z，升级后25挂牌、40版本、0邮件回执、0开启来源；PRAGMA integrity_check=ok。
- 浏览器真实工作空间确认邮件未配置、收件箱发送记录空态、来源健康页面可用；截图private/screenshots/email-desktop.png。不以空态截图证明外部发送成功；协议发送证据来自隔离合成测试。
- 公开高校外链 https://www.zjpse.com/prjs/lease/detail/235950.html 返回302到同站/history/prjs/lease/detail/235950.html；该明确目标200（78114字节），只读保存private/zjpse-history-235950.html，HTML文本为导航/框架，无公告正文可验证。未扩大白名单、未绕过访问控制，不计完整第二来源。
- 无真实SMTP服务商验证、最终邮箱回执、生产容器/多worker验证；静默与每日摘要、持久告警历史未实现。
