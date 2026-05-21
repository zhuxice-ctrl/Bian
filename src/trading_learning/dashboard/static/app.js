const state = {
  overview: null,
  experiments: [],
  datasets: [],
  reviews: [],
  knowledge: [],
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
  document.querySelector("#metrics").innerHTML = [
    metric(text.reviewDays, totals.review_days),
    metric(text.reviewTrades, totals.review_trade_count),
    metric(text.reviewPnl, fmt.format(totals.review_pnl)),
    metric(text.planRate, `${fmt.format(totals.plan_follow_rate * 100)}%`),
    metric(text.experiments, totals.experiment_count),
    metric(text.knowledge, totals.knowledge_count),
  ].join("");
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
  if (!state.datasets.length) {
    select.innerHTML = `<option value="">\u6682\u65e0\u672c\u5730\u6570\u636e</option>`;
    document.querySelector("#datasetList").innerHTML = "";
    return;
  }
  select.innerHTML = state.datasets
    .map((dataset) => {
      const value = `${dataset.symbol}|${dataset.path}`;
      return `<option value="${escapeHtml(value)}">${escapeHtml(dataset.symbol)} ${escapeHtml(dataset.interval)} &middot; ${dataset.row_count} bars</option>`;
    })
    .join("");
  document.querySelector("#datasetList").innerHTML = state.datasets
    .map(
      (dataset) => `
        <article class="item">
          <span>${escapeHtml(dataset.symbol)} &middot; ${escapeHtml(dataset.interval)} &middot; ${dataset.row_count} bars</span>
          <strong>${escapeHtml(dataset.path)}</strong>
          <p>${escapeHtml(dataset.first_opened_at || "-")} \u2192 ${escapeHtml(dataset.last_opened_at || "-")}</p>
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

function createCharts() {
  const chartOptions = {
    layout: { background: { color: "#ffffff" }, textColor: "#334155", fontSize: 12 },
    grid: { vertLines: { color: "#edf2f7" }, horzLines: { color: "#edf2f7" } },
    crosshair: { mode: LightweightCharts.CrosshairMode.Normal },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#d9e1ea" },
    rightPriceScale: { borderColor: "#d9e1ea" },
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
    upColor: "#0f8b5f",
    downColor: "#b42318",
    borderUpColor: "#0f8b5f",
    borderDownColor: "#b42318",
    wickUpColor: "#0f8b5f",
    wickDownColor: "#b42318",
  });
  state.chart.volumeSeries = state.chart.volumeChart.addSeries(LightweightCharts.HistogramSeries, {
    priceFormat: { type: "volume" },
    priceScaleId: "",
  });
  state.chart.ma20Series = state.chart.klineChart.addSeries(LightweightCharts.LineSeries, {
    color: "#245a92",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  state.chart.ma60Series = state.chart.klineChart.addSeries(LightweightCharts.LineSeries, {
    color: "#8a5a00",
    lineWidth: 2,
    priceLineVisible: false,
    lastValueVisible: false,
  });
  state.chart.equityChart = LightweightCharts.createChart(document.querySelector("#equityChart"), {
    layout: { background: { color: "#ffffff" }, textColor: "#334155", fontSize: 12 },
    grid: { vertLines: { color: "#edf2f7" }, horzLines: { color: "#edf2f7" } },
    timeScale: { timeVisible: true, secondsVisible: false, borderColor: "#d9e1ea" },
    rightPriceScale: { borderColor: "#d9e1ea" },
  });
  state.chart.equitySeries = state.chart.equityChart.addSeries(LightweightCharts.LineSeries, {
    color: "#176b87",
    lineWidth: 2,
    priceLineVisible: false,
  });
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
      color: candle.close >= candle.open ? "rgba(15,139,95,0.45)" : "rgba(180,35,24,0.45)",
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
    const [overview, reviews, experiments, knowledge, datasets] = await Promise.all([
      getJson("/api/overview"),
      getJson("/api/reviews?limit=8"),
      getJson("/api/experiments?limit=12"),
      getJson("/api/knowledge?limit=12"),
      getJson("/api/datasets"),
    ]);
    state.overview = overview;
    state.reviews = reviews.reviews;
    state.experiments = experiments.experiments;
    state.knowledge = knowledge.cards;
    state.datasets = datasets.datasets;
    renderOverview();
    renderReviews();
    renderExperiments();
    renderDatasets();
    renderKnowledge();
    if (state.experiments.length) {
      await loadReplay();
    } else if (state.datasets.length) {
      await loadDataset();
    } else {
      renderBacktestReport(null);
      renderExperimentReview(null);
    }
    document.querySelector("#connectionStatus").textContent = text.online;
  } catch (error) {
    document.querySelector("#connectionStatus").textContent = text.failed;
    console.error(error);
  }
}

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
boot();
