const state = {
  overview: null,
  experiments: [],
  datasets: [],
  reviews: [],
  knowledge: [],
  controlConsole: null,
  paperStatus: null,
  paperHistory: [],
  paperEquityCurve: [],
  replay: null,
  report: null,
  reviewDraft: null,
  reportFilters: {
    side: "",
    result: "",
    start: "",
    end: "",
    risk: "",
  },
  comparison: null,
  chart: {
    klineChart: null,
    volumeChart: null,
    candleSeries: null,
    volumeSeries: null,
    ma20Series: null,
    ma60Series: null,
    equityChart: null,
    equitySeries: null,
    paperEquityChart: null,
    paperEquitySeries: null,
    paperBenchmarkSeries: null,
    markerApi: null,
    data: [],
    volumeData: [],
    ma20Data: [],
    ma60Data: [],
    visibleStart: 0,
    visibleCount: 120,
    playbackTimer: null,
    syncLock: false,
  },
};

const text = {
  reviewDays: "\u590d\u76d8\u5929\u6570",
  reviewTrades: "\u590d\u76d8\u4ea4\u6613",
  reviewPnl: "\u590d\u76d8\u76c8\u4e8f",
  planRate: "\u8ba1\u5212\u6267\u884c\u7387",
  experiments: "\u5b9e\u9a8c\u6570\u91cf",
  knowledge: "\u77e5\u8bc6\u5361\u7247",
  followed: "\u9075\u5b88\u8ba1\u5212",
  drifted: "\u504f\u79bb\u8ba1\u5212",
  pnl: "\u76c8\u4e8f",
  noLesson: "\u6682\u65e0\u6559\u8bad\u8bb0\u5f55",
  trades: "\u4ea4\u6613",
  winRate: "\u80dc\u7387",
  chooseReplay: "\u9009\u62e9\u4e00\u4e2a\u5b9e\u9a8c\u8f7d\u5165 K \u7ebf\u56de\u653e",
  chooseDataset: "\u9009\u62e9\u4e00\u4e2a\u5386\u53f2\u6570\u636e\u96c6\u8f7d\u5165 K \u7ebf",
  online: "\u672c\u5730\u5728\u7ebf",
  failed: "\u8bfb\u53d6\u5931\u8d25",
  noTrade: "\u6ca1\u6709\u9009\u4e2d\u4ea4\u6613",
  play: "\u64ad\u653e",
  pause: "\u6682\u505c",
  noReport: "\u9009\u62e9\u7b56\u7565\u5b9e\u9a8c\u540e\u663e\u793a\u56de\u6d4b\u62a5\u544a",
  noReview: "\u9009\u62e9\u7b56\u7565\u5b9e\u9a8c\u540e\u663e\u793a\u590d\u76d8\u8349\u7a3f",
  generatedReview: "\u672a\u4fdd\u5b58\u9884\u89c8",
  savedReview: "\u5df2\u4fdd\u5b58\u8349\u7a3f",
  noRiskFlags: "\u6682\u65e0\u98ce\u9669\u6807\u8bb0",
  noFocusTrades: "\u6682\u65e0\u91cd\u70b9\u4e8f\u635f\u4ea4\u6613",
  empty: "\u6682\u65e0\u8bb0\u5f55",
  noPaper: "\u6682\u65e0 paper trading \u6570\u636e\uff0c\u5148\u8fd0\u884c backfill \u6216 /paper-update",
};

const routes = {
  today: { title: "\u4eca\u65e5\u5de5\u4f5c", coach: "\u5148\u68c0\u67e5\u6570\u636e\u3001\u672a\u590d\u76d8\u5b9e\u9a8c\u548c\u4e0b\u4e00\u6b65\u7814\u7a76\u4efb\u52a1\u3002" },
  chart: { title: "\u56fe\u8868\u6559\u7ec3", coach: "\u5728\u771f\u5b9e K \u7ebf\u4e0a\u5207\u6362\u5468\u671f\u3001\u8f85\u52a9\u7ebf\u548c\u4ea4\u6613\u70b9\uff0c\u5148\u5206\u6790\u7ed3\u6784\u518d\u770b\u56de\u6d4b\u6536\u76ca\u3002" },
  data: { title: "\u6570\u636e\u6559\u7ec3", coach: "\u4f18\u5148\u4fdd\u8bc1\u6570\u636e\u65b0\u9c9c\u3001\u5b8c\u6574\u3001\u6765\u6e90\u6e05\u695a\uff0c\u7f3a\u53e3\u6570\u636e\u5148\u4fee\u590d\u518d\u56de\u6d4b\u3002" },
  strategy: { title: "\u7b56\u7565\u6559\u7ec3", coach: "\u6bcf\u4e2a\u7b56\u7565\u90fd\u8981\u5199\u6e05\u5047\u8bbe\u3001\u53c2\u6570\u548c\u5931\u6548\u6761\u4ef6\u3002" },
  paper: { title: "Paper Trading", coach: "\u68c0\u67e5\u7b56\u7565\u6743\u76ca\u3001\u4eca\u65e5 PnL\u3001\u76ee\u6807\u4ed3\u4f4d\u548c\u4fe1\u53f7\u662f\u5426\u4e00\u81f4\u3002" },
  backtests: { title: "\u56de\u6d4b\u6559\u7ec3", coach: "\u5173\u6ce8\u56de\u64a4\u3001\u4ea4\u6613\u8d28\u91cf\u3001\u8d39\u7528\u6ed1\u70b9\u548c\u662f\u5426\u8fc7\u62df\u5408\u3002" },
  experiments: { title: "\u5b9e\u9a8c\u6559\u7ec3", coach: "\u6bd4\u8f83\u5b9e\u9a8c\u65f6\u5148\u770b\u7a33\u5b9a\u6027\uff0c\u518d\u51b3\u5b9a\u7ee7\u7eed\u3001\u6dd8\u6c70\u6216\u8fdb\u5165\u6d4b\u8bd5\u7f51\u5019\u9009\u3002" },
  review: { title: "\u590d\u76d8\u6559\u7ec3", coach: "\u91cd\u70b9\u590d\u76d8\u4e8f\u635f\u4ea4\u6613\u3001\u8fdd\u53cd\u89c4\u5219\u548c\u7b56\u7565\u5931\u6548\u6761\u4ef6\u3002" },
  knowledge: { title: "\u5b66\u4e60\u6559\u7ec3", coach: "\u628a\u91cd\u590d\u9519\u8bef\u6c89\u6dc0\u6210\u77e5\u8bc6\u5361\u7247\u548c\u4e0b\u6b21\u6d4b\u8bd5\u524d\u7684\u68c0\u67e5\u9879\u3002" },
  testnet: { title: "\u6d4b\u8bd5\u7f51\u6559\u7ec3", coach: "\u6d4b\u8bd5\u7f51\u53ea\u9a8c\u8bc1\u6d41\u7a0b\uff0c\u4e0d\u4ee3\u8868\u53ef\u4ee5\u8fdb\u5165\u5b9e\u76d8\u3002" },
  safety: { title: "\u5b89\u5168\u6559\u7ec3", coach: "\u5b9e\u76d8\u9ed8\u8ba4\u5173\u95ed\uff0c\u4efb\u4f55\u6267\u884c\u90fd\u4e0d\u80fd\u7ed5\u8fc7\u95e8\u7981\u548c kill-switch\u3002" },
  settings: { title: "\u8bbe\u7f6e\u6559\u7ec3", coach: "\u53ea\u663e\u793a\u914d\u7f6e\u72b6\u6001\uff0c\u4e0d\u6253\u5370\u5bc6\u94a5\u3001token \u6216\u5bc6\u7801\u3002" },
};

