# 演示彩排版完整审阅包 · 2026-10-25

最新本机包为`private/LeaseRadar_Review_20261025_Rehearsal.zip`，17,007,025字节，SHA256 `5366beb6b6647c043e47f1cf4cbc506a32697056ec84893fdd2e1b03c9ee0590`。仅存本机private，不上传GitHub；此前`LeaseRadar_Review_20261025_DemoFreeze.zip`是本轮较早的81文件有效包，旧包与失败现场都保留。新包源码提交为`1fbeef22548b1974367371c91d1d0af1d340b7cd`，应用0.1.16；包含本轮彩排记录与修订录制稿、六页PDF审阅稿及207.5秒静态分镜草稿。

执行：

```sh
.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261025_Rehearsal.zip
.venv/bin/python scripts/verify_recording_bundle.py private/LeaseRadar_Review_20261025_Rehearsal.zip
PYTHONPATH=backend .venv/bin/python -m pytest -q backend/tests/test_recording_bundle.py
```

预解压清单、条目路径、CRC、大小与逐项哈希验证通过。82个payload文件中，81个仓库文件与`source_commit`逐字节一致，另1个`START_HERE.md`由打包器生成；`MANIFEST.json`另列。`working_tree_dirty=true`仅反映仓库仍有用户既有未跟踪文件，包内仓库文件全部匹配固定提交。14项包专项测试通过；本轮完整应用282项测试、Poppler合成PDF集成1项、JS语法、依赖和差异检查通过。

GitHub主线`b3a715c`的[Tests运行](https://github.com/17-chen/LeaseRadar/actions/runs/40152105180)于2026-10-25完成且成功，包含Linux Python3.12应用测试、迁移、JS及Poppler集成。Actions对Node.js 20弃用与Ubuntu标签迁移有提示，不影响本次结果；后续提交应按其自身CI核对。

从这个确切ZIP独立解压至`private/review-restore-20261025-e137r8qy`，以新的隔离SQLite目录并禁止socket连接，完成6候选/7版本/5提醒初始化、合成账号登录、场景/静态资源读取、筛选4条、三候选比较及CSV四行。依赖沿用本机既有虚拟环境；未在新操作系统重新安装，也不把禁外网应用运行等同于离线安装依赖。

`mode=synthetic_demo_review_bundle`、`ready_to_submit=false`。视频尚未人工逐字听审，静态分镜不是连续录屏；PDF内容及正式规则/评审访问仍未终审，未报名或正式提交。真实来源、邮件、真实服务和用户试用范围没有变化。包内不含private数据库、账号、私人笔记、真实公告或密钥。
