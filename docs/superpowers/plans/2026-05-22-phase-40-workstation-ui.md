# Phase 40 Workstation UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the dashboard surface into a navigable local quant workstation with focused subpages, a real Lightweight Charts Chart Lab, and a collapsible AI Coach panel.

**Architecture:** Keep the current vanilla HTML/CSS/JS stack and existing dashboard APIs. Convert the long page into a route-like single-page shell using hash navigation, page sections, shared status chrome, and context-specific AI Coach content. Preserve all existing element ids needed by current JavaScript and tests while adding new shell markers for Phase 40.

**Tech Stack:** Python HTTP dashboard service, static HTML/CSS/JavaScript, local TradingView Lightweight Charts bundle, pytest static/API tests, Node JavaScript syntax check, browser smoke verification.

---

## Files

- Modify: `src/trading_learning/dashboard/static/index.html`
  - Add the workstation shell, left navigation rail, top status strip, focused page sections, and collapsible AI Coach panel.
  - Keep existing ids for controls, charts, lists, and action buttons.
- Modify: `src/trading_learning/dashboard/static/styles.css`
  - Replace the light prototype dashboard styling with a professional dark research workstation system.
  - Add route page visibility, chart lab layout, page-specific responsive rules, and coach collapse states.
- Modify: `src/trading_learning/dashboard/static/app.js`
  - Add hash-route navigation, nav active state, coach content updates, coach collapse toggle, top status rendering, and safe page defaults.
  - Keep existing data loading, chart rendering, backtest actions, review actions, and comparison behavior.
- Modify: `tests/test_dashboard.py`
  - Add static shell markers and script behavior assertions for Phase 40.
  - Update the HTTP static page assertion to the new product name while preserving backward compatibility markers where useful.
- Modify: `task_plan.md`, `progress.md`, `findings.md`
  - Record Phase 40 implementation and verification results.

## Task 1: Add Static Shell Tests

- [ ] **Step 1: Add expected shell markers to `tests/test_dashboard.py`**

Add these markers to `test_dashboard_static_page_exposes_interactive_replay_controls`:

```python
'id="workstationShell"',
'id="pageToday"',
'id="pageChart"',
'id="pageData"',
'id="pageStrategy"',
'id="pageBacktests"',
'id="pageExperiments"',
'id="pageReview"',
'id="pageKnowledge"',
'id="pageTestnet"',
'id="pageSafety"',
'id="pageSettings"',
'id="coachPanel"',
'id="coachToggle"',
'id="coachTitle"',
'id="coachBody"',
'data-route="chart"',
'data-page="chart"',
```

Update the HTTP static page title assertion:

```python
assert "Bian Local Quant Workstation" in html
```

- [ ] **Step 2: Add expected script markers to `test_dashboard_static_script_uses_lightweight_charts_engine`**

Add these markers:

```python
"const routes =",
"function navigateTo",
"function setActiveRoute",
"function renderCoachPanel",
"function toggleCoach",
"function renderTopStatus",
"window.addEventListener(\"hashchange\"",
```

- [ ] **Step 3: Run the targeted tests and verify failure**

Run:

```powershell
pytest tests/test_dashboard.py::test_dashboard_static_page_exposes_interactive_replay_controls tests/test_dashboard.py::test_dashboard_static_script_uses_lightweight_charts_engine -q
```

Expected: failure because the new Phase 40 shell markers do not exist yet.

## Task 2: Implement Workstation HTML Shell

- [ ] **Step 1: Replace the top-level static page structure**

Update `index.html` so the body starts with:

```html
<div class="workstation-shell" id="workstationShell">
  <aside class="side-rail" id="appNav" aria-label="主导航">
    <div class="rail-brand">
      <strong>Bian</strong>
      <span>Local Quant</span>
    </div>
    <a href="#today" data-route="today">今日</a>
    <a href="#chart" data-route="chart">图表</a>
    <a href="#data" data-route="data">数据</a>
    <a href="#strategy" data-route="strategy">策略</a>
    <a href="#backtests" data-route="backtests">回测</a>
    <a href="#experiments" data-route="experiments">实验</a>
    <a href="#review" data-route="review">复盘</a>
    <a href="#knowledge" data-route="knowledge">知识</a>
    <a href="#testnet" data-route="testnet">测试网</a>
    <a href="#safety" data-route="safety">安全</a>
    <a href="#settings" data-route="settings">设置</a>
  </aside>
```

