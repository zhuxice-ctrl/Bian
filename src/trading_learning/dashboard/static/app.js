const state = {
  overview: null,
  experiments: [],
  reviews: [],
  knowledge: [],
  replay: null,
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
};

const fmt = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 });

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
          <span>${escapeHtml(review.review_date)} · ${escapeHtml(review.symbols_watched.join(", "))}</span>
          <strong>${review.plan_followed ? text.followed : text.drifted} · ${text.pnl} ${fmt.format(review.pnl)}</strong>
          <p>${escapeHtml(review.lesson || text.noLesson)}</p>
        </article>
      `,
    )
    .join("");
}

function renderExperiments() {
  const select = document.querySelector("#experimentSelect");
  select.innerHTML = state.experiments
    .map((experiment) => `<option value="${escapeHtml(experiment.external_id)}">${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)} · ${escapeHtml(experiment.external_id)}</option>`)
    .join("");
  document.querySelector("#experimentList").innerHTML = state.experiments
    .map(
      (experiment) => `
        <article class="item">
          <span>${escapeHtml(experiment.strategy_name)} · ${escapeHtml(experiment.symbol)} ${escapeHtml(experiment.interval)}</span>
          <strong>${escapeHtml(experiment.external_id)}</strong>
          <p>${text.trades} ${experiment.metrics.trade_count ?? 0} · ${text.winRate} ${fmt.format((experiment.metrics.win_rate ?? 0) * 100)}% · ${text.pnl} ${fmt.format(experiment.metrics.realized_pnl ?? 0)}</p>
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
          <span>${escapeHtml(card.category)} · ${escapeHtml(card.tags.join(", "))}</span>
          <strong>${escapeHtml(card.title)}</strong>
          <p>${escapeHtml(card.content)}</p>
        </article>
      `,
    )
    .join("");
}

function renderKline() {
  const canvas = document.querySelector("#klineCanvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  const replay = state.replay;
  if (!replay || !replay.candles || !replay.candles.length) {
    ctx.fillStyle = "#64748b";
    ctx.font = "14px Arial";
    ctx.fillText(text.chooseReplay, 24, 32);
    return;
  }

  const visibleCount = Number(document.querySelector("#replayRange").value);
  const candles = replay.candles.slice(-visibleCount);
  const highs = candles.map((candle) => candle.high);
  const lows = candles.map((candle) => candle.low);
  const high = Math.max(...highs);
  const low = Math.min(...lows);
  const pad = 28;
  const chartWidth = canvas.width - pad * 2;
  const chartHeight = canvas.height - pad * 2;
  const xStep = chartWidth / candles.length;
  const y = (price) => pad + ((high - price) / Math.max(1, high - low)) * chartHeight;

  ctx.strokeStyle = "#d9e1ea";
  ctx.lineWidth = 1;
  for (let i = 0; i < 5; i += 1) {
    const yy = pad + (chartHeight / 4) * i;
    ctx.beginPath();
    ctx.moveTo(pad, yy);
    ctx.lineTo(canvas.width - pad, yy);
    ctx.stroke();
  }

  candles.forEach((candle, index) => {
    const x = pad + index * xStep + xStep / 2;
    const rising = candle.close >= candle.open;
    ctx.strokeStyle = rising ? "#0f8b5f" : "#b42318";
    ctx.fillStyle = ctx.strokeStyle;
    ctx.beginPath();
    ctx.moveTo(x, y(candle.high));
    ctx.lineTo(x, y(candle.low));
    ctx.stroke();
    const bodyTop = y(Math.max(candle.open, candle.close));
    const bodyBottom = y(Math.min(candle.open, candle.close));
    ctx.fillRect(x - Math.max(2, xStep * 0.26), bodyTop, Math.max(3, xStep * 0.52), Math.max(2, bodyBottom - bodyTop));
  });

  const firstTime = new Date(candles[0].opened_at).getTime();
  const lastTime = new Date(candles[candles.length - 1].opened_at).getTime();
  (replay.trades || []).forEach((trade) => {
    const time = new Date(trade.timestamp).getTime();
    if (time < firstTime || time > lastTime) return;
    const ratio = (time - firstTime) / Math.max(1, lastTime - firstTime);
    const x = pad + ratio * chartWidth;
    const yy = y(trade.price);
    ctx.fillStyle = trade.side === "BUY" ? "#0f8b5f" : "#b42318";
    ctx.beginPath();
    ctx.arc(x, yy, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillText(trade.side, x + 7, yy - 7);
  });
}

async function loadReplay() {
  const select = document.querySelector("#experimentSelect");
  if (!select.value) {
    renderKline();
    return;
  }
  state.replay = await getJson(`/api/kline?experiment=${encodeURIComponent(select.value)}&limit=300`);
  renderKline();
}

async function boot() {
  try {
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
document.querySelector("#replayRange").addEventListener("input", renderKline);
boot();