const fmt = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });
const timeFmt = new Intl.DateTimeFormat("zh-CN", {
  month: "2-digit",
  day: "2-digit",
  hour: "2-digit",
  minute: "2-digit",
});

async function getJson(path) {
  const response = await fetch(path);
  return response.json();
}

async function postJson(path, body) {
  const response = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  return response.json();
}

function metric(label, value) {
  return `<div class="metric"><span>${label}</span><strong>${value}</strong></div>`;
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function toChartTime(value) {
  return Math.floor(new Date(value).getTime() / 1000);
}

function renderOverview() {
  const totals = state.overview.totals;
  const workspace = state.overview.workspace_state || {};
  document.querySelector("#metrics").innerHTML = [
    metric(text.reviewDays, totals.review_days),
    metric(text.reviewTrades, totals.review_trade_count),
    metric(text.reviewPnl, fmt.format(totals.review_pnl)),
    metric(text.planRate, `${fmt.format(totals.plan_follow_rate * 100)}%`),
    metric(text.experiments, totals.experiment_count),
    metric(text.knowledge, totals.knowledge_count),
  ].join("");
  renderEmptyState(workspace);
}

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
  const dailyPlan = state.controlConsole?.coach?.daily_plan;
  const planHtml =
    route === "today" && dailyPlan
      ? `<div class="coach-card"><strong>${escapeHtml(dailyPlan.stage || "AI Coach")}</strong><p>${escapeHtml(dailyPlan.summary || "")}</p></div>`
      : "";
  document.querySelector("#coachTitle").textContent = config.title;
  document.querySelector("#coachBody").innerHTML = `
    <div class="coach-card">
      <strong>${escapeHtml(config.title)}</strong>
      <p>${escapeHtml(config.coach)}</p>
    </div>
    ${planHtml}
  `;
}

function navigateTo(route = currentRoute()) {
  setActiveRoute(route);
  renderCoachPanel(route);
  requestAnimationFrame(resizeCharts);
}

function toggleCoach() {
  const panel = document.querySelector("#coachPanel");
  const collapsed = panel.classList.toggle("collapsed");
  const button = document.querySelector("#coachToggle");
  button.textContent = collapsed ? "\u5c55\u5f00" : "\u6536\u8d77";
  button.setAttribute("aria-expanded", String(!collapsed));
  requestAnimationFrame(resizeCharts);
}

function renderTopStatus() {
  const gate = state.controlConsole?.production_gate || {};
  const safetyText = gate.real_trading_enabled ? "\u5b9e\u76d8\u5f00\u542f" : "\u5b9e\u76d8\u5173\u95ed";
  document.querySelector("#connectionStatus").textContent = text.online;
  document.querySelector("#topSafetyStatus").textContent = safetyText;
}

function renderEmptyState(workspace) {
  const panel = document.querySelector("#emptyStatePanel");
  if (!workspace || workspace.status !== "empty") {
    panel.innerHTML = "";
    panel.hidden = true;
    return;
  }
  panel.hidden = false;
  panel.innerHTML = `
    <strong>\u5f53\u524d\u662f\u5e72\u51c0\u5de5\u4f5c\u533a</strong>
    <p>\u8fd8\u6ca1\u6709\u771f\u5b9e\u590d\u76d8\u3001\u56de\u6d4b\u5b9e\u9a8c\u6216\u77e5\u8bc6\u5361\u3002\u5148\u5237\u65b0\u516c\u5171\u884c\u60c5\uff0c\u518d\u8fd0\u884c\u7b2c\u4e00\u4e2a\u57fa\u7ebf\u56de\u6d4b\u3002</p>
    <ol>${(workspace.next_steps || []).map((step) => `<li><code>${escapeHtml(step.command)}</code></li>`).join("")}</ol>
  `;
}

function renderReviews() {
  document.querySelector("#reviewList").innerHTML = state.reviews
    .map(
      (review) => `
        <article class="item">
          <span>${escapeHtml(review.review_date)} &middot; ${escapeHtml(review.symbols_watched.join(", "))}</span>
          <strong>${review.plan_followed ? text.followed : text.drifted} &middot; ${text.pnl} ${fmt.format(review.pnl)}</strong>
          <p>${escapeHtml(review.lesson || text.noLesson)}</p>
        </article>
      `,
    )
    .join("");
}

function renderExperiments() {
  const select = document.querySelector("#experimentSelect");
  select.innerHTML = state.experiments
    .map((experiment) => `<option value="${escapeHtml(experiment.external_id)}">${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)} &middot; ${escapeHtml(experiment.external_id)}</option>`)
    .join("");
  document.querySelector("#comparisonSelect").innerHTML = state.experiments
    .map((experiment) => `<option value="${escapeHtml(experiment.external_id)}">${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)} &middot; ${escapeHtml(experiment.external_id)}</option>`)
    .join("");
  document.querySelector("#experimentList").innerHTML = state.experiments
    .map(
      (experiment) => `
        <article class="item">
          <span>${escapeHtml(experiment.strategy_name)} &middot; ${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)}</span>
          <strong>${escapeHtml(experiment.external_id)}</strong>
          <p>${text.trades} ${experiment.metrics.trade_count ?? 0} &middot; ${text.winRate} ${fmt.format((experiment.metrics.win_rate ?? 0) * 100)}% &middot; ${text.pnl} ${fmt.format(experiment.metrics.realized_pnl ?? 0)}</p>
        </article>
      `,
    )
    .join("");
}

function renderDatasets() {
  const select = document.querySelector("#datasetSelect");
  const cachedDatasets = state.datasets.filter((dataset) => dataset.exists);
  if (!cachedDatasets.length) {
    select.innerHTML = `<option value="">\u6682\u65e0\u672c\u5730\u6570\u636e</option>`;
    document.querySelector("#datasetList").innerHTML = state.datasets
      .map(
        (dataset) => `
        <article class="item muted-item">
          <span>${escapeHtml(dataset.symbol)} &middot; ${escapeHtml(dataset.interval)} &middot; ${escapeHtml(dataset.source)}</span>
          <strong>${escapeHtml(dataset.path)}</strong>
          <p>\u672a\u7f13\u5b58\uff1a\u4f7f\u7528 /market-refresh \u6216 refresh-market-data \u5237\u65b0</p>
        </article>
      `,
      )
      .join("");
    return;
  }
  select.innerHTML = cachedDatasets
    .map((dataset) => {
      const value = `${dataset.symbol}|${dataset.path}`;
      return `<option value="${escapeHtml(value)}">${escapeHtml(dataset.symbol)} ${escapeHtml(dataset.interval)} &middot; ${dataset.row_count} bars</option>`;
    })
    .join("");
  document.querySelector("#datasetList").innerHTML = state.datasets
    .map(
      (dataset) => `
        <article class="item">
          <span>${escapeHtml(dataset.symbol)} &middot; ${escapeHtml(dataset.interval)} &middot; ${dataset.exists ? `${dataset.row_count} bars` : "\u672a\u7f13\u5b58"}</span>
          <strong>${escapeHtml(dataset.path)}</strong>
          <p>${escapeHtml(dataset.first_opened_at || "-")} \u2192 ${escapeHtml(dataset.last_opened_at || "-")} &middot; gaps=${dataset.gap_count ?? 0} &middot; next=${escapeHtml(dataset.next_expected_opened_at || "-")} &middot; ${escapeHtml(dataset.source || "-")}</p>
        </article>
      `,
    )
    .join("");
}

