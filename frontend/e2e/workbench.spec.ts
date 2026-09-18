import { expect, test } from '@playwright/test'
import type { Page } from '@playwright/test'

async function demo(page: Page, route = 'overview') {
  await page.goto(`/#/${route}`)
  await page.getByRole('button', { name: '演示数据', exact: true }).click()
}
async function completed(page: Page) {
  await expect(page.locator('.job-completed,.job-failed')).toBeVisible({ timeout: 60000 })
  await expect(page.locator('.job-completed')).toBeVisible()
}

test('overview, filtering, pagination and lottery isolation', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await demo(page)
  await expect(page.locator('.draw-meta h2')).toContainText('SIM-')
  await page.getByRole('link', { name: '开奖数据', exact: true }).click()
  await expect(page.locator('tbody tr')).toHaveCount(25)
  await page.getByRole('textbox', { name: '搜索期号' }).fill('SIM-000007ea-00240')
  await expect(page.locator('tbody tr')).toHaveCount(1)
  await page.getByRole('textbox', { name: '搜索期号' }).fill('')
  await page.getByRole('button', { name: '下一页', exact: true }).click()
  await expect(page.getByText('第 2 / 10 页', { exact: true })).toBeVisible()
  await page.getByRole('combobox', { name: '选择彩种' }).selectOption('dlt')
  await expect(page.locator('tbody tr').first().locator('.ball-main')).toHaveCount(5)
  await expect(page.locator('tbody tr').first().locator('.ball-special')).toHaveCount(2)
  expect(errors).toEqual([])
})

test('CSV import, idempotence, quarantine and dialog keyboard access', async ({ page }) => {
  await demo(page, 'draws')
  await page.getByRole('button', { name: '导入 CSV', exact: true }).click()
  await expect(page.getByRole('dialog')).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(page.getByRole('dialog')).toHaveCount(0)
  const csv =
    'issue,draw_date,main_numbers,special_numbers\nSIM-E2E-VALID,2025-12-25,01 02 03 04 05 06,07\nSIM-E2E-BAD,2025-12-25,01 01 03 04 05 06,07\n'
  for (let attempt = 0; attempt < 2; attempt++) {
    await page.getByRole('button', { name: '导入 CSV', exact: true }).click()
    await page
      .locator('input[type=file]')
      .setInputFiles({ name: 'fixture.csv', mimeType: 'text/csv', buffer: Buffer.from(csv) })
    await page.getByRole('button', { name: '校验并导入', exact: true }).click()
    await expect(
      page.getByText(attempt ? /新增 0 条，重复 1 条，隔离 1 条/ : /新增 1 条，重复 0 条，隔离 1 条/),
    ).toBeVisible()
    await page.getByRole('button', { name: '完成', exact: true }).click()
  }
  await page.getByRole('tab', { name: /质量报告/ }).click()
  await expect(page.getByText('SIM-E2E-BAD', { exact: true }).first()).toBeVisible()
  await page.getByRole('button', { name: '标记已查看', exact: true }).first().click()
  await expect(page.getByText('已处理', { exact: true }).first()).toBeVisible()
})

test('real worker completes a model comparison through the UI', async ({ page }) => {
  await demo(page, 'backtest')
  await page.getByLabel('测试期数', { exact: true }).fill('20')
  await page.getByLabel('训练窗口上限', { exact: true }).fill('80')
  await page.getByRole('button', { name: '开始滚动回测', exact: true }).click()
  await completed(page)
  await expect(page.locator('.comparison-table tbody tr')).toHaveCount(4)
  await expect(page.getByRole('heading', { name: '累计平均 Brier', exact: true })).toBeVisible()
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('button', { name: '导出完整报告', exact: true }).click()
  expect((await downloadPromise).suggestedFilename()).toMatch(/^lottolab-backtest-.*\.json$/)
})

test('Monte Carlo and covering calculations preserve their interpretation', async ({ page }) => {
  await demo(page, 'simulation')
  await page.getByRole('combobox', { name: '模拟次数', exact: true }).selectOption('10000')
  await page.getByRole('button', { name: '开始模拟', exact: true }).click()
  await completed(page)
  await expect(page.getByRole('heading', { name: '命中分布：模拟与理论' })).toBeVisible()
  await page.getByRole('link', { name: '组合覆盖', exact: true }).click()
  await page.getByRole('button', { name: '计算覆盖方案', exact: true }).click()
  await completed(page)
  await expect(page.locator('.ticket-row')).toHaveCount(10)
  await expect(page.getByText(/覆盖目标不包含附加区/)).toBeVisible()
})

test('statistics use saved results and adjusted p-values', async ({ page }) => {
  await demo(page, 'statistics')
  await page.getByRole('tab', { name: '组合结构', exact: true }).click()
  await expect(page.getByRole('heading', { name: '号码分区', exact: true })).toBeVisible()
  await expect(page.getByRole('heading', { name: '两号码共现', exact: true })).toBeVisible()
  await page.getByRole('button', { name: '查看全部 528 组号码对', exact: true }).click()
  await expect(page.getByRole('button', { name: '收起共现明细', exact: true })).toBeVisible()
  await page.getByRole('tab', { name: '随机性检验', exact: true }).click()
  await page.getByRole('combobox', { name: '零模型模拟次数', exact: true }).selectOption('999')
  await page.getByRole('button', { name: '运行随机性检验', exact: true }).click()
  await completed(page)
  await expect(page.getByRole('columnheader', { name: '校正后 p 值', exact: true })).toBeVisible()
  await expect(page.getByText(/预设检验族 150 项/)).toBeVisible()
})

test('online verify checks tickets against draws', async ({ page, request }) => {
  const errors: string[] = []
  page.on('pageerror', (error) => errors.push(error.message))
  await demo(page, 'online')
  const draws = await request.get('/api/v1/draws?lottery=ssq&dataset_kind=synthetic&limit=1')
  expect(draws.ok()).toBeTruthy()
  const first = (await draws.json()).items[0]
  const pad = (n: number) => String(n).padStart(2, '0')
  const ticket = `${first.main_numbers.map(pad).join(' ')} + ${first.special_numbers.map(pad).join(' ')}`
  await page.getByLabel(/票面/).fill(ticket)
  await page.getByLabel('期号（逗号分隔）', { exact: true }).fill(first.issue)
  await page.getByRole('button', { name: '验奖', exact: true }).click()
  await expect(page.getByText(/命中 1 注/)).toBeVisible()
  expect(errors).toEqual([])
})

test('mobile layout, navigation, dark theme and API failure recovery', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await demo(page)
  await expect(page.locator('.draw-meta h2')).toContainText('SIM-')
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth)).toBeLessThanOrEqual(391)
  await page.getByRole('button', { name: '打开导航', exact: true }).click()
  await page.getByRole('button', { name: '切换深色', exact: true }).click()
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark')
  await page.getByRole('link', { name: '研究方法', exact: true }).click()
  await expect(page.getByRole('heading', { name: '研究方法与边界', exact: true })).toBeVisible()
  await page.goto('/#/overview')
  await page.route('**/api/v1/overview?**', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({ detail: '测试：数据服务暂时不可用' }),
    }),
  )
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page.getByRole('alert')).toContainText('测试：数据服务暂时不可用')
  await page.unroute('**/api/v1/overview?**')
  await page.getByRole('button', { name: '刷新', exact: true }).click()
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.screenshot({
    path: test.info().outputPath('mobile.png'),
    fullPage: true,
    animations: 'disabled',
  })
})
