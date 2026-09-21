import { expect, test } from '@playwright/test'

test.describe('grammar assistant', () => {
  test.beforeEach(async ({ page }) => {
    const errors = []
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()) })
    page.on('pageerror', error => errors.push(error.message))
    await page.goto('/')
    await expect(page.locator('.classification-main')).toBeVisible()
    await expect.poll(() => errors).toEqual([])
  })

  test('loads and auto-analyzes all demos', async ({ page }) => {
    for (const [name, type] of [['Regular', 'Type 3'], ['CFG', 'Type 2'], ['Left recursive', 'Type 2'], ['Context-sensitive', 'Type 1'], ['Unrestricted', 'Type 0']]) {
      await page.getByRole('button', { name }).click()
      await expect(page.locator('.classification-main')).toContainText(type)
    }
    await page.getByRole('button', { name: 'Left recursive' }).click()
    await expect(page.locator('.content-block').filter({ hasText: 'Validation results' })).toContainText('0 signals')
    await expect(page.locator('.stepper-nav button')).toHaveCount(3)
  })

  test('shows validation, parse, automaton, sharing, theme, and viewport behavior', async ({ page, context }) => {
    const editor = page.getByLabel('Grammar production rules')
    const analyze = page.getByRole('button', { name: 'Analyze grammar' })
    await editor.fill('S aA')
    await expect(analyze).toBeEnabled()
    await analyze.click()
    await expect(page.locator('.content-block').filter({ hasText: 'Validation results' })).toContainText('invalid production')
    await editor.fill('S -> a | a')
    await expect(analyze).toBeEnabled()
    await analyze.click()
    await expect(page.locator('.content-block').filter({ hasText: 'Validation results' })).toContainText('Duplicate production')
    await editor.fill('')
    await expect(analyze).toBeEnabled()
    await analyze.click()
    await expect(page.locator('.content-block').filter({ hasText: 'Validation results' })).toContainText('At least one production is required')

    await page.getByRole('button', { name: 'CFG' }).click()
    await page.getByRole('button', { name: 'Parse tree' }).click()
    const parseInput = page.getByLabel('Test grammar string')
    await parseInput.fill('aabb')
    await page.getByRole('button', { name: 'Parse string' }).click()
    await expect(page.locator('.parse-result')).toContainText('Accepted')
    await parseInput.fill('aabc')
    await page.getByRole('button', { name: 'Parse string' }).click()
    await expect(page.locator('.parse-result')).toContainText("Unknown symbol 'c'.")

    await page.getByRole('button', { name: 'Regular' }).click()
    const automatonInput = page.getByLabel('Test automaton string')
    await automatonInput.fill('b')
    await page.getByRole('button', { name: 'Test string' }).click()
    await expect(page.locator('.parse-result')).toContainText('Accepted')
    await automatonInput.fill('a')
    await page.getByRole('button', { name: 'Test string' }).click()
    await expect(page.locator('.parse-result')).toContainText('Rejected')

    await page.getByRole('button', { name: 'Copy share link' }).click()
    const shareUrl = await page.evaluate(() => location.href)
    const shared = await context.newPage()
    await shared.goto(shareUrl)
    await expect(shared.getByLabel('Grammar production rules')).toHaveValue('S -> aA | b\nA -> aS | a')

    await page.getByRole('button', { name: /Toggle/ }).click()
    await page.reload()
    await expect(page.locator('.app-shell')).toHaveAttribute('data-theme', 'dark')
    for (const width of [1440, 900, 390]) {
      await page.setViewportSize({ width, height: 900 })
      expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(width)
    }
  })
})