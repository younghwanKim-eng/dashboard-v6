"""
worker_app.py — 모바일 근로자용 Streamlit 앱.
app.py 의 main() 이 역할 분기 후 render(user, login_time) 를 호출한다.

하단 탭 4개:  🏠 홈 · 📋 내 업무 · ✅ 안전 점검 · 👤 내 정보
탭 전환은 URL 쿼리파라미터 ?m=worker&t=<home|tasks|safety|me> 로 처리한다.
"""
from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

import worker_data as wd
import worker_styles as ws

# 관리자 앱 재사용 함수들 (circular import — Python이 sys.modules를 재사용하므로 안전)
from app import (
    SAFETY_CHECK_ITEMS,
    compute_work_verdict,
    equipment_limits,
    filter_weather_for_user,
    generate_ground_tilt,
    load_equipment,
    load_weather,
    pick_allow_deg,
)


# ─────────────────────────────────────────────────────────────
# 공통 유틸
# ─────────────────────────────────────────────────────────────
def _current_tab() -> str:
    try:
        qp = st.query_params
        t = qp.get("t", "home")
    except Exception:
        qp = st.experimental_get_query_params()
        v = qp.get("t", ["home"])
        t = v[0] if v else "home"
    if isinstance(t, list):
        t = t[0] if t else "home"
    t = (t or "home").lower()
    return t if t in {"home", "tasks", "safety", "me"} else "home"


def _goto(tab: str, **extra):
    try:
        st.query_params.clear()
        st.query_params["m"] = "worker"
        st.query_params["t"] = tab
        for k, v in extra.items():
            st.query_params[k] = str(v)
    except Exception:
        qp = {"m": "worker", "t": tab}
        qp.update({k: str(v) for k, v in extra.items()})
        st.experimental_set_query_params(**qp)
    st.rerun()


def _verdict_level(verdict: dict) -> tuple[str, str, str]:
    """compute_work_verdict() 결과를 (level_code, badge_kind, 한글 요약 헤드라인)으로 변환.

    app.py 는 'risk_score' + 'verdict'(한글) + 'hard_stop_reason' 을 돌려주므로
    모바일 뱃지 체계 (ok/caution/stop) 로 매핑한다."""
    if verdict.get("hard_stop_reason"):
        return "STOP", "stop", "작업 중지 (법정 기준 초과)"
    score = int(verdict.get("risk_score", 0) or 0)
    if score < 30:
        return "OK", "ok", "작업 가능"
    if score < 60:
        return "CAUTION", "caution", "조건부 작업 가능 — 주의"
    return "STOP", "stop", "작업 중지 권고"


# ─────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────
def render(user: dict, login_time: datetime):
    ws.inject_mobile_shell()

    tab = _current_tab()
    title_map = {
        "home":   "오늘의 작업",
        "tasks":  "내 업무",
        "safety": "안전 점검",
        "me":     "내 정보",
    }
    ws.topbar(title_map.get(tab, "홈"),
              subtitle=f"{user.get('branch','')}지점 · {user.get('name','')}")

    # 공통 데이터 (가벼운 캐시 — app.py의 @st.cache_data 재사용)
    try:
        weather = load_weather()
        equip = load_equipment()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        _tabbar(tab)
        return
    tilt_df = generate_ground_tilt(n=600)
    matched_weather = filter_weather_for_user(weather, user["branch"], login_time)
    equip_limits_df = equipment_limits(equip, user["equipment"])

    verdict = compute_work_verdict(
        user, login_time, matched_weather, tilt_df, equip_limits_df
    )

    if tab == "home":
        _render_home(user, login_time, verdict, matched_weather, equip_limits_df)
    elif tab == "tasks":
        _render_tasks(user, verdict)
    elif tab == "safety":
        _render_safety(user, login_time, equip_limits_df)
    elif tab == "me":
        _render_me(user, login_time)

    _tabbar(tab)


def _tabbar(active: str):
    ws.tabbar(active, {"m": "worker"})


