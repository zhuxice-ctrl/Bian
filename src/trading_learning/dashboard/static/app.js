const state = {
  overview: null,
  experiments: [],
  reviews: [],
  knowledge: [],
  replay: null,
  chart: {
    visibleStart: 0,
    visibleCount: 120,
    cursorIndex: null,
    selectedTradeIndex: null,
    isDragging: false,
    dragX: 0,
    dragStart: 0,
    playbackTimer: null,
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
  online: "\u672c\u5730\u5728\u7ebf",
  failed: "\u8bfb\u53d6\u5931\u8d25",
  noTrade: "\u6ca1\u6709\u9009\u4e2d\u4ea4\u6613",
  play: "\u64ad\u653e",
  pause: "\u6682\u505c",
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

function visibleCandles() {
  if (!state.replay || !state.replay.candles.length) return [];
  const candles = state.replay.candles;
  const count = Math.min(state.chart.visibleCount, candles.length);
  const start = Math.max(0, Math.min(state.chart.visibleStart, candles.length - count));
  state.chart.visibleStart = start;
  return candles.slice(start, start + count);
}

function movingAverage(candles, windowSize) {
  return candles.map((_, index) => {
    if (index + 1 < windowSize) return null;
    const slice = candles.slice(index + 1 - windowSize, index + 1);
    return slice.reduce((sum, candle) => sum + candle.close, 0) / windowSize;
  });
}

function priceScale(candles) {
  const highs = candles.map((candle) => candle.high);
  const lows = candles.map((candle) => candle.low);
  const high = Math.max(...highs);
  const low = Math.min(...lows);
  const padding = Math.max((high - low) * 0.08, 1);
  return { high: high + padding, low: low - padding };
}

function renderKline() {
  const canvas = document.querySelector("#klineCanvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const candles = visibleCandles();
  if (!candles.length) {
    ctx.fillStyle = "#64748b";
    ctx.font = "14px Arial";
    ctx.fillText(text.chooseReplay, 24, 32);
    renderVolume([]);
    updateOhlcPanel(null);
    return;
  }

  const pad = { left: 58, right: 70, top: 18, bottom: 30 };
  const chartWidth = canvas.width - pad.left - pad.right;
  const chartHeight = canvas.height - pad.top - pad.bottom;
  const xStep = chartWidth / candles.length;
  const scale = priceScale(candles);
  const y = (price) => pad.top + ((scale.high - price) / Math.max(1, scale.high - scale.low)) * chartHeight;

  drawPriceGrid(ctx, canvas, pad, chartHeight, scale);
  candles.forEach((candle, index) => drawCandle(ctx, candle, index, pad, xStep, y));
  drawMovingAverage(ctx, candles, 20, pad, xStep, y, "#245a92", document.querySelector("#toggleMa20").checked);
  drawMovingAverage(ctx, candles, 60, pad, xStep, y, "#8a5a00", document.querySelector("#toggleMa60").checked);
  drawTradeMarkers(ctx, candles, pad, xStep, y);
  renderCrosshair(ctx, canvas, candles, pad, xStep, y);
  renderVolume(candles);
  syncRange();
}

function drawPriceGrid(ctx, canvas, pad, chartHeight, scale) {
  ctx.strokeStyle = "#e4eaf0";
  ctx.fillStyle = "#64748b";
  ctx.font = "12px Arial";
  for (let i = 0; i < 6; i += 1) {
    const yy = pad.top + (chartHeight / 5) * i;
    const price = scale.high - ((scale.high - scale.low) / 5) * i;
    ctx.beginPath();
    ctx.moveTo(pad.left, yy);
    ctx.lineTo(canvas.width - pad.right, yy);
    ctx.stroke();
    ctx.fillText(fmt.format(price), canvas.width - pad.right + 8, yy + 4);
  }
}

function drawCandle(ctx, candle, index, pad, xStep, y) {
  const x = pad.left + index * xStep + xStep / 2;
  const rising = candle.close >= candle.open;
  ctx.strokeStyle = rising ? "#0f8b5f" : "#b42318";
  ctx.fillStyle = ctx.strokeStyle;
  ctx.beginPath();
  ctx.moveTo(x, y(candle.high));
  ctx.lineTo(x, y(candle.low));
  ctx.stroke();
  const bodyTop = y(Math.max(candle.open, candle.close));
  const bodyBottom = y(Math.min(candle.open, candle.close));
  ctx.fillRect(x - Math.max(2, xStep * 0.3), bodyTop, Math.max(3, xStep * 0.6), Math.max(2, bodyBottom - bodyTop));
}

function drawMovingAverage(ctx, candles, windowSize, pad, xStep, y, color, enabled) {
  if (!enabled) return;
  const values = movingAverage(candles, windowSize);
  ctx.strokeStyle = color;
  ctx.lineWidth = 1.4;
  ctx.beginPath();
  let started = false;
  values.forEach((value, index) => {
    if (value === null) return;
    const x = pad.left + index * xStep + xStep / 2;
    const yy = y(value);
    if (!started) {
      ctx.moveTo(x, yy);
      started = true;
    } else {
      ctx.lineTo(x, yy);
    }
  });
  ctx.stroke();
}

function drawTradeMarkers(ctx, candles, pad, xStep, y) {
  const first = new Date(candles[0].opened_at).getTime();
  const last = new Date(candles[candles.length - 1].opened_at).getTime();
  (state.replay.trades || []).forEach((trade, tradeIndex) => {
    const time = new Date(trade.timestamp).getTime();
    if (time < first || time > last) return;
    const candleIndex = nearestCandleIndex(candles, time);
    const x = pad.left + candleIndex * xStep + xStep / 2;
    const yy = y(trade.price);
    ctx.fillStyle = trade.side === "BUY" ? "#0f8b5f" : "#b42318";
    ctx.beginPath();
    ctx.arc(x, yy, state.chart.selectedTradeIndex === tradeIndex ? 7 : 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillText(trade.side, x + 8, yy - 8);
  });
}

function renderCrosshair(ctx, canvas, candles, pad, xStep, y) {
  if (state.chart.cursorIndex === null) {
    updateOhlcPanel(candles[candles.length - 1]);
    return;
  }
  const index = Math.max(0, Math.min(candles.length - 1, state.chart.cursorIndex));
  const candle = candles[index];
  const x = pad.left + index * xStep + xStep / 2;
  const yy = y(candle.close);
  ctx.strokeStyle = "#334155";
  ctx.setLineDash([4, 4]);
  ctx.beginPath();
  ctx.moveTo(x, pad.top);
  ctx.lineTo(x, canvas.height - pad.bottom);
  ctx.moveTo(pad.left, yy);
  ctx.lineTo(canvas.width - pad.right, yy);
  ctx.stroke();
  ctx.setLineDash([]);
  updateOhlcPanel(candle);
}

function renderVolume(candles) {
  const canvas = document.querySelector("#volumeCanvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (!candles.length) return;
  const pad = { left: 58, right: 70, top: 8, bottom: 20 };
  const width = canvas.width - pad.left - pad.right;
  const height = canvas.height - pad.top - pad.bottom;
  const maxVolume = Math.max(...candles.map((candle) => candle.volume), 1);
  const xStep = width / candles.length;
  candles.forEach((candle, index) => {
    const barHeight = (candle.volume / maxVolume) * height;
    const x = pad.left + index * xStep + xStep * 0.18;
    const y = pad.top + height - barHeight;
    ctx.fillStyle = candle.close >= candle.open ? "rgba(15,139,95,0.55)" : "rgba(180,35,24,0.55)";
    ctx.fillRect(x, y, Math.max(2, xStep * 0.64), barHeight);
  });
}

function updateOhlcPanel(candle) {
  const panel = document.querySelector("#ohlcPanel");
  if (!candle) {
    panel.textContent = text.chooseReplay;
    return;
  }
  const change = candle.close - candle.open;
  const changePct = candle.open ? (change / candle.open) * 100 : 0;
  panel.innerHTML = `
    <strong>${timeFmt.format(new Date(candle.opened_at))}</strong>
    <span>O ${fmt.format(candle.open)} / H ${fmt.format(candle.high)} / L ${fmt.format(candle.low)} / C ${fmt.format(candle.close)}</span>
    <span>${text.pnl} ${fmt.format(change)} (${fmt.format(changePct)}%)</span>
    <span>VOL ${fmt.format(candle.volume)}</span>
  `;
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

function nearestCandleIndex(candles, timestamp) {
  let best = 0;
  let bestDistance = Number.POSITIVE_INFINITY;
  candles.forEach((candle, index) => {
    const distance = Math.abs(new Date(candle.opened_at).getTime() - timestamp);
    if (distance < bestDistance) {
      best = index;
      bestDistance = distance;
    }
  });
  return best;
}

function syncRange() {
  const range = document.querySelector("#replayRange");
  const candles = state.replay?.candles || [];
  range.max = Math.max(0, candles.length - 1);
  range.value = Math.min(candles.length - 1, state.chart.visibleStart + state.chart.visibleCount - 1);
}

function canvasIndexFromEvent(event) {
  const canvas = document.querySelector("#klineCanvas");
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const candles = visibleCandles();
  if (!candles.length) return null;
  const padLeft = 58;
  const padRight = 70;
  const width = rect.width - padLeft - padRight;
  const ratio = Math.max(0, Math.min(1, (x - padLeft) / width));
  return Math.max(0, Math.min(candles.length - 1, Math.floor(ratio * candles.length)));
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
  const candles = state.replay?.candles || [];
  if (!candles.length) return;
  const maxStart = Math.max(0, candles.length - state.chart.visibleCount);
  state.chart.visibleStart = Math.max(0, Math.min(maxStart, state.chart.visibleStart + delta));
  renderKline();
}

function jumpToNextTrade() {
  const candles = state.replay?.candles || [];
  const trades = state.replay?.trades || [];
  if (!candles.length || !trades.length) return;
  const currentTime = new Date(candles[Math.min(candles.length - 1, state.chart.visibleStart + state.chart.visibleCount - 1)].opened_at).getTime();
  const nextIndex = trades.findIndex((trade) => new Date(trade.timestamp).getTime() > currentTime);
  const tradeIndex = nextIndex >= 0 ? nextIndex : 0;
  state.chart.selectedTradeIndex = tradeIndex;
  const tradeTime = new Date(trades[tradeIndex].timestamp).getTime();
  const candleIndex = nearestCandleIndex(candles, tradeTime);
  state.chart.visibleStart = Math.max(0, candleIndex - Math.floor(state.chart.visibleCount * 0.55));
  updateTradeDetail(trades[tradeIndex]);
  renderKline();
}

function selectNearestTrade(event) {
  const index = canvasIndexFromEvent(event);
  if (index === null || !state.replay) return;
  const candles = visibleCandles();
  const candle = candles[index];
  const time = new Date(candle.opened_at).getTime();
  let bestIndex = null;
  let bestDistance = Number.POSITIVE_INFINITY;
  (state.replay.trades || []).forEach((trade, tradeIndex) => {
    const distance = Math.abs(new Date(trade.timestamp).getTime() - time);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestIndex = tradeIndex;
    }
  });
  if (bestIndex !== null) {
    state.chart.selectedTradeIndex = bestIndex;
    updateTradeDetail(state.replay.trades[bestIndex]);
    renderKline();
  }
}

async function loadReplay() {
  const select = document.querySelector("#experimentSelect");
  if (!select.value) {
    renderKline();
    return;
  }
  state.replay = await getJson(`/api/kline?experiment=${encodeURIComponent(select.value)}&limit=1000`);
  const candles = state.replay.candles || [];
  state.chart.visibleCount = Math.min(120, Math.max(20, candles.length));
  state.chart.visibleStart = Math.max(0, candles.length - state.chart.visibleCount);
  state.chart.cursorIndex = null;
  state.chart.selectedTradeIndex = null;
  updateTradeDetail(null);
  renderKline();
}

function bindChartInteractions() {
  const canvas = document.querySelector("#klineCanvas");
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    const candles = state.replay?.candles || [];
    if (!candles.length) return;
    const direction = event.deltaY > 0 ? 1 : -1;
    const nextCount = state.chart.visibleCount + direction * 12;
    state.chart.visibleCount = Math.max(20, Math.min(candles.length, nextCount));
    state.chart.visibleStart = Math.max(0, Math.min(state.chart.visibleStart, candles.length - state.chart.visibleCount));
    renderKline();
  });
  canvas.addEventListener("mousedown", (event) => {
    state.chart.isDragging = true;
    state.chart.dragX = event.clientX;
    state.chart.dragStart = state.chart.visibleStart;
  });
  canvas.addEventListener("mousemove", (event) => {
    if (state.chart.isDragging) {
      const rect = canvas.getBoundingClientRect();
      const candlesPerPixel = state.chart.visibleCount / Math.max(1, rect.width - 128);
      const moved = Math.round((state.chart.dragX - event.clientX) * candlesPerPixel);
      const candles = state.replay?.candles || [];
      state.chart.visibleStart = Math.max(0, Math.min(Math.max(0, candles.length - state.chart.visibleCount), state.chart.dragStart + moved));
    }
    state.chart.cursorIndex = canvasIndexFromEvent(event);
    renderKline();
  });
  canvas.addEventListener("mouseup", () => {
    state.chart.isDragging = false;
  });
  canvas.addEventListener("mouseleave", () => {
    state.chart.isDragging = false;
    state.chart.cursorIndex = null;
    renderKline();
  });
  canvas.addEventListener("click", selectNearestTrade);
}

async function boot() {
  try {
    bindChartInteractions();
    const [overview, reviews, experiments, knowledge] = await Promise.all([
      getJson("/api/overview"),
      getJson("/api/reviews?limit=8"),
      getJson("/api/experiments?limit=12"),
      getJson("/api/knowledge?limit=12"),
    ]);
    state.overview = overview;
    state.reviews = reviews.reviews;
    state.experiments = experiments.experiments;
    state.knowledge = knowledge.cards;
    renderOverview();
    renderReviews();
    renderExperiments();
    renderKnowledge();
    await loadReplay();
    document.querySelector("#connectionStatus").textContent = text.online;
  } catch (error) {
    document.querySelector("#connectionStatus").textContent = text.failed;
    console.error(error);
  }
}

document.querySelector("#loadReplay").addEventListener("click", loadReplay);
document.querySelector("#replayRange").addEventListener("input", (event) => {
  const value = Number(event.target.value);
  state.chart.visibleStart = Math.max(0, value - state.chart.visibleCount + 1);
  renderKline();
});
document.querySelector("#stepBack").addEventListener("click", () => stepReplay(-1));
document.querySelector("#stepForward").addEventListener("click", () => stepReplay(1));
document.querySelector("#playPause").addEventListener("click", startPlayback);
document.querySelector("#nextTrade").addEventListener("click", jumpToNextTrade);
document.querySelector("#toggleMa20").addEventListener("change", renderKline);
document.querySelector("#toggleMa60").addEventListener("change", renderKline);
boot();
