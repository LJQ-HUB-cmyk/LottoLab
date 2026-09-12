# 任务与恢复状态

## 当前任务：v1.0.0 最终封板

用户已要求按最终封板推进；GitHub CLI 已登录 LeilaoMi，指定仓库具备 push/admin 权限，main 仍为原始 7e81ed2。沿用云发布授权，冻结现有范围，完成可恢复、可追溯的稳定发布。

- [ ] T110：核对产品/科学/安全边界，统一 1.0.0 版本，清除当前文档中与线上状态冲突的旧表述。
- [ ] T111：完善 Linux 容器非空数据及任务重启验证，提交并推送最终代码，取得真实 GitHub Actions 后端/PostgreSQL/浏览器/容器 PASS。
- [ ] T112：生产数据库只读备份，独立空库恢复及逐表/原始快照校验，形成可重复运行的维护入口。
- [ ] T113：最终预览部署、正式发布与版本/计算/历史持久化检查，保留回滚目标与原生产数据。
- [ ] T114：源码并入主分支、发布版本标签与 Release，更新封板记录和最终证据；实际完成后标记封板。

封板前云部署和旧本地阶段的记录如下，原有 PASS/失败历史保持可追溯；尚未执行的封板检查不提前标为通过。

更新：2026-09-13。用户已授权 LottoLab 业务开发，并选择“电脑关机后完整使用，优先免费云服务”。**免费云正式部署与真实 Vercel 验收已完成：https://lottolab-zeta.vercel.app。** 下方首版本地验证属于云改造前的基线。本地启动入口 Start-LottoLab.cmd；本次线上验收时本机 API/worker 未运行。

## 当前任务：免费云部署

- [x] T100：请求内监管子进程，最多 240 秒、同时一个任务；超时/取消/中断恢复及跨 PostgreSQL 实例限制已验证；本地 worker 保留。
- [x] T101：数据库压缩快照、Alembic 迁移与空目标迁移工具完成；真实 1,300 期、9 个任务及 4 份快照迁入 PostgreSQL，全部指纹一致，来源未变。
- [x] T102：云入口、私有读写鉴权、Linux 依赖锁定、前端构建、上传排除规则和私有配置工具完成。
- [x] T103：88 项后端测试、原有 7 条本地浏览器验收、Ruff/mypy/TypeScript/构建、真实 PostgreSQL 和迁移往返通过，证据如下。
- [x] T104：Neon Free 正式/预览迁移、Vercel Linux 构建与运行 PASS；两个环境的鉴权、八页面、浏览器提交计算、刷新持久化及手机布局 PASS。预览四类在线计算、默认回测、CSV 往返及备用源同步 PASS；正式版在本机服务关闭时验收通过。

Vercel CLI 私有认证位于 .local/vercel-config/，项目关联在 .vercel/project.json。统一通过 `python scripts/vercel_cli.py` 调用。账号 scope 为 wouuify23-7389s-projects；原 sales-copilot 项目未改动。用户已阅读并接受集成条款。Neon 资源 lottolab-db 仅连接 production，lottolab-preview-db 仅连接 preview；均明确指定 free_v3、iad1、auth=false，并核对实际价格 Free、不要求信用卡。

`.env.cloud.local` 与 `.env.cloud.preview.local` 含独立数据库连接和随机管理令牌；正式令牌沿用此前生成值，Vercel 管理令牌配置为 Secret。`.env.local` 是 Vercel link 写入的私有配置。这些文件均被 Git 和上传规则排除；实际 deploy --dry 的 75 个文件清单也确认无私密配置、数据库或源 ZIP。没有付费、没有推送。

真实 Neon 迁移报告位于 .local/cloud-config/{production,preview}-{dry-run,migration}.json；两套最初均迁入 1,300 开奖、9 历史任务、4 导入、2 冻结版本、4 原始快照，逐表指纹一致。最终复核确认本机来源和迁入原记录均未变，所有新增数据库快照也可解压校验。正式库现有 10 个任务（含本次浏览器验收模拟）；预览库有 18 个任务和 1,301 期开奖（备用源新增一期 DLT），两库相互独立。

云运行实际修复了三处平台差异：入口显式加入 backend 路径、静态目录锚定源码；计算子进程使用独立脚本，避免 multiprocessing spawn 重新启动 Vercel 托管程序；源码版本不依赖本项目的已安装 distribution 元数据。相关 20 项回归和最终 88 项完整 PostgreSQL 回归通过。

