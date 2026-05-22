from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from importlib.resources import files
from typing import Any
from urllib.parse import parse_qs, urlparse


class DashboardRequestHandler(BaseHTTPRequestHandler):
    data: Any

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/":
                self._write_static("index.html", "text/html; charset=utf-8")
                return
            if parsed.path == "/static/styles.css":
                self._write_static("styles.css", "text/css; charset=utf-8")
                return
            if parsed.path == "/static/app.js":
                self._write_static("app.js", "application/javascript; charset=utf-8")
                return
            if parsed.path == "/static/vendor/lightweight-charts.standalone.production.js":
                self._write_static("vendor/lightweight-charts.standalone.production.js", "application/javascript; charset=utf-8")
                return
            if parsed.path == "/api/overview":
                self._write_json(self.data.overview(), HTTPStatus.OK)
                return
            if parsed.path == "/api/reviews":
                query = parse_qs(parsed.query)
                self._write_json(self.data.reviews(limit=self._limit(query)), HTTPStatus.OK)
                return
            if parsed.path == "/api/experiments":
                query = parse_qs(parsed.query)
                self._write_json(self.data.experiments(limit=self._limit(query)), HTTPStatus.OK)
                return
            if parsed.path == "/api/knowledge":
                query = parse_qs(parsed.query)
                self._write_json(self.data.knowledge(limit=self._limit(query)), HTTPStatus.OK)
                return
            if parsed.path == "/api/reports":
                query = parse_qs(parsed.query)
                self._write_json(
                    self.data.reports(report_type=query.get("type", [None])[0], limit=self._limit(query)),
                    HTTPStatus.OK,
                )
                return
            if parsed.path == "/api/datasets":
                self._write_json(self.data.datasets(), HTTPStatus.OK)
                return
            if parsed.path == "/api/control-console":
                self._write_json(self.data.control_console(), HTTPStatus.OK)
                return
            if parsed.path == "/api/backtest-report":
                query = parse_qs(parsed.query)
                self._write_json(
                    self.data.backtest_report(query.get("experiment", [""])[0]),
                    HTTPStatus.OK,
                )
                return
            if parsed.path == "/api/experiment-review":
                query = parse_qs(parsed.query)
                self._write_json(
                    self.data.experiment_review(query.get("experiment", [""])[0]),
                    HTTPStatus.OK,
                )
                return
            if parsed.path == "/api/experiment-comparison":
                query = parse_qs(parsed.query)
                experiment_ids = [
                    item.strip()
                    for item in query.get("experiments", [""])[0].split(",")
                    if item.strip()
                ]
                self._write_json(self.data.experiment_comparison(experiment_ids), HTTPStatus.OK)
                return
            if parsed.path == "/api/kline":
                query = parse_qs(parsed.query)
                if "experiment" in query:
                    self._write_json(
                        self.data.kline_replay(query["experiment"][0], limit=self._limit(query)),
                        HTTPStatus.OK,
                    )
                    return
                self._write_json(
                    self.data.kline(
                        csv_path=query.get("csv", [""])[0],
                        symbol=query.get("symbol", ["BTCUSDT"])[0],
                        limit=self._limit(query),
                    ),
                    HTTPStatus.OK,
                )
                return
        except ValueError as exc:
            self._write_json({"status": "invalid", "message": str(exc)}, HTTPStatus.OK)
            return
        except FileNotFoundError as exc:
            self._write_json({"status": "not_found", "message": str(exc)}, HTTPStatus.OK)
            return

        self._write_json({"status": "not_found", "message": "not found"}, HTTPStatus.NOT_FOUND)

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, body: dict[str, Any], status: HTTPStatus) -> None:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _write_static(self, filename: str, content_type: str) -> None:
        content = files("trading_learning.dashboard.static").joinpath(filename).read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    @staticmethod
    def _limit(query: dict[str, list[str]]) -> int:
        try:
            return max(1, min(1000, int(query.get("limit", ["300"])[0])))
        except ValueError:
            return 300


def build_dashboard_handler(data: Any) -> type[DashboardRequestHandler]:
    class ConfiguredDashboardRequestHandler(DashboardRequestHandler):
        pass

    ConfiguredDashboardRequestHandler.data = data
    return ConfiguredDashboardRequestHandler
