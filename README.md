<p align="center">
  <img src="docs/assets/hero.svg" alt="LottoLab · 彩票历史数据与概率实验工作台" width="100%">
</p>

<p align="center">
  <a href="https://github.com/LeilaoMi/lottery-design/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/LeilaoMi/lottery-design/ci.yml?branch=main&amp;label=CI" alt="CI"></a>
  <a href="https://github.com/LeilaoMi/lottery-design/releases"><img src="https://img.shields.io/github/v/release/LeilaoMi/lottery-design?color=286ca3&amp;label=release" alt="Latest release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-627b94" alt="MIT License"></a>
</p>

<p align="center">
  <a href="docs/getting-started.md">安装</a> ·
  <a href="docs/user-guide.md">使用指南</a> ·
  <a href="docs/deployment.md">部署</a> ·
  <a href="docs/methodology.md">研究方法</a> ·
  <a href="CONTRIBUTING.md">参与贡献</a>
</p>

**LottoLab 是一个中文彩票数据研究工作台。** 覆盖 8 个中国彩票——双色球、大乐透、七乐彩、快乐8、福彩3D、排列3、排列5、七星彩——把判定、验奖、注数计算、采集与推荐收敛到单一后端；池型玩法（双色球/大乐透/七乐彩/快乐8）走完整的统计检验、模型比较、时间回测与组合覆盖流程，数字型玩法走逐位频率与逐位均匀性检验，全部放在同一个可复现的实验框架里。

当前版本支持本地运行、Docker 和 Vercel + PostgreSQL 部署。云端工作台公开可访问、无需登录；开奖数据每日自动同步，真实一等奖注数/销量每日刷新；自行部署即可获得独立的数据与实验空间。

## 界面预览

[![LottoLab 开奖观察：最新开奖、数据范围与号码频率](docs/assets/workbench.webp)](docs/assets/workbench.webp)

<p align="center"><sub>v1.0.0 实际界面。截图中的期数与结果来自该实例，仓库不附带历史数据库。</sub></p>

<details>
<summary>查看移动端界面</summary>
<p align="center">
  <img src="docs/assets/workbench-mobile.webp" alt="LottoLab 移动端开奖观察" width="360">
</p>
</details>

## 功能概览

<table>
  <thead><tr><th width="104">能力</th><th>当前实现</th></tr></thead>
  <tbody>
    <tr><td><strong>数据整理</strong></td><td>8 彩种来源同步（17500/cwl/sporttery 多源交叉）、CSV 导入导出、原始快照、重复校验与冲突复核；开奖每日自动同步、一等奖注数/销量每日刷新</td></tr>
    <tr><td><strong>历史观察</strong></td><td>池型：号码频率、遗漏、和值、跨度、奇偶、分区、连号、重号与共现；数字型：逐位数字频率与遗漏</td></tr>
    <tr><td><strong>统计检验</strong></td><td>池型无放回零模型 + Monte Carlo + 序列相关 + 多重比较校正；数字型逐位均匀性卡方</td></tr>
    <tr><td><strong>模型比较</strong></td><td>均匀随机、历史频率、逻辑回归、梯度提升树，共用时间回测协议</td></tr>
    <tr><td><strong>在线工具</strong></td><td>7 策略推荐（含冷门避撞）+ 结构分 + 实测撞号指数 + 双色球冷门度（预计同奖人数/因子）；单式/复式/胆拖注数、批量验奖、票面 CSV 导出、策略回测、预测复盘闭环（推荐落台账→开奖自动对账命中率）</td></tr>
    <tr><td><strong>实验留存</strong></td><td>保存参数、种子、冻结数据、逐期结果和代码指纹，支持回测 JSON 导出</td></tr>
    <tr><td><strong>模拟覆盖</strong></td><td>Monte Carlo 分布对照、合法组合生成、贪心覆盖与覆盖率估计</td></tr>
    <tr><td><strong>统计诚实</strong></td><td>独立性检验为 null；冷门度只对浮动奖有意义且仅双色球有验证系数（大乐透/七乐彩样本外不成立）；一切只描述历史、不改变中奖概率</td></tr>
  </tbody>