正式部署为 dpl_GSoE7kAMSrjvJJyJkSzsWyaxSefb，固定网址 https://lottolab-zeta.vercel.app；验收预览为 dpl_2dqatH7GEJhhgSFYv8gr4A4rxuwq。初始故障部署保留为平台历史，已由修复版替换。正式浏览器模拟 e4a44dc1-de4c-4340-ad33-97c8b8bab33e 已完成并能在刷新鉴权后恢复；预览默认四模型回测 863a237a-09ff-4b0f-aab2-40fe24b209ff 使用 120 期测试、500 期训练窗口，17.22 秒完成。非敏感汇总见 docs/validation/2026-09-13-cloud.json。

固定版本 CLI 的 curl 子命令不识别 --global-config，已经通过官方 CLI 生成本项目自动化访问凭据；当前 .local/live_client.py 从已认证项目 API 在内存读取该凭据，按 Vercel 官方机制保持预览保护并取得浏览器会话，不输出凭据、不关闭保护。

### 云改造验证证据

| 检查 | 结果 | 实际证据 |
|---|---|---|
| 后端完整回归（含 PostgreSQL） | PASS，88/88，24.28 秒 | .local/pytest-cloud-results.xml |
| Ruff / 格式 / mypy | PASS | 新增入口与子进程相关文件 lint/格式通过，19 个后端源文件类型检查 |
| 前端及 Vercel build 脚本 | PASS | 冻结 pnpm 安装、TypeScript 与 Vite，正式/预览 Linux 构建完成 |
| 浏览器 | PASS，本地 6/6、云模式 1/1，另完成真实预览/正式站 | 两个公网环境各 14 项检查：八页面、私人访问、浏览器计算、刷新历史、390px 布局与零 JS 异常 |
| PostgreSQL 17.10 | PASS | .local/cloud-validation/pg-98a54b955a9d4e62bb123b0ae4719302/verification.json |
| 真实来源迁移 | PASS | 1,300 开奖、9 任务、4 导入、2 冻结版本、4 快照逐表一致；原库前后指纹一致 |
| SQLite/PostgreSQL 往返 | PASS | 非 UTC 时区回归；修复无时区时间被目标服务器重新解释的问题 |
| Linux CPython 3.12 依赖 | PASS（实际运行） | Vercel Python 3.12.14；NumPy/SciPy/scikit-learn 的真实云计算完成，实验保存依赖版本和源码指纹 |
| Vercel 认证/项目关联 | PASS | Hobby 项目 lottolab 已正式发布，预览保护保持启用 |
| Neon Free / 迁移 | PASS | 两个环境独立资源，真实 Neon 逐表指纹一致，报告位于 .local/cloud-config/ |
| Vercel 构建 / 运行 | PASS | 预览四类实验 3–6 秒，默认回测 17.22 秒；正式 API/浏览器/静态缓存检查通过，当前部署错误日志为 0 |
| 云 CSV 与公开来源 | PASS | 1,000 条 CSV 重导入全为重复；SSQ/DLT 备用源各同步 30 期，官方接口失败如实记录 |

最新 PostgreSQL 检查使用隔离原生临时实例并已停止；未操作受阻 Docker。失败的早期诊断报告原样保留，不作为 PASS 证据。浏览器报告目录已分开为 local/cloud，配置枚举和格式检查通过，避免相互覆盖。

## 已完成

- [x] T01–T07：读取引用聊天、校验 GitHub 原始包、整理 21 份资料、建立规则/规格。原 LICENSE 和压缩包未修改。
- [x] T10–T16：Python/React 工程、规则校验、SQLAlchemy/Alembic、配置、health、锁文件与 CI。最终 Ruff PASS，mypy 15 个源文件 PASS，TypeScript/Vite PASS。
- [x] T20–T23：官方/备用来源、CSV、原始快照、幂等导入、查询、质量报告、冲突处理。真实 SSQ 1,000 期、DLT 300 期；恢复导入拒绝/冲突均 0。
- [x] T30–T33：精确零模型、描述统计、形态/分区/共现、随机性校准与 Bonferroni。完整 SSQ 检验 150 项，结果详见科学审计。
- [x] T40–T43：严格按期开奖的特征与训练切分、基线、未来扰动和截断回归、冻结数据与逐期结果。
- [x] T50–T53：固定参数逻辑回归/梯度提升树、训练侧预处理、边际概率一致性、配对区间与科学审计。自动调参/独立校准器不在首版实现范围。
- [x] T60–T62：Monte Carlo、SSQ 可结算时的税前 ROI、覆盖优化与精确枚举验证；DLT/演示收益明确禁用。
- [x] T70–T72：八个页面、真实数据与实验、错误恢复、窄屏、深色模式。最终一次 E2E：6/6 PASS，26.2 秒。
- [x] T83：README、运行维护、科学审计和最终验收文档已更新，区分本地通过与外部受阻。
- [x] T90：DLT 号码规则、真实来源、跨彩种隔离与 60 期实际四模型回放通过。

