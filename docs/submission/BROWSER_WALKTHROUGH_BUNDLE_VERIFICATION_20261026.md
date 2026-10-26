# 连续浏览器片段版完整审阅包 · 2026-10-26

本机包：`private/LeaseRadar_Review_20261026_BrowserWalkthrough.zip`，21,821,531字节，SHA256 `5653880185dd98b6be1f9107f8f46c36b57bdc069f8bf79006c3f69bd2a7f30f`。只在private，未上传GitHub或外部平台。`source_commit=512678b2375152cef9fe529930322e2bb8435526`，应用0.1.16；较10月25日85文件包多了无音轨连续浏览器WebM、证明、录制脚本和审阅说明。

执行：

```sh
.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261026_BrowserWalkthrough.zip
.venv/bin/python scripts/verify_recording_bundle.py private/LeaseRadar_Review_20261026_BrowserWalkthrough.zip
```

预解压路径/类型、CRC、大小和逐项SHA256校验通过。89个payload文件中，88个仓库文件与固定提交Git blob逐字节一致，另1个`START_HERE.md`由打包器生成；`MANIFEST.json`另列。`working_tree_dirty=true`是既有用户未跟踪文件，不表示包内含未提交源码。包内无private数据库/账号/私人笔记、`.env`、密钥或真实原始公告。

从这个确切ZIP解压到`private/review-restore-browser-sj5jiymc`，只用解压源码与本机已有锁依赖，在禁止`socket.connect`条件下新建隔离SQLite。恢复得到6候选、7版本、5站内提醒、0网络请求；未登录场景401，合成账号登录后场景、首页、JS/CSS可读，筛选4条、三候选比较、同条件CSV四行通过。依赖未在新系统重新下载/安装，不把禁外网运行称为跨平台离线安装。

打包器核对静态分镜MP4及WebM的签名、文件哈希、字节数、版本与合成/录制方式；17项包专项通过。完整285项应用回归、1项Poppler集成、JS语法、录制脚本语法、依赖和差异检查通过；1条上游Starlette/AnyIO弃用警告保留。WebM 55.68秒、VP8无音轨，关键帧目视及完整解码见`BROWSER_WALKTHROUGH_20261026.md`。静态分镜207.5秒带合成旁白，人工逐字听审仍未完成。

`mode=synthetic_demo_review_bundle`、`ready_to_submit=false`。WebM只是自动化连续浏览器操作的补充画面，不能单独作为讲解视频；PDF仍是审阅稿，比赛实时规则、资格/报名、评审访问、最终视频形式及正式提交均未签收。真实来源、真实OCR、生产部署、邮件投递和试用没有新增验收。
