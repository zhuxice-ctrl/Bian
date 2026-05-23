from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from typing import Any
from uuid import uuid4


ALLOWED_TASK_TYPES = {"local_status", "backtest_ma", "market_refresh"}
FINAL_STATES = {"succeeded", "failed", "rejected", "expired"}


@dataclass(frozen=True)
class RemoteTask:
    external_id: str
    requester_user_id: str
    command_text: str
    task_type: str
    risk_level: str
    payload: dict[str, Any]
    state: str
    runner_id: str
    result_summary: str
    result_payload: dict[str, Any]
    error_message: str
    created_at: str
    claimed_at: str | None
    completed_at: str | None
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "external_id": self.external_id,
            "requester_user_id": self.requester_user_id,
            "command_text": self.command_text,
            "task_type": self.task_type,
            "risk_level": self.risk_level,
            "payload": self.payload,
            "state": self.state,
            "runner_id": self.runner_id,
            "result_summary": self.result_summary,
            "result_payload": self.result_payload,
            "error_message": self.error_message,
            "created_at": self.created_at,
            "claimed_at": self.claimed_at,
            "completed_at": self.completed_at,
            "updated_at": self.updated_at,
        }


def remote_task_from_dict(data: dict[str, Any]) -> RemoteTask:
    return RemoteTask(
        external_id=str(data["external_id"]),
        requester_user_id=str(data.get("requester_user_id", "")),
        command_text=str(data.get("command_text", "")),
        task_type=str(data["task_type"]),
        risk_level=str(data.get("risk_level", "")),
        payload=data.get("payload") if isinstance(data.get("payload"), dict) else {},
        state=str(data.get("state", "")),
        runner_id=str(data.get("runner_id", "")),
        result_summary=str(data.get("result_summary", "")),
        result_payload=data.get("result_payload") if isinstance(data.get("result_payload"), dict) else {},
        error_message=str(data.get("error_message", "")),
        created_at=str(data.get("created_at", "")),
        claimed_at=data.get("claimed_at"),
        completed_at=data.get("completed_at"),
        updated_at=str(data.get("updated_at", "")),
    )


class TaskQueue:
    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    def create_task(
        self,
        *,
        requester_user_id: str,
        command_text: str,
        task_type: str,
        payload: dict[str, Any],
        risk_level: str,
    ) -> RemoteTask:
        if task_type not in ALLOWED_TASK_TYPES:
            raise ValueError(f"unsupported task type: {task_type}")
        external_id = f"task-{uuid4()}"
        with self.conn:
            self.conn.execute(
                """
                insert into remote_tasks (
                  external_id, requester_user_id, command_text, task_type, risk_level, payload
                ) values (?, ?, ?, ?, ?, ?)
                """,
                (
                    external_id,
                    requester_user_id,
                    command_text,
                    task_type,
                    risk_level,
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )
        task = self.get_task(external_id)
        if task is None:
            raise RuntimeError("created task could not be loaded")
        return task

    def list_recent(self, *, limit: int = 5) -> list[RemoteTask]:
        rows = self.conn.execute(
            "select * from remote_tasks order by id desc limit ?",
            (limit,),
        ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def get_task(self, external_id: str) -> RemoteTask | None:
        row = self.conn.execute(
            "select * from remote_tasks where external_id = ?",
            (external_id,),
        ).fetchone()
        return self._row_to_task(row) if row else None

    def claim_next(self, *, runner_id: str, capabilities: tuple[str, ...]) -> RemoteTask | None:
        supported = [task_type for task_type in capabilities if task_type in ALLOWED_TASK_TYPES]
        if not supported:
            return None
        placeholders = ",".join("?" for _ in supported)
        with self.conn:
            row = self.conn.execute(
                f"""
                select * from remote_tasks
                where state = 'queued' and task_type in ({placeholders})
                order by id asc
                limit 1
                """,
                supported,
            ).fetchone()
            if row is None:
                return None
            self.conn.execute(
                """
                update remote_tasks
                set state = 'claimed',
                    runner_id = ?,
                    claimed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                where external_id = ? and state = 'queued'
                """,
                (runner_id, row["external_id"]),
            )
        return self.get_task(row["external_id"])

    def complete_task(
        self,
        external_id: str,
        *,
        runner_id: str,
        state: str,
        result_summary: str = "",
        result_payload: dict[str, Any] | None = None,
        error_message: str = "",
    ) -> RemoteTask:
        if state not in FINAL_STATES:
            raise ValueError(f"unsupported completion state: {state}")
        with self.conn:
            self.conn.execute(
                """
                update remote_tasks
                set state = ?,
                    runner_id = ?,
                    result_summary = ?,
                    result_payload = ?,
                    error_message = ?,
                    completed_at = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                where external_id = ?
                """,
                (
                    state,
                    runner_id,
                    result_summary,
                    json.dumps(result_payload or {}, ensure_ascii=False, sort_keys=True),
                    error_message,
                    external_id,
                ),
            )
        task = self.get_task(external_id)
        if task is None:
            raise ValueError(f"unknown task: {external_id}")
        return task

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> RemoteTask:
        return RemoteTask(
            external_id=row["external_id"],
            requester_user_id=row["requester_user_id"],
            command_text=row["command_text"],
            task_type=row["task_type"],
            risk_level=row["risk_level"],
            payload=json.loads(row["payload"]),
            state=row["state"],
            runner_id=row["runner_id"],
            result_summary=row["result_summary"],
            result_payload=json.loads(row["result_payload"]),
            error_message=row["error_message"],
            created_at=row["created_at"],
            claimed_at=row["claimed_at"],
            completed_at=row["completed_at"],
            updated_at=row["updated_at"],
        )
