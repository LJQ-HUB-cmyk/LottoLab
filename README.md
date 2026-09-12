# LottoLab

彩票历史数据、统计检验、时间序列回测与组合覆盖实验平台。稳定版 `1.0.0` 已在云端上线，也可在本机使用，支持双色球（SSQ）和大乐透（DLT），默认中文界面。

**线上入口：[https://lottolab-zeta.vercel.app](https://lottolab-zeta.vercel.app)**。打开后使用部署者保管的管理员令牌进入；本机私有配置 `.env.cloud.local` 中的 `LOTTOLAB_ADMIN_TOKEN` 保存了当前正式令牌。只复制该变量的值，不复制数据库连接。使用方法见 [线上使用说明](docs/ONLINE_ACCESS.md)。

**这台电脑直接双击 `Start-LottoLab.cmd`，或打开 <http://127.0.0.1:8000>。** 启动器检查迁移、启动 API 和计算进程，并打开页面；保留启动窗口，按 `Ctrl+C` 停止。本次交付使用 SQLite，本机依赖、前端构建和真实数据已准备好。

2026-09-13 封板验收：**[GitHub CI](https://github.com/LeilaoMi/lottery-design/actions/runs/34713631649) 三组检查全部通过，89 项后端测试含真实 PostgreSQL，7 条浏览器流程通过，Docker 重建保留非空数据、任务、审计和原始快照**。v1.0.0 预览与正式站均完成八页面、云端计算、刷新恢复与 390px 布局检查。正式数据库的 1,300 期开奖、10 条发布前任务及全部快照完成只读备份和独立恢复，发布后原记录逐条保持一致。见 [封板证据](docs/validation/2026-09-13-release.json)、[最终验收](FINAL_AUDIT.md) 和 [发布说明](RELEASE.md)。

云端采用 **Vercel Hobby + Neon Free PostgreSQL**，不依赖本机 API、worker 或 Docker，已在本机服务关闭时完成公网验收。Cloudflare 可选用于已有域名，当前默认网址已带 HTTPS。部署步骤、免费额度和当前限制见 [免费云部署](docs/CLOUD_DEPLOYMENT.md)。源码和真实 CI 已在 GitHub 归档；固定版本与源码下载见 [v1.0.0 Release](https://github.com/LeilaoMi/lottery-design/releases/tag/v1.0.0)，封板后按补丁版本维护。容器交付已在独立 Linux runner 验收；本机 Docker Desktop 的历史故障仍保留，默认本地启动和云端均不依赖它。

## 已实现功能

| 页面 | 功能 |
|---|---|
| 开奖观察 | 最新收录开奖、来源、实际覆盖范围、号码频率、和值走势 |
| 开奖数据 | 搜索、日期筛选、分页、CSV 导入/导出、导入记录、质量报告、冲突复核 |
| 统计检验 | 频率、遗漏、和值、奇偶、跨度、大小号、连号、重号、分区、共现、随机性检验 |
| 模型档案 / 滚动回测 | 均匀随机、历史频率、逻辑回归、梯度提升树；逐期结果、差值区间与校正后 p 值 |
| 随机模拟 | 精确超几何抽样、模拟与理论分布对照、置信区间 |
| 组合覆盖 | 合法去重组合、预算、子集覆盖、候选池内精确覆盖、完整主区空间的估计覆盖 |
| 研究方法 | 概率定义、防泄漏、检验假设、收益口径与方法限制 |

真实数据和演示数据分开；演示期号以 `SIM-` 开头，演示数据不计算 ROI。长任务有队列、进度、取消、失败状态和保存结果。回测可导出完整 JSON。

## 当前收录数据

| 彩种 | 期数 | 实际日期范围 | 最新收录期号 |
|---|---:|---|---|
| 双色球 | 1,000 | 2019-12-15 至 2026-09-10 | 2026105 |
| 大乐透 | 300 | 2024-09-11 至 2026-09-09 | 2026103 |

数据最初来自中国福彩和中国体彩公开接口，原始响应按 SHA-256 保存。本次恢复会话时，由四份官方快照重新解析到 SQLite；页面来源标为“快照恢复”。这些是真实历史数据，恢复导入时间不同于最初网络抓取时间。

表格为正式站上线时迁入的数据，也与保留的本机数据一致，不代表完整历史覆盖。点击“同步数据”访问官方来源，失败时尝试 500 公开数据备用源。本次 Vercel iad1 实测中官方接口暂不可用，SSQ/DLT 均成功使用备用源；来源和失败提示保留在导入报告中。预览库同步多收录的一期 DLT 未写入正式库。号码或财务字段有差异时，会隔离并要求复核；当前更新由用户点击触发，未设置定时同步。

## 第一次安装

在仓库根目录执行，需要 Python 3.12、Node.js 24 和 pnpm 11.19.0。本机已安装，无需重复创建虚拟环境。

```powershell
py -3.12 -m venv .venv
./.venv/Scripts/python.exe -m pip install -r requirements.lock
./.venv/Scripts/python.exe -m pip install --no-deps -e .
pnpm --dir frontend install --frozen-lockfile
pnpm --dir frontend build
./.venv/Scripts/python.exe scripts/bootstrap_env.py
./Start-LottoLab.cmd
```

`bootstrap_env.py` 默认生成 SQLite 配置及随机管理令牌，已有 `.env` 原样保留。配置和数据不进 Git；新检出的仓库开始时没有开奖数据，可在页面同步或导入 CSV。

Linux/macOS 使用对应的 `.venv/bin/python`，通过 `python scripts/start_local.py` 启动；本次原生桌面验收环境为 Windows。

## 日常运行

```powershell
./Start-LottoLab.cmd --check
./Start-LottoLab.cmd
./Start-LottoLab.cmd --sqlite --port 8001
./Start-LottoLab.cmd --no-browser
```

同端口已有 LottoLab 且计算进程就绪时，启动器复用现有服务；端口被其他程序占用时会报告错误。日志在 `.local/api.log` 与 `.local/worker.log`。

命令行也可迁移、同步或创建演示数据：

```powershell
./.venv/Scripts/python.exe -m lottolab.cli migrate
./.venv/Scripts/python.exe -m lottolab.cli sync --lottery ssq --count 1000
./.venv/Scripts/python.exe -m lottolab.cli sync --lottery dlt --count 300
./.venv/Scripts/python.exe -m lottolab.cli demo --lottery ssq --count 600 --seed 2026
```

手动分开启动时，分别运行 `python -m lottolab.cli serve` 和 `python -m lottolab.worker`；两者必须使用同一数据库与数据目录。前端开发可运行 `pnpm --dir frontend dev`，访问 5173 端口，允许来源配置见 [运行维护](docs/OPERATIONS.md)。

## CSV 格式

必需四列，号码用空格分隔，真实期号用四位年份加三位序号：

```csv
issue,draw_date,main_numbers,special_numbers
2026105,2026-09-10,02 04 13 14 15 30,08
```

可选列：`lottery,dataset_kind,sales,pool_amount,prizes`。`prizes` 是以奖级为键、每注税前金额为值的 JSON 对象，含逗号时遵守 CSV 引号转义。支持 UTF-8/GB18030，本地最多 8 MiB、云端最多 4 MiB，均最多 10,000 行。

重复导入幂等；非法记录和来源冲突有具体报告。采用修订保存旧值与最终新值，已经冻结的实验数据保持原样。缺失开奖不插值。

## Docker 与 PostgreSQL

Compose 包含 PostgreSQL 17、API 和 worker，前端静态文件随 API 镜像提供。数据库端口为 `127.0.0.1:55432`，容器界面为 <http://127.0.0.1:18080>。容器写入须在“管理权限”输入本机 `.env` 的管理员令牌，令牌仅保存在当前页面内存。

Docker Desktop 正常运行且 `.env` 已生成后：

```powershell
docker compose up -d --build --wait
./.venv/Scripts/python.exe scripts/check_container.py
```

新环境希望原生 API 连接本地 PostgreSQL 时，可在第一次生成配置时使用 `python scripts/bootstrap_env.py --postgres`。已有配置不会自动切换。**SQLite 与 PostgreSQL 是独立数据库，切换模式不会自动搬迁数据。**

GitHub CI 已在独立 Linux 环境完成镜像构建、两个彩种各 100 期 synthetic 数据导入、真实 worker 计算和保留卷重建校验。本机 PostgreSQL 配置备份及本机 Docker 故障记录见运行维护文档。当前默认启动方式不依赖 Docker。

## 检查与备份

```powershell
./.venv/Scripts/python.exe -m ruff check backend tests scripts migrations app.py
./.venv/Scripts/python.exe -m ruff format --check backend tests scripts migrations app.py
./.venv/Scripts/python.exe -m mypy backend
./.venv/Scripts/python.exe -m pytest -q
pnpm --dir frontend exec prettier --check src e2e playwright.config.ts playwright.cloud.config.ts vite.config.ts
pnpm --dir frontend build
pnpm --dir frontend exec playwright test
pnpm --dir frontend exec playwright test --config playwright.cloud.config.ts
./.venv/Scripts/python.exe scripts/backup_local.py
# 正式云库只读备份，并在独立本地空库验证恢复：
./.venv/Scripts/python.exe scripts/backup_cloud.py
```

浏览器测试创建独立 SQLite 库，本地 worker 流程使用 8011 端口，云端请求流程使用 8012 端口，不修改真实数据；两套报告分别保存在 `frontend/playwright-report/local` 与 `cloud`。Windows 优先使用已安装的 Edge；其他环境先在 `frontend` 运行 `pnpm exec playwright install --with-deps chromium`。

真实 PostgreSQL 测试需要 `LOTTOLAB_TEST_DATABASE_URL` 指向专用本地实例；只创建和清理自身临时 schema。CI 已配置 PostgreSQL 17 服务。没有设置该变量时，这两项测试会明确 SKIPPED，不能把它记为 PostgreSQL 通过。

本地备份脚本生成一致性数据库副本，并复制原始快照、私有 `.env` 和校验清单，包含管理员令牌。云备份脚本读取 `.env.cloud.local`，以只读事务复制所有表及嵌入快照，再恢复到另一个新建 SQLite 文件；云备份不包含令牌和连接配置。两类备份都写入独立的 `.local/backups/` 子目录并应私下保管。恢复步骤见 [运行维护](docs/OPERATIONS.md) 和 [发布与恢复](RELEASE.md)。

## 工程与证据

- [产品规格](PROJECT_SPEC.md)、[阶段进度](PLAN.md)、[任务状态](TASKS.md)
- [科学审计](SCIENTIFIC_AUDIT.md)、[最终验收](FINAL_AUDIT.md)、[运行维护](docs/OPERATIONS.md)
- [免费云部署](docs/CLOUD_DEPLOYMENT.md)
- [实现取舍](docs/IMPLEMENTATION_NOTES.md)、[最初资料审计](PROJECT_AUDIT.md)
- [原始资料索引](docs/SOURCES.md)、[方案评审](docs/DESIGN_REVIEW.md)

代码在 `backend/lottolab/` 和 `frontend/src/`，迁移在 `migrations/`。原始压缩包、LICENSE 和 21 份设计资料保留。上游：<https://github.com/LeilaoMi/lottery-design>。

本平台用于历史数据分析、统计实验和概率教育，不提供中奖保证，也不构成购彩建议。结果和适用范围见科学审计。许可证：[MIT](LICENSE)。