Keep all existing control ids inside route pages so existing JavaScript continues to work.

- [ ] **Step 2: Create focused page sections**

Wrap existing content into page sections with these ids and attributes:

```html
<section class="workspace-page today-page" id="pageToday" data-page="today">...</section>
<section class="workspace-page chart-page" id="pageChart" data-page="chart">...</section>
<section class="workspace-page data-page" id="pageData" data-page="data">...</section>
<section class="workspace-page strategy-page" id="pageStrategy" data-page="strategy">...</section>
<section class="workspace-page backtests-page" id="pageBacktests" data-page="backtests">...</section>
<section class="workspace-page experiments-page" id="pageExperiments" data-page="experiments">...</section>
<section class="workspace-page review-page" id="pageReview" data-page="review">...</section>
<section class="workspace-page knowledge-page" id="pageKnowledge" data-page="knowledge">...</section>
<section class="workspace-page testnet-page" id="pageTestnet" data-page="testnet">...</section>
<section class="workspace-page safety-page" id="pageSafety" data-page="safety">...</section>
<section class="workspace-page settings-page" id="pageSettings" data-page="settings">...</section>
```

- [ ] **Step 3: Add the AI Coach panel**

Add this panel beside the page workspace:

```html
<aside class="coach-panel" id="coachPanel">
  <div class="coach-header">
    <div>
      <span>AI Coach</span>
      <strong id="coachTitle">今日工作</strong>
    </div>
    <button id="coachToggle" type="button" aria-expanded="true">收起</button>
  </div>
  <div class="coach-body" id="coachBody"></div>
</aside>
```

## Task 3: Implement Shell Styling

- [ ] **Step 1: Replace the root theme with dark workstation tokens**

Use these variables in `styles.css`:

```css
:root {
  color-scheme: dark;
  --bg: #070b12;
  --surface: #0b121c;
  --panel: #101827;
  --panel-soft: #131d2b;
  --ink: #e5edf7;
  --muted: #94a3b8;
  --line: #243244;
  --accent: #4f8cff;
  --buy: #2dd4bf;
  --sell: #ef4444;
  --warn: #f59e0b;
}
```

- [ ] **Step 2: Add layout and route visibility CSS**

Add:

```css
.workstation-shell {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 86px minmax(0, 1fr) 340px;
  background: var(--bg);
}
.workspace-page { display: none; }
.workspace-page.active { display: block; }
.coach-panel.collapsed { display: none; }
```

- [ ] **Step 3: Add responsive behavior**

At `max-width: 1100px`, collapse the shell to one column, make nav horizontal, and let the coach panel move below the main page.

## Task 4: Implement Route And Coach JavaScript

- [ ] **Step 1: Add route metadata**

Add near the top of `app.js`:

```javascript
const routes = {
  today: { title: "今日工作", coach: "先检查数据、未复盘实验和下一步研究任务。" },
  chart: { title: "图表教练", coach: "在真实 K 线上切换周期、辅助线和交易点，先分析结构再看回测收益。" },
  data: { title: "数据教练", coach: "优先保证数据新鲜、完整、来源清楚，缺口数据先修复再回测。" },
  strategy: { title: "策略教练", coach: "每个策略都要写清假设、参数和失效条件。" },
  backtests: { title: "回测教练", coach: "关注回撤、交易质量、费用滑点和是否过拟合。" },
  experiments: { title: "实验教练", coach: "比较实验时先看稳定性，再决定继续、淘汰或进入测试网候选。" },
  review: { title: "复盘教练", coach: "重点复盘亏损交易、违反规则和策略失效条件。" },
  knowledge: { title: "学习教练", coach: "把重复错误沉淀成知识卡片和下次测试前的检查项。" },
  testnet: { title: "测试网教练", coach: "测试网只验证流程，不代表可以进入实盘。" },
  safety: { title: "安全教练", coach: "实盘默认关闭，任何执行都不能绕过门禁和 kill-switch。" },
  settings: { title: "设置教练", coach: "只显示配置状态，不打印密钥、token 或密码。" },
};
```

