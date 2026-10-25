# PDF更新版完整审阅包 · 2026-10-25

本机包：`private/LeaseRadar_Review_20261025_PdfReview.zip`，17,012,406字节，SHA256 `9ee30755522930f33dcf2ad08a03b2de04796d92ea5144cbc6f5e80d1a815dec`，未上传GitHub或外部平台。源码提交固定为`f7f1fc7e849082d008bfc2cb6c662d93a00abf5b`，应用版本0.1.16。旧82文件彩排包仍保留，内容不能代表本次PDF更新。

本轮将10月25日六页PDF审阅稿、PDF逐页QA、静态分镜听审清单、比赛要求核验边界和最新彩排记录纳入显式清单。包有85个payload文件，其中84个仓库文件与固定提交的Git blob逐字节相同；另1个`START_HERE.md`由打包器生成。`MANIFEST.json`另列，`working_tree_dirty=true`因既有用户未跟踪文件，不表示包中混入未提交源码。包内无`private/`、`.env`、账号、数据库、私人笔记、真实公告或密钥。

执行`.venv/bin/python scripts/build_recording_bundle.py --include-video --output private/LeaseRadar_Review_20261025_PdfReview.zip`，再运行`.venv/bin/python scripts/verify_recording_bundle.py private/LeaseRadar_Review_20261025_PdfReview.zip`；预解压安全路径、类型、CRC、大小与逐项SHA256通过。该包独立解压至`private/review-restore-pdf-wyuh71s4`，仅用解压源码与既有本机锁依赖，在禁止`socket.connect`条件下创建新隔离SQLite：6候选、7版本、5站内提醒、0网络请求；未登录场景接口401，登录后场景/首页/JS/CSS可读，筛选4条、三候选比较和同条件CSV四行通过。没有对现有服务、真实来源、SMTP或外部收件人操作。依赖未在新系统离线安装，不能宣称跨平台离线安装能力。

本轮完整应用回归首次因受限沙箱禁止本机SMTP绑定为281过/1失败；获准本机回环监听后282项全过，原失败保留。Poppler合成PDF集成1项、JS语法、`pip check`和`git diff --check`通过；1条Starlette/AnyIO上游弃用警告保留。PDF六页110 DPI逐页渲染和文本检查见`PDF_REVIEW_20261025.md`。

`mode=synthetic_demo_review_bundle`，`ready_to_submit=false`。207.5秒视频仍是合成静态分镜，未真人逐字听审，最终视频形式未定；PDF为审阅稿，官网实时规则、资格/报名、评审访问、正式授权与提交均未签收。真实来源覆盖、真实PDF/OCR、生产部署/投递和试用无新增验收。
