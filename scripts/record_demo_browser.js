#!/usr/bin/env node
/** Record the seven-step synthetic demo in a real browser, without credentials on screen. */
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const ROOT = path.resolve(__dirname, '..');
const PRIVATE = path.join(ROOT, 'private');
function argument(name) {
  const index = process.argv.indexOf(name);
  if (index < 0 || !process.argv[index + 1]) throw new Error(`缺少 ${name}`);
  return process.argv[index + 1];
}
function inside(child, parent) {
  const relative = path.relative(parent, child);
  return relative && relative !== '..' && !relative.startsWith('..' + path.sep) && !path.isAbsolute(relative);
}
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
    const page = await context.newPage();
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(url.origin, { waitUntil: 'networkidle' });
    await page.locator('#workspace').waitFor({ state: 'visible' });
    await page.locator('#demo-banner').waitFor({ state: 'visible' });
    await page.locator('#demo-route summary').click();
    await page.waitForTimeout(3000);
    const observations = [];
    for (let step = 1; step <= 7; step++) {
      await page.locator('#demo-route-next').click();
      await page.waitForFunction(n => document.querySelector('#demo-route-progress')?.textContent.includes(`第 ${n} / 7 步`), step);
      const title = (await page.locator('#demo-route-title').textContent()).trim();
      observations.push({ step, title, time: new Date().toISOString() });
      if (step === 1 && !(await page.locator('#results-label').textContent()).includes('4 条'))
        throw new Error('合成筛选结果不是4条');
      if ([2, 3, 4, 6].includes(step)) {
        await page.locator('#detail').waitFor({ state: 'visible' });
        await page.waitForTimeout(7500);
        await page.locator('#close-detail').click();
      } else {
        await page.waitForTimeout(7500);
      }
    }
    if (errors.length) throw new Error(`页面脚本错误：${errors.join(' | ')}`);
    const videoPath = await page.video().path();
    await context.close();
    const bytes = fs.readFileSync(videoPath);
    const proof = {
      schema: 1, capture_kind: 'automated_continuous_browser_session', synthetic: true,
      audio: false, credential_entry_recorded: false, blocked_external_requests: true,
      source_commit: execFileSync('git', ['rev-parse', 'HEAD'], { cwd: ROOT, encoding: 'utf8' }).trim(),
      playwright_core: require(path.join(require.resolve(modulePath), '..', 'package.json')).version,
      video: path.basename(videoPath), bytes: bytes.length,
      sha256: crypto.createHash('sha256').update(bytes).digest('hex'), observations,
    };
    fs.writeFileSync(path.join(output, 'capture-proof.json'), JSON.stringify(proof, null, 2) + '\n', { mode: 0o600 });
    console.log(`七步浏览器录制完成：${videoPath}；只含合成页面、无音轨，仍需人工审阅。`);
  } finally {
    await browser.close();
  }
}
main().catch(error => { console.error(error.message); process.exitCode = 1; });
