# 最终验收记录

本地基线日期：2026-09-12；免费云更新：2026-09-13；版本：LottoLab 0.1.0。

**免费云正式部署与实际公网验收已通过：[https://lottolab-zeta.vercel.app](https://lottolab-zeta.vercel.app)。** Vercel Hobby 提供网页和计算，Neon Free 保存数据；本机 API/worker 均关闭时仍完成了云端计算与结果恢复。完整容器交付验收仍受本机 Docker 环境阻塞，云方案不依赖 Docker。默认本地启动器 Start-LottoLab.cmd 使用 SQLite，原 PostgreSQL 卷保留。

## 免费云验证

| 项目 | 结果 | 实际证据与范围 |
|---|---|---|
| 后端完整回归 | PASS | 88/88，24.28 秒，含 PostgreSQL 17.10；.local/pytest-cloud-results.xml |
| Python lint / 格式 / 类型 | PASS | 新增入口与子进程相关文件 Ruff/格式通过，mypy 19 个后端源文件通过 |
| 前端与云构建脚本 | PASS | 本地以及真实 Vercel 构建完成，pnpm 11.19.0 冻结安装、TypeScript/Vite |
| 本地浏览器基线 | PASS | 原生 6/6、云模式 1/1；独立 E2E 库与请求内计算 |
| 数据迁移往返与并发 | PASS | PostgreSQL 17.10 非 UTC 时区往返、两个独立应用争用单任务；.local/cloud-validation/pg-98a54b955a9d4e62bb123b0ae4719302/verification.json |
| Linux 依赖 | PASS（实际运行） | Vercel Python 3.12.14、NumPy 2.5.3、SciPy 1.18.1、scikit-learn 1.9.1；源码和依赖版本保存到实验 |
| Vercel / Neon 账号配置 | PASS | Hobby 项目 lottolab，两个环境独立的 Neon free_v3 数据库，连接 TLS，管理员令牌为 Secret |
| 正式 Neon 数据迁移 | PASS | 1,300 开奖、9 实验、4 导入、2 冻结数据集、4 原始快照逐表指纹一致；.local/cloud-config/production-migration.json |
| 预览 API 计算与导入 | PASS | 模拟、回测、随机性和覆盖均完成并重新读取；1,000 条 CSV 往返全为重复，无拒绝/冲突 |
| 默认规模四模型回测 | PASS | 120 期测试、500 期训练窗口、2,000 次 bootstrap，17.22 秒完成；运行 ID 863a237a-09ff-4b0f-aab2-40fe24b209ff |
| 预览/正式公网浏览器 | PASS | 两个环境各 14 项检查：八页面、令牌验证、彩种隔离、提交模拟、刷新读取历史、390px 布局，零 JS 异常 |
| 正式 HTTPS 与权限 | PASS | 公共页面和 3 个静态资源可访问，静态缓存 immutable；私有查询/导出/计算匿名 403，已授权查询 no-store |
| 正式云端计算 | PASS | 模拟 e4a44dc1-de4c-4340-ad33-97c8b8bab33e 通过浏览器提交、完成、刷新后重新鉴权及读取 |
| 云端公开来源 | PASS（备用源） | iad1 官方接口暂不可用，SSQ/DLT 备用源各收录/核对 30 期，来源和提示如实保留；仅预览库新增一期 DLT |
| 全部原记录与快照 | PASS | 最终复核保留本机来源及迁入原记录；正式 4 份、预览 7 份快照全部解压校验；.local/cloud-config/final-integrity-verification.json |
| 正式部署运行日志 | PASS | 当前部署最近 30 分钟错误记录为 0；.local/cloud-config/production-runtime-log-verification.json |
| 本机服务独立性 | PASS | 无本项目 API/worker 进程，8000/8011/8012 均未监听时完成公网验收；没有使用端口转发 |
| 实际关机/手机实机网络 | SKIPPED | 未关闭用户电脑或控制手机；移动端使用真实 Chromium 的 390px 视口验证 |

数据迁移修复 SQLite 无时区时间被 PostgreSQL 非 UTC 会话重新解释的问题，往返保持原始时刻及历史代码指纹；gzip 损坏检测包含无效 DEFLATE。云端实际运行还修复了源码路径、静态目录和计算子进程重复导入宿主启动程序的问题，并让源码版本记录不依赖已安装 distribution。相关 20 项回归与完整 88 项测试通过。

正式与预览使用独立数据库和令牌，构建不执行数据库迁移，原始快照压缩入库。CLI 包装脚本修复 Windows 参数转义与全局参数顺序问题。固定 CLI 的 curl 对 --global-config 支持有缺陷，本次按官方自动化访问机制取得保护会话，未关闭预览保护。

正式部署 ID 为 dpl_GSoE7kAMSrjvJJyJkSzsWyaxSefb；已验收预览 ID 为 dpl_2dqatH7GEJhhgSFYv8gr4A4rxuwq。初始云启动失败由新部署替换，预览失败任务保留。最终正式库有 1,300 开奖、10 任务，预览库有 1,301 开奖、18 任务；其中迁入的原 9 条任务和全部其他原记录均保持一致。数据库物理大小分别约 9.86 MB、10.49 MB，两个资源再次确认是 free_v3 / Free。

非敏感结果汇总在 [云验收 JSON](docs/validation/2026-09-13-cloud.json)，使用方式在 [线上使用说明](docs/ONLINE_ACCESS.md)。运行时源码指纹为 8fc12fc7c54b4917ce5eb437a48ddd3bb9b6c20c97e13412ebaa4fe8e01bcd79；旧实验仍保留自己的原指纹。源码尚未推送 GitHub，不宣称远程 CI 已通过。

以下保留云改造前的本地基线，不将历史 PASS 当作当前容器或线上结果。

## 完成的产品流程

SSQ/DLT 历史数据导入、校验、分页查询、来源追溯、冲突隔离与修订、统计与随机性检验、四模型滚动回测、模拟、组合覆盖和实验历史都已连接真实 API。前端含八个中文页面、移动端和深色模式。实验任务持久化，结果可查看或导出。

本次改正了修订审计遗漏保留财务字段的问题，记录最终入库值，并为冻结数据保留来源导入 ID。最终备份全量检查还发现清单曾包含会消失的 WAL/SHM 临时文件，已修正为关闭连接后生成清单，并增加独立进程回归测试。补齐形态/分区/共现展示、所有任务执行版本记录，以及不同模型选择组合不影响已有模型的随机种子分配。

## 实际检查

| 项目 | 结果 | 实际证据与范围 |
|---|---|---|
| 后端行为/边界/失败/防泄漏测试 | PASS | 最终 pytest：55 passed，4.23 秒，.local/pytest-results.xml |
| Python lint 与格式 | PASS | Ruff 检查 backend、tests、scripts、migrations |
| 后端类型检查 | PASS | mypy：15 个源文件，无问题 |
| 依赖一致性 | PASS | pip check：No broken requirements found |
| 前端格式 | PASS | Prettier 检查源码、E2E 与配置 |
| TypeScript 与生产构建 | PASS | tsc + Vite，包含 charts 独立包，最终无空 chunk 警告 |
| 浏览器全流程 | PASS | 最终一次 Playwright 6/6，26.2 秒 |
| 桌面与手机实测 | PASS | 真实数据、模型与统计；390px 页面无整体横向溢出，深色结构页正常，无 JS 异常 |
| SQLite 空库迁移 | PASS | E2E 每次创建隔离新库，执行两条迁移并导入 |
| 本地启动/重复启动/停止/重启 | PASS | 启动器确认 API+worker 就绪，复用已有服务，停止后自身进程树退出，再启动正常 |
| SQLite 持久化 | PASS | 1,000 SSQ + 300 DLT、重启前 4 条已完成任务、4 份原始快照不变，完整性检查通过 |
| 初始配置生成 | PASS | 在隔离目录生成 SQLite 和 PostgreSQL 配置，令牌/密码非空，重复执行保留文件，未更改当前配置 |
| SQLite 备份 | PASS | 一致性备份、完整性检查、原始文件及 SHA-256 清单 |
| PostgreSQL 集成 | PASS（此前） | 迁移两次、号码约束、幂等、跨彩种唯一性、审计修订、冻结版本；公共库前后 1,300 条 |
| Docker 镜像/服务 | PASS（此前版本） | 之前完成镜像构建和服务启动；此项不代表当前源码最终容器通过 |
| 当前源码 Docker 完整复验 | BLOCKED | Docker Desktop 无法启动，最终构建、鉴权/worker smoke 及保留卷重启未通过 |
| GitHub Actions | SKIPPED | 工作流已配置，未推送运行 |
| 公开部署（本地基线时点） | SKIPPED | 9 月 12 日基线尚未发布；9 月 13 日云验收结果见上方 |
| 原始材料保护 | PASS | LICENSE 和预测项目.zip 相对 HEAD 无差异；工作区 diff --check 通过 |

上游 Starlette/httpx 测试客户端产生两条弃用警告，未影响测试通过；没有通过删断言、关闭核心检查或伪造结果消除失败。

六条浏览器流程覆盖：查询/分页/彩种隔离；CSV 幂等与非法行复核/对话框键盘；四模型任务及报告下载；模拟与覆盖；分区/共现/随机性结果；手机导航/深色/服务错误恢复。测试库独立于真实数据。

## 真实数据与实验

当前 SQLite 保存 1,300 条真实记录。官方原始响应校验后恢复导入，未加入合成记录填空。日期范围、来源和五条最终运行的参数/版本/结果见 [结构化证据](docs/validation/2026-09-12.json) 与 [科学审计](SCIENTIFIC_AUDIT.md)。

SSQ 120 期与 DLT 60 期回放均未给逻辑回归或树模型产生显著优势结论，频率模型的 Brier 较差。该结论只限这些窗口。300 期随机性检验经 150 项校正后未显著；模拟中的不利偏离、名义区间和覆盖前提如实保留。

截图位于本机 .local/：dashboard-desktop.png、dashboard-mobile.png、backtest-desktop.png、dlt-backtest-desktop.png、structure-desktop.png、structure-mobile-dark.png、randomness-desktop.png。完整报告在 .local/reports/。

## Docker 阻塞与替代交付

恢复会话时 Docker Desktop 的旧通信文件无法访问，出现 dockerInference 和 docker-secrets-engine/engine.sock 启动错误。第一处临时目录保留了备份；第二处清理命令被自动审批审查拒绝，返回 blocked by policy，未执行。没有删除数据库卷、重置 Docker 或修改系统代理。

本机 .env 已在私有备份后切到 SQLite。从四份官方快照恢复数据，再运行真实实验、本地重启和备份验收，保证当前应用可用。PostgreSQL 旧数据及实验仍在其原有卷中；两种数据库不会自动合并。

Docker Desktop 恢复后，应按 docs/OPERATIONS.md 构建最终源码，运行 check_container.py，保留卷重启，再运行 --after-restart。完成前 P8 保持 PARTIAL/BLOCKED。

## 明确限制

- 没有完成全历史/完整节假日日历核对，也没有完整的历史修订公布时点档案。
- 首版为固定参数的探索性回放，没有自动调参、独立校准器或预登记不可重复访问的确认性检验区。
- 多重校正按次实验进行，不涵盖所有历史搜索。
- SSQ ROI 依赖可追溯的当期每注奖金且采用税前口径；DLT 和演示数据禁用 ROI。
- 没有做长期高并发压力测试、多用户或公网运维验收。
- 没有提交/推送代码，没有获得远程 CI 或公网部署结果。

这些边界是交付状态的一部分。默认本地流程可用，环境阻塞不被记为通过。
