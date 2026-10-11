# 0.1.5 工作流阶段验收

日期：2026-10-11。不是完整规格或生产上线验收。

## 本阶段完成

- 用户级明确匹配即时/每日、待确认每日汇总、IANA时区、摘要时间、跨午夜静默和可选报名催办例外。旧用户保存设置前保留原行为。worker恢复后汇总已到时间的事件，不伪造原发现时间。
- 摘要按用户及待接受事件组批，每批最多100条；独立成员唯一键和事务状态领取防重复组批。SMTP只发送代表记录，保留各事件和站内历史；作废/暂停成员不进入发送正文。摘要带观测窗口及来源覆盖/暂停快照。
- 提醒、邮件、摘要、人工纠正和告警历史分页；未读统计覆盖全部提醒，不再限定最近100条。
- 管理员字段纠正需要依据和原因；版本比较冲突409，写入不可变版本与审计，不制造市场变化。源再次更新保留人工值，差异进入conflict，整体匹配unknown；可以核验继续保留或撤销到最新源值。
- 同一挂牌、同一资产、重挂与整体/成员的明确人工关联和撤销。同一挂牌在搜索/CSV聚合出处；已知冲突不采最后写入值，保留原始记录与私人笔记。比较不能重复选择同一已关联挂牌。重挂仍是独立机会，不拆整体价格。
- 默认48页/日、3页/批回扫预算可由管理员设置（最大240页/日、10页/批）；首页与详情优先，按实际完成页数记录今日覆盖，不宣称全量一致快照。来源异常/陈旧告警保存恢复历史；暂停来源不制造“持续成功”。
- 来源和任务随机租约token，续租/入库/完成均检查当前归属；合成测试验证旧任务在网络请求返回后不能写入新owner数据。这不是多worker生产压力验收。
- 公网DNS全地址检查后连接核准IP，保留原Host/TLS SNI，不禁证书、不跟重定向。真实只读访问：农交云首页12个详情链接/143页，高校首页0条招租匹配/470页；不是新全量采集或第二来源字段接通。
- /imports只接受两个已适配来源的公开详情，持久任务由worker处理；DEMO replay拒绝live与已有挂牌库；评测JSONL计算已标注字段precision/coverage/known-truth recall，拒绝重复记录和项目组跨拆分泄漏。
- private/runtime.json集中外部配置，环境变量优先；readiness-check不发送、不启用、不输出凭据。

## 检查证据

本机128项pytest通过；包含本地合成SMTP，初次沙箱禁止端口监听的失败保留并以权限允许的完整执行复核，没有skip。node语法、pip check、Compose配置、git diff检查通过。Python3.13本机；CI Python3.12在GitHub核对，不把本机结果当远端结果。

0003有数据迁移到head的回归继续通过。真实库先备份到private/backups/20261011T124446Z，再升级0007；独立目录复制该0006备份并升级0007，integrity=ok、foreign_key_errors=0、25挂牌/41版本/0通知/0邮件/0人工纠正/0摘要保持，41份原文hash一致。证明文件private/workflows-restore-proof.json不公开。

浏览器隔离DEMO（private/workflows-demo-20261011，真实库未加入合成纠正/关联）：通知偏好保存每日、22:00–07:00；面积60→65保存且核验时间仍2026-10-10；两条关联搜索变一条并保留unknown冲突；纠正撤销历史保留；390px手机body宽375，无页面横向溢出。截图private/screenshots/workflow-notification-preferences.png、workflow-associated-candidate.png、workflow-review-desktop.png、workflow-preferences-mobile.png。

## 实际命令

```sh
PYTHONPATH=backend .venv/bin/python -m app.cli backup
PYTHONPATH=backend .venv/bin/python -m app.cli migrate
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
PYTHONPATH=backend .venv/bin/python -m app.cli readiness-check
PYTHONPATH=backend .venv/bin/python -m app.cli digest-once
PYTHONPATH=backend .venv/bin/python -m app.cli evaluate private/labels.jsonl --output private/evaluation.json
PYTHONPATH=backend .venv/bin/pytest -q backend/tests
```

labels.jsonl是用户真实标注输入，不是仓库已提供的真实评测集。fixtures/evaluation.synthetic.jsonl仅用于命令演示，实际执行结果私有，不当成业绩。回放使用独立空DATA_DIR、DATABASE_URL并设APP_MODE=demo，先migrate后执行replay fixtures/replay/demo_manifest.json；拒绝真实库。

## 未验证与边界

真实邮件通道关闭，所有来源enabled=false；没有真实收件人投递、长期监测、Docker实际运行、PostgreSQL恢复、生产多worker、真实试用、性能P95或比赛提交。密钥和原文仍私有。人工关联是明确关系图，未自动校准地址相似去重；现存已接受的历史消息不会因关联追溯删除。来源告警站内持久可查，未外发；检索仍在内存匹配，不宣称大规模性能达标。剩余开发与最后统一配置见FINAL_SETUP_CHECKLIST.md和TODO.md。
