"""
worker_styles.py — 모바일 근로자 앱 전용 CSS.
Streamlit 기본 UI 위에 모바일 반응형 스킨을 덮어씌운다.
- 사이드바·메인 메뉴·푸터 숨김
- 세로 1열 레이아웃 (최대 폭 480px, 중앙 정렬)
- 하단 고정 탭 바 (safe-area-inset-bottom 반영)
- 최소 터치 영역 44px
- 상태 뱃지, 카드 셸, sticky 하단 버튼
- Streamlit 라이트/다크 테마 기본 변수 활용
"""
from __future__ import annotations

import streamlit as st

# ── 브랜드 색상 토큰 (관리자 앱과 일치) ──
INK        = "#0F2940"
PAPER      = "#F6F2EA"
AMBER      = "#E8821E"
GREEN      = "#2E7D4F"
AMBER_SOFT = "#FFF4E6"
GREEN_SOFT = "#E8F5EE"
RED        = "#C0392B"
RED_SOFT   = "#FDECEA"
STEEL      = "#5A6C7D"
LINE       = "#E0DCC8"


def inject_mobile_shell():
    """모바일 레이아웃 CSS를 한 번만 주입한다."""
    if st.session_state.get("_mobile_css_injected"):
        return
    st.session_state["_mobile_css_injected"] = True
    st.markdown(
        f"""
        <style>
          /* ───────── 1. Streamlit 기본 UI 숨김/축소 ───────── */
          [data-testid="stSidebar"],
          [data-testid="collapsedControl"],
          header[data-testid="stHeader"],
          #MainMenu, footer {{ display:none !important; }}

          .stApp {{
            background:{PAPER};
            color:{INK};
          }}

          /* ───────── 2. 모바일 뷰포트 (최대 480px, 중앙) ───────── */
          .block-container {{
            padding:1rem 1rem 7rem 1rem !important;  /* 하단 탭 바(70px) 확보 */
            max-width:480px !important;
            margin-left:auto; margin-right:auto;
          }}

          /* 입력 요소 min 44px (iOS 접근성 기준) */
          .stButton>button, .stDownloadButton>button,
          .stTextInput input, .stTextArea textarea,
          .stSelectbox div[data-baseweb="select"] > div,
          .stRadio label, .stCheckbox label {{
            min-height:44px;
            font-size:16px !important;  /* iOS 자동 줌 방지 */
          }}
          .stButton>button {{
            border-radius:10px;
            font-weight:700;
          }}
          .stButton>button[kind="primary"] {{
            background:{AMBER}; color:#fff; border:0;
          }}

          /* ───────── 3. 모바일 상단 바 ───────── */
          .m-topbar {{
            position:sticky; top:0; z-index:50;
            margin:-1rem -1rem 1rem -1rem;
            padding:env(safe-area-inset-top) 1rem 0.75rem 1rem;
            padding-top:calc(env(safe-area-inset-top) + 0.75rem);
            background:{INK}; color:#fff;
            display:flex; align-items:center; justify-content:space-between;
          }}
          .m-topbar .t-title {{ font-weight:800; font-size:17px; }}
          .m-topbar .t-sub   {{ font-size:12px; color:#CFE0EE; letter-spacing:.04em; }}

          /* ───────── 4. 카드 쉘 ───────── */
          .m-card {{
            background:#fff; border:1px solid {LINE}; border-radius:12px;
            padding:14px 14px; margin:10px 0;
            box-shadow:0 1px 2px rgba(15,41,64,.04);
          }}
          .m-card .label {{ font-size:12px; color:{STEEL}; margin-bottom:4px; }}
          .m-card .value {{ font-size:18px; font-weight:700; color:{INK}; }}

          /* ───────── 5. 상태 뱃지 (텍스트 + 색 동시 표기) ───────── */
          .m-badge {{
            display:inline-block; padding:4px 10px; border-radius:999px;
            font-size:12px; font-weight:700;
          }}
          .m-badge.ok      {{ background:{GREEN_SOFT}; color:{GREEN}; }}
          .m-badge.caution {{ background:{AMBER_SOFT}; color:{AMBER}; }}
          .m-badge.stop    {{ background:{RED_SOFT};   color:{RED};   }}
          .m-badge.wait    {{ background:#EEF1F4;      color:{STEEL}; }}
          .m-badge.doing   {{ background:#E6F0FA;      color:#2563A6; }}
          .m-badge.paused  {{ background:#F3E8FF;      color:#7E22CE; }}
          .m-badge.review  {{ background:{AMBER_SOFT}; color:{AMBER}; }}
          .m-badge.done    {{ background:{GREEN_SOFT}; color:{GREEN}; }}

          /* ───────── 6. 작업 가능 큰 배너 (홈 상단) ───────── */
          .m-verdict {{
            border-radius:14px; padding:16px 16px;
            display:flex; align-items:center; gap:12px;
            color:#fff; margin:4px 0 12px 0;
          }}
          .m-verdict.ok      {{ background:linear-gradient(135deg,{GREEN},#1F5A38); }}
          .m-verdict.caution {{ background:linear-gradient(135deg,{AMBER},#B86614); color:#fff; }}
          .m-verdict.stop    {{ background:linear-gradient(135deg,{RED},#8B2A1F); }}
          .m-verdict .icon {{ font-size:34px; line-height:1; }}
          .m-verdict .title {{ font-weight:800; font-size:20px; }}
          .m-verdict .sub   {{ font-size:13px; opacity:.95; margin-top:2px; }}

          /* ───────── 7. 공지 알림 스트립 ───────── */
          .m-notice {{
            background:{AMBER_SOFT}; border-left:4px solid {AMBER};
            padding:10px 12px; border-radius:8px; margin:8px 0;
          }}
          .m-notice .t {{ font-weight:700; color:{INK}; font-size:14px; }}
          .m-notice .d {{ color:{STEEL}; font-size:12px; margin-top:2px; }}

          /* ───────── 8. 하단 탭 바 ───────── */
          .m-tabbar {{
            position:fixed; left:0; right:0; bottom:0; z-index:100;
            background:#fff; border-top:1px solid {LINE};
            padding:4px 0 calc(env(safe-area-inset-bottom) + 4px) 0;
            display:flex; justify-content:space-around;
          }}
          .m-tabbar .tab {{
            flex:1; min-height:52px;
            display:flex; flex-direction:column; align-items:center; justify-content:center;
            font-size:11px; color:{STEEL}; text-decoration:none; gap:2px;
          }}
          .m-tabbar .tab .ic {{ font-size:20px; }}
          .m-tabbar .tab.active {{ color:{AMBER}; font-weight:700; }}

          /* ───────── 9. 폼 간격 ───────── */
          .stCheckbox {{ padding:4px 0; }}
          .stCheckbox label {{ font-size:15px; }}
          hr {{ border:0; border-top:1px solid {LINE}; margin:10px 0; }}

          /* ───────── 10. 반응형 (더 큰 화면에서도 중앙 정렬 유지) ───────── */
          @media (min-width:900px) {{
            .block-container {{ max-width:480px !important; }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ── 공통 UI helper ──
def topbar(title: str, subtitle: str = ""):
    st.markdown(
        f"""
        <div class="m-topbar">
          <div>
            <div class="t-sub">AISoft SAFETY</div>
            <div class="t-title">{title}</div>
          </div>
          <div class="t-sub">{subtitle}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def tabbar(active: str, base_params: dict):
    """하단 탭 바. active in {home, tasks, safety, me}.
    각 탭은 ?m=worker&t=<name>으로 이동한다."""
    def _link(name: str, icon: str, label: str) -> str:
        qp = dict(base_params)
        qp["t"] = name
        q = "&".join(f"{k}={v}" for k, v in qp.items())
        cls = "tab active" if active == name else "tab"
        return (
            f'<a class="{cls}" href="?{q}" target="_self">'
            f'<span class="ic">{icon}</span><span>{label}</span></a>'
        )

    html = (
        '<div class="m-tabbar">'
        + _link("home",   "🏠", "홈")
        + _link("tasks",  "📋", "내 업무")
        + _link("safety", "✅", "안전 점검")
        + _link("me",     "👤", "내 정보")
        + "</div>"
    )
    st.markdown(html, unsafe_allow_html=True)


def card(label: str, value: str):
    st.markdown(
        f'<div class="m-card"><div class="label">{label}</div>'
        f'<div class="value">{value}</div></div>',
        unsafe_allow_html=True,
    )


def badge(text: str, kind: str) -> str:
    return f'<span class="m-badge {kind}">{text}</span>'
