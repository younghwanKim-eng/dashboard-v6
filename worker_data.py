"""
worker_data.py — 모바일 근로자 앱 데이터 계층.
JSON 파일 영속 (data/assignments.json, announcements.json, inquiries.json).

- 작업(assignments)  : 로그인 아이디(id) 별 리스트
    상태 전이         : pending → in_progress ⇄ paused → review_requested → done
- 공지(announcements): 전체 공유. 긴급(critical) / 일반(info) 두 수준
- 문의(inquiries)    : 근로자가 보낸 문의 로그. Gmail 발송은 send_inquiry_email()에서

보안 원칙 (지침 §5):
- list_assignments / get_assignment / update_status 는 반드시 user id로 필터링
- 다른 근로자의 데이터는 반환하지 않음
"""
from __future__ import annotations

import json
import os
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
ASSIGN_PATH = DATA_DIR / "assignments.json"
ANNOUNCE_PATH = DATA_DIR / "announcements.json"
INQUIRY_PATH = DATA_DIR / "inquiries.json"

INQUIRY_RECIPIENT = "leelyanglae@naver.com"  # 사용자 결정값 (2026-10-13)

# ── 상태 전이표 ──
STATUS_LABELS = {
    "pending":           "대기",
    "in_progress":       "진행 중",
    "paused":            "일시정지",
    "review_requested":  "검토 요청",
    "done":              "완료",
}
STATUS_BADGE_KIND = {
    "pending":          "wait",
    "in_progress":      "doing",
    "paused":           "paused",
    "review_requested": "review",
    "done":             "done",
}
# 어떤 상태에서 어떤 전이를 허용하는지 (근로자 권한)
ALLOWED_TRANSITIONS = {
    "pending":          ["in_progress"],
    "in_progress":      ["paused", "review_requested"],
    "paused":           ["in_progress"],
    "review_requested": [],   # 관리자 승인 대기 — 근로자는 더 못 바꿈
    "done":             [],   # 종료 — 근로자는 못 바꿈
}
TRANSITION_LABEL = {
    "in_progress":      "작업 시작 / 재개",
    "paused":           "일시정지",
    "review_requested": "완료 보고 (검토 요청)",
}


# ─────────────────────────────────────────────────────────────
# 공통 I/O
# ─────────────────────────────────────────────────────────────
def _load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2, default=str)
    os.replace(tmp, path)


def _now_iso() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


# ─────────────────────────────────────────────────────────────
# ① 작업 (assignments)
# ─────────────────────────────────────────────────────────────
def _load_assignments() -> list[dict]:
    data = _load_json(ASSIGN_PATH, [])
    return data if isinstance(data, list) else []


def list_assignments(user_id: str) -> list[dict]:
    """현재 사용자에게 배정된 작업만 반환. 다른 사용자 데이터 노출 금지."""
    return [a for a in _load_assignments() if a.get("worker_id") == user_id]


def get_assignment(user_id: str, task_id: str) -> dict | None:
    for a in _load_assignments():
        if a.get("worker_id") == user_id and a.get("id") == task_id:
            return a
    return None


def update_status(user_id: str, task_id: str, new_status: str) -> tuple[bool, str]:
    """상태를 전이. 권한/전이 검증 통과 시만 저장."""
    if new_status not in STATUS_LABELS:
        return False, f"알 수 없는 상태: {new_status}"
    rows = _load_assignments()
    for a in rows:
        if a.get("id") != task_id:
            continue
        if a.get("worker_id") != user_id:
            return False, "본인에게 배정된 작업이 아닙니다."
        cur = a.get("status", "pending")
        allowed = ALLOWED_TRANSITIONS.get(cur, [])
        if new_status not in allowed:
            return False, (
                f"'{STATUS_LABELS.get(cur, cur)}'에서 "
                f"'{STATUS_LABELS[new_status]}'(으)로 바꿀 수 없습니다."
            )
        a["status"] = new_status
        hist = a.setdefault("history", [])
        hist.append({"at": _now_iso(), "to": new_status})
        _save_json(ASSIGN_PATH, rows)
        return True, f"상태가 '{STATUS_LABELS[new_status]}'(으)로 변경되었습니다."
    return False, "해당 작업을 찾을 수 없습니다."


