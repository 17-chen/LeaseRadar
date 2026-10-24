# 本地完整审阅包复核 · 2026-10-24

> 此为`e369687`的历史包记录。当天后续前端会话提示和PDF第5页更新后，当前包另见[FULL_REVIEW_BUNDLE_VERIFICATION_20261024_MOBILE.md](FULL_REVIEW_BUNDLE_VERIFICATION_20261024_MOBILE.md)。保留原哈希与失败记录，不将两个包混为同一版本。

## 本轮交付物

- 本机文件：`private/LeaseRadar_Review_20261024.zip`，16,897,396字节；SHA256 `ec71c3290ebbe5f29541c101fd5cc1ceac041336052dc896b4ba70ff5f52be39`。仅留在private，不推送GitHub。
- 包的`source_commit`为`e369687d96f78ace8d648935568661a7b097c858`，应用标识0.1.16；80个payload文件，79个仓库文件与该提交Git对象逐字节一致，`START_HERE.md`由构建器生成。`working_tree_dirty=true`反映既有未跟踪文件，包内已提交文件逐字节核对通过。
- PDF材料日期2026-10-24，包内PDF SHA256 `79fd66cd07d5ef14f42d9a043c49ad274345aabfd4f0db7649ac6126fe637524`；历史工程依据仍为2026-10-21/`ccd5a1c`/262项，不把本轮280项回归改写为当时证据。
- 包内静态分镜MP4 SHA256 `833ffa946aaa5c7b75fffbcfbf62dce25bb0f54fc7de6148ab8c15d36b9c5806`，与既有解码证明及时间线核对。视频未逐字人工听审，不是连续录屏。`mode=synthetic_demo_review_bundle`且`ready_to_submit=false`。

## 构建与验证

```sh
.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261024.zip
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

首次在受限沙箱运行完整测试时，本机SMTP用例因`127.0.0.1`绑定被系统拒绝：279通过、1失败。仅获得本机监听权限后重跑完整测试，280通过、1条Starlette/AnyIO上游弃用警告。Poppler集成1通过，JS语法、依赖一致性和Git空白检查通过。没有外部邮件发送。

PDF以110 DPI渲染全部6页并逐页目视检查，无裁切/重叠；`pdfinfo`确认6页A4、无表单/JavaScript/加密；`pypdf`文字层检查创新点、开源依赖、版本/证据边界，无本机绝对路径或SMTP密码字段。QA图保存在`private/pdf-qa-20261024`。

ZIP CRC、MANIFEST每项大小/SHA256、路径无`private/`或`.env`、79项Git对象逐字节一致均通过。独立解压到新目录`private/review-restore-20261024`，只用解压目录源码运行`--prepare-only`，得到6条合成候选、7个版本、5条站内提醒，报告网络请求0。此次只重做数据初始化恢复；登录、静态资源和筛选HTTP链路在10月23日旧包独立恢复中通过，应用代码未变。锁依赖从全新环境安装仍需软件源，未验收Windows或生产容器。

## 仍未签收

PDF是审阅稿，官方实时表单/主体资格和最终措辞待核对；视频需逐字听审并确定最终形式；390px最新界面及自然过期浏览器提示未补；评审访问/视频托管和正式提交需要用户授权或操作。没有真实来源新采集、真实数据修改、真实收件人投递、生产部署或用户试用。本包不代表比赛提交完成。
