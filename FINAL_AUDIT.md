# 最终验收记录

日期：2026-09-13；版本：LottoLab 1.0.0；范围：PROJECT_SPEC.md。

**1.0.0 的功能、真实云部署、容器、数据恢复和安全边界验收均 PASS。** 正式站为 [https://lottolab-zeta.vercel.app](https://lottolab-zeta.vercel.app)。源码已归档 GitHub 主分支，合并后的 CI 和 Vercel Git 自动部署复验均通过。封板提交的固定标签、源码包及最终提交/部署校验记录由 [v1.0.0 Release](https://github.com/LeilaoMi/lottery-design/releases/tag/v1.0.0) 提供。

本次没有增加新的产品功能或修改数据库 schema。现有 Vercel Hobby、两个独立 Neon Free 数据库和管理员令牌保留；没有付费升级。

## 当前版本验收

| 检查 | 结果 | 实际证据与范围 |
|---|---|---|
| GitHub 全新 Linux CI | PASS | [34713631649](https://github.com/LeilaoMi/lottery-design/actions/runs/34713631649)，源码 6bc8c505c07b741146eaab831c7a227e9a6330fb，backend/browser/container 全部成功 |
| 完整后端测试 | PASS | 89/89，0 失败、0 跳过，19.628 秒；包含真实 PostgreSQL 测试 |
| Python lint/格式/类型 | PASS | CI Ruff、格式、mypy；本地另外以 Linux/win32 类型目标检查全部 19 个后端文件 |
| 进程监管回归 | PASS | 20/20，20.89 秒；真实子进程、宿主入口隔离、超时、取消与结果保存 |
| PostgreSQL 集成脚本 | PASS | 迁移、号码约束、幂等、跨彩种唯一性、审计修订、冻结数据；临时 schema 自行清理 |
| 前端与两类浏览器流程 | PASS | 冻结安装、Prettier、TypeScript/Vite；本地 worker 6 条 + 云请求模式 1 条 |
| 最终 Docker 镜像 | PASS | 独立 Linux runner 构建并启动 PostgreSQL/API/worker，使用私有临时配置 |
| 容器重建持久化 | PASS | SSQ/DLT 各 100 期 synthetic；CSV/审计指纹、真实 worker 结果和 2 份原始快照在保留卷重建后相同 |
| Python 依赖一致性 | PASS | CI pip check；锁定 49 个 Python 包的 OSV 查询未发现已知漏洞 |
| 前端生产依赖检查 | PASS | pnpm audit --prod：45 个依赖，0 已知漏洞 |
| 版本与凭据检查 | PASS | Python、前端、安装元数据、uv.lock 都为 1.0.0；候选源文件未发现项目密钥或私有运行目录 |
| 正式云备份与独立恢复 | PASS | 只读复制 1,300 开奖、10 任务、4 导入、2 冻结数据集、4 快照；两份 SQLite 完整性、逐表指纹和文件 SHA-256 一致 |
| 独立预览四类计算 | PASS | 模拟、四模型回测、随机性、覆盖 3.09–4.48 秒完成，重新读取与执行版本/源码指纹一致 |
| 两站真实浏览器 | PASS | 每站 14 项检查：八页面、拒绝无效令牌、彩种隔离、提交模拟、刷新鉴权和结果恢复、390px 布局、0 JS 异常 |
| 正式数据与隐私 | PASS | 正式 1,000 SSQ + 300 DLT；历史实验版本保留，查询/CSV 为 no-store，匿名私人读写/导出 403 |
| 发布前全部原记录 | PASS | 两库逐表、逐条哈希对比；旧记录和嵌入快照未改变，新增验收实验留档 |
| 部署日志 | PASS | 指定当前预览/正式部署的近 1 小时查询：error 条目 0，5xx 响应 0；仅代表该检查窗口 |
| 本机服务独立性 | PASS | 8000/8011/8012 均未监听时完成真实公网 API 和计算流程 |
| 实际关机、手机实机 | SKIPPED | 未关闭用户电脑或操作物理手机；使用真实 Chromium 的 390px 视口验证 |
| 本机 Docker Desktop 修复 | BLOCKED（本机环境） | 历史通信文件故障仍在，未重试此前被策略拒绝的清理；不影响已通过的 Linux 容器和云部署验收 |

首次 CI 的 Linux mypy 检查到了 Windows 专有 CREATE_NO_WINDOW 常量，已改用明确的 sys.platform 分支并完整复验。原始失败记录保留为 Actions 34713101518，没有删除测试、降低断言或隐藏失败。

上游测试客户端仍报告 Starlette/httpx 与 anyio 的两条弃用警告，不影响当前通过结果；未为隐藏警告更换未经验证的依赖。

## 发布、数据和恢复

本次已验收预览为 dpl_B7FuuvxfMRQu6zyG8czyYhTiHnYL；正式配置部署为 dpl_ABXUyTssffK1ufp68BkmQvgaTM4p。实际部署地区 iad1、Python 3.12.14；两个环境使用独立数据库和令牌，预览保护保持启用。

后端源码指纹：

```text
925cfaf89cc014c21969914c66e7b0df60ca92a79c48ddf2671160659bbf915a
```

预览四类实验与正式浏览器模拟 6e0143e5-ecb1-4823-b19b-bc866a3ac6d2 均保存版本 1.0.0、该指纹以及实际 NumPy/SciPy/scikit-learn 版本。历史回测仍保存原指纹 22285223d60062c6c7b22a544073f6c2ff19075c6822167ab30e4e56e09de698。

发布前逐条基线为正式 1,300 开奖/10 任务、预览 1,301 开奖/18 任务。本次验收后分别为 11 和 23 个任务，新增任务完整保留。原开奖、导入、冻结数据、快照和历史任务未变。公开 JSON 仅包含非敏感证据，不包含数据库副本、管理员令牌或部署认证。

正式只读备份目录为 .local/backups/cloud-20260912T185552Z-8cfd204d/。lottolab.db 和 restore-check.db 各 3,260,416 字节，SHA-256 均为 8acebfb6ff9ee0110fd626fa8efdce09af314b5071b671b517f120e287f3496f。备份没有连接配置或管理员令牌，部署者应单独私密保管配置。恢复必须先在独立目标验证，不能将首次迁移指向已含数据的正式库。

旧正式 0.1.0 部署 dpl_GSoE7kAMSrjvJJyJkSzsWyaxSefb 为本次回滚目标。当前无 schema 变更；代码回滚保留数据库。完整操作见 [RELEASE.md](RELEASE.md) 和 [运行维护](docs/OPERATIONS.md)。

主分支 5140b0fad5827ab31ad357e22d1c2afa675d368b 的 [CI](https://github.com/LeilaoMi/lottery-design/actions/runs/34715062726) 三组全部成功。Vercel Git 自动部署 dpl_6Vc519DoynYW6i4pUXHA9Dkw7qti 对应该提交，新增模拟 9d74cf5c-0951-405a-b903-6dc6cc7e72bc 在真实云端完成并重新读取；初次正式浏览器模拟和两个彩种历史继续保留。正式任务数因此从 11 增为 12。最终标签提交和部署的校验摘要随 GitHub Release 提供。

## 已完成的产品范围

SSQ/DLT 历史导入、来源与快照、校验/冲突修订、CSV、统计与随机性研究、四模型滚动回测、Monte Carlo、组合覆盖、实验历史与结果导出均通过真实 API 连接八个中文页面。本地 SQLite、Docker/PostgreSQL 和免费云部署均有各自验收证据。

科学结果不随版本号重新编造。SSQ 120 期和 DLT 60 期回放、150 项校正的随机性检查、区间与覆盖分母仍见 [SCIENTIFIC_AUDIT.md](SCIENTIFIC_AUDIT.md)。这些窗口未给逻辑回归或树模型产生显著优势结论；结论不能外推为保证随机或保证盈利。

首次云版的默认 120 期四模型回测实测 17.22 秒、CSV 往返及备用来源同步证据保留在 [0.1.0 云验收](docs/validation/2026-09-13-cloud.json)；本地安装/停止/重启和最初实验见 [本地历史记录](docs/validation/2026-09-12.json)。历史记录中的“未推送”或“未发布”仅描述当时状态，不是本版本状态。

## 固定边界

- 免费云同时最多一项任务，单项最多 240 秒；CSV 最多 4 MiB、10,000 行。未做长期高并发承诺。
- 记录更新由用户点击同步；未配置定时无人值守同步。iad1 的官方接口此前不可达，已验证并标注 500 备用源。
- 不保证完整历史、完整节假日开奖日历或所有修订的发布时点；真实与 synthetic 数据始终分开。
- 固定超参数的探索性回测，不包含自动调参、独立校准器或预登记确认性试验；多重校正按次实验处理。
- SSQ ROI 需要可追溯历史奖金且使用税前口径；DLT 与演示数据禁用 ROI。
- 当前为个人管理令牌模式，无多用户账户；无持续无人值守运维监控。Cloudflare 仅为可选 DNS。

详细当前证据见 [封板 JSON](docs/validation/2026-09-13-release.json)。验收结论按以上明确范围成立，后续修复通过新补丁版本发布并保留旧标签。