def allowed_next(user_id: str, task_id: str) -> list[str]:
    a = get_assignment(user_id, task_id)
    if not a:
        return []
    return ALLOWED_TRANSITIONS.get(a.get("status", "pending"), [])


# ─────────────────────────────────────────────────────────────
# ② 공지 (announcements) — 전체 공유, 읽기 전용
# ─────────────────────────────────────────────────────────────
def list_announcements() -> list[dict]:
    data = _load_json(ANNOUNCE_PATH, [])
    rows = data if isinstance(data, list) else []
    # 최신순
    rows.sort(key=lambda x: x.get("posted_at", ""), reverse=True)
    return rows


# ─────────────────────────────────────────────────────────────
# ③ 문의 (inquiries) — 근로자별 로그 + Gmail 발송
# ─────────────────────────────────────────────────────────────
def _load_inquiries() -> list[dict]:
    data = _load_json(INQUIRY_PATH, [])
    return data if isinstance(data, list) else []


def list_my_inquiries(user_id: str) -> list[dict]:
    return [q for q in _load_inquiries() if q.get("from_id") == user_id]


def submit_inquiry(user: dict, subject: str, body: str,
                   send_email: bool = True) -> dict:
    """문의를 저장하고, 가능하면 gsk gmail send_email 로 발송.
    반환값: {ok, id, email_sent, email_error}"""
    subject = (subject or "").strip() or "(제목 없음)"
    body = (body or "").strip()
    rec = {
        "id":          "q_" + uuid.uuid4().hex[:8],
        "from_id":     user["id"],
        "from_name":   user.get("name", ""),
        "from_branch": user.get("branch", ""),
        "from_equip":  user.get("equipment", ""),
        "subject":     subject,
        "body":        body,
        "created_at":  _now_iso(),
        "email_sent":  False,
        "email_error": None,
        "recipient":   INQUIRY_RECIPIENT,
    }

    if send_email:
        ok, err = _send_gmail(
            to=INQUIRY_RECIPIENT,
            subject=f"[현장 문의] {user.get('branch','')} · "
                    f"{user.get('name','')} · {subject}",
            body=(
                f"보낸 사람 : {user.get('name','')} ({user['id']})\n"
                f"소속       : {user.get('branch','')}지점\n"
                f"장비       : {user.get('equipment','')}\n"
                f"작성 시각 : {rec['created_at']}\n"
                f"\n"
                f"────────────────────────\n"
                f"{body}\n"
                f"────────────────────────\n"
                f"\n"
                f"(모바일 근로자 앱에서 자동 발송)"
            ),
        )
        rec["email_sent"] = ok
        rec["email_error"] = err

    rows = _load_inquiries()
    rows.append(rec)
    _save_json(INQUIRY_PATH, rows)
    return rec


def _send_gmail(to: str, subject: str, body: str) -> tuple[bool, str | None]:
    """gsk gmail send_email 호출. 실패 시 (False, 에러메시지)."""
    try:
        proc = subprocess.run(
            [
                "gsk", "gmail", "send_email",
                "--recipient", to,
                "--subject", subject,
                "--body", body,
            ],
            capture_output=True, text=True, timeout=30,
        )
        if proc.returncode == 0:
            return True, None
        return False, (proc.stderr or proc.stdout or "unknown error").strip()[:300]
    except FileNotFoundError:
        return False, "gsk CLI 미설치 — 문의는 저장되었습니다."
    except subprocess.TimeoutExpired:
        return False, "메일 발송 시간 초과 — 문의는 저장되었습니다."
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"[:300]