## 交付验证

| 检查 | 结果 | 证据 |
|---|---|---|
| 后端测试 | PASS，55/55 | .local/pytest-results.xml |
| Ruff / 格式 | PASS | 最终检查覆盖 backend/tests/scripts/migrations |
| mypy | PASS，15 个源文件 | 本次终端检查 |
| 前端格式/类型/构建 | PASS | Prettier、tsc、Vite；最终构建无空 chunk 警告 |
| 浏览器 E2E | PASS，6/6 | frontend/test-results/.last-run.json、playwright-report/ |
| 真实界面与计算 | PASS | 五条最终实验、桌面/手机截图、无 JS 异常 |
| SQLite 重启 | PASS | 1,300 条开奖、4 条重启前实验、4 份快照保持；.local/persistence-verification.json |
| 首次配置与备份 | PASS | 隔离验证 SQLite/PostgreSQL 配置生成、不覆盖现有文件；备份完整性与 SHA-256 |
| PostgreSQL 集成 | PASS（之前的检查） | .local/postgres-verification.json，临时 schema，原库前后均 1,300 条 |
| 当前源码最终 Docker 构建/重启 | BLOCKED | Docker Desktop 启动错误；通信文件清理被策略拒绝 |
| GitHub 远程 CI / 公开部署（本地首版时点） | SKIPPED | 该基线验收时尚未推送/发布；后续云目标见上方 T104 |

## 当前数据与实验

本机 .env 已切为 SQLite，原 PostgreSQL 配置私有备份在 .local/backups/environment-postgres-20260912.env。PostgreSQL 原卷保留。

四个原始官方快照校验通过后恢复到 .local/lottolab.db，页面来源包含“快照恢复”。这不是合成数据，也不是从 PostgreSQL 搬迁实验。SSQ 覆盖 2019-12-15—2026-09-10，DLT 覆盖 2024-09-11—2026-09-09，不代表完整历史。

最终运行 ID：

- SSQ 回测：bead7f3d-1afe-4f93-b3b4-7281b6199283
- DLT 回测：98253b6a-ff8b-4b1b-84b0-5c8a1e691c50
- 随机性：c3985713-426c-413f-a1c2-d572db5ee78c
- 模拟：8ba79ece-5334-4a21-adce-c4c9a121308a
- 覆盖：cb16281a-f190-4f19-b553-06c8c7536b66

完整 JSON 位于 .local/reports/，可在页面查看历史回测并导出。结构化摘要在 docs/validation/2026-09-12.json。没有删除较早的运行或选择性隐藏负面结果。

## 尚未完成的外部验收

- [ ] T80：Docker Desktop 恢复后，以最终源码重新构建并运行镜像。
- [ ] T81：运行 check_container.py，再保留命名卷重启，运行 --after-restart。当前只有 SQLite 重启已通过。
- [ ] T82：后续明确授权推送后，查看实际 GitHub Actions 结果；不能用本地通过代替远程结果。

Docker 问题是遗留通信文件无法访问。第一处临时目录已备份；清理 docker-secrets-engine/engine.sock 的命令被自动审批拒绝，原因 blocked by policy，未执行。没有重置 Docker、删除卷或更改系统代理。

## 继续时先做什么

1. 读取本文件、FINAL_AUDIT.md 与实际 Git/运行状态。
2. T104 已完成，先核对当前线上版本和用户的新需求。已有 CLI 登录、Vercel 项目与 Neon Free 资源，无需重新确认条款或重复创建。
3. 后续修改按 docs/CLOUD_DEPLOYMENT.md 显式部署 preview，验证后再更新 production。两库已含真实数据，不能重新执行首次空库迁移 --apply；需要 schema 更新时使用单独审阅的增量迁移。
4. 本地入口仍是 Start-LottoLab.cmd，服务状态须实查。Docker 故障不阻塞云方案，不重试被策略拒绝的清理。
5. 修改后只运行相应检查；未改业务代码不重跑全部实验。Git 分支为 codex/workflow-setup，实现已由 CLI 上传 Vercel，但 Git 改动仍未提交/推送；保留原修改，仅使用命令级 safe.directory。GitHub Actions 未运行。

旧全局配置工作已经结束，当前只聚焦彩票项目。不要因本地验收完成而宣称 Docker、GitHub CI 或公网服务已完成。

## 最后一次修复

备份清单曾包含连接关闭后消失的 WAL/SHM 临时文件；已在生成清单前关闭 SQLite 连接。新增独立进程回归验证后，最终后端测试为 55/55 PASS。有效最终备份在 .local/backups/20260912-173537-750011/，包含当前 1,300 条开奖和 9 条已保存任务。旧诊断备份加注说明，原样保留。
