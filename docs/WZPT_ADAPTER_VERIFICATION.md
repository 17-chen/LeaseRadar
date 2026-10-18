# 0.1.11 高校公告适配器可靠性

日期：2026-10-18（Asia/Shanghai）。Python3.13本机/Python3.12 CI，无新依赖、无数据库迁移，继续0011。

## 本次完成

独立backend/app/adapters/wzpt.py及fixtures/wzpt/labeled_notice.html（合成样例）。按明确标签解析金额/周期、面积/地址/地区及日期；同值单位归一化，多行冲突或格式不明保留unknown和全部依据。金额Decimal，区间/多面积不取首个数字，金额与周期共同核验；未知不换算月租。

披露日期只保留日期，不赋予报名时刻；仅明确“报名截止时间/竞价截止时间”且包含有效时间的标签生成带Asia/Shanghai时区日期。日期缺时间/冲突/无效保持未知。用途、租期、免租及租金备注原文进证据，不将商业/餐饮原文推断为咖啡经营许可。附件仅正文区域已核准HTTPS PDF/DOCX元数据，不扩大网络白名单。解析版本升级为reprocessing，不制造市场变更。

前端补原文条款的中文依据标签，沿用已有详情证据组件。未增加字段自动纠正或合同总成本推断。

## 真实观察

2026-10-18通过既有固定DNS连接、TLS校验、禁止跳转的fetch，对产权平台首页和高校2025历史全文各做一次只读GET，均成功。原HTML与proof仅在private/source-check-20261018。

- 高校历史样本https://www.wzpt.edu.cn/2025/0710/c739771a2844693/page.htm：年租234000元、面积约1500㎡、披露截止2025-07-23，均与原文核对；月租基准19500元，成本仍不完整。用途条款有审批限制，许可/报名截止仍unknown；不得推荐为当前可报名机会。
- 产权首页租赁栏目指向https://www.zjpse.com/page/s/zcdt/zccz_index?ssjg=38。该域名不在现有网络白名单，本次未自动跳转或声称接通。

只核对1条历史结构化公告，不计算准确率、不宣称第二来源现时全覆盖或多样样本验收。未将历史样本插入真实库，原25挂牌/41版本保持。没有真实邮件或自动采集启用。

## 检查与运行

18项新适配器测试通过，含完整ingest/字段依据/原观测时间/幂等及解析升级语义；此前229项完整回归和72项相关回归通过。最终新增两项用例与整个代码交由本次CI再次全量验证（总231项）。node语法、pip兼容、git diff检查通过。

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
node --check frontend/app.js
# 没有数据库升级；正常停止已有API/worker后按README重启加载0.1.11
PYTHONPATH=backend .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
PYTHONPATH=backend .venv/bin/python -m app.local_worker
```

未验证：当前第二来源多格式覆盖、异域交易平台适配、真实PDF/OCR、生产Docker/多worker压力与真实试用。剩余时间和用户事项分别见docs/DELIVERY_PLAN.md。