function renderKnowledge() {
  document.querySelector("#knowledgeList").innerHTML = state.knowledge
    .map(
      (card) => `
        <article class="item">
          <span>${escapeHtml(card.category)} &middot; ${escapeHtml(card.tags.join(", "))}</span>
          <strong>${escapeHtml(card.title)}</strong>
          <p>${escapeHtml(card.content)}</p>
        </article>
      `,
    )
    .join("");
}

function renderControlConsole() {
  const data = state.controlConsole;
  if (!data) return;
  const counts = data.health?.counts || {};
  const paper = data.paper_trading || {};
  document.querySelector("#consoleMetrics").innerHTML = [
    metric("\u26412\u5730\u5065\u5eb7", data.health?.status || "-"),
    metric("\u961f\u5217\u4efb\u52a1", data.tasks?.length ?? 0),
    metric("AI Coach", data.coach?.proposals?.length ?? 0),
    metric("\u7b56\u7565 Profile", data.strategy_lab?.profiles?.length ?? 0),
    metric("\u53c2\u6570\u626b\u63cf", data.strategy_lab?.sweeps?.length ?? 0),
    metric("Paper", paper.status === "ok" ? `${fmt.format(paper.cumulative_return_pct || 0)}%` : "-"),
  ].join("");
  renderWorkspaceStatus(data.workspace_state || {});
  renderDailyCoachPlan(data.coach?.daily_plan || null);
  renderReviewQueue(data.coach?.review_queue || []);
  renderTaskQueue(data.tasks || []);
  renderCoachProposals(data.coach?.proposals || []);
  renderStrategyLab(data.strategy_lab || {});
  renderTestnetOrders(data.testnet?.orders || []);
  renderPaperConsoleSummary(data.paper_trading || null);
  renderProductionGate(data.production_gate || {});
  renderReferenceList(data.references || []);
  renderTopStatus();
  renderCoachPanel(currentRoute());
}

function signedClass(value) {
  const number = Number(value || 0);
  if (number > 0) return "positive";
  if (number < 0) return "negative";
  return "";
}

function renderPaperTrading() {
  renderPaperStatus(state.paperStatus);
  renderPaperSignals(state.paperStatus);
  renderPaperEquityCurve(state.paperEquityCurve);
  renderPaperHistoryTable(state.paperHistory);
}

function renderPaperStatus(status) {
  const target = document.querySelector("#paperStatusMetrics");
  if (!target) return;
  if (!status || status.status !== "ok") {
    target.innerHTML = metric("Paper Trading", status?.message || text.noPaper);
    return;
  }
  target.innerHTML = [
    metric("\u5f53\u524d\u6743\u76ca", fmt.format(status.equity || 0)),
    metric("\u7d2f\u8ba1\u6536\u76ca\u7387", `<span class="${signedClass(status.cumulative_return_pct)}">${fmt.format(status.cumulative_return_pct || 0)}%</span>`),
    metric("\u4eca\u65e5 PnL", `<span class="${signedClass(status.daily_pnl)}">${fmt.format(status.daily_pnl || 0)}%</span>`),
    metric("\u5f53\u524d\u4ed3\u4f4d", fmt.format(status.target_position || 0)),
  ].join("");
}

function renderPaperSignals(status) {
  const target = document.querySelector("#paperSignals");
  if (!target) return;
  if (!status || status.status !== "ok") {
    target.innerHTML = `<p class="empty-note">${text.noPaper}</p>`;
    return;
  }
  const signals = status.signals || {};
  const rows = [
    ["FAST", signals.trend_fast],
    ["MOM", signals.momentum],
    ["MR", signals.mean_rev],
    ["VOL", signals.vol_regime],
    ["Combined", signals.combined],
  ];
  target.innerHTML = rows
    .map(([label, value]) => {
      const number = Math.max(-2, Math.min(2, Number(value || 0)));
      const width = Math.abs(number) / 2 * 50;
      const side = number >= 0 ? "right" : "left";
      return `
        <div class="signal-row">
          <span>${escapeHtml(label)}</span>
          <div class="signal-track"><i class="${side}" style="width:${width}%"></i></div>
          <strong class="${signedClass(number)}">${fmt.format(number)}</strong>
        </div>
      `;
    })
    .join("");
}

function renderPaperEquityCurve(curve) {
  if (!state.chart.paperEquitySeries || !state.chart.paperBenchmarkSeries) return;
  const data = curve || [];
  state.chart.paperEquitySeries.setData(
    data.filter((point) => point.date).map((point) => ({ time: point.date, value: point.equity })),
  );
  state.chart.paperBenchmarkSeries.setData(
    data
      .filter((point) => point.date && point.benchmark_equity)
      .map((point) => ({ time: point.date, value: point.benchmark_equity })),
  );
}

function renderPaperHistoryTable(history) {
  const table = document.querySelector("#paperHistoryTable");
  if (!table) return;
  const rows = history || [];
  table.innerHTML = `
    <thead><tr><th>\u65e5\u671f</th><th>PnL</th><th>\u4ed3\u4f4d</th><th>\u4fe1\u53f7</th></tr></thead>
    <tbody>
      ${
        rows.length
          ? rows
              .map(
                (row) => `
                  <tr>
                    <td>${escapeHtml(row.date)}</td>
                    <td class="${signedClass(row.daily_pnl)}">${fmt.format(row.daily_pnl || 0)}%</td>
                    <td>${fmt.format(row.target_position || 0)}</td>
                    <td>F ${fmt.format(row.signals?.trend_fast || 0)} / M ${fmt.format(row.signals?.momentum || 0)} / MR ${fmt.format(row.signals?.mean_rev || 0)} / V ${fmt.format(row.signals?.vol_regime || 0)}</td>
                  </tr>
                `,
              )
              .join("")
          : `<tr><td colspan="4">${text.noPaper}</td></tr>`
      }
    </tbody>
  `;
}

function renderPaperConsoleSummary(status) {
  const box = document.querySelector("#paperConsoleSummary");
  if (!box) return;
  if (!status || status.status !== "ok") {
    box.textContent = status?.message || text.noPaper;
    return;
  }
  box.innerHTML = `
    <strong>${escapeHtml(status.date)} &middot; ${fmt.format(status.equity || 0)}</strong>
    <span>\u7d2f\u8ba1 ${fmt.format(status.cumulative_return_pct || 0)}% / \u4eca\u65e5 ${fmt.format(status.daily_pnl || 0)}%</span>
    <span>\u4ed3\u4f4d ${fmt.format(status.target_position || 0)} / Combined ${fmt.format(status.signals?.combined || 0)}</span>
  `;
}

