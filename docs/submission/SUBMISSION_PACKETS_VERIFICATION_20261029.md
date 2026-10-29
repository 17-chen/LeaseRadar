# 明日提交准备包核验 · 2026-10-29

## 最新：用户确认报名与个人参赛后

用户确认已报名并收到组委会确认邮件、个人参赛。PDF/提交对照/邮件稿已按这一事实更新，未读取原邮件或写入姓名、电话等私人资料；视频平台待定，尚未收到实际评审链接。下面两个最新包仍`ready_to_submit=false`，因为源码/视频访问与听审未签收。

固定提交`5154540ccc134d2fcc63dbca05e2dbe430a01cf1`：

- 完整包`private/LeaseRadar_Review_20261029_Individual.zip`，60,619,092字节，SHA256 `5f1dfe8164b2c6d561986999d976c637e5b8c22404bc05bd6a889ef76c16a535`。114个payload文件，113项仓库字节匹配，预解压验证及确切ZIP独立禁外网6/7/5合成初始化、登录/资源/筛选4条与字幕检查通过；恢复目录`private/individual-prep-restore-ms77_j7l`。
- 小包`private/LeaseRadar_Submission_Individual_20261029.zip`，258,842字节，SHA256 `94c1a2738661780ded5b061823164966359e1d35f199bb20c63d88bed41837c8`。4项payload及清单，前三项PDF/对照/邮件稿逐字节匹配固定提交，另1项为生成指南；CRC/大小/哈希通过，报名状态明确为用户已确认。

最新PDF为276,422字节，SHA256 `6d8ef6942f0ce0cb29eda04e5cf0aff4aafadcdb219bc651528e0dc5867a4a45`，第6页同步个人报名事实后重新渲染目视，其余五页像素与已核验版一致。27项打包专项再次通过；此前完整326项/1项Poppler通过，`2427cb0`的[CI运行40873855827](https://github.com/17-chen/LeaseRadar/actions/runs/40873855827)成功。之后材料/交接提交按最终head另核。

## 用户回复前的历史版本

固定源码提交`f9980e3f48760a7c48a51c864d24e1b5137cf106`，以下两包均只在本机private目录，未上传ZIP、未对外发送，均`ready_to_submit=false`。

## 完整审阅/恢复包

`private/LeaseRadar_Review_20261029_SubmissionPrep.zip`，60,618,288字节，SHA256 `5dca09b271f2d39f2efbbc3278a46a02b264efff318ab114a6c7052f9005346a`。114个payload文件，113项仓库文件逐字节匹配固定提交，另1项为生成的START_HERE.md；清单另计。

包含10月29日更新PDF、现有五类媒体/字幕/审阅服务、提交对照与未发送邮件稿。预解压校验通过路径、CRC、大小和哈希；确切ZIP独立解压至`private/submission-prep-restore-nbqfwpie`，禁止外部socket的进程中合成初始化6候选/7版本/5消息、登录、场景标识、首页/JS和筛选4条通过，包内字幕生成器`--check`通过。PDF哈希为`e91ee68c133e65aad99d87b3b9b977b1986f778f84ac7d41292fb51857582640`，与本次逐页QA产物一致。

依赖来自本机已有锁定环境，不宣称跨系统离线安装。没有纳入账号、数据库、真实公告、私人笔记、用户原有Un8(1)/或两张UI图片；这些既有未跟踪项使全局dirty，但不影响包内逐项提交匹配。这个约60MB的包用于内部审阅/恢复，不默认当正式邮件附件，也不替代评审所需链接。

## 小型提交核对包

`private/LeaseRadar_Submission_Preflight_20261029.zip`，258,421字节，SHA256 `03600f0afb971cb165861776d723037aafc46341265a7daf2bd802b0abb98316`。4个payload文件（新版PDF、提交检查表、未发送邮件稿、生成的READ_FIRST.md）及MANIFEST.json；前三项与固定提交的源文件逐字节匹配。ZIP CRC、逐项大小和哈希通过。

小包不包含可运行代码或视频；通过源码链接与待填视频链接提交的要求见[明日对照表](SUBMISSION_READINESS_20261029.md)。邮件草稿含占位资料，不能当已发送材料；清单明确报名确认未见、视频链接为空、评审源码访问未确认、邮件未发送。

## 检查与仍缺事项

本轮完整326项应用回归通过（49.16秒），1项Poppler集成通过，最终PDF更新后27项打包专项通过；字幕重建、JS语法、依赖和差异检查通过。六页PDF渲染/文本与实时官网/报名弹窗核查见[PDF记录](PDF_REVIEW_20261029.md)、[比赛要求](../COMPETITION_REQUIREMENTS.md)。保留既有Starlette/AnyIO弃用警告，以及旧PDF和中间排版样本。

实时表单已确认存在学生团队选项；没有执行本人报名或同意承诺。仍需确认真实主体/报名审核、源码和视频评审访问，完成人工听审与最终资料核对，再按确认邮件提交并留真实回执。源码、视频内容与生产/真实接入范围均不因此扩张。GitHub同步及最终CI按后续head核对。
