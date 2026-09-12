# 本地运行与维护

更新：2026-09-12。当前交付为 Windows + SQLite + 独立 API/worker。Docker 与 PostgreSQL 路径已建立，最终容器重启检查仍待本机 Docker 恢复。

## 启动与文件

双击根目录 `Start-LottoLab.cmd`，访问 <http://127.0.0.1:8000>。启动检查同时要求数据库可访问、计算进程在线、本地写权限有效。保留启动窗口，按 `Ctrl+C` 停止。Windows 启动器用 Job Object 管理 API、worker 及其计算子进程。

| 位置 | 用途 |
|---|---|
| `.env` | 私有本机配置，当前为 SQLite |
| `.local/lottolab.db` | 开奖、导入审计、冻结数据集、实验 |
| `.local/raw/*.snapshot` | 以 SHA-256 命名的原始响应和导入文件 |
| `.local/api.log` / `.local/worker.log` | 启动日志 |
| `.local/e2e/<run>/` | 独立浏览器测试数据 |
| `.local/backups/` | 私有备份，不进 Git |
| `.local/backups/environment-postgres-20260912.env` | 切换 SQLite 前保留的 PostgreSQL 配置 |

此次 SQLite 数据由官方快照恢复，随后重新运行验收实验；PostgreSQL 中的旧实验仍留在原数据库，没有被自动迁移。当前本地历史列表保留全部运行。

## 权限与前端开发

默认启动器仅绑定 `127.0.0.1`，显式允许本地写入，并限制 Host/Origin。外部来源和伪造转发地址的写入在测试中被拒绝。

容器关闭无令牌写入。右上角“管理权限”使用 `.env` 的 `LOTTOLAB_ADMIN_TOKEN`，仅保留在页面内存，刷新后须重新输入。不要把令牌放入聊天、截图或公开记录。

默认启动器将来源限制为自己的端口。使用 Vite 5173 时，停止启动器，然后在不同终端运行以下三个入口；`.env.example` 中已有 8000/5173 的允许来源：

```powershell
./.venv/Scripts/python.exe -m lottolab.cli serve
# 另一个终端
./.venv/Scripts/python.exe -m lottolab.worker
# 第三个终端
pnpm --dir frontend dev
```

API 为 8000，Vite 为 5173。后端改动后重启服务；生产前端改动后重新构建并刷新已打开的页面。

公开域名、TLS、托管账号、多用户登录和运维监控尚未配置，本次没有公开部署。

## 任务与故障

单个 worker 每次处理一个任务，计算放在独立子进程。最多 8 个排队/运行任务，默认超时 600 秒。可从页面取消任务；进程中断遗留的运行状态在超时回收后变为失败，随后可重新提交。

API/worker 必须共用数据库和 `LOTTOLAB_DATA_DIR`。本机 `.local` 与容器 `/data` 不是同一目录。切换到容器前先停止原生启动器；切回原生前先 `docker compose stop api worker`，避免两套 worker 混用一个队列及不同快照目录。

- 页面打不开：看启动窗口与 API 日志；必要时选择 `--port 8001`。
- 计算服务离线：看 worker 日志，确认两进程使用同一配置。
- 官方来源失败：查看任务错误；仍可读取历史库或导入 CSV。
- 存在冲突：在“开奖数据 → 质量报告”比较后处理，再运行实验。
- 数据不足：补充历史数据，或明确切换到演示数据验证功能。

## SQLite 备份与恢复

运行 `python scripts/backup_local.py`，每次新建时间戳目录，使用 SQLite 备份接口、执行完整性检查、复制原始快照和私有配置、生成校验清单。同步期间备份可能多保存少量尚未被数据库引用的快照，不影响已有记录。

恢复时：

1. 停止指向该数据库的服务。
2. 另行备份当前数据库、配置和原始快照。
3. 验证备份清单及数据库完整性，恢复匹配的数据库、`raw/`、`.env`。
4. 执行迁移、启动，核对总期数、日期范围和历史实验。

本次已验证生成的备份及快照校验值，未覆盖当前工作库进行破坏性恢复。

## 容器现状与复验

Compose 的 `postgres_data` 保存 PostgreSQL，`app_data` 保存容器原始快照和心跳。数据库端口 55432，容器界面端口 18080。

本机 Docker Desktop 在恢复会话中报旧通信文件无法访问，涉及 `dockerInference` 和 `docker-secrets-engine/engine.sock`。第一处临时目录已备份；清理第二处文件的命令被自动审批策略拒绝，返回 `blocked by policy`，没有执行。数据库卷没有被删除，Docker 没有被重置。需要先恢复 Docker Desktop 正常启动，再运行：

```powershell
docker compose up -d --build --wait
./.venv/Scripts/python.exe scripts/check_container.py
docker compose down
docker compose up -d --wait
./.venv/Scripts/python.exe scripts/check_container.py --after-restart
```

这里的 `down` 保留命名卷。首次检查验证前端、PostgreSQL、匿名写入拒绝、管理令牌及 worker 执行。第二次验证相同开奖总数与之前完成的任务，输出 `.local/container-verification.json`。当前未获得最终 PASS。

`bootstrap_env.py --postgres` 只影响新生成的配置，已有 `.env` 原样保留。切换连接前保存当前配置；SQLite 与 PostgreSQL 数据不会自动合并。

PostgreSQL 集成脚本在独立临时 schema 测试，结束时只移除本次 schema：

```powershell
./.venv/Scripts/python.exe scripts/check_postgres.py
```

需要当前配置为本地 PostgreSQL，或设置专用本地 `LOTTOLAB_TEST_DATABASE_URL`；当前默认 SQLite 不能直接运行此项。

### PostgreSQL 备份

先准备本次独立备份目录。在 db 容器内生成文件再复制，避免 PowerShell 文本重定向损坏二进制 dump：

```powershell
docker compose exec -T db pg_dump -U lottolab -d lottolab -Fc -f /tmp/lottolab.dump
docker compose cp db:/tmp/lottolab.dump .local/backups/lottolab-postgres.dump
docker compose cp api:/data/raw .local/backups/docker-raw
```

保留匹配的私有配置和原生 `.local/raw`；容器和原生快照不自动同步。恢复前先在独立测试库用 `pg_restore` 验证，再决定切换，避免覆盖现有库。

## 证据位置

检查命令见 README。记录在 `FINAL_AUDIT.md`、`SCIENTIFIC_AUDIT.md`、`docs/validation/` 及本机 `.local/`。GitHub Actions 已配置，尚未推送运行。

## 本次最终备份

已修正备份程序在关闭 SQLite 连接前生成清单的问题，避免将随后消失的 WAL/SHM 临时文件列入清单。黑盒回归测试在写前日志仍打开的数据库上运行独立备份进程，并在该进程退出后核对所有文件、校验值和已提交记录。

修复后的本次完整备份为 `.local/backups/20260912-173537-750011/`。较早两个诊断目录原样保留并加入 VERIFICATION_NOTE.txt，不作为最终可校验备份使用。