# ─────────────────────────────────────────────────────────────
# 🏠 홈
# ─────────────────────────────────────────────────────────────
def _render_home(user, login_time, verdict, matched_weather, equip_limits_df):
    today = datetime.now().strftime("%Y년 %m월 %d일 (%a)")
    st.markdown(f"**{today}** · 로그인 참조시각 `{login_time.strftime('%Y-%m-%d %H:%M')}`")

    # 큰 작업 가능 배너
    level, kind, headline = _verdict_level(verdict)
    icon = verdict.get("emoji") or {"OK": "✅", "CAUTION": "⚠️", "STOP": "🛑"}.get(level, "ℹ️")
    score = int(verdict.get("risk_score", 0) or 0)
    reasons = verdict.get("reasons") or []
    reason_txt = " · ".join(reasons[:2]) if reasons else "현재 조건 기준"
    hard = verdict.get("hard_stop_reason")
    if hard:
        reason_txt = hard
    st.markdown(
        f'''
        <div class="m-verdict {kind}">
          <div class="icon">{icon}</div>
          <div>
            <div class="title">{headline}</div>
            <div class="sub">종합 위험도 {score}/100 · {reason_txt}</div>
          </div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    # 핵심 수치 3개
    allow = pick_allow_deg(equip_limits_df)
    allow_txt = f"{allow:.2f}°" if allow is not None else "N/A"
    if not matched_weather.empty:
        max_wind = float(matched_weather["풍속(m/s)"].max() or 0)
        total_rain = float(matched_weather["강수량(mm)"].sum() or 0)
    else:
        max_wind, total_rain = 0.0, 0.0
    c1, c2, c3 = st.columns(3)
    with c1: ws.card("최대 풍속", f"{max_wind:.1f} m/s")
    with c2: ws.card("강수량", f"{total_rain:.1f} mm")
    with c3: ws.card("허용 경사", allow_txt)

    # 공지 (상단 2건)
    notices = wd.list_announcements()[:2]
    if notices:
        st.markdown("#### 📣 안전 공지")
        for n in notices:
            tag = "🚨" if n.get("level") == "critical" else "📌"
            st.markdown(
                f'''
                <div class="m-notice">
                  <div class="t">{tag} {n.get("title","")}</div>
                  <div class="d">{n.get("posted_at","")} · {n.get("posted_by","")}</div>
                  <div>{n.get("body","")}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

    # 오늘의 작업 요약
    tasks = wd.list_assignments(user["id"])
    st.markdown("#### 📋 오늘의 작업")
    if not tasks:
        st.info("오늘 배정된 작업이 없습니다.")
    else:
        for t in tasks[:3]:
            st_status = t.get("status", "pending")
            label = wd.STATUS_LABELS.get(st_status, st_status)
            kind  = wd.STATUS_BADGE_KIND.get(st_status, "wait")
            st.markdown(
                f'''
                <div class="m-card">
                  <div class="label">{t.get("scheduled_start","")} ~ {t.get("scheduled_end","")} · {t.get("site","")}</div>
                  <div class="value">{t.get("title","")}</div>
                  <div style="margin-top:6px;">{ws.badge(label, kind)}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )
        if st.button("내 업무 전체 보기", use_container_width=True):
            _goto("tasks")


# ─────────────────────────────────────────────────────────────
# 📋 내 업무
# ─────────────────────────────────────────────────────────────
def _render_tasks(user, verdict):
    # 단건 상세 보기?
    try:
        qp = st.query_params
        detail_id = qp.get("task", None)
    except Exception:
        qp = st.experimental_get_query_params()
        v = qp.get("task", [None])
        detail_id = v[0] if v else None
    if isinstance(detail_id, list):
        detail_id = detail_id[0] if detail_id else None

    if detail_id:
        _render_task_detail(user, detail_id, verdict)
        return

    # 목록
    tasks = wd.list_assignments(user["id"])
    if not tasks:
        st.info("오늘 배정된 작업이 없습니다. 관리자에게 문의해 주세요.")
        return

    # 상태별 그룹 (진행 중 → 대기 → 일시정지 → 검토요청 → 완료)
    order = ["in_progress", "pending", "paused", "review_requested", "done"]
    tasks_sorted = sorted(tasks, key=lambda t: order.index(t.get("status", "pending"))
                          if t.get("status", "pending") in order else 99)
    for t in tasks_sorted:
        st_status = t.get("status", "pending")
        label = wd.STATUS_LABELS.get(st_status, st_status)
        kind  = wd.STATUS_BADGE_KIND.get(st_status, "wait")
        st.markdown(
            f'''
            <div class="m-card">
              <div class="label">{t.get("scheduled_start","")} ~ {t.get("scheduled_end","")} · {t.get("site","")} · {t.get("equipment","")}</div>
              <div class="value">{t.get("title","")}</div>
              <div style="margin-top:6px;">{ws.badge(label, kind)}</div>
            </div>
            ''',
            unsafe_allow_html=True,
        )
        if st.button(f"상세 열기 · {t['id']}", key=f"open_{t['id']}",
                     use_container_width=True):
            _goto("tasks", task=t["id"])


def _render_task_detail(user, task_id, verdict):
    task = wd.get_assignment(user["id"], task_id)
    if not task:
        st.error("해당 작업을 찾을 수 없거나 접근 권한이 없습니다.")
        if st.button("← 내 업무로", use_container_width=True):
            _goto("tasks")
        return

    if st.button("← 내 업무 목록", use_container_width=True):
        _goto("tasks")

    st_status = task.get("status", "pending")
    label = wd.STATUS_LABELS.get(st_status, st_status)
    kind  = wd.STATUS_BADGE_KIND.get(st_status, "wait")

    st.markdown(f"### {task.get('title','')}")
    st.markdown(ws.badge(label, kind), unsafe_allow_html=True)

    st.markdown(
        f'''
        <div class="m-card">
          <div class="label">일정</div>
          <div class="value">{task.get("scheduled_date","")} · {task.get("scheduled_start","")} ~ {task.get("scheduled_end","")}</div>
        </div>
        <div class="m-card">
          <div class="label">현장 · 위치</div>
          <div class="value">{task.get("site","")} · {task.get("location","")}</div>
        </div>
        <div class="m-card">
          <div class="label">장비</div>
          <div class="value">{task.get("equipment","")}</div>
        </div>
        <div class="m-card">
          <div class="label">담당 관리자</div>
          <div class="value">{task.get("supervisor","")} · {task.get("supervisor_phone","")}</div>
        </div>
        ''',
        unsafe_allow_html=True,
    )

    st.markdown("**작업 내용**")
    for w in task.get("work_items", []):
        st.markdown(f"- {w}")

    sn = task.get("safety_notes")
    if sn:
        st.markdown(
            f'<div class="m-notice"><div class="t">⚠️ 안전 지시</div><div>{sn}</div></div>',
            unsafe_allow_html=True,
        )

    # 작업 가능 여부 요약
    lv, k, hd = _verdict_level(verdict)
    score = int(verdict.get("risk_score", 0) or 0)
    st.markdown(
        f'<div class="m-notice"><div class="t">금일 작업 가능 여부</div>'
        f'<div>{ws.badge(hd, k)} · 종합 위험도 {score}/100</div></div>',
        unsafe_allow_html=True,
    )

    # ─ 상태 변경 ─
    st.markdown("---")
    st.markdown("### 상태 변경")
    allowed = wd.allowed_next(user["id"], task_id)
    if not allowed:
        st.caption(f"현재 상태 '{label}' 에서는 추가 변경이 불가합니다.")
    else:
        for nxt in allowed:
            nxt_label = wd.TRANSITION_LABEL.get(nxt, wd.STATUS_LABELS[nxt])
            key = f"btn_{task_id}_{nxt}"
            if nxt == "review_requested":
                # 되돌리기 어려운 완료 보고 → 확인 모달
                if st.button(f"📨 {nxt_label}", key=key, use_container_width=True,
                             type="primary"):
                    st.session_state[f"_confirm_{task_id}"] = True
                if st.session_state.get(f"_confirm_{task_id}"):
                    st.warning(
                        "완료 보고 후에는 근로자가 상태를 되돌릴 수 없습니다. "
                        "관리자 승인 전까지 대기 상태가 됩니다."
                    )
                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("예, 보고합니다", key=f"yes_{task_id}",
                                     use_container_width=True, type="primary"):
                            ok, msg = wd.update_status(user["id"], task_id, nxt)
                            st.session_state.pop(f"_confirm_{task_id}", None)
                            (st.success if ok else st.error)(msg)
                            if ok:
                                st.rerun()
                    with c2:
                        if st.button("취소", key=f"no_{task_id}",
                                     use_container_width=True):
                            st.session_state.pop(f"_confirm_{task_id}", None)
                            st.rerun()
            else:
                if st.button(f"▶ {nxt_label}", key=key, use_container_width=True):
                    ok, msg = wd.update_status(user["id"], task_id, nxt)
                    (st.success if ok else st.error)(msg)
                    if ok:
                        st.rerun()

    # 상태 이력
    hist = task.get("history", [])
    if hist:
        with st.expander("🕒 상태 변경 이력"):
            for h in hist[::-1]:
                st.write(f"- {h.get('at','')} → "
                         f"**{wd.STATUS_LABELS.get(h.get('to',''), h.get('to',''))}**")


# ─────────────────────────────────────────────────────────────
# ✅ 안전 점검
# ─────────────────────────────────────────────────────────────
def _render_safety(user, login_time, equip_limits_df):
    allow = pick_allow_deg(equip_limits_df)
    equip = user.get("equipment", "")
    wind_limit = (
        "10 m/s" if "스카이" in equip else
        "18 m/s" if "크레인" in equip else "15 m/s"
    )

    header = f"**{user.get('name','')}** · {equip}"
    if allow is not None:
        header += f" · 허용 경사 **{allow:.2f}°**"
    st.markdown(header)
    st.caption(f"풍속 한계 참고치: {wind_limit}")

    with st.form("safety_form_mobile", clear_on_submit=False):
        checks: list[bool] = []
        for i, item in enumerate(SAFETY_CHECK_ITEMS):
            if isinstance(item, dict):
                label = item.get("label", item.get("name", f"항목 {i+1}"))
                hint = item.get("hint", "")
            elif isinstance(item, (tuple, list)) and len(item) >= 2:
                # app.py 포맷: (key, label)
                label = str(item[1])
                hint = ""
            else:
                label = str(item)
                hint = ""
            # 장비별 라벨 보정
            if "풍속" in label:
                label = f"{label} (한계 {wind_limit})"
            if "경사" in label and allow is not None:
                label = f"{label} (허용 ≤ {allow:.2f}°)"
            c = st.checkbox(f"**{i+1:02d}.** {label}", key=f"chk_m_{i}")
            if hint:
                st.caption(hint)
            checks.append(c)
        submitted = st.form_submit_button(
            "제출", use_container_width=True, type="primary"
        )

    if submitted:
        passed = sum(1 for c in checks if c)
        total = len(checks)
        rate = (passed / total * 100) if total else 0.0
        if rate >= 90:
            lv, lv_kind, lv_label = "OK", "ok", "✅ 점검 통과"
        elif rate >= 60:
            lv, lv_kind, lv_label = "CAUTION", "caution", "⚠️ 조건부 통과 (재확인)"
        else:
            lv, lv_kind, lv_label = "STOP", "stop", "🛑 점검 미흡 — 작업 중지 권고"

        # 세션 이력에 기록 (관리자 앱과 동일한 session_state 사용)
        log = st.session_state.setdefault("safety_check_log", [])
        log.append({
            "일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "작업자": user.get("name", ""),
            "장비": equip,
            "통과율": f"{rate:.0f}%",
            "결과": lv_label,
            "로그인시각": login_time.strftime("%Y-%m-%d %H:%M"),
        })

        st.markdown(
            f'<div class="m-verdict {lv_kind}">'
            f'<div class="icon">{"✅" if lv=="OK" else ("⚠️" if lv=="CAUTION" else "🛑")}</div>'
            f'<div><div class="title">{lv_label}</div>'
            f'<div class="sub">통과율 {rate:.0f}% ({passed}/{total})</div></div></div>',
            unsafe_allow_html=True,
        )
        if lv == "STOP":
            st.error("미흡 항목을 보완한 뒤 다시 제출하거나, 관리자에게 문의하세요.")

    # 오늘 제출 이력
    log = st.session_state.get("safety_check_log", [])
    today_str = datetime.now().strftime("%Y-%m-%d")
    today_log = [r for r in log if r.get("일시", "").startswith(today_str)
                 and r.get("작업자") == user.get("name", "")]
    if today_log:
        st.markdown("#### 오늘 제출 이력")
        st.dataframe(pd.DataFrame(today_log), hide_index=True,
                     use_container_width=True)


# ─────────────────────────────────────────────────────────────
# 👤 내 정보
# ─────────────────────────────────────────────────────────────
def _render_me(user, login_time):
    st.markdown("### 👤 내 프로필")
    ws.card("이름", user.get("name", ""))
    ws.card("아이디", f'`{user.get("id","")}`')
    ws.card("소속", f'{user.get("branch","")}지점')
    ws.card("장비", user.get("equipment", ""))
    ws.card("로그인 참조시각", login_time.strftime("%Y-%m-%d %H:%M:%S"))
    st.caption(
        "📝 이름·소속·장비는 **관리자만 수정** 가능합니다. "
        "변경이 필요하면 아래 '관리자에게 문의'로 요청해 주세요."
    )

    st.markdown("---")
    st.markdown("### ✉️ 관리자에게 문의")
    with st.form("inquiry_form"):
        subj = st.text_input("제목", placeholder="예: 안전장비 교체 요청")
        body = st.text_area("내용", placeholder="문의 내용을 입력하세요 (필수)",
                            height=140)
        send = st.form_submit_button("문의 보내기", use_container_width=True,
                                     type="primary")
    if send:
        if not (body or "").strip():
            st.error("문의 내용을 입력해 주세요.")
        else:
            rec = wd.submit_inquiry(user, subj, body, send_email=True)
            if rec.get("email_sent"):
                st.success(f"✉️ 관리자({rec['recipient']})에게 메일을 보냈습니다.")
            else:
                st.warning(
                    f"메일 발송은 실패했지만 문의는 저장되었습니다. "
                    f"관리자가 '내 정보' 이력에서 확인할 수 있습니다. "
                    f"(사유: {rec.get('email_error','')})"
                )
            st.rerun()

    # 내 문의 이력
    my = wd.list_my_inquiries(user["id"])
    if my:
        st.markdown("#### 📬 내 문의 이력")
        for q in sorted(my, key=lambda x: x.get("created_at", ""), reverse=True)[:10]:
            tag = "✅ 발송됨" if q.get("email_sent") else "💾 저장만"
            st.markdown(
                f'''
                <div class="m-card">
                  <div class="label">{q.get("created_at","")} · {tag}</div>
                  <div class="value">{q.get("subject","")}</div>
                  <div style="font-size:13px;color:#5A6C7D;margin-top:6px;white-space:pre-wrap;">{(q.get("body","") or "")[:200]}</div>
                </div>
                ''',
                unsafe_allow_html=True,
            )

    # 최근 점검 이력
    log = st.session_state.get("safety_check_log", [])
    mine = [r for r in log if r.get("작업자") == user.get("name", "")]
    if mine:
        st.markdown("---")
        st.markdown("### 🧰 최근 안전 점검 이력 (세션)")
        st.dataframe(pd.DataFrame(mine[-10:][::-1]), hide_index=True,
                     use_container_width=True)

    # 로그아웃
    st.markdown("---")
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.clear()
        try:
            st.query_params.clear()
        except Exception:
            st.experimental_set_query_params()
        st.rerun()
