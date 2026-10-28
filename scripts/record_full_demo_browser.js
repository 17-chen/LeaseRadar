#!/usr/bin/env node
/** Capture a paced, synthetic ten-scene browser walkthrough for local video review. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PRIVATE = path.join(ROOT, 'private');
const starts = [0, 19.7, 41.2, 62.7, 82.7, 100.8, 120.6, 139.4, 159.8, 180.5];
const titles = ['开场', '自由筛选', '比较三条候选', '查看金额依据', '查看周期未知',
  '提醒收件箱', '跟进与笔记', '来源与受阻', '我的收藏', '范围与收尾'];
function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`缺少 ${name}`);
  return process.argv[index + 1];
}
function inside(child, parent) {
  const relative = path.relative(parent, child);
  return relative && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
}
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
async function main() {
  const url = new URL(argument('--url'));
  if (url.protocol !== 'http:' || url.hostname !== '127.0.0.1' || !url.port || url.pathname !== '/' || url.search || url.hash)
    throw new Error('只允许127.0.0.1的本地DEMO根地址');
  const guide = fs.realpathSync(argument('--guide'));
  if (!inside(guide, path.join(PRIVATE, 'demo-runs')) || path.basename(guide) !== 'DEMO_GUIDE.md')
    throw new Error('只允许private/demo-runs内的合成账号指南');
  const output = path.resolve(argument('--output-dir'));
  if (!inside(output, PRIVATE) || fs.existsSync(output)) throw new Error('输出必须是private内不存在的新目录');
  const password = fs.readFileSync(guide, 'utf8').match(/密码：([^\n]+)/)?.[1];
  if (!password) throw new Error('合成账号指南缺少密码');
  const modulePath = process.env.PLAYWRIGHT_CORE_PATH || 'playwright-core';
  const { chromium } = require(modulePath);
  const chrome = process.env.CHROME_EXECUTABLE || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
  const ffmpeg = process.env.PLAYWRIGHT_FFMPEG || '/Users/chenxin/Library/Caches/ms-playwright/ffmpeg-1011/ffmpeg-mac';
  fs.mkdirSync(output, { recursive: false, mode: 0o700 });
  const browser = await chromium.launch({ executablePath: chrome, headless: true });
  try {
    const context = await browser.newContext({
      viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1,
      recordVideo: { dir: output, size: { width: 1280, height: 800 } }, acceptDownloads: false,
    });
    await context.route('**/*', route => {
      const target = new URL(route.request().url());
      return target.origin === url.origin || target.protocol === 'data:'
        ? route.continue() : route.abort('blockedbyclient');
    });
    const login = await context.request.post(`${url.origin}/api/v1/auth/login`, {
      data: { username: 'demo', password },
    });
    if (login.status() !== 200) throw new Error(`合成账号登录失败：${login.status()}`);
    const me = await context.request.get(`${url.origin}/api/v1/auth/me`);
    if (me.status() !== 200 || (await me.json()).mode !== 'demo') throw new Error('目标不是DEMO');
    const scenario = await context.request.get(`${url.origin}/api/v1/demo/scenario`);
    if (scenario.status() !== 200 || (await scenario.json()).synthetic !== true)
      throw new Error('目标不是合成演示场景');
    const created = Date.now();
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url.origin, { waitUntil: 'networkidle' });
    await page.locator('#workspace').waitFor({ state: 'visible' });
    await page.locator('#demo-banner').waitFor({ state: 'visible' });
    await page.locator('#demo-route summary').click();
    const ready = Date.now();
    const observations = [];
    async function at(seconds) {
      const remaining = Math.round(seconds * 1000 - (Date.now() - ready));
      if (remaining > 0) await page.waitForTimeout(remaining);
    }
    async function step(index) {
      await page.locator('#demo-route-next').click();
      await page.waitForFunction(n => document.querySelector('#demo-route-progress')?.textContent.includes(`第 ${n} / 7 步`), index);
      const title = (await page.locator('#demo-route-title').textContent()).trim();
      if (title !== titles[index]) throw new Error(`第${index}步标题异常：${title}`);
    }
    observations.push({ scene: 1, title: titles[0], seconds: 0 });
    for (let scene = 2; scene <= 10; scene++) {
      await at(starts[scene - 1]);
      if ([4, 5, 6, 8].includes(scene)) await page.locator('#close-detail').click();
      if (scene <= 8) {
        await step(scene - 1);
        if (scene === 2 && !(await page.locator('#results-label').textContent()).includes('4 条'))
          throw new Error('合成筛选结果不是4条');
        if ([3, 4, 5, 7].includes(scene)) await page.locator('#detail').waitFor({ state: 'visible' });
        if (scene === 8) {
          const blocked = page.getByText('访问受阻', { exact: true }).first();
          await blocked.scrollIntoViewIfNeeded();
          await blocked.waitFor({ state: 'visible' });
        }
      } else if (scene === 9) {
        await page.locator('nav [data-view="listings"]').click();
        await page.locator('[data-quick-view="favorites"]').click();
        await page.waitForFunction(() => document.querySelector('[data-quick-view="favorites"]')?.getAttribute('aria-pressed') === 'true');
        await page.locator('#results-label').scrollIntoViewIfNeeded();
      } else {
        await page.locator('[data-quick-view="all"]').click();
        await page.locator('#demo-route').scrollIntoViewIfNeeded();
      }
      observations.push({ scene, title: titles[scene - 1], seconds: (Date.now() - ready) / 1000 });
    }
    await at(207.5);
    if (errors.length) throw new Error(`页面脚本错误：${errors.join(' | ')}`);
    const raw = await page.video().path();
    await context.close();
    const readyDelay = (ready - created) / 1000;
    const final = path.join(output, 'full-browser.webm');
    execFileSync(ffmpeg, ['-hide_banner', '-loglevel', 'error',
      '-i', raw, '-t', '207.5', '-r', '25', '-c:v', 'libvpx', '-b:v', '1200k', '-an', final],
      { timeout: 180000 });
    const bytes = fs.readFileSync(final);
    const proof = {
      schema: 1, capture_kind: 'paced_automated_continuous_browser_session', synthetic: true,
      audio: false, credential_entry_recorded: false, external_requests_blocked: true,
      source_commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(),
      playwright_core: require(path.join(require.resolve(modulePath), '..', 'package.json')).version,
      raw_sha256: hash(fs.readFileSync(raw)), browser_ready_delay_seconds: readyDelay,
      trim_seconds: 0,
      video: path.basename(final), bytes: bytes.length, sha256: hash(bytes),
      planned_duration_seconds: 207.5, observations,
    };
    fs.writeFileSync(path.join(output, 'capture-proof.json'), JSON.stringify(proof, null, 2) + '\n', { mode: 0o600 });
    console.log(`十场景连续浏览器录制完成：${final}；无音轨，仍需人工审阅。`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.stack || error.message); process.exitCode = 1; });