</table>

界面提供深色主题和移动端布局。真实数据与演示数据分开显示，数据来源、计算状态和实验限制随结果保留。

## 快速开始

使用 Docker Compose 启动完整服务。需要 **Git、Python 3.12、Docker 和 Compose v2**；前端依赖会在镜像内构建。

```bash
git clone https://github.com/LeilaoMi/lottery-design.git
cd lottery-design
python scripts/bootstrap_env.py
docker compose up -d --build --wait
```

打开 **[http://127.0.0.1:18080](http://127.0.0.1:18080)**，在“管理权限”中输入本地生成的 `.env` 内的 `LOTTOLAB_ADMIN_TOKEN`，即可同步数据、导入 CSV 和运行实验。

首次启动为空数据库；通过页面“同步数据”或“导入 CSV”建立数据集。日常停止使用 `docker compose down`，数据保存在命名卷中。

不使用 Docker 时，按 **[本地安装指南](docs/getting-started.md)** 安装 Python 与前端依赖，Windows 可通过 `Start-LottoLab.cmd` 启动。

## 运行与部署

| 方式 | 默认数据库 | 适用场景 |
| :--- | :--- | :--- |
| 本地 | SQLite | 个人分析与开发 |
| Docker | PostgreSQL 17 | 自托管与较长实验 |
| Vercel | Neon PostgreSQL | 个人云端使用 |

本地与 Docker 使用独立 worker；云端按请求计算，电脑关机后仍可访问，默认每次最多运行 **1 项实验、240 秒**。Vercel Hobby 与 Neon Free 可用于符合其条款及配额的个人部署；具体额度以服务商为准。Cloudflare 可选用于自有域名的 DNS。

部署配置、独立预览环境、备份与恢复见 **[部署指南](docs/deployment.md)**。

## 文档导航

<table>
  <thead><tr><th width="104">文档</th><th>内容</th></tr></thead>
  <tbody>
    <tr><td><a href="docs/getting-started.md">安装启动</a></td><td>本地与 Docker 的安装、启动和首次导入</td></tr>
    <tr><td><a href="docs/user-guide.md">使用指南</a></td><td>权限、数据同步、CSV 格式与实验流程</td></tr>
    <tr><td><a href="docs/deployment.md">部署指南</a></td><td>Vercel + Neon、自托管、备份和更新</td></tr>
    <tr><td><a href="docs/methodology.md">研究方法</a></td><td>零模型、时间切分、评价指标与边界</td></tr>
    <tr><td><a href="CONTRIBUTING.md">贡献指南</a></td><td>源码结构、开发环境与验证</td></tr>
    <tr><td><a href="CHANGELOG.md">变更记录</a></td><td>已发布版本的功能变化</td></tr>
  </tbody>
</table>

## 使用边界

- 数据每日自动同步、一等奖注数/销量每日刷新；公开来源可能因地区限制暂不可用，此时可手动同步或导入 CSV。
- 频率、"冷热"和冷门度只描述历史样本与分奖人数；模型输出、覆盖与推荐结果都不代表已证明的预测优势，也不改变中奖概率。
- 冷门度只对浮动奖有意义，且仅双色球有样本外验证的系数（大乐透/七乐彩经拟合验证不成立、不发布）；固定奖玩法中了为定额、无人分摊，冷门度对期望为 0。
- SSQ 的历史 ROI 仅在奖金资料完整、可追溯时计算，采用税前口径；DLT 暂不计算 ROI。
- 云端工作台公开可访问、无需登录；自托管（本地/Docker）读取公开、写入默认仅本机或凭管理员令牌，不提供多用户账户与角色管理。

本平台用于历史数据分析、统计实验和概率教育，不提供中奖保证，也不构成购彩建议。

## 许可证

源代码采用 [MIT License](LICENSE)。外部数据的使用仍应遵守其来源条款。