- [ ] **Step 2: Add navigation functions**

Implement:

```javascript
function currentRoute() {
  const route = window.location.hash.replace("#", "");
  return routes[route] ? route : "today";
}

function setActiveRoute(route) {
  document.querySelectorAll("[data-page]").forEach((page) => {
    page.classList.toggle("active", page.dataset.page === route);
  });
  document.querySelectorAll("[data-route]").forEach((link) => {
    link.classList.toggle("active", link.dataset.route === route);
  });
}

function renderCoachPanel(route) {
  const config = routes[route] || routes.today;
  document.querySelector("#coachTitle").textContent = config.title;
  document.querySelector("#coachBody").innerHTML = `<p>${escapeHtml(config.coach)}</p>`;
}

function navigateTo(route = currentRoute()) {
  setActiveRoute(route);
  renderCoachPanel(route);
  requestAnimationFrame(resizeCharts);
}
```

- [ ] **Step 3: Add top status and coach toggle**

Implement:

```javascript
function toggleCoach() {
  const panel = document.querySelector("#coachPanel");
  const collapsed = panel.classList.toggle("collapsed");
  const button = document.querySelector("#coachToggle");
  button.textContent = collapsed ? "展开" : "收起";
  button.setAttribute("aria-expanded", String(!collapsed));
  requestAnimationFrame(resizeCharts);
}

function renderTopStatus() {
  const gate = state.controlConsole?.production_gate || {};
  const status = gate.real_trading_enabled ? "实盘开启" : "实盘关闭";
  document.querySelector("#connectionStatus").textContent = text.online;
  document.querySelector("#topSafetyStatus").textContent = status;
}
```

- [ ] **Step 4: Wire events**

Add:

```javascript
window.addEventListener("hashchange", () => navigateTo());
document.querySelector("#coachToggle").addEventListener("click", toggleCoach);
```

Call `navigateTo()` after initial render in `boot()`.

## Task 5: Verify Phase 40

- [ ] **Step 1: Run targeted dashboard tests**

Run:

```powershell
pytest tests/test_dashboard.py tests/test_dashboard_actions.py -q
```

Expected: all selected tests pass.

- [ ] **Step 2: Run full test suite**

Run:

```powershell
pytest -q
```

Expected: all tests pass.

- [ ] **Step 3: Check dashboard JavaScript syntax**

Run:

```powershell
node --check src\trading_learning\dashboard\static\app.js
```

Expected: no output and exit code 0.

- [ ] **Step 4: Browser smoke**

Start the dashboard:

```powershell
trading-learning dashboard-serve --host 127.0.0.1 --port 8780
```

Verify:

- `/` loads.
- `#chart`, `#data`, `#backtests`, `#review`, and `#safety` switch pages.
- The chart container is present and no fake hand-drawn candles are used.
- Coach panel opens/closes.
- Mobile width does not overlap controls.

## Task 6: Update Planning And Commit

- [ ] **Step 1: Mark Phase 40 complete**

Update `task_plan.md` Phase 40 status and acceptance criteria when verification passes.

- [ ] **Step 2: Record progress and findings**

Update `progress.md` with verification outputs and `findings.md` with any UI implementation lessons.

- [ ] **Step 3: Commit**

Run:

```powershell
git add src/trading_learning/dashboard/static/index.html src/trading_learning/dashboard/static/styles.css src/trading_learning/dashboard/static/app.js tests/test_dashboard.py task_plan.md progress.md findings.md docs/superpowers/plans/2026-05-22-phase-40-workstation-ui.md
git commit -m "feat: add local quant workstation shell"
```
