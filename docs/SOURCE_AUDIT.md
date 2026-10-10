# 阶段0来源审计（初步）

检查时间：2026-10-10 13:33（Asia/Shanghai）。证据：source_curl_checks.json、source_http_checks.json；原文快照仅临时存于/tmp，未纳入公开仓库。

| 来源 | 直接网络观察 | 判断与未验证项 |
|---|---|---|
| 农交云 | 列表GET 200，61695字节，HTML标题正确；发现5条详情链接，5次获取有面积/报名文本 | candidate；尚未实现结构化解析、分页、状态复查和附件 |
| 温州产权平台 | 首页GET 200，66777字节，标题为温州联合产权交易中心-首页 | candidate；检索工具403与直接获取不同，不按全站blocked处理；列表与详情待核验 |
| 浙交汇历史详情 | GET 302，未跟随跳转 | pending；最终域名/重定向待检查，与产权平台可能重复，不计为独立来源 |
| 温州职业技术学院 | 历史公告GET 200，82433字节，标题正确 | candidate；是历史解析样本，不是当前机会；栏目覆盖与独立发布范围待核验 |

## 样本链接

- https://www.nongjy.cn/web/propertyBid/detail/2019
- https://www.nongjy.cn/web/propertyBid/detail/2020
- https://www.nongjy.cn/web/propertyBid/detail/2021
- https://www.nongjy.cn/web/propertyBid/detail/2022
- https://www.nongjy.cn/web/propertyBid/detail/2023
- https://www.wzpt.edu.cn/2025/0710/c739771a2844693/page.htm

当前5条农交云详情检查只确认正文存在相关词，不构成字段正确性验收；详情状态码未单独记录，需后续补充。

## 环境与访问规则

沙箱内DNS访问失败；授权网络后Python HTTPS仍因本地证书链失败。系统curl在保留TLS校验下可获取页面，因此不能归因为所有网站不可用。正式开发前修复Python可信证书配置，不关闭验证。
农交云、高校robots.txt返回404，不等于允许持续抓取。来源条款、分页与附件需继续核查后确定频率。

## 阶段0验收缺口

尚未达到完整阶段0验收：没有适配器解析验证；第二来源只有可访问首页/公告；每来源5–10条不同格式样本、价格周期/期限/状态标注、完整分页和访问规则未完成。
比赛信息待用户提供；依赖锁定、GitHub仓库因阶段/登录状态尚未完成。禁止将本次HTTP获取称为生产接入成功。

## 正式开发后复核（2026-10-10）

httpx可信证书链下实际适配器获取成功，未禁用TLS校验。农交云列表12条、总142页；两页24条入库；12条第一页复查中6条DOCX精确标的首年租金核对成功。分页参数pageNum/pageSize从网页公开脚本读取，并实际验证不同页不是重复。

高校栏目https://www.wzpt.edu.cn/tzgg/list.htm的下一页链接/tzgg/list2.htm已观察；5页/470页扫描发现https://www.wzpt.edu.cn/2026/0107/c739771a3318095/page.htm，其正文只有浙交汇链接，关键字段未覆盖。历史2025公告可解析表格，但不是当前在租机会。第二来源仍未达到完整正文与关键附件验收。

DOCX附件保存在private/snapshots，仅本地使用；没有授权转发真实快照。站点规则完整核查尚缺，持续采集默认关闭；当前只低频有限验证。
