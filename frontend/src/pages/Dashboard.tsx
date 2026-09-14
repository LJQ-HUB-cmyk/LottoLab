import { ArrowRight, Database, FlaskConical, RefreshCw, Upload } from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { fmt, pct, query, useResource } from '../api'
import type { Overview } from '../api'
import { Balls, Empty, ErrorNote, Loading, Metric, PageTitle, Panel } from '../components'
import { useWorkspace } from '../Workspace'

export function Dashboard() {
  const workspace = useWorkspace()
  const { data, error, loading, reload } = useResource<Overview>(
    `/overview?${query(workspace)}`,
    workspace.version,
  )
  if (loading && !data) return <Loading />
  return (
    <>
      <PageTitle
        title="开奖观察"
        description="从历史数据出发，用统计与对照实验检验假设。"
        actions={
          <button className="button button-quiet" onClick={reload}>
            <RefreshCw size={16} />
            刷新
          </button>
        }
      />
      <ErrorNote message={error} />
      {data && (
        <>
          <section className="draw-feature">
            <div className="draw-feature-main">
              <div className="feature-label">
                <span className="live-dot" />
                最新收录<span>{workspace.datasetKind === 'synthetic' ? '演示数据' : '真实数据'}</span>
              </div>
              {data.latest ? (
                <>
                  <div className="draw-meta">
                    <h2>第 {data.latest.issue} 期</h2>
                    <time>{data.latest.draw_date}</time>
                  </div>
                  <Balls main={data.latest.main_numbers} special={data.latest.special_numbers} />
                  <div className="draw-feature-footer">
                    <span>来源：{data.latest.source}</span>
                    <a href="#/draws">
                      浏览历史开奖 <ArrowRight size={15} />
                    </a>
                  </div>
                </>
              ) : (
                <div className="first-run">
                  <h2>让第一份数据进入工作台</h2>
                  <p>同步公开开奖记录，或导入自己的 CSV 文件。</p>
                  <div className="button-row">
                    <button className="button button-primary" onClick={workspace.sync}>
                      <RefreshCw size={16} />
                      同步公开数据
                    </button>
                    <button className="button" onClick={workspace.openImport}>
                      <Upload size={16} />
                      导入 CSV
                    </button>
                  </div>
                  <button className="text-button" onClick={workspace.demo}>
                    先体验演示数据
                  </button>
                </div>
              )}
            </div>
            <div className="draw-feature-aside">
              <div className="probability-symbol">
                <span>Ω</span>
                <i />
              </div>
              <h3>每种合法组合，机会相同</h3>
              <p>在均匀、独立的开奖模型下，一注命中全部号码的概率为</p>
              <strong>1 / {fmt(data.rule.combinations)}</strong>
              <a href="#/methodology">
                了解概率与实验方法 <ArrowRight size={14} />
              </a>
            </div>
          </section>
          <div className="metric-strip">
            <Metric
              label="已收录期数"
              value={fmt(data.total)}
              note={data.first_date ? `从 ${data.first_date} 开始` : '等待第一份数据'}
            />
            <Metric label="完成的实验" value={fmt(data.experiments)} note="每次运行独立留档" />
            <Metric
              label="待复核记录"
              value={fmt(data.quality_issues)}
              note={data.quality_issues ? '查看数据页中的质量报告' : '当前没有非法或冲突记录'}
            />
            <Metric
              label="最近 100 期主区和值"
              value={fmt(data.statistics.mean_sum, 1)}
              note={`理论均值 ${fmt(data.statistics.expected_sum, 1)}`}
            />
          </div>
          {data.total > 0 ? (
            <>
              <Panel
                title="号码出现频率"
                subtitle={
                  data.statistics.family === 'digit'
                    ? `最近 ${data.statistics.sample_size} 期各位数字的出现次数。`
                    : `最近 ${data.statistics.sample_size} 期主区，虚线为均匀模型的期望次数。`
                }
                action={
                  <a className="panel-link" href="#/statistics">
                    展开统计 <ArrowRight size={14} />
                  </a>
                }
              >
                <div className="chart">
                  <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                    <BarChart
                      data={data.statistics.frequency.main}
                      margin={{ top: 20, right: 18, left: 0, bottom: 4 }}
                    >
                      <CartesianGrid strokeDasharray="3 4" vertical={false} />
                      <XAxis
                        dataKey="number"
                        tickFormatter={(n) => String(n).padStart(2, '0')}
                        tickLine={false}
                        axisLine={false}
                        interval={1}
                      />
                      <YAxis width={36} tickLine={false} axisLine={false} />
                      <Tooltip
                        cursor={{ fill: 'var(--chart-hover)' }}
                        formatter={(value) => [fmt(Number(value)), '出现次数']}
                        labelFormatter={(label) => `号码 ${String(label).padStart(2, '0')}`}
                      />
                      {data.statistics.family === 'pool' && (
                        <ReferenceLine
                          y={(data.statistics.sample_size * data.rule.main_count) / data.rule.main_max}
                          stroke="#2d8792"
                          strokeDasharray="6 4"
                        />
                      )}
                      <Bar
                        isAnimationActive={false}
                        dataKey="count"
                        fill="#b85b6c"
                        radius={[3, 3, 0, 0]}
                        maxBarSize={24}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="chart-footnote">
                  <span>
                    <i className="legend-swatch red" />
                    历史次数
                  </span>
                  <span>
                    <i className="legend-line" />
                    均匀模型期望
                  </span>
                  <small>频率高低描述历史，不改变下一期理论概率。</small>
                </div>
              </Panel>
              <div className="grid-two dashboard-bottom">
                <Panel
                  title="和值随时间变化"
                  subtitle={
                    data.statistics.family === 'digit'
                      ? '逐期开奖的各位数字之和，仅作描述统计。'
                      : '逐期开奖的主区和值，仅作描述统计。'
                  }
                >
                  <div className="chart chart-small">
                    <ResponsiveContainer width="100%" height="100%" minWidth={0}>
                      <LineChart data={data.statistics.trajectory}>
                        <CartesianGrid strokeDasharray="3 4" vertical={false} />
                        <XAxis dataKey="issue" tickLine={false} axisLine={false} minTickGap={55} />
                        <YAxis width={36} tickLine={false} axisLine={false} />
                        <Tooltip />
                        <ReferenceLine
                          y={data.statistics.expected_sum}
                          stroke="#8099a9"
                          strokeDasharray="5 4"
                        />
                        <Line
                          isAnimationActive={false}
                          type="linear"
                          dataKey="sum"
                          name="和值"
                          stroke="#347ea1"
                          strokeWidth={1.8}
                          dot={false}
                        />
                      </LineChart>
                    </ResponsiveContainer>
                  </div>
                </Panel>
                <Panel title="从观察到验证" subtitle="把直觉变成可以复核的实验。" className="next-steps">
                  <a href="#/statistics">
                    <BarIcon />
                    <div>
                      <strong>检验历史分布</strong>
                      <p>检验频率、和值与序列相关，查看多重校正后的结果。</p>
                    </div>
                    <ArrowRight size={18} />
                  </a>
                  <a href="#/backtest">
                    <FlaskConical size={24} />
                    <div>
                      <strong>比较模型与随机基线</strong>
                      <p>只用过去的数据预测下一期，保留所有实验结果。</p>
                    </div>
                    <ArrowRight size={18} />
                  </a>
                  <a href="#/draws">
                    <Database size={24} />
                    <div>
                      <strong>核对数据来源</strong>
                      <p>查看导入记录、来源快照校验值与异常说明。</p>
                    </div>
                    <ArrowRight size={18} />
                  </a>
                </Panel>
              </div>
            </>
          ) : (
            <Empty title="你的研究工作台已准备好">数据进入后，这里会展示频率、走势和实验摘要。</Empty>
          )}
          <div className="coverage-note">
            实际收录范围：{data.first_date || '—'} 至 {data.last_date || '—'}
            。当前覆盖范围不代表全部开奖历史。
            {data.statistics.family === 'digit'
              ? ' 各位数字在其自身取值区间内独立均匀。'
              : ` 单号码主区入选概率为 ${pct(data.rule.main_count / data.rule.main_max, 2)}。`}
          </div>
        </>
      )}
    </>
  )
}

function BarIcon() {
  return (
    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8">
      <path d="M4 20V10m8 10V4m8 16v-7" />
      <path d="M2 21h20" />
    </svg>
  )
}
