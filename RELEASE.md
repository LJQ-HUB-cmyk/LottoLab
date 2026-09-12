# LottoLab 1.0.0 发布与封板

状态：封板验收进行中，尚未发布版本标签。用户于 2026-09-13 要求完成当前产品范围的最终封板。

## 固定范围

本版提供 SSQ/DLT 历史数据、来源和质量审计、统计检验、四模型滚动回测、Monte Carlo、组合覆盖及保存实验；支持本地 SQLite、Docker/PostgreSQL 和 Vercel Hobby + Neon Free。规格以 PROJECT_SPEC.md 为准，研究结论以 SCIENTIFIC_AUDIT.md 的实际窗口与证据为准。

本版不包含全历史保证、DLT 收益结算、多用户账户、定时同步、自动调参或盈利承诺。免费云单任务最多 240 秒、同时一项；官方来源不可达时如实使用备用源。封板固定已验收行为，后续修复另发补丁版本，不修改既有发布标签。

## 发布门槛

- Python/前端/安装元数据版本一致，依赖锁定，凭据及本机数据排除在源代码之外。
- GitHub Actions 使用全新 Linux 环境完成后端/PostgreSQL、前端构建、两类浏览器流程。
- Docker 使用独立 CI 项目：SSQ/DLT 各 100 期 synthetic 数据、计算、容器重建后数据/审计/任务/原始快照保持。
- 正式数据库只读备份并恢复到独立本地空库，逐表指纹和完整性通过；不覆盖正式或预览数据库。
- 当前源码在独立预览环境验证后，以正式配置发布；核对版本、权限、计算、历史记录和回滚目标。
- GitHub 主分支、不可变版本标签、发布记录及实际云端版本可相互追溯。最终证据见 FINAL_AUDIT.md 与 docs/validation/。

## 备份与恢复

在仓库根目录、已安装依赖的环境运行：

```powershell
./.venv/Scripts/python.exe scripts/backup_cloud.py
```

脚本读取私有 `.env.cloud.local`，以只读一致性事务读取正式数据库，把所有表、任务和压缩原始快照写入新建的 `.local/backups/cloud-*/lottolab.db`，再恢复为另一份 `restore-check.db`。`manifest.json` 保存逐表指纹、文件 SHA-256 和恢复结果，不包含数据库密码或管理员令牌。来源有运行任务时拒绝备份，待任务结束后重试。备份文件含私人研究数据，保存在私有位置。

预览库备份使用 `--source-env .env.cloud.preview.local`。程序每次创建独立目录，不替换已有备份。

需要恢复服务时，先校验 manifest 中的 SHA-256，在独立配置中使用已经验收的 SQLite 副本，并设置 `LOTTOLAB_SNAPSHOT_STORAGE=database`；核对数据和实验后再决定切换。迁回 PostgreSQL 时，先在新的专属空数据库使用 `scripts/migrate_cloud.py` 的 dry-run，再明确应用。不能把首次迁移指向已含数据的正式数据库。管理员令牌和连接配置由部署者另外保管。

## 后续补丁发布

1. 从当前主分支创建修复分支，更新版本与变更记录，提交 PR。
2. 等待三组 CI 检查通过；通过 `python scripts/vercel_cli.py deploy --target preview --yes` 验证独立预览环境。
3. 对正式数据库执行上述只读备份；如有 schema 变更，单独评审向后兼容迁移。
4. 通过 `python scripts/vercel_cli.py deploy --prod --yes` 使用正式环境配置发布，复核实际版本与核心流程。预览配置使用独立数据库，不能直接把预览环境提升为正式配置。
5. 为已验收提交建立新的版本标签和 Release，记录部署 ID 与回滚目标。CI 不保存云数据库凭据，不在 PR 中自动发布正式环境。

## 回滚

代码回滚使用 `python scripts/vercel_cli.py rollback <此前正式部署ID> --yes`，保留数据库和原始快照。发布时记录上一正式部署；执行前确认旧代码与当前 schema 兼容。本次封板没有数据库 schema 变更。回滚命令不用于恢复被覆盖的数据，数据恢复须先在独立目标验证。

本机 Docker Desktop 历史故障单独保留；容器交付门槛由 GitHub 托管 Linux 环境的真实重建/持久化检查验收，不把本机环境记为已修复。