function renderWorkspaceStatus(workspace) {
  document.querySelector("#workspaceStatus").innerHTML = `
    <strong>\u5de5\u4f5c\u533a: ${escapeHtml(workspace.status || "-")}</strong>
    <span>\u590d\u76d8 ${workspace.counts?.daily_reviews ?? 0} / \u5b9e\u9a8c ${workspace.counts?.strategy_experiments ?? 0} / \u77e5\u8bc6 ${workspace.counts?.knowledge_cards ?? 0}</span>
  `;
}

function renderDailyCoachPlan(plan) {
  const box = document.querySelector("#dailyCoachPlan");
  if (!plan) {
    box.textContent = text.empty;
    return;
  }
  box.innerHTML = `
    <strong>AI Coach: ${escapeHtml(plan.stage || "-")}</strong>
    <p>${escapeHtml(plan.summary || "")}</p>
    <ol>${(plan.actions || []).map((action) => `<li>${escapeHtml(action.title)} <code>${escapeHtml(action.command)}</code></li>`).join("")}</ol>
  `;
}

function renderReviewQueue(queue) {
  const target = document.querySelector("#reviewQueueList");
  if (!target) return;
  target.innerHTML = queue.length
    ? queue
        .map(
          (item) => `
            <article class="item">
              <span>${escapeHtml(item.reason || "\u590d\u4e60")} &middot; ${escapeHtml((item.tags || []).join(", "))}</span>
              <strong>${escapeHtml(item.title || item.card_external_id)}</strong>
              <p>\u4f18\u5148\u7ea7 ${escapeHtml(item.importance ?? "-")} &middot; ${escapeHtml(item.category || "-")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
}

function renderTaskQueue(tasks) {
  document.querySelector("#taskQueueList").innerHTML = tasks.length
    ? tasks
        .map(
          (task) => `
            <article class="item">
              <span>${escapeHtml(task.task_type)} &middot; ${escapeHtml(task.state)} &middot; ${escapeHtml(task.risk_level)}</span>
              <strong>${escapeHtml(task.external_id)}</strong>
              <p>${escapeHtml(task.result_summary || task.command_text || "-")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
}

function renderCoachProposals(proposals) {
  document.querySelector("#coachProposalList").innerHTML = proposals.length
    ? proposals
        .map(
          (proposal) => `
            <article class="item">
              <span>${escapeHtml(proposal.status)} &middot; ${escapeHtml(proposal.source_experiment_external_id || "\u57fa\u7ebf")}</span>
              <strong>${escapeHtml(proposal.hypothesis?.title || proposal.external_id)}</strong>
              <p>${escapeHtml(proposal.suggested_command || "-")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
}

function renderStrategyLab(strategyLab) {
  const profiles = strategyLab.profiles || [];
  const sweeps = strategyLab.sweeps || [];
  const decisions = strategyLab.decisions || [];
  document.querySelector("#strategyProfileList").innerHTML = profiles.length
    ? profiles
        .map(
          (profile) => `
            <article class="item">
              <span>${escapeHtml(profile.symbol)} ${escapeHtml(profile.interval)} &middot; ${escapeHtml(profile.strategy_name)}</span>
              <strong>${escapeHtml(profile.name)}</strong>
              <p>${escapeHtml(JSON.stringify(profile.parameters || {}))}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
  document.querySelector("#sweepList").innerHTML = sweeps.length
    ? sweeps
        .map(
          (sweep) => `
            <article class="item">
              <span>${escapeHtml(sweep.symbol)} ${escapeHtml(sweep.interval)} &middot; ${sweep.run_count} runs</span>
              <strong>${escapeHtml(sweep.best_experiment || sweep.external_id)}</strong>
              <p>${escapeHtml(sweep.overfitting_warning || "-")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
  const decisionTarget = document.querySelector("#experimentDecisionList");
  if (decisionTarget) {
    decisionTarget.innerHTML = decisions.length
      ? decisions
          .map(
            (decision) => `
              <article class="item">
                <span>${escapeHtml(decision.decision)} &middot; ${escapeHtml(decision.updated_at || "-")}</span>
                <strong>${escapeHtml(decision.experiment_external_id)}</strong>
                <p>${escapeHtml(decision.reason || "-")}</p>
              </article>
            `,
          )
          .join("")
      : `<p class="empty-note">${text.empty}</p>`;
  }
}

function renderTestnetOrders(orders) {
  document.querySelector("#testnetOrderList").innerHTML = orders.length
    ? orders
        .map(
          (order) => `
            <article class="item">
              <span>${escapeHtml(order.action)} &middot; ${escapeHtml(order.status || "-")}</span>
              <strong>${escapeHtml(order.symbol)} ${escapeHtml(order.side)} ${escapeHtml(order.order_type)}</strong>
              <p>order_id=${escapeHtml(order.order_id || "-")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
}

function renderProductionGate(gate) {
  const missing = gate.missing || [];
  document.querySelector("#productionGatePanel").innerHTML = `
    <strong>${gate.real_trading_enabled ? "\u5b9e\u76d8\u5df2\u542f\u7528" : "\u5b9e\u76d8\u7981\u7528"}</strong>
    <span>kill_switch=${gate.kill_switch_active ? "on" : "off"}</span>
    <p>${escapeHtml(gate.message || "")}</p>
    <p>${missing.length ? escapeHtml(missing.join(", ")) : "\u65e0\u7f3a\u5931\u9879"}</p>
  `;
}

function renderReferenceList(references) {
  const target = document.querySelector("#referenceList");
  if (!target) return;
  target.innerHTML = references.length
    ? references
        .map(
          (reference) => `
            <article class="item">
              <span>${escapeHtml(reference.role || "\u53c2\u8003")}</span>
              <strong>${escapeHtml(reference.project || "-")}</strong>
              <p>${escapeHtml(reference.lesson || reference.note || "")}</p>
            </article>
          `,
        )
        .join("")
    : `<p class="empty-note">${text.empty}</p>`;
}

function createCharts() {
  const chartOptions = {
    layout: { background: { color: "#05080d" }, textColor: "#94a3b8", fontSize: 12 },
    grid: { vertLines: { color: "#111827" }, horzLines: { color: "#111827" } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#243244" },
    rightPriceScale: { borderColor: "#243244" },
    handleScroll: { mouseWheel: true, pressedMouseMove: true, horzTouchDrag: true, vertTouchDrag: false },
    handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
  };
  const volumeOptions = {
    ...chartOptions,
    height: 120,
    rightPriceScale: { visible: false },
    leftPriceScale: { visible: false },
  };
  state.chart.klineChart = LightweightCharts.createChart(document.querySelector("#klineChart"), chartOptions);
  state.chart.volumeChart = LightweightCharts.createChart(document.querySelector("#volumeChart"), volumeOptions);
  state.chart.candleSeries = state.chart.klineChart.addSeries(LightweightCharts.CandlestickSeries, {
    upColor: "#2dd4bf",
    downColor: "#ef4444",
    borderUpColor: "#2dd4bf",
    borderDownColor: "#ef4444",
    wickUpColor: "#2dd4bf",
    wickDownColor: "#ef4444",
  });
  state.chart.volumeSeries = state.chart.volumeChart.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "volume" },
    priceScaleId: "",
  });
  state.chart.ma20Series = state.chart.klineChart.addSeries(LightweightCharts.LineSeries, {
    color: "#60a5fa",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  state.chart.ma60Series = state.chart.klineChart.addSeries(LightweightCharts.LineSeries, {
    color: "#facc15",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  state.chart.equityChart = LightweightCharts.createChart(document.querySelector("#equityChart"), {
    layout: { background: { color: "#05080d" }, textColor: "#94a3b8", fontSize: 12 },
    grid: { vertLines: { color: "#111827" }, horzLines: { color: "#111827" } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#243244" },
    rightPriceScale: { borderColor: "#243244" },
  });
  state.chart.equitySeries = state.chart.equityChart.addSeries(LightweightCharts.LineSeries, {
    color: "#4f8cff",
    lineWidth: 2,
    priceLineVisible: false,
  });
  const paperChartTarget = document.querySelector("#paperEquityChart");
  if (paperChartTarget) {
    state.chart.paperEquityChart = LightweightCharts.createChart(paperChartTarget, {
      layout: { background: { color: "#05080d" }, textColor: "#94a3b8", fontSize: 12 },
      grid: { vertLines: { color: "#111827" }, horzLines: { color: "#111827" } },
      timeScale: { timeVisible: false, secondsVisible: false, borderColor: "#243244" },
      rightPriceScale: { borderColor: "#243244" },
    });
    state.chart.paperEquitySeries = state.chart.paperEquityChart.addSeries(LightweightCharts.LineSeries, {
      color: "#2dd4bf",
      lineWidth: 2,
      priceLineVisible: false,
    });
    state.chart.paperBenchmarkSeries = state.chart.paperEquityChart.addSeries(LightweightCharts.LineSeries, {
      color: "#f59e0b",
      lineWidth: 2,
      priceLineVisible: false,
    });
  }
  state.chart.markerApi = LightweightCharts.createSeriesMarkers(state.chart.candleSeries, []);
  state.chart.klineChart.subscribeCrosshairMove(updateCrosshairPanel);
  state.chart.klineChart.subscribeClick(selectNearestTradeByClick);
  state.chart.klineChart.timeScale().subscribeVisibleLogicalRangeChange((range) => {
    if (!range || state.chart.syncLock) return;
    state.chart.syncLock = true;
    state.chart.volumeChart.timeScale().setVisibleLogicalRange(range);
    state.chart.syncLock = false;
    state.chart.visibleStart = Math.max(0, Math.floor(range.from));
    state.chart.visibleCount = Math.max(1, Math.ceil(range.to - range.from));
    syncRange();
  });
  window.addEventListener("resize", resizeCharts);
  resizeCharts();
}

function resizeCharts() {
  const kline = document.querySelector("#klineChart");
  const volume = document.querySelector("#volumeChart");
  const equity = document.querySelector("#equityChart");
  if (!state.chart.klineChart || !state.chart.volumeChart) return;
  state.chart.klineChart.applyOptions({ width: kline.clientWidth, height: kline.clientHeight });
  state.chart.volumeChart.applyOptions({ width: volume.clientWidth, height: volume.clientHeight });
  state.chart.equityChart.applyOptions({ width: equity.clientWidth, height: equity.clientHeight });
  const paperEquity = document.querySelector("#paperEquityChart");
  if (state.chart.paperEquityChart && paperEquity) {
    state.chart.paperEquityChart.applyOptions({ width: paperEquity.clientWidth, height: paperEquity.clientHeight });
  }
}

function movingAverage(candles, windowSize) {
  return candles
    .map((_, index) => {
      if (index + 1 < windowSize) return null;
      const slice = candles.slice(index + 1 - windowSize, index + 1);
      return {
        time: toChartTime(candles[index].opened_at),
        value: slice.reduce((sum, candle) => sum + candle.close, 0) / windowSize,
      };
    })
    .filter(Boolean);
}

function chartDataFromReplay(replay) {
  const candles = replay.candles || [];
  return {
    candleData: candles.map((candle) => ({
      time: toChartTime(candle.opened_at),
      open: candle.open,
      high: candle.high,
      low: candle.low,
      close: candle.close,
    })),
    volumeData: candles.map((candle) => ({
      time: toChartTime(candle.opened_at),
      value: candle.volume,
      color: candle.close >= candle.open ? "rgba(45,212,191,0.45)" : "rgba(239,68,68,0.45)",
    })),
    ma20Data: movingAverage(candles, 20),
    ma60Data: movingAverage(candles, 60),
  };
}

function clearChartData() {
  state.chart.data = [];
  state.chart.volumeData = [];
  state.chart.ma20Data = [];
  state.chart.ma60Data = [];
  state.chart.candleSeries.setData([]);
  state.chart.volumeSeries.setData([]);
  state.chart.ma20Series.setData([]);
  state.chart.ma60Series.setData([]);
  state.chart.markerApi.setMarkers([]);
  syncRange();
}

function renderKline() {
  if (!state.replay || state.replay.status !== "ok") {
    clearChartData();
    setOhlcMessage(state.replay?.message || text.chooseReplay);
    updateTradeDetail(null);
    return;
  }
  if (!state.replay || !state.replay.candles || !state.replay.candles.length) {
    clearChartData();
    setOhlcMessage(text.chooseReplay);
    updateTradeDetail(null);
    return;
  }
  const data = chartDataFromReplay(state.replay);
  state.chart.data = data.candleData;
  state.chart.volumeData = data.volumeData;
  state.chart.ma20Data = data.ma20Data;
  state.chart.ma60Data = data.ma60Data;
  state.chart.candleSeries.setData(data.candleData);
  state.chart.volumeSeries.setData(data.volumeData);
  renderIndicators();
  state.chart.markerApi.setMarkers(tradeMarkers());
  updateTradeDetail(null);
  const count = data.candleData.length;
  state.chart.visibleCount = Math.min(160, Math.max(30, count));
  state.chart.visibleStart = Math.max(0, count - state.chart.visibleCount);
  applyVisibleRange();
  syncRange();
  updateOhlcPanel(state.replay.candles[state.replay.candles.length - 1]);
}

function renderIndicators() {
  state.chart.ma20Series.setData(document.querySelector("#toggleMa20").checked ? state.chart.ma20Data : []);
  state.chart.ma60Series.setData(document.querySelector("#toggleMa60").checked ? state.chart.ma60Data : []);
}

function tradeMarkers() {
  return (state.replay?.trades || []).map((trade) => ({
    time: toChartTime(trade.timestamp),
    position: trade.side === "BUY" ? "belowBar" : "aboveBar",
    color: trade.side === "BUY" ? "#0f8b5f" : "#b42318",
    shape: trade.side === "BUY" ? "arrowUp" : "arrowDown",
    text: trade.side,
    id: trade.external_id,
  }));
}

function updateCrosshairPanel(param) {
  if (!param || !param.time || !state.replay) return;
  const candle = state.replay.candles.find((item) => toChartTime(item.opened_at) === param.time);
  updateOhlcPanel(candle || null);
}

function updateOhlcPanel(candle) {
  if (!candle) {
    setOhlcMessage(text.chooseReplay);
    return;
  }
  const panel = document.querySelector("#ohlcPanel");
  const change = candle.close - candle.open;
  const changePct = candle.open ? (change / candle.open) * 100 : 0;
  panel.innerHTML = `
    <strong>${timeFmt.format(new Date(candle.opened_at))}</strong>
    <span>O ${fmt.format(candle.open)} / H ${fmt.format(candle.high)} / L ${fmt.format(candle.low)} / C ${fmt.format(candle.close)}</span>
    <span>${text.pnl} ${fmt.format(change)} (${fmt.format(changePct)}%)</span>
    <span>VOL ${fmt.format(candle.volume)}</span>
  `;
}

function setOhlcMessage(message) {
  document.querySelector("#ohlcPanel").textContent = message;
}

function updateTradeDetail(trade) {
  const panel = document.querySelector("#tradeDetail");
  if (!trade) {
    panel.textContent = text.noTrade;
    return;
  }
  panel.innerHTML = `
    <strong>${escapeHtml(trade.side)} ${escapeHtml(trade.symbol)}</strong>
    <span>${escapeHtml(trade.timestamp)} @ ${fmt.format(trade.price)}</span>
    <span>QTY ${fmt.format(trade.quantity)} / FEE ${fmt.format(trade.fee)}</span>
    <span>${escapeHtml(trade.reason || "")}</span>
  `;
}

function renderBacktestReport(report) {
  state.report = report;
  const metricsBox = document.querySelector("#reportMetrics");
  const table = document.querySelector("#tradeTable");
  if (!report || report.status !== "ok") {
    metricsBox.innerHTML = metric("\u56de\u6d4b\u62a5\u544a", text.noReport);
    table.innerHTML = "";
    renderTradeFilters(null);
    state.chart.equitySeries.setData([]);
    return;
  }
  const metrics = report.metrics;
  metricsBox.innerHTML = [
    metric("\u4ea4\u6613", metrics.trade_count),
    metric("\u56de\u5408", metrics.round_trips),
    metric("\u80dc\u7387", `${fmt.format((metrics.win_rate || 0) * 100)}%`),
    metric("\u76c8\u4e8f", fmt.format(metrics.realized_pnl || 0)),
    metric("\u6700\u5927\u56de\u64a4", fmt.format(metrics.max_drawdown || 0)),
    metric("\u624b\u7eed\u8d39", fmt.format(metrics.total_fees || 0)),
  ].join("");
  state.chart.equitySeries.setData(
    (report.equity_curve || [])
      .filter((point) => point.time)
      .map((point) => ({ time: toChartTime(point.time), value: point.equity })),
  );
  renderTradeFilters(report.filter_options || {});
  renderTradeTable();
}

function renderTradeFilters(options) {
  const side = document.querySelector("#tradeSideFilter");
  const result = document.querySelector("#tradeResultFilter");
  const risk = document.querySelector("#tradeRiskFilter");
  const start = document.querySelector("#tradeStartFilter");
  const end = document.querySelector("#tradeEndFilter");
  const sides = options?.sides || [];
  const results = options?.results || [];
  const risks = options?.risk_flags || [];
  side.innerHTML = [`<option value="">\u5168\u90e8</option>`, ...sides.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)].join("");
  result.innerHTML = [
    `<option value="">\u5168\u90e8</option>`,
    ...results.map((item) => `<option value="${escapeHtml(item)}">${item === "win" ? "\u76c8\u5229" : item === "loss" ? "\u4e8f\u635f" : "\u6301\u4ed3"}</option>`),
  ].join("");
  risk.innerHTML = [`<option value="">\u5168\u90e8</option>`, ...risks.map((item) => `<option value="${escapeHtml(item)}">${escapeHtml(item)}</option>`)].join("");
  start.min = options?.start_time ? options.start_time.slice(0, 10) : "";
  start.max = options?.end_time ? options.end_time.slice(0, 10) : "";
  end.min = start.min;
  end.max = start.max;
  side.value = state.reportFilters.side;
  result.value = state.reportFilters.result;
  risk.value = state.reportFilters.risk;
  start.value = state.reportFilters.start;
  end.value = state.reportFilters.end;
}

function filteredReportTrades() {
  const trades = state.report?.trades || [];
  const riskOptions = state.report?.filter_options?.risk_flags || [];
  if (state.reportFilters.risk && !riskOptions.includes(state.reportFilters.risk)) {
    return [];
  }
  return trades.filter((trade) => {
    const tradeDate = String(trade.timestamp || "").slice(0, 10);
    if (state.reportFilters.side && trade.side !== state.reportFilters.side) return false;
    if (state.reportFilters.result && trade.round_trip_result !== state.reportFilters.result) return false;
    if (state.reportFilters.start && tradeDate < state.reportFilters.start) return false;
    if (state.reportFilters.end && tradeDate > state.reportFilters.end) return false;
    return true;
  });
}

function renderTradeTable() {
  const table = document.querySelector("#tradeTable");
  if (!state.report || state.report.status !== "ok") {
    table.innerHTML = "";
    return;
  }
  const trades = filteredReportTrades();
  table.innerHTML = `
    <thead>
      <tr><th>\u65b9\u5411</th><th>\u7ed3\u679c</th><th>\u65f6\u95f4</th><th>\u4ef7\u683c</th><th>PNL</th><th>\u64cd\u4f5c</th></tr>
    </thead>
    <tbody>
      ${trades.length ? trades
        .map(
          (trade) => `
            <tr>
              <td>${escapeHtml(trade.side)}</td>
              <td>${escapeHtml(trade.round_trip_result || "-")}</td>
              <td>${escapeHtml(trade.timestamp)}</td>
              <td>${fmt.format(trade.price)}</td>
              <td>${fmt.format(trade.round_trip_pnl || 0)}</td>
              <td><button type="button" data-trade-id="${escapeHtml(trade.external_id)}">\u5b9a\u4f4d</button></td>
            </tr>
          `,
        )
        .join("") : `<tr><td colspan="6">\u6ca1\u6709\u7b26\u5408\u6761\u4ef6\u7684\u4ea4\u6613</td></tr>`}
    </tbody>
  `;
  table.querySelectorAll("button[data-trade-id]").forEach((button) => {
    button.addEventListener("click", () => focusTrade(button.dataset.tradeId));
  });
}

async function loadExperimentComparison() {
  const selected = Array.from(document.querySelector("#comparisonSelect").selectedOptions).map((option) => option.value);
  const ids = selected.length ? selected : state.experiments.slice(0, 2).map((experiment) => experiment.external_id);
  const comparison = await getJson(`/api/experiment-comparison?experiments=${encodeURIComponent(ids.join(","))}`);
  renderExperimentComparison(comparison);
}

function renderExperimentComparison(comparison) {
  state.comparison = comparison;
  const table = document.querySelector("#comparisonTable");
  if (!comparison || comparison.status !== "ok" || !comparison.experiments.length) {
    table.innerHTML = `<tbody><tr><td>\u9009\u62e9\u81f3\u5c11\u4e00\u4e2a\u5b9e\u9a8c\u8fdb\u884c\u5bf9\u6bd4</td></tr></tbody>`;
    return;
  }
  const metricKeys = comparison.metric_keys || [];
  const parameterKeys = comparison.parameter_keys || [];
  table.innerHTML = `
    <thead>
      <tr>
        <th>\u5b9e\u9a8c</th><th>\u6807\u7684</th>
        ${metricKeys.map((key) => `<th>${escapeHtml(key)}</th>`).join("")}
        ${parameterKeys.map((key) => `<th>${escapeHtml(key)}</th>`).join("")}
      </tr>
    </thead>
    <tbody>
      ${comparison.experiments
        .map(
          (experiment) => `
            <tr>
              <td>${escapeHtml(experiment.external_id)}</td>
              <td>${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)}</td>
              ${metricKeys.map((key) => `<td>${escapeHtml(experiment.metrics[key] ?? "-")}</td>`).join("")}
              ${parameterKeys.map((key) => `<td>${escapeHtml(experiment.parameters[key] ?? "-")}</td>`).join("")}
            </tr>
          `,
        )
        .join("")}
    </tbody>
  `;
}

function renderExperimentReview(review) {
  state.reviewDraft = review;
  const status = document.querySelector("#experimentReviewStatus");
  const summary = document.querySelector("#reviewSummary");
  const riskFlags = document.querySelector("#reviewRiskFlags");
  const focusTrades = document.querySelector("#reviewFocusTrades");
  const questions = document.querySelector("#reviewQuestions");
  const tasks = document.querySelector("#reviewLearningTasks");
  if (!review || !["ok", "generated"].includes(review.status)) {
    status.textContent = review?.message || text.noReview;
    summary.innerHTML = "";
    riskFlags.textContent = text.noRiskFlags;
    focusTrades.textContent = text.noFocusTrades;
    questions.innerHTML = "";
    tasks.innerHTML = "";
    return;
  }
  const draft = review.draft || {};
  const detail = draft.summary || {};
  status.textContent = review.persisted ? text.savedReview : text.generatedReview;
  summary.innerHTML = [
    metric("\u6807\u7684", `${escapeHtml(detail.symbol || "-")} ${escapeHtml(detail.interval || "")}`),
    metric("\u5b9e\u9a8c", escapeHtml(detail.experiment_external_id || review.experiment_external_id || "-")),
    metric("\u76c8\u4e8f", fmt.format(detail.realized_pnl || 0)),
    metric("\u80dc\u7387", `${fmt.format((detail.win_rate || 0) * 100)}%`),
    metric("\u56de\u64a4", fmt.format(detail.max_drawdown || 0)),
    metric("\u624b\u7eed\u8d39", fmt.format(detail.total_fees || 0)),
  ].join("");
  riskFlags.innerHTML = renderRiskFlags(draft.risk_flags || []);
  focusTrades.innerHTML = renderFocusTrades(draft.focus_trades || []);
  questions.innerHTML = renderNumberedItems(draft.review_questions || []);
  tasks.innerHTML = renderNumberedItems(draft.learning_tasks || []);
  focusTrades.querySelectorAll("button[data-trade-id]").forEach((button) => {
    button.addEventListener("click", () => focusTrade(button.dataset.tradeId));
  });
}

function renderRiskFlags(flags) {
  if (!flags.length) {
    return `<p class="empty-note">${text.noRiskFlags}</p>`;
  }
  return flags
    .map(
      (flag) => `
        <article class="risk-flag severity-${escapeHtml(flag.severity || "low")}">
          <strong>${escapeHtml(flag.code || "")}</strong>
          <span>${escapeHtml(flag.message || "")}</span>
        </article>
      `,
    )
    .join("");
}

function renderFocusTrades(trades) {
  if (!trades.length) {
    return `<p class="empty-note">${text.noFocusTrades}</p>`;
  }
  return trades
    .map((trade) => {
      const tradeId = trade.exit_trade_id || trade.entry_trade_id || "";
      return `
        <article class="focus-trade">
          <strong>${escapeHtml(trade.entry_trade_id || "-")} \u2192 ${escapeHtml(trade.exit_trade_id || "-")}</strong>
          <span>${escapeHtml(trade.entry_time || "")} / ${escapeHtml(trade.exit_time || "")}</span>
          <span>PNL ${fmt.format(trade.pnl || 0)} (${fmt.format((trade.pnl_pct || 0) * 100)}%)</span>
          <button type="button" data-trade-id="${escapeHtml(tradeId)}">\u5b9a\u4f4d</button>
        </article>
      `;
    })
    .join("");
}

function renderNumberedItems(items) {
  if (!items.length) {
    return `<p class="empty-note">-</p>`;
  }
  return `<ol>${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ol>`;
}

async function loadBacktestReport() {
  const select = document.querySelector("#experimentSelect");
  if (!select.value) {
    renderBacktestReport(null);
    return;
  }
  const report = await getJson(`/api/backtest-report?experiment=${encodeURIComponent(select.value)}`);
  renderBacktestReport(report);
}

async function loadExperimentReview() {
  const select = document.querySelector("#experimentSelect");
  if (!select.value) {
    renderExperimentReview(null);
    return;
  }
  const review = await getJson(`/api/experiment-review?experiment=${encodeURIComponent(select.value)}`);
  renderExperimentReview(review);
}

async function refreshExperimentsAndConsole(selectedExperimentId) {
  const [experiments, overview, controlConsole] = await Promise.all([
    getJson("/api/experiments?limit=12"),
    getJson("/api/overview"),
    getJson("/api/control-console"),
  ]);
  state.experiments = experiments.experiments;
  state.overview = overview;
  state.controlConsole = controlConsole;
  renderOverview();
  renderExperiments();
  renderControlConsole();
  if (selectedExperimentId) {
    document.querySelector("#experimentSelect").value = selectedExperimentId;
  }
}

async function runDashboardBacktest(event) {
  event.preventDefault();
  const status = document.querySelector("#backtestActionStatus");
  status.textContent = "\u8fd0\u884c\u4e2d...";
  const result = await postJson("/api/actions/backtest-ma", {
    strategy: document.querySelector("#backtestStrategy").value,
    symbol: document.querySelector("#backtestSymbol").value,
    interval: document.querySelector("#backtestInterval").value,
    csv: document.querySelector("#backtestCsv").value,
    start: document.querySelector("#backtestStart").value,
    end: document.querySelector("#backtestEnd").value,
    train_ratio: Number(document.querySelector("#backtestTrainRatio").value),
    short: Number(document.querySelector("#backtestShort").value),
    long: Number(document.querySelector("#backtestLong").value),
  });
  status.textContent = result.status === "saved" ? `\u5df2\u4fdd\u5b58 ${result.external_id}` : `${result.status}: ${result.message || ""}`;
  if (result.status === "saved") {
    await refreshExperimentsAndConsole(result.external_id);
    await loadReplay();
  }
}

async function saveReviewDraftAction() {
  const experiment = document.querySelector("#experimentSelect").value;
  if (!experiment) return;
  const result = await postJson("/api/actions/experiment-review", { experiment });
  document.querySelector("#experimentReviewStatus").textContent = result.message || result.status;
  await loadExperimentReview();
}

async function commitReviewAction() {
  const experiment = document.querySelector("#experimentSelect").value;
  if (!experiment) return;
  const result = await postJson("/api/actions/experiment-review-commit", { experiment });
  document.querySelector("#experimentReviewStatus").textContent = result.message || result.status;
  await refreshExperimentsAndConsole(experiment);
  await loadExperimentReview();
}

function focusTrade(tradeId) {
  const trade = (state.report?.trades || []).find((item) => item.external_id === tradeId);
  if (!trade) return;
  const candleIndex = nearestCandleIndex(toChartTime(trade.timestamp));
  state.chart.visibleStart = Math.max(0, candleIndex - Math.floor(state.chart.visibleCount * 0.55));
  applyVisibleRange();
  updateTradeDetail(trade);
  syncRange();
}

function nearestCandleIndex(timestamp) {
  let best = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  state.chart.data.forEach((candle, index) => {
    const distance = Math.abs(candle.time - timestamp);
    if (distance < bestDistance) {
      best = index;
      bestDistance = distance;
    }
  });
  return best;
}

function syncRange() {
  const range = document.querySelector("#replayRange");
  const count = state.chart.data.length;
  if (!count) {
    range.max = 0;
    range.value = 0;
    return;
  }
  range.max = Math.max(0, count - 1);
  range.value = Math.min(count - 1, state.chart.visibleStart + state.chart.visibleCount - 1);
}

function applyVisibleRange() {
  const count = state.chart.data.length;
  if (!count) return;
  const from = Math.max(0, Math.min(state.chart.visibleStart, count - 1));
  const to = Math.max(from + 1, Math.min(count - 1, from + state.chart.visibleCount));
  state.chart.klineChart.timeScale().setVisibleLogicalRange({ from, to });
  state.chart.volumeChart.timeScale().setVisibleLogicalRange({ from, to });
}

function startPlayback() {
  if (state.chart.playbackTimer) {
    clearInterval(state.chart.playbackTimer);
    state.chart.playbackTimer = null;
    document.querySelector("#playPause").textContent = text.play;
    return;
  }
  document.querySelector("#playPause").textContent = text.pause;
  state.chart.playbackTimer = setInterval(() => stepReplay(1), 450);
}

function stepReplay(delta) {
  const count = state.chart.data.length;
  if (!count) return;
  const maxStart = Math.max(0, count - state.chart.visibleCount);
  state.chart.visibleStart = Math.max(0, Math.min(maxStart, state.chart.visibleStart + delta));
  applyVisibleRange();
  syncRange();
}

function jumpToNextTrade() {
  const trades = state.replay?.trades || [];
  if (!state.chart.data.length || !trades.length) return;
  const visibleEnd = Math.min(state.chart.data.length - 1, state.chart.visibleStart + state.chart.visibleCount - 1);
  const currentTime = state.chart.data[visibleEnd].time;
  const nextIndex = trades.findIndex((trade) => toChartTime(trade.timestamp) > currentTime);
  const tradeIndex = nextIndex >= 0 ? nextIndex : 0;
  const trade = trades[tradeIndex];
  const candleIndex = nearestCandleIndex(toChartTime(trade.timestamp));
  state.chart.visibleStart = Math.max(0, candleIndex - Math.floor(state.chart.visibleCount * 0.55));
  applyVisibleRange();
  updateTradeDetail(trade);
  syncRange();
}

function selectNearestTradeByClick(param) {
  if (!param || !param.time || !state.replay) return;
  let selected = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  (state.replay.trades || []).forEach((trade) => {
    const distance = Math.abs(toChartTime(trade.timestamp) - param.time);
    if (distance < bestDistance) {
      selected = trade;
      bestDistance = distance;
    }
  });
  updateTradeDetail(selected);
}

async function loadReplay() {
  const select = document.querySelector("#experimentSelect");
  if (!select.value) {
    updateOhlcPanel(null);
    return;
  }
  state.replay = await getJson(`/api/kline?experiment=${encodeURIComponent(select.value)}&limit=5000`);
  renderKline();
  await loadBacktestReport();
  await loadExperimentReview();
  await loadExperimentComparison();
}

async function loadDataset() {
  const select = document.querySelector("#datasetSelect");
  if (!select.value) {
    setOhlcMessage(text.chooseDataset);
    return;
  }
  const [symbol, path] = select.value.split("|");
  state.replay = await getJson(`/api/kline?csv=${encodeURIComponent(path)}&symbol=${encodeURIComponent(symbol)}&limit=5000`);
  renderKline();
  renderBacktestReport(null);
  renderExperimentReview(null);
}

async function boot() {
  try {
    createCharts();
    const [overview, reviews, experiments, knowledge, datasets, controlConsole, paperStatus, paperHistory, paperCurve] = await Promise.all([
      getJson("/api/overview"),
      getJson("/api/reviews?limit=8"),
      getJson("/api/experiments?limit=12"),
      getJson("/api/knowledge?limit=12"),
      getJson("/api/datasets"),
      getJson("/api/control-console"),
      getJson("/api/paper-trading/status"),
      getJson("/api/paper-trading/history?days=30"),
      getJson("/api/paper-trading/equity-curve"),
    ]);
    state.overview = overview;
    state.reviews = reviews.reviews;
    state.experiments = experiments.experiments;
    state.knowledge = knowledge.cards;
    state.datasets = datasets.datasets;
    state.controlConsole = controlConsole;
    state.paperStatus = paperStatus;
    state.paperHistory = paperHistory.history || [];
    state.paperEquityCurve = paperCurve.equity_curve || [];
    renderOverview();
    renderReviews();
    renderExperiments();
    renderDatasets();
    renderKnowledge();
    renderControlConsole();
    renderPaperTrading();
    navigateTo();
    if (state.experiments.length) {
      await loadReplay();
    } else if (state.datasets.some((dataset) => dataset.exists)) {
      await loadDataset();
    } else {
      renderBacktestReport(null);
      renderExperimentReview(null);
    }
    renderTopStatus();
  } catch (error) {
    document.querySelector("#connectionStatus").textContent = text.failed;
    console.error(error);
  }
}

window.addEventListener("hashchange", () => navigateTo());
document.querySelector("#coachToggle").addEventListener("click", toggleCoach);
document.querySelector("#loadReplay").addEventListener("click", loadReplay);
document.querySelector("#loadDataset").addEventListener("click", loadDataset);
document.querySelector("#replayRange").addEventListener("input", (event) => {
  const value = Number(event.target.value);
  state.chart.visibleStart = Math.max(0, value - state.chart.visibleCount + 1);
  applyVisibleRange();
});
document.querySelector("#stepBack").addEventListener("click", () => stepReplay(-1));
document.querySelector("#stepForward").addEventListener("click", () => stepReplay(1));
document.querySelector("#playPause").addEventListener("click", startPlayback);
document.querySelector("#nextTrade").addEventListener("click", jumpToNextTrade);
document.querySelector("#toggleMa20").addEventListener("change", renderIndicators);
document.querySelector("#toggleMa60").addEventListener("change", renderIndicators);
["#tradeSideFilter", "#tradeResultFilter", "#tradeStartFilter", "#tradeEndFilter", "#tradeRiskFilter"].forEach((selector) => {
  document.querySelector(selector).addEventListener("change", (event) => {
    const key = {
      tradeSideFilter: "side",
      tradeResultFilter: "result",
      tradeStartFilter: "start",
      tradeEndFilter: "end",
      tradeRiskFilter: "risk",
    }[event.target.id];
    state.reportFilters[key] = event.target.value;
    renderTradeTable();
  });
});
document.querySelector("#clearTradeFilters").addEventListener("click", () => {
  state.reportFilters = { side: "", result: "", start: "", end: "", risk: "" };
  renderTradeFilters(state.report?.filter_options || {});
  renderTradeTable();
});
document.querySelector("#loadComparison").addEventListener("click", loadExperimentComparison);
document.querySelector("#backtestForm").addEventListener("submit", runDashboardBacktest);
document.querySelector("#saveReviewDraftAction").addEventListener("click", saveReviewDraftAction);
document.querySelector("#commitReviewAction").addEventListener("click", commitReviewAction);
boot();
