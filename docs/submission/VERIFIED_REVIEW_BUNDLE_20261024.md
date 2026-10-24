# 本地审阅包预解压校验与独立恢复 · 2026-10-24

## 交付物与范围

当前本机审阅包为`private/LeaseRadar_Review_20261024_Verified.zip`，16,899,655字节，SHA256 `04f113b37172c0de442089644597897a20b2bf9aaa550dfe13ad286c3d943285`。留在private，不推送GitHub。81个payload文件中，80个仓库文件与`b5132b9c9391f40701bb4f031f79fae4dcfe5f8e`逐字节一致，另一个`START_HERE.md`由打包器生成；此外有`MANIFEST.json`。该包取代10月24日Mobile包作为当前本地审阅包，旧包与失败记录保留。

新增标准库`scripts/verify_recording_bundle.py`，随小包及完整包一起提供。解压前从已取得的仓库运行：

```sh
.venv/bin/python scripts/verify_recording_bundle.py private/LeaseRadar_Review_20261024_Verified.zip
```

校验器拒绝重复/越界路径、符号链接或特殊文件、加密项、超限体积、清单缺失/多余项、错误字节数与SHA256，并在逐文件读取时验证ZIP CRC。它检查包内部一致性，不验证发布者身份；不能把包内清单当数字签名。不要从不可信ZIP直接执行其中的脚本。

## 本轮验证

从新包独立解压到`private/review-restore-verified-e2n3qtke`，用解压源码和本机既有锁依赖运行。禁用`socket.connect`，合成DEMO初始化得到6候选/7版本/5站内提醒；未登录场景接口返回401，登录后场景/首页/JS/CSS可读，面积≥30平方米、首年月基准≤12000元且可报名的筛选得4条，三候选比较与同条件CSV均返回200。无真实来源请求、SMTP投递或现有业务数据库修改。包内视频仍是原静态分镜草稿；10场景标题、图片哈希、时间线连续性与解码证明一致，**没有人工逐字听审**。

```sh
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests
PATH='/Users/chenxin/.cache/codex-runtimes/codex-primary-runtime/dependencies/native/poppler/poppler/bin:/usr/bin:/bin' PYTHONPATH=backend .venv/bin/python -m pytest -q backend/integration/test_document_tools.py
node --check frontend/app.js
.venv/bin/pip check
git diff --check
```

完整回归首轮受沙箱禁止本地SMTP测试绑定端口影响，280通过/1失败；获准仅本机监听后重跑为281通过，1条既有Starlette/AnyIO弃用警告。Poppler集成1通过，JS语法、锁依赖一致性及差异检查通过。专项测试包含修改字节、越界路径、重复条目和符号链接拒绝。未新增应用依赖、迁移或API版本。

## 尚未签收

`ready_to_submit=false`。PDF仍为审阅稿；视频尚未逐字听审，也未确定正式所需最终形式；官网实时表单/资格、评审源码与视频访问、正式提交尚待核准或授权。包不含离线依赖，未验证Windows、生产容器或真实SMTP。真实来源仍为历史有限存量：农交云24条、高校链接型1条；没有新接通完整第二来源，也没有真实OCR准确率/生产部署/试用业绩。
