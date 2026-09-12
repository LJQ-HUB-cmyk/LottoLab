import { ChevronLeft, ChevronRight, Download, Search, ShieldCheck, Upload } from 'lucide-react'
import { useState } from 'react'
import { api, fmt, query, stamp, useResource } from '../api'
import type { Drawing, IngestionRun, Quality } from '../api'
import { Balls, Empty, ErrorNote, Loading, PageTitle, Panel } from '../components'
import { useWorkspace } from '../Workspace'

export function Draws() {
  const workspace = useWorkspace()
  const [search, setSearch] = useState('')
  const [start, setStart] = useState('')
  const [end, setEnd] = useState('')
  const [offset, setOffset] = useState(0)
  const [tab, setTab] = useState<'draws' | 'sources' | 'quality'>('draws')
  const extra: Record<string, string | number> = { search, offset, limit: 25 }
  if (start) extra.start_date = start
  if (end) extra.end_date = end
  const records = useResource<{ items: Drawing[]; total: number }>(
    `/draws?${query(workspace, extra)}`,
    workspace.version,
  )
  const ingestions = useResource<{ items: IngestionRun[] }>(
    `/ingestions?${query(workspace)}`,
    workspace.version,
  )
  const quality = useResource<{ items: Quality[] }>(`/quality?${query(workspace)}`, workspace.version)
  const unresolved = quality.data?.items.filter((item) => item.resolution_state === 'open').length || 0
  return (
    <>
      <PageTitle
        title="开奖数据"
        description="查阅每期开奖、追溯数据来源，保留异常记录的处理证据。"
        actions={
          <>
            <a className="button" href={`/api/v1/draws/export?${query(workspace)}`}>
              <Download size={16} />
              导出 CSV
            </a>
            <button className="button button-primary" onClick={workspace.openImport}>
              <Upload size={16} />
              导入数据
            </button>
          </>
        }
      />
      <div className="tabs" role="tablist" aria-label="数据视图">
        {[
          ['draws', '开奖记录'],
          ['sources', '导入与来源'],
          ['quality', '质量报告'],
        ].map(([id, label]) => (
          <button
            role="tab"
            aria-selected={tab === id}
            className={tab === id ? 'active' : ''}
            key={id}
            onClick={() => setTab(id as typeof tab)}
          >
            {label}
            {id === 'quality' && !!unresolved && <span>{unresolved}</span>}
          </button>
        ))}
      </div>
      {tab === 'draws' && (
        <Panel>
          <div className="filter-bar">
            <label className="search-field">
              <Search size={17} />
              <input
                aria-label="搜索期号"
                value={search}
                placeholder="搜索期号"
                onChange={(e) => {
                  setSearch(e.target.value)
                  setOffset(0)
                }}
              />
            </label>
            <label>
              开始日期
              <input
                type="date"
                value={start}
                onChange={(e) => {
                  setStart(e.target.value)
                  setOffset(0)
                }}
              />
            </label>
            <label>
              结束日期
              <input
                type="date"
                value={end}
                onChange={(e) => {
                  setEnd(e.target.value)
                  setOffset(0)
                }}
              />
            </label>
            <span className="filter-count">共 {fmt(records.data?.total)} 期</span>
          </div>
          <ErrorNote message={records.error} />
          {records.loading ? (
            <Loading />
          ) : records.data?.items.length ? (
            <>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      <th>期号</th>
                      <th>开奖日期</th>
                      <th>开奖号码</th>
                      <th>主区和值</th>
                      <th>来源</th>
                    </tr>
                  </thead>
                  <tbody>
                    {records.data.items.map((draw) => (
                      <tr key={draw.id}>
                        <td className="strong">{draw.issue}</td>
                        <td>{draw.draw_date}</td>
                        <td>
                          <Balls main={draw.main_numbers} special={draw.special_numbers} compact />
                        </td>
                        <td>{draw.main_numbers.reduce((a, b) => a + b, 0)}</td>
                        <td>
                          <span className="source-label">{draw.source}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <div className="pagination">
                <span>
                  第 {Math.floor(offset / 25) + 1} / {Math.max(1, Math.ceil(records.data.total / 25))} 页
                </span>
                <button className="button" disabled={offset === 0} onClick={() => setOffset((n) => n - 25)}>
                  <ChevronLeft size={16} />
                  上一页
                </button>
                <button
                  className="button"
                  disabled={offset + 25 >= records.data.total}
                  onClick={() => setOffset((n) => n + 25)}
                >
                  下一页
                  <ChevronRight size={16} />
                </button>
              </div>
            </>
          ) : (
            <Empty title={search || start || end ? '没有符合筛选条件的期次' : '还没有开奖记录'}>
              {search || start || end ? '调整期号或日期范围后重试。' : '同步公开数据或导入 CSV 文件。'}
            </Empty>
          )}
        </Panel>
      )}
      {tab === 'sources' && (
        <Panel title="数据导入记录" subtitle="原始快照按校验值保存；同一期次冲突不会自动覆盖。">
          <ErrorNote message={ingestions.error} />
          {ingestions.loading ? (
            <Loading />
          ) : !ingestions.data?.items.length ? (
            <Empty title="尚无导入记录" />
          ) : (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>时间 / 来源</th>
                    <th>读取</th>
                    <th>新增</th>
                    <th>重复</th>
                    <th>隔离</th>
                    <th>快照校验值</th>
                  </tr>
                </thead>
                <tbody>
                  {ingestions.data.items.map((run) => (
                    <tr key={run.id}>
                      <td>
                        {stamp(run.created_at)}
                        <small className="table-sub">
                          {run.source_url.startsWith('https://') ? (
                            <a href={run.source_url} target="_blank" rel="noreferrer">
                              {run.source}
                            </a>
                          ) : (
                            run.source
                          )}
                        </small>
                      </td>
                      <td>{fmt(run.received)}</td>
                      <td>{fmt(run.accepted)}</td>
                      <td>{fmt(run.duplicates)}</td>
                      <td>{run.rejected + run.conflicts}</td>
                      <td>
                        <span title={run.snapshot_hash} className="hash-value">
                          {run.snapshot_hash.slice(0, 16)}…
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Panel>
      )}
      {tab === 'quality' && (
        <Panel title="异常与冲突" subtitle="非法记录隔离，合法但异常的日期保留并标注。">
          <ErrorNote message={quality.error} />
          {quality.loading ? (
            <Loading />
          ) : !quality.data?.items.length ? (
            <div className="quality-clear">
              <ShieldCheck size={42} />
              <h3>当前没有待复核记录</h3>
              <p>这表示已导入数据通过格式和规则校验，不等同于对开奖随机性的证明。</p>
            </div>
          ) : (
            <div className="quality-list">
              {quality.data.items.map((item) => (
                <QualityRow key={item.id} item={item} onResolved={workspace.refresh} />
              ))}
            </div>
          )}
        </Panel>
      )}
    </>
  )
}

function QualityRow({ item, onResolved }: { item: Quality; onResolved: () => void }) {
  const [error, setError] = useState('')
  const [pending, setPending] = useState(false)
  async function resolve(action: 'keep_existing' | 'accept_incoming') {
    if (
      action === 'accept_incoming' &&
      !window.confirm(`采用第 ${item.issue} 期的新记录？旧记录及原始来源会保留在修订审计中。`)
    )
      return
    setPending(true)
    setError('')
    try {
      await api(`/quality/${item.id}/resolve`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          expected_identity_hash: item.existing_identity_hash,
          expected_record_hash: item.existing_record_hash,
        }),
      })
      onResolved()
    } catch (e) {
      setError(e instanceof Error ? e.message : '处理失败，请刷新后重试')
    } finally {
      setPending(false)
    }
  }
  return (
    <div>
      <span
        className={`badge ${item.resolution_state === 'resolved' ? 'badge-completed' : item.severity === 'warning' ? 'badge-review' : 'badge-failed'}`}
      >
        {item.resolution_state === 'resolved'
          ? '已处理'
          : item.severity === 'conflict'
            ? '冲突'
            : item.severity === 'warning'
              ? '提示'
              : '非法记录'}
      </span>
      <div className="grow">
        <strong>{item.issue || `第 ${item.row} 行`}</strong>
        <p>{item.reason}</p>
        <small>{stamp(item.created_at)}</small>
        {item.resolution_state === 'open' && item.incoming && item.existing && (
          <div className="conflict-comparison">
            {[
              ['当前记录', item.existing],
              ['新记录', item.incoming],
            ].map(([name, raw]) => {
              const draw = raw as NonNullable<Quality['incoming']>
              return (
                <div key={name as string}>
                  <h4>
                    {name as string} · {draw.draw_date}
                  </h4>
                  <Balls main={draw.main_numbers} special={draw.special_numbers} compact />
                  <p>
                    销量：{draw.sales ?? '未提供'}　奖池：{draw.pool_amount ?? '未提供'}
                  </p>
                  <small>
                    奖级金额：
                    {Object.entries(draw.prizes)
                      .map(([tier, amount]) => `${tier} 等奖 ${amount}`)
                      .join('；') || '未提供'}
                  </small>
                </div>
              )
            })}
          </div>
        )}
        {item.resolution_state === 'open' && (
          <div className="quality-actions">
            <button className="button" disabled={pending} onClick={() => void resolve('keep_existing')}>
              {item.severity === 'conflict' ? '保留已有记录' : '标记已查看'}
            </button>
            {item.incoming && item.existing && (
              <button className="button" disabled={pending} onClick={() => void resolve('accept_incoming')}>
                采用新记录并留存审计
              </button>
            )}
          </div>
        )}
        <ErrorNote message={error} />
      </div>
    </div>
  )
}
