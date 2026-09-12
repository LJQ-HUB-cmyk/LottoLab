# 免费云部署

更新：2026-09-13。**正式站已上线：[https://lottolab-zeta.vercel.app](https://lottolab-zeta.vercel.app)**，电脑关机后仍可查询数据、导入、运行实验和查看历史。Vercel Hobby 和两个独立的 Neon Free 数据库已配置完成；1.0.0 实际云端计算、浏览器、备份恢复和持久化验收通过。日常使用见 [线上使用说明](ONLINE_ACCESS.md)，当前证据见 [封板验收](validation/2026-09-13-release.json)，首次云上线的历史证据见 [云验收记录](validation/2026-09-13-cloud.json)。以下安装和迁移步骤供恢复/维护参考，当前无需重新执行。

## 服务分工与免费范围

| 服务 | 用途 | 本项目选择 |
|---|---|---|
| Vercel Hobby | React 静态页面、FastAPI、按请求运行的计算 | 使用免费个人套餐；第一版直接使用 Vercel 分配的 HTTPS 地址 |
| Neon Free | PostgreSQL：开奖、审计、冻结数据、实验及压缩原始快照 | 新建本项目专属空数据库，推荐 AWS US East，与 Vercel iad1 靠近 |
| Cloudflare Free | 可选的已有域名 DNS | 没有自有域名也可完成部署；当前不需要 Workers、D1、R2 或 Containers |

Neon 是额外的免费数据库服务，本次通过 Vercel Marketplace 原生集成创建，无需手工填写连接密码。当前科学计算依赖 NumPy、SciPy、scikit-learn，直接沿用 Python 比改写为 Workers/D1 更容易验证和维护。Cloudflare 免费 Workers 的 CPU/内存限制不适合原样运行这些计算，Containers 需要 Workers Paid。

官方配额核对于 2026-09-12，后续以账号控制台和官方文档为准：

- Vercel Hobby 面向个人非商业使用；Fluid Compute 单函数最长 300 秒、2 GB 内存，每月含 4 CPU 小时、360 GB 小时内存时间及 100 万次调用。
- Python 函数未压缩包上限 500 MB。本项目 36 个 Linux CPython 3.12 运行依赖解包约 240.58 MiB；实际 Vercel 构建报告 247.09 MB 并完成依赖优化，Python 3.12.14 已实际运行四类计算。
- Neon Free 每项目数据库存储 0.5 GB、每月 100 CU 小时计算、5 GB 对外传输；闲置约 5 分钟后可缩至零。初次访问或唤醒会比热启动慢。
- 当前 4 份官方快照从 1,874,912 字节压缩至 170,661 字节。这个数字不包含开奖表、索引和实验结果；实验历史仍会占用数据库容量。

免费额度适合个人和少量访问。避免反复运行大规模实验；额度到达上限时以平台行为为准，不自动升级付费。当前没有启用付费产品。

## 云端行为

页面和 API 在同一个 Vercel 项目。每次提交的计算在该 HTTP 请求内启动受监管的独立 Python 脚本，默认最长 240 秒，为函数退出和状态保存保留时间。配置经私有标准输入传递，保留平台运行时依赖路径，不重新加载 Vercel 的启动程序。同一数据库最多一个待执行/运行中的任务，多实例通过 PostgreSQL 事务锁共同执行限制。计算结果提交后请求才结束，不依赖请求返回后的后台进程。

计算中请等待响应。连接断开后重新打开实验历史查看状态；平台中断留下的旧任务会在下一次已授权查询/提交时标记失败，避免无限排队。请求中断时不能保证任务完成，失败后可减少规模重试。超时和取消会停止子进程。无需本机 API、worker 或 Docker 常驻。

云端所有私有数据读取、导出与写入都需要管理员令牌。首页静态页面、健康检查、规则和模型目录是公开的。令牌仅保存在当前页面内存，刷新后需重新输入；数据库连接和管理员令牌均不进入前端编译变量。

云端使用数据库原始快照存储；临时磁盘不承担持久化。空闲页面不持续轮询健康接口，以免让免费数据库一直保持唤醒。CSV 上传上限为 4 MiB、10,000 行；本地仍为 8 MiB。

## 连接账号与私有配置

在仓库根目录执行，Windows 使用下列 Python 路径；其他系统使用 `.venv/bin/python`。

```powershell
New-Item -ItemType Directory -Force -Path .local/cloud-cli | Out-Null
pnpm --dir .local/cloud-cli add --save-exact --ignore-scripts vercel@59.16.0
./.venv/Scripts/python.exe scripts/bootstrap_cloud.py
./.venv/Scripts/python.exe scripts/vercel_cli.py login
./.venv/Scripts/python.exe scripts/vercel_cli.py whoami
```

`bootstrap_cloud.py` 只在文件不存在时创建 `.env.cloud.local` 和随机管理员令牌，不会覆盖本地 `.env` 或打印密钥。在 Vercel 的官方登录页面完成登录。CLI 固定为 59.16.0，始终使用本项目目录和 `.local/vercel-config/` 私有认证目录；Windows 直接调用 Node，避免批处理把 URL 中的 `&` 解释成命令。已有安装与登录可跳过相应步骤。

先 `vercel_cli.py link` 关联本项目，再使用原生集成。新账号首次安装时，Vercel 会提供条款确认链接，需要账号本人阅读并接受；确认后重试同一命令。已存在同名资源时先检查，不能重复创建。

```powershell
./.venv/Scripts/python.exe scripts/vercel_cli.py integration list --json
./.venv/Scripts/python.exe scripts/vercel_cli.py integration add neon --plan free_v3 --metadata region=iad1 --metadata auth=false --name lottolab-db --environment production --prefix LOTTOLAB_ --no-env-pull --no-claim --non-interactive
```

本次正式资源为 `lottolab-db`，另一个独立 Free 资源 `lottolab-preview-db` 仅关联 preview。实际返回的套餐为 `free_v3`，价格 Free、不要求信用卡，含每项目 0.5 GB、100 CU 小时，最多 100 个项目。不要把付费套餐作为创建失败的自动回退。

集成会向对应 Vercel 环境写入 `LOTTOLAB_DATABASE_URL`，并提供其他兼容变量。可用 `vercel_cli.py env pull .local/cloud-config/production.env --environment production` 将配置下载到私有目录，再把数据库值写入 `.env.cloud.local`；预览环境使用 `.env.cloud.preview.local`，管理员令牌独立生成。保留原有正式管理令牌。真实连接及令牌不发送到聊天、不写入仓库、不放进命令行参数。

如果使用已有 Neon 账号，手工路径仍可用：创建专属空 Free 数据库，复制 pooled PostgreSQL 连接并保留 SSL 参数，形如 `postgresql://USER:PASSWORD@HOST-pooler.neon.tech/DB?sslmode=require`。本次已由集成完成连接，无需再注册或复制。

```powershell
./.venv/Scripts/python.exe scripts/bootstrap_cloud.py --check
```

此检查只验证语法，不表示已经连通数据库。`.env*`、`.local/`、原始 ZIP、测试报告和本地数据库均从上传内容排除；`.vercel/` 也不进 Git。

## 首次迁移现有数据

先等待本地运行任务完成，迁移期间不再提交新导入/实验。迁移读取一致的源数据库快照，不修改来源；迁移后本机与云数据库各自独立，不自动双向同步。

```powershell
./.venv/Scripts/python.exe scripts/migrate_cloud.py
./.venv/Scripts/python.exe scripts/migrate_cloud.py --apply
```

第一个命令是只读预检。第二个仅向本项目专属空目标写入：执行 Alembic 迁移、复制全部开奖/审计/冻结数据/任务、校验所有原始快照，逐表核对 SHA-256 指纹后提交。目标已有数据、含其他应用表、源任务尚未结束、原始快照缺失或损坏时会停止。任何后续插入或一致性检查失败都会回滚目标事务。

SQLite 不保存时区信息，来源中的 UTC 时间会先恢复时区，再写入 PostgreSQL，避免服务器时区改变历史记录的时刻。历史实验原有代码指纹保持原样。

本项目当前 SQLite 来源有 1,300 期开奖、9 条历史任务、4 次导入、2 个冻结数据集、4 份原始快照。迁移报告的实际数字优先于文档。构建脚本不连接数据库、不自动执行迁移，预览构建也不会触碰生产数据。

两套云数据库现已填入数据并校验通过，不应再次运行首次迁移 `--apply`。后续 schema 更新需要独立的增量 Alembic 迁移。云端与本机数据并不自动双向同步。

## 关联 Vercel 项目并发布

部署前先核对 CLI 登录身份和目标。已有项目按实际项目名和 scope 关联；新项目可以在 `link` 的提示中创建。使用 Hobby，不启用付费附加产品。

```powershell
./.venv/Scripts/python.exe scripts/vercel_cli.py link
./.venv/Scripts/python.exe scripts/vercel_cli.py project inspect
```

控制台项目配置：

| 项目设置 | 值 |
|---|---|
| Root Directory | 本仓库根目录；不能选 `frontend` 或父工作区 |
| Framework | FastAPI |
| Python | 3.12，由 `.python-version` 指定 |
| Node | 24.x，与前端本地验证一致 |
| Function region | iad1（`vercel.json`）；数据库选择附近地区 |
| Build | 由 `pyproject.toml` 的 `[tool.vercel.scripts]` 调用 `python scripts/build_vercel.py` |
| Frontend build | pnpm 11.19.0，冻结锁文件安装，构建到 `frontend/dist` |

不要把项目改为纯 Vite 静态站点。Python 依赖来自锁定的 `pyproject.toml` 和 `uv.lock`，编译后的 `/assets` 可由 CDN 提供。业务数据只存 PostgreSQL。

把私有配置中的下列值添加到 Vercel 项目的目标环境。可以在控制台添加，或使用 CLI 的交互/标准输入；不要将密钥作为命令行参数。修改环境变量后需要重新部署才能生效。

| 环境变量 | 要求 |
|---|---|
| `LOTTOLAB_DATABASE_URL` | Neon pooled PostgreSQL 连接，启用 TLS |
| `LOTTOLAB_ADMIN_TOKEN` | 私有配置生成的随机令牌，至少 32 字符 |
| `LOTTOLAB_JOB_TIMEOUT_SECONDS` | 可选，默认 240，只允许 1–240 |
| `LOTTOLAB_ALLOWED_HOSTS` | 可选，仅附加真实自定义域名，逗号分隔；不含协议/端口/通配符 |
| `LOTTOLAB_ALLOWED_ORIGINS` | 可选的其他 HTTPS 来源；通常不需要 |

项目自动使用 Vercel 的 `VERCEL_URL`、`VERCEL_PROJECT_PRODUCTION_URL`、`VERCEL_BRANCH_URL` 生成域名和来源白名单。保留 Vercel 系统环境变量注入。

预览环境使用独立的空测试数据库/数据库分支及独立令牌。不要把生产数据库变量复制到所有预览环境，防止预览操作改动生产实验。预览通过后再发布生产环境：

```powershell
./.venv/Scripts/python.exe scripts/vercel_cli.py deploy --target preview
# 完成下方预览验收后，发布 Production：
./.venv/Scripts/python.exe scripts/vercel_cli.py deploy --prod
```

第一次部署也要显式使用 `--target preview`：CLI 对新项目的首次默认部署可能指向 production。v1.0.0 的正式配置部署 dpl_ABXUyTssffK1ufp68BkmQvgaTM4p 已通过公网验收。旧 0.1.0 部署 dpl_GSoE7kAMSrjvJJyJkSzsWyaxSefb 保留为此次发布的回滚目标；无数据库 schema 变更。主分支后续触发的部署以 Vercel 控制台和 GitHub Release 的记录为准。

实现已提交到 GitHub，PR #1 的三组 CI 均通过。Vercel 现有 Git 集成关联 LeilaoMi/lottery-design，生产分支为 main；PR 更新会创建预览，合并 main 会触发正式构建。后续改动先通过 PR 的 CI 与独立预览验收，再合并发布；CLI 仍可手动发布。GitHub Actions 只使用临时测试数据库，不保存云数据库凭据。父工作区的 Codex 配置、私有备份和原始运行数据均排除在源码与上传之外。

## 线上验收与 Cloudflare 域名

实际取得网址后逐项记录结果：

1. HTTPS 页面和静态资源正常；未提供令牌的数据读取、导出和计算返回 403。
2. 输入正确令牌可查看迁入的 SSQ/DLT 数据、原有导入记录和历史实验。
3. 提交一次小规模模拟/回测，状态变为完成并保存结果；刷新重新鉴权后仍可读取。
4. CSV 导入、去重和数据库快照正常；并发任务限制生效。
5. 从实际 Vercel 地区尝试官方数据同步。公开源可能限制海外地址；失败不能冒充同步成功，仍保留历史查询和 CSV 导入路径。
6. 等待空闲/重新部署后检查持久化及冷启动；确认请求时限、日志和套餐用量。
7. 本机服务全部关闭，使用另一台设备或手机网络访问同一地址，验证不依赖本机。

如果 Vercel 预览启用了 Deployment Protection，保持保护，使用已登录的 Vercel 浏览器会话验证。固定版本 59.16.0 的 `vercel curl` 不识别包装脚本所需的 `--global-config`，会错误转发给系统 curl。本次先由官方 CLI 生成本项目自动化访问凭据，再按官方文档的请求头/浏览器 Cookie 机制完成测试；凭据仅在内存和被忽略的私有文件中使用，不关闭保护。正式固定网址可公开打开页面，业务数据仍要求应用管理员令牌。

当前已完成上面的公网流程，默认四模型回测 120 期/训练窗口 500 期约 17 秒完成。官方来源在 iad1 暂不可达，两彩种通过备用来源同步成功；CSV 往返和快照完整性也已验证。电脑的 LottoLab 服务关闭时可使用正式站；手机布局以 390px Chromium 视口检查，未操作用户的手机或将电脑实际关机。

需要自有域名时，先在 Vercel 项目添加域名，再把 Vercel 控制台给出的 DNS 记录准确填入 Cloudflare。首次采用 DNS only，SSL/证书由 Vercel 验证完成；不要照抄固定 IP，也不要更改无关域名记录。默认 `*.vercel.app` 已包含 HTTPS，域名绑定不阻塞上线。

## 后续维护

保持管理员令牌私密，必要时在 Vercel 中轮换并重新部署。定期查看 Vercel/Neon 用量；数据库免费额度不等同于独立离线备份。运行 `python scripts/backup_cloud.py` 可对正式库做只读一致性备份，并在新建 SQLite 文件验证独立恢复；原始压缩快照和全部表均参与指纹校验。脚本每次生成独立目录，不覆盖现有库。完整恢复和回滚步骤见 [发布说明](../RELEASE.md)。

未来 schema 变动按审阅后的 Alembic 迁移单独执行，确认兼容性后部署；不把生产迁移放进每次构建或函数冷启动。CPU 长任务、多人使用或超过免费额度后需要另行评估运行方式。

## 官方参考

- [Vercel FastAPI](https://vercel.com/docs/frameworks/backend/fastapi)
- [Vercel Functions 限制](https://vercel.com/docs/functions/limitations)
- [Vercel Hobby](https://vercel.com/docs/plans/hobby)
- [Vercel Python runtime](https://vercel.com/docs/functions/runtimes/python)
- [Vercel 自动化访问部署保护](https://vercel.com/docs/deployment-protection/methods-to-bypass-deployment-protection/protection-bypass-automation)
- [Neon Free 与套餐](https://neon.com/docs/introduction/plans)
- [Cloudflare Workers 限制](https://developers.cloudflare.com/workers/platform/limits/)
- [Cloudflare Containers 套餐](https://developers.cloudflare.com/containers/platform/pricing/)
