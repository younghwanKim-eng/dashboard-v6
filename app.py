"""
중장비 전도 예방 대시보드
- VSCode + Streamlit 환경에서 실행
- 실행 방법: streamlit run app.py

요구사항:
1. 재해 유형: 중장비 전도
2. 사용 중장비: 이동식 크레인, 굴착기, 지게차, 레미콘, 펌프카, 덤프트럭, 스카이, 카고트럭(윙바디)
3. 임의 지반 기울기 데이터 (경·위도 등 인증 데이터 제외)
4. 건설장비 7종 지반 경사도·전도 한계 종합 데이터표 (equipment_slope_data.csv) 활용
5. 2018.xls 날씨 데이터 활용
6. 로그인(아이디/패스워드 배열 기반)
7. 로그인 시 소속(지점명) 기준 + 시간 2018~2025, 06:00~17:00 사이로 지정
8. 로그인 후 → 사용자 정보 화면 + 대시보드 화면
"""

from __future__ import annotations

import hashlib
import io
import random
from datetime import datetime, time, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 0. 기본 설정
# ============================================================
st.set_page_config(
    page_title="중장비 전도 예방 대시보드",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE = Path(__file__).resolve().parent
DATA_DIR = BASE / "data"
WEATHER_PATH = DATA_DIR / "2018.xls"
EQUIP_PATH = DATA_DIR / "equipment_slope_data.csv"

# 요구사항 2 - 사용 할 중장비 목록
EQUIPMENT_LIST = [
    "이동식 크레인",
    "굴착기",
    "지게차",
    "레미콘",
    "펌프카",
    "덤프트럭",
    "스카이(고소작업차)",
    "카고트럭(윙바디)",
]

# 재해 유형
ACCIDENT_TYPE = "중장비 전도"

# ============================================================
# 1. 사용자 배열 (요구사항 6)
# 아이디, 패스워드, 이름, 소속(지점명), 건설기계장비명
# 소속은 2018.xls의 실제 지점명(속초, 서울, 대전, 대구, 광주, 태백)에 맞춤
# ============================================================
def _hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


USERS = [
    # ─ 관리자 1명 (v6 신규) : 관리자 대시보드 전용 ─
    {"id": "admin01",   "pw": _hash_pw("1234"), "name": "관리자",
     "branch": "본사", "equipment": "-", "role": "admin"},
    # ─ 현장 근로자 8명 : 기본 진입은 모바일 홈 ─
    {"id": "sokcho01",  "pw": _hash_pw("1234"), "name": "김현장",
     "branch": "속초", "equipment": "이동식 크레인", "role": "worker"},
    {"id": "seoul01",   "pw": _hash_pw("1234"), "name": "이안전",
     "branch": "서울", "equipment": "굴착기", "role": "worker"},
    {"id": "daejeon01", "pw": _hash_pw("1234"), "name": "박관리",
     "branch": "대전", "equipment": "지게차", "role": "worker"},
    {"id": "daegu01",   "pw": _hash_pw("1234"), "name": "최기사",
     "branch": "대구", "equipment": "레미콘", "role": "worker"},
    {"id": "gwangju01", "pw": _hash_pw("1234"), "name": "정반장",
     "branch": "광주", "equipment": "펌프카", "role": "worker"},
    {"id": "taebaek01", "pw": _hash_pw("1234"), "name": "홍작업",
     "branch": "태백", "equipment": "덤프트럭", "role": "worker"},
    {"id": "seoul02",   "pw": _hash_pw("1234"), "name": "조소장",
     "branch": "서울", "equipment": "스카이(고소작업차)", "role": "worker"},
    {"id": "daegu02",   "pw": _hash_pw("1234"), "name": "강운전",
     "branch": "대구", "equipment": "카고트럭(윙바디)", "role": "worker"},
]


def authenticate(uid: str, pw: str):
    h = _hash_pw(pw)
    for u in USERS:
        if u["id"] == uid and u["pw"] == h:
            return {k: v for k, v in u.items() if k != "pw"}
    return None


# ============================================================
# 2. 데이터 로더
# ============================================================
@st.cache_data(show_spinner=False)
def load_weather() -> pd.DataFrame:
    """2018.xls 날씨 데이터 로드 (풍속, 일시, 강수량, 적설량, 풍향, 시정)."""
    df = pd.read_excel(WEATHER_PATH)
    df["일시"] = pd.to_datetime(df["일시"], errors="coerce")
    # 숫자형 변환
    for col in ["강수량(mm)", "풍속(m/s)", "풍향(16방위)", "적설(cm)", "시정(10m)"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def load_equipment() -> pd.DataFrame:
    """건설장비 지반 경사도·전도 한계 종합 데이터."""
    df = pd.read_csv(EQUIP_PATH)
    return df


# ============================================================
# 3. 임의 지반 기울기 데이터 (요구사항 3)
# 경·위도 등 인증서 필요한 데이터 제외
# ============================================================
@st.cache_data(show_spinner=False)
def generate_ground_tilt(n: int = 500, seed: int = 42) -> pd.DataFrame:
    """
    중장비 전도 사고 방지용 임의 지반 기울기 데이터 생성.
    경·위도 등 인증 데이터는 포함하지 않는다.
    """
    rng = np.random.default_rng(seed)
    rows = []
    base = datetime(2018, 1, 1, 6, 0)
    for i in range(n):
        branch = rng.choice(["속초", "서울", "대전", "대구", "광주", "태백"])
        equip = rng.choice(EQUIPMENT_LIST)
        # 임의 기울기 (전후·좌우), 단위: 도(°)
        tilt_fb = round(float(rng.normal(1.2, 1.1)), 2)  # 전후
        tilt_lr = round(float(rng.normal(1.0, 1.0)), 2)  # 좌우
        tilt_fb = max(0.0, tilt_fb)
        tilt_lr = max(0.0, tilt_lr)
        soil = rng.choice(["다짐 사질토", "점성토", "되메움토", "쇄석 포설", "콘크리트"])
        pad = bool(rng.random() < 0.7)  # 받침판 사용 여부
        hours = rng.integers(0, 11)  # 6~17시
        minutes = rng.integers(0, 60)
        ts = base + timedelta(days=int(rng.integers(0, 365 * 3)),
                              hours=int(hours), minutes=int(minutes))
        rows.append({
            "측정시각": ts,
            "지점명": branch,
            "장비명": equip,
            "전후기울기(°)": tilt_fb,
            "좌우기울기(°)": tilt_lr,
            "최대기울기(°)": max(tilt_fb, tilt_lr),
            "지반종류": soil,
            "받침판사용": pad,
        })
    df = pd.DataFrame(rows)
    df = df.sort_values("측정시각").reset_index(drop=True)
    return df


# ============================================================
# 4. 장비별 전도 한계 매핑 (equipment_slope_data.csv 기반)
# 요구사항 4: 7종 지반 경사도·전도 한계
# ============================================================
# 사용자 장비명 → equipment_slope_data.csv group_ko 매핑
EQUIP_TO_GROUP = {
    "이동식 크레인":       ["크롤러 크레인"],
    "굴착기":              ["휠굴착기"],
    "지게차":              ["지게차"],
    "레미콘":              ["덤프트럭"],  # 레미콘 트럭은 덤프트럭과 유사한 차량 기준 적용(참고용)
    "펌프카":              ["콘크리트 펌프카"],
    "덤프트럭":            ["덤프트럭"],
    "스카이(고소작업차)":  ["고소작업차(스카이)"],
    "카고트럭(윙바디)":    ["카고트럭/윙바디"],
}


def equipment_limits(equip_df: pd.DataFrame, equip_name: str) -> pd.DataFrame:
    groups = EQUIP_TO_GROUP.get(equip_name, [])
    if not groups:
        return equip_df.iloc[0:0]
    return equip_df[equip_df["group_ko"].isin(groups)].copy()


def pick_allow_deg(sub: pd.DataFrame) -> float | None:
    """장비 서브셋에서 allow_work_deg를 숫자로 추출 (가장 보수적인 값)."""
    vals = []
    for v in sub["allow_work_deg"].astype(str):
        v = v.strip()
        if v.startswith("<="):
            try:
                vals.append(float(v.replace("<=", "").strip()))
            except ValueError:
                pass
        else:
            try:
                vals.append(float(v))
            except ValueError:
                pass
    return min(vals) if vals else None


def pick_overturn_deg(sub: pd.DataFrame) -> float | None:
    """전도 임계각(가장 작은 값=가장 보수적)."""
    vals = []
    for v in sub["overturn_deg"].astype(str):
        for token in v.replace("/", " ").split():
            try:
                vals.append(float(token))
            except ValueError:
                pass
    return min(vals) if vals else None


# ============================================================
# 5. 로그인 화면 (요구사항 6, 7)
# ============================================================
def render_login():
    st.title("🏗️ 중장비 전도 예방 시스템 — 로그인")
    st.caption("재해 유형: **중장비 전도** / 사용 중장비 8종")

    with st.form("login_form"):
        uid = st.text_input("아이디", placeholder="예: sokcho01")
        pw = st.text_input("비밀번호", type="password",
                           placeholder="예: 1234")
        submit = st.form_submit_button("로그인", use_container_width=True)

    with st.expander("🔑 개발용 테스트 계정 (아이디 / 비밀번호)"):
        for u in USERS:
            role_tag = "👔 관리자" if u.get("role") == "admin" else "👷 근로자"
            st.write(
                f"- `{u['id']}` / `1234` — {role_tag} · {u['name']} / "
                f"{u['branch']}지점 / {u['equipment']}"
            )
        st.caption(
            "💡 **근로자 계정**은 로그인하면 모바일 홈으로, "
            "**관리자 계정(admin01)**은 관리자 대시보드로 자동 진입합니다. "
            "주소창에 `?m=admin` 또는 `?m=worker`를 붙여 수동 전환 가능합니다."
        )

    if submit:
        user = authenticate(uid.strip(), pw.strip())
        if user is None:
            st.error("아이디 또는 비밀번호가 일치하지 않습니다.")
            return

        # 로그인 성공 → 요구사항 7
        # 로그인 시점의 시간정보를 2018~2025, 06:00~17:00 사이로 임의 지정
        rng = random.Random(hash((user["id"], datetime.now().isoformat())))
        year = rng.randint(2018, 2025)
        month = rng.randint(1, 12)
        day = rng.randint(1, 28)
        hour = rng.randint(6, 17)
        minute = rng.randint(0, 59)
        login_time = datetime(year, month, day, hour, minute, 0)

        st.session_state["user"] = user
        st.session_state["login_time"] = login_time
        st.rerun()


# ============================================================
# 6. 로그인 후 화면 (요구사항 8)
# 사용자 정보 + 대시보드
# ============================================================
def filter_weather_for_user(weather: pd.DataFrame, branch: str,
                            login_time: datetime) -> pd.DataFrame:
    """
    로그인 사용자의 소속(지점명)과 로그인 시간정보를 기준으로
    엑셀파일 값과 대조하여 추출. (요구사항 7)
    - 지점명 일치
    - 날짜 일치 (해당 날짜의 06:00~17:00 전체)
    - 데이터 범위를 벗어나면 가장 가까운 날짜로 fallback
    """
    df = weather[weather["지점명"] == branch].copy()
    if df.empty:
        return df

    target_date = login_time.date()
    df["_date"] = df["일시"].dt.date

    day_df = df[df["_date"] == target_date]
    if day_df.empty:
        # 2018.xls는 2018~2020 범위 → 가장 가까운 날 매칭
        all_dates = pd.Series(df["_date"].unique())
        all_dates_dt = pd.to_datetime(all_dates)
        nearest_idx = (all_dates_dt - pd.Timestamp(target_date)).abs().idxmin()
        nearest = all_dates.iloc[nearest_idx]
        day_df = df[df["_date"] == nearest].copy()
        day_df["_fallback_date"] = nearest

    # 06:00 ~ 17:00
    day_df = day_df[(day_df["일시"].dt.hour >= 6) &
                    (day_df["일시"].dt.hour <= 17)]
    return day_df.drop(columns=["_date"], errors="ignore")


def kpi_row(user, login_time, matched_count, equip_limits_df):
    allow = pick_allow_deg(equip_limits_df)
    overturn = pick_overturn_deg(equip_limits_df)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👤 이름", user["name"])
    c2.metric("🕒 시간", login_time.strftime("%Y-%m-%d %H:%M"))
    c3.metric("🏗️ 건설기계장비명", user["equipment"])
    c4.metric("📍 소속", f"{user['branch']}지점")

    c5, c6, c7, c8 = st.columns(4)
    c5.metric("🚨 재해 유형", ACCIDENT_TYPE)
    c6.metric("📊 매칭 날씨 기록", f"{matched_count:,} 건")
    c7.metric("허용 작업 경사(°)",
              f"{allow:.2f}" if allow is not None else "제조사 기준")
    c8.metric("전도 임계각(°)",
              f"{overturn:.2f}" if overturn is not None else "N/A")


def render_user_info_tab(user, login_time, matched_weather, equip_limits_df):
    st.subheader("👤 로그인 사용자 정보")
    info = pd.DataFrame([{
        "이름": user["name"],
        "아이디": user["id"],
        "소속(지점명)": user["branch"],
        "건설기계장비명": user["equipment"],
        "로그인 시간": login_time.strftime("%Y-%m-%d %H:%M:%S"),
        "재해 유형": ACCIDENT_TYPE,
    }])
    st.table(info)

    st.subheader(f"🌤️ 소속·시간 대조 결과 — {user['branch']}지점")
    if matched_weather.empty:
        st.warning("해당 지점/시간에 매칭되는 날씨 데이터가 없습니다.")
    else:
        if "_fallback_date" in matched_weather.columns:
            st.info(
                f"⚠️ 로그인 시간({login_time.date()})은 날씨 데이터 범위 밖입니다. "
                f"가장 가까운 날짜({matched_weather['_fallback_date'].iloc[0]}) "
                "데이터를 대조에 사용했습니다."
            )
        st.dataframe(
            matched_weather.drop(columns=["_fallback_date"], errors="ignore"),
            hide_index=True, use_container_width=True
        )

        # 다운로드
        csv = matched_weather.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "📥 소속·시간 대조 결과 CSV 다운로드",
            data=csv,
            file_name=f"matched_{user['branch']}_"
                      f"{login_time.strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv",
        )

    st.subheader(f"📋 장비 전도 한계 — {user['equipment']}")
    if equip_limits_df.empty:
        st.info("해당 장비의 한계 데이터가 없습니다.")
    else:
        st.dataframe(equip_limits_df, hide_index=True,
                     use_container_width=True)


def render_dashboard_tab(user, login_time, matched_weather, tilt_df,
                         equip_limits_df):
    st.subheader(f"📊 대시보드 — {user['branch']}지점 / {user['equipment']}")

    allow = pick_allow_deg(equip_limits_df) or 3.0
    overturn = pick_overturn_deg(equip_limits_df)

    # ---- 날씨 요약 KPI ----
    if not matched_weather.empty:
        st.markdown("### 1) 기상 요약 (해당 지점·날짜 06:00~17:00)")
        c1, c2, c3, c4, c5 = st.columns(5)
        c1.metric("평균 풍속(m/s)",
                  f"{matched_weather['풍속(m/s)'].mean():.2f}")
        c2.metric("최대 풍속(m/s)",
                  f"{matched_weather['풍속(m/s)'].max():.2f}")
        c3.metric("총 강수량(mm)",
                  f"{matched_weather['강수량(mm)'].sum():.1f}")
        c4.metric("최대 적설(cm)",
                  f"{matched_weather['적설(cm)'].max():.1f}")
        c5.metric("최소 시정(10m)",
                  f"{matched_weather['시정(10m)'].min():.0f}")

        # 풍속 라인 차트
        wx = matched_weather.sort_values("일시")
        fig_wind = px.line(
            wx, x="일시", y="풍속(m/s)",
            markers=True,
            title="시간대별 풍속 추이",
        )
        # 중장비 전도 관련 작업중지 풍속(10m/s = 고소작업차 기준) 경계선
        fig_wind.add_hline(
            y=10, line_dash="dash", line_color="orange",
            annotation_text="고소작업차 작업중지(10 m/s)",
        )
        fig_wind.add_hline(
            y=18, line_dash="dash", line_color="red",
            annotation_text="크롤러 크레인 작업중지(18 m/s)",
        )
        st.plotly_chart(fig_wind, use_container_width=True)

        # 강수량 + 적설 조합
        fig_rain = go.Figure()
        fig_rain.add_trace(go.Bar(
            x=wx["일시"], y=wx["강수량(mm)"], name="강수량(mm)",
            marker_color="#4C9AFF",
        ))
        fig_rain.add_trace(go.Scatter(
            x=wx["일시"], y=wx["적설(cm)"], name="적설(cm)",
            mode="lines+markers", yaxis="y2",
            marker_color="#A569BD",
        ))
        fig_rain.update_layout(
            title="강수량 · 적설 추이",
            yaxis=dict(title="강수량(mm)"),
            yaxis2=dict(title="적설(cm)", overlaying="y", side="right"),
            legend=dict(orientation="h", y=-0.2),
        )
        st.plotly_chart(fig_rain, use_container_width=True)

        # 풍향 분포 (16방위를 각도로 보고 극좌표)
        if "풍향(16방위)" in wx.columns:
            wind_rose = wx.dropna(subset=["풍향(16방위)", "풍속(m/s)"])
            if not wind_rose.empty:
                fig_rose = px.bar_polar(
                    wind_rose, r="풍속(m/s)", theta="풍향(16방위)",
                    color="풍속(m/s)",
                    color_continuous_scale="Viridis",
                    title="풍향·풍속 분포 (풍향: 0~360°)",
                )
                st.plotly_chart(fig_rose, use_container_width=True)

    # ---- 지반 기울기 분석 ----
    st.markdown("### 2) 임의 지반 기울기 — 전도 사고 방지 분석")
    st.caption(
        "경·위도 등 인증 데이터는 포함하지 않은 임의 생성 데이터입니다."
    )

    user_tilt = tilt_df[
        (tilt_df["지점명"] == user["branch"]) &
        (tilt_df["장비명"] == user["equipment"])
    ].copy()

    if user_tilt.empty:
        # 지점 전체로 fallback
        user_tilt = tilt_df[tilt_df["지점명"] == user["branch"]].copy()
        st.info("해당 장비 데이터가 적어 지점 전체 장비 데이터를 표시합니다.")

    if not user_tilt.empty:
        # 위험 분류
        def classify(deg):
            if deg >= allow:
                if overturn is not None and deg >= overturn:
                    return "🔴 전도 위험"
                return "🟠 작업중지 권고"
            if deg >= allow * 0.7:
                return "🟡 주의"
            return "🟢 안전"

        user_tilt["판정"] = user_tilt["최대기울기(°)"].apply(classify)

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("🟢 안전",
                  f"{(user_tilt['판정'] == '🟢 안전').sum()} 건")
        c2.metric("🟡 주의",
                  f"{(user_tilt['판정'] == '🟡 주의').sum()} 건")
        c3.metric("🟠 작업중지",
                  f"{(user_tilt['판정'] == '🟠 작업중지 권고').sum()} 건")
        c4.metric("🔴 전도 위험",
                  f"{(user_tilt['판정'] == '🔴 전도 위험').sum()} 건")

        # 산점도: 전후 vs 좌우 기울기 + 허용/임계 경계선
        fig_tilt = px.scatter(
            user_tilt, x="전후기울기(°)", y="좌우기울기(°)",
            color="판정", symbol="지반종류",
            hover_data=["측정시각", "장비명", "받침판사용"],
            color_discrete_map={
                "🟢 안전": "#2ECC71",
                "🟡 주의": "#F1C40F",
                "🟠 작업중지 권고": "#E67E22",
                "🔴 전도 위험": "#E74C3C",
            },
            title=f"지반 기울기 분포 — 허용 작업 경사 {allow:.2f}°",
        )
        fig_tilt.add_vline(x=allow, line_dash="dash", line_color="orange")
        fig_tilt.add_hline(y=allow, line_dash="dash", line_color="orange")
        if overturn is not None:
            fig_tilt.add_vline(x=overturn, line_dash="dot",
                               line_color="red")
            fig_tilt.add_hline(y=overturn, line_dash="dot",
                               line_color="red")
        st.plotly_chart(fig_tilt, use_container_width=True)

        # 판정 분포 파이
        pie_df = user_tilt["판정"].value_counts().reset_index()
        pie_df.columns = ["판정", "건수"]
        fig_pie = px.pie(
            pie_df, names="판정", values="건수",
            title="판정 분포",
            color="판정",
            color_discrete_map={
                "🟢 안전": "#2ECC71",
                "🟡 주의": "#F1C40F",
                "🟠 작업중지 권고": "#E67E22",
                "🔴 전도 위험": "#E74C3C",
            },
        )
        st.plotly_chart(fig_pie, use_container_width=True)

        # 지반 종류별 평균 기울기
        soil_mean = (user_tilt.groupby("지반종류")["최대기울기(°)"]
                     .mean().reset_index().sort_values("최대기울기(°)"))
        fig_soil = px.bar(
            soil_mean, x="지반종류", y="최대기울기(°)",
            color="최대기울기(°)",
            color_continuous_scale="RdYlGn_r",
            title="지반 종류별 평균 최대 기울기",
        )
        fig_soil.add_hline(y=allow, line_dash="dash",
                           line_color="red",
                           annotation_text=f"허용 {allow:.2f}°")
        st.plotly_chart(fig_soil, use_container_width=True)

        # 상세 테이블
        with st.expander("📋 임의 지반 기울기 원본 데이터"):
            st.dataframe(user_tilt, hide_index=True,
                         use_container_width=True)

    # ---- 종합 위험도 (풍속 + 기울기) ----
    st.markdown("### 3) 종합 전도 위험도")
    risk_score = 0
    reasons = []
    if not matched_weather.empty:
        max_wind = matched_weather["풍속(m/s)"].max()
        if max_wind >= 18:
            risk_score += 40
            reasons.append(f"최대 풍속 {max_wind:.1f} m/s ≥ 18 (크레인 작업중지)")
        elif max_wind >= 10:
            risk_score += 25
            reasons.append(f"최대 풍속 {max_wind:.1f} m/s ≥ 10 (고소작업차 중지)")
        elif max_wind >= 7:
            risk_score += 10
            reasons.append(f"최대 풍속 {max_wind:.1f} m/s (주의)")

        max_snow = matched_weather["적설(cm)"].max()
        if pd.notna(max_snow) and max_snow >= 5:
            risk_score += 15
            reasons.append(f"적설 {max_snow:.1f} cm")

        total_rain = matched_weather["강수량(mm)"].sum()
        if pd.notna(total_rain) and total_rain >= 20:
            risk_score += 15
            reasons.append(f"총 강수량 {total_rain:.1f} mm (지반 연약 우려)")

    if not user_tilt.empty:
        danger_cnt = (user_tilt["판정"]
                      .isin(["🟠 작업중지 권고", "🔴 전도 위험"]).sum())
        if danger_cnt > 0:
            risk_score += min(30, danger_cnt * 3)
            reasons.append(f"기울기 위험 기록 {danger_cnt} 건")

    risk_score = min(100, risk_score)
    color = ("#2ECC71" if risk_score < 30 else
             "#F1C40F" if risk_score < 60 else "#E74C3C")

    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=risk_score,
        title={"text": f"{user['equipment']} 전도 위험도 (0~100)"},
        gauge={
            "axis": {"range": [0, 100]},
            "bar": {"color": color},
            "steps": [
                {"range": [0, 30],  "color": "#D5F5E3"},
                {"range": [30, 60], "color": "#FCF3CF"},
                {"range": [60, 100],"color": "#FADBD8"},
            ],
        },
    ))
    st.plotly_chart(fig_gauge, use_container_width=True)

    if reasons:
        st.warning("위험 요인:\n- " + "\n- ".join(reasons))
    else:
        st.success("특이 위험 요인이 감지되지 않았습니다.")

    st.caption(
        "※ ‘📣 금일 건설기계장비 작업 가능 여부’ 판정 배너는 "
        "화면 상단(탭 메뉴 위)에 공통 표시됩니다."
    )



# ============================================================
# 6-C. 금일 작업 가능 여부 — 공통 계산 + 상단 배너
# ============================================================
def compute_work_verdict(user, login_time, matched_weather, tilt_df,
                         equip_limits_df):
    """종합 전도 위험도와 금일 작업 가능 여부를 계산해 dict 로 반환."""
    allow = pick_allow_deg(equip_limits_df) or 3.0
    overturn = pick_overturn_deg(equip_limits_df)

    # 1) 위험 점수 집계 (대시보드 탭과 동일 로직)
    risk_score = 0
    reasons = []

    max_wind = None
    if not matched_weather.empty:
        mw = matched_weather["풍속(m/s)"].max()
        if pd.notna(mw):
            max_wind = float(mw)
            if max_wind >= 18:
                risk_score += 40
                reasons.append(
                    f"최대 풍속 {max_wind:.1f} m/s ≥ 18 (크레인 작업중지)")
            elif max_wind >= 10:
                risk_score += 25
                reasons.append(
                    f"최대 풍속 {max_wind:.1f} m/s ≥ 10 (고소작업차 중지)")
            elif max_wind >= 7:
                risk_score += 10
                reasons.append(f"최대 풍속 {max_wind:.1f} m/s (주의)")

        max_snow = matched_weather["적설(cm)"].max()
        if pd.notna(max_snow) and max_snow >= 5:
            risk_score += 15
            reasons.append(f"적설 {max_snow:.1f} cm")

        total_rain = matched_weather["강수량(mm)"].sum()
        if pd.notna(total_rain) and total_rain >= 20:
            risk_score += 15
            reasons.append(f"총 강수량 {total_rain:.1f} mm (지반 연약 우려)")

    # 임의 지반 기울기 — 해당 지점·장비 기준
    user_tilt = tilt_df[
        (tilt_df["지점명"] == user["branch"]) &
        (tilt_df["장비명"] == user["equipment"])
    ]
    if not user_tilt.empty:
        danger_cnt = ((user_tilt["최대기울기(°)"] >= allow).sum())
        if danger_cnt > 0:
            risk_score += min(30, int(danger_cnt) * 3)
            reasons.append(f"기울기 위험 기록 {int(danger_cnt)} 건")

    risk_score = min(100, int(risk_score))

    # 2) 기본 판정 (초록/노랑/빨강)
    today_str = login_time.strftime("%Y-%m-%d")
    if risk_score < 30:
        verdict = "작업 가능"
        color = "#2ECC71"
        emoji = "✅"
        detail = (f"오늘({today_str}) <b>{user['equipment']}</b> 작업을 "
                  "진행하셔도 됩니다. 다만 작업 전 아웃트리거/받침판 등 "
                  "기본 안전조치는 반드시 확인하세요.")
    elif risk_score < 60:
        verdict = "조건부 작업 가능 (주의)"
        color = "#F1C40F"
        emoji = "⚠️"
        detail = (f"오늘({today_str})은 주의가 필요한 날입니다. "
                  f"<b>{user['equipment']}</b> 작업은 가능하지만, 아래 위험 요인을 "
                  "현장에서 재확인하고 책임자 승인 후 진행하세요.")
    else:
        verdict = "작업 중지 권고"
        color = "#E74C3C"
        emoji = "🛑"
        detail = (f"오늘({today_str})은 전도 위험이 높아 "
                  f"<b>{user['equipment']}</b> 작업을 중지하실 것을 권고합니다. "
                  "기상 상황이 개선된 후 재평가하세요.")

    # 3) 장비별 법정 하드 룰 오버라이드
    hard_stop_reason = None
    if max_wind is not None:
        if user["equipment"] == "스카이(고소작업차)" and max_wind >= 10:
            hard_stop_reason = (
                f"고소작업차 작업중지 기준 10 m/s 초과 "
                f"(측정 최대 풍속 {max_wind:.1f} m/s)")
        elif user["equipment"] == "이동식 크레인" and max_wind >= 18:
            hard_stop_reason = (
                f"크레인 작업중지 기준 18 m/s 초과 "
                f"(측정 최대 풍속 {max_wind:.1f} m/s)")
    if hard_stop_reason:
        verdict = "작업 중지 (법정 기준 초과)"
        color = "#E74C3C"
        emoji = "🛑"
        detail = (f"오늘({today_str}) <b>{user['equipment']}</b> 작업은 "
                  f"<b>금지</b>됩니다. 사유: {hard_stop_reason}.")

    return {
        "risk_score":       risk_score,
        "reasons":          reasons,
        "allow":            allow,
        "overturn":         overturn,
        "verdict":          verdict,
        "color":            color,
        "emoji":            emoji,
        "detail":           detail,
        "hard_stop_reason": hard_stop_reason,
    }


def render_work_verdict_banner(user, verdict_payload):
    """부제목 바로 밑에 들어가는 큰 작업 가능 여부 배너."""
    p = verdict_payload
    st.markdown("### 📣 금일 건설기계장비 작업 가능 여부")
    st.markdown(
        f"""
        <div style="
            background: {p['color']}22;
            border: 2px solid {p['color']};
            border-radius: 12px;
            padding: 20px;
            margin: 6px 0 14px 0;
            text-align: center;
        ">
            <div style="font-size: 40px;">{p['emoji']}</div>
            <div style="
                font-size: 28px;
                font-weight: 700;
                color: {p['color']};
                margin: 8px 0;
            ">{p['verdict']}</div>
            <div style="font-size: 15px; color: #333; line-height: 1.6;">
                {p['detail']}
            </div>
            <div style="
                font-size: 12px;
                color: #666;
                margin-top: 12px;
            ">
                위험도 점수 {p['risk_score']} / 100 ·
                장비 {user['equipment']} ·
                지점 {user['branch']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.expander("판정 근거 상세 보기"):
        st.write(f"- 종합 위험도 점수: **{p['risk_score']} / 100**")
        st.write(f"- 장비 허용 작업 경사: **{p['allow']:.2f}°**")
        if p["overturn"] is not None:
            st.write(f"- 장비 전도 임계각: **{p['overturn']:.2f}°**")
        if p["reasons"]:
            st.write("- 위험 요인:")
            for r in p["reasons"]:
                st.write(f"    - {r}")
        else:
            st.write("- 위험 요인: 특이사항 없음")
        if p["hard_stop_reason"]:
            st.error(f"⚠️ 법정 하드 룰 적용: {p['hard_stop_reason']}")
        st.caption(
            "본 판정은 과거 날씨 기록·임의 지반 기울기 데이터 기반 "
            "참고용이며, 현장 책임자의 최종 안전 판단을 대체하지 않습니다."
        )


# ============================================================
# 6-D. 작업 전 안전 점검 체크리스트
# ============================================================
SAFETY_CHECK_ITEMS = [
    ("outrigger",   "아웃트리거 / 받침판 설치 및 상태 양호"),
    ("slope",       "현장 지반 기울기 ≤ 허용 작업 경사 확인"),
    ("wind",        "풍속이 장비 한계 미만 (이동식 크레인 18 m/s, 스카이 10 m/s)"),
    ("rain_snow",   "강수량·적설량 확인 (미끄러운 노면·시정 저하 우려)"),
    ("visibility",  "시야 확보·시정 거리 양호 (안개·저녁 시간 등)"),
    ("license",     "운전자/작업자 자격증·음주·건강 상태 확인"),
    ("ppe",         "안전모·안전벨트·안전화·장갑 등 보호구 착용"),
    ("perimeter",   "주변 작업자 안전거리 확보 및 출입 통제"),
    ("signaler",    "신호수 배치 및 핸드신호·무전기 교신 체계 점검"),
    ("emergency",   "비상 연락망·비상 장비(소화기·구급함) 비치 확인"),
]


def render_safety_check_tab(user, login_time, equip_limits_df):
    """작업 전 안전 점검 체크리스트 탭.

    일일 점검 결과를 session_state['safety_check_log'] 에 누적 저장하고,
    오늘 날짜 기준 이력을 화면에 표시한다.
    """
    allow = pick_allow_deg(equip_limits_df) or 3.0

    st.subheader("✅ 작업 전 안전 점검 체크리스트")
    st.caption(
        f"{user['name']} ({user['id']}) · {user['branch']}지점 · "
        f"{user['equipment']} · 점검 기준 시각 "
        f"{login_time.strftime('%Y-%m-%d %H:%M')}"
    )

    # 헬퍼: 각 항목별 장비·지점 맥락 라벨 만들기
    equip = user["equipment"]
    items_display = []
    for key, label in SAFETY_CHECK_ITEMS:
        if key == "slope":
            label = f"현장 지반 기울기 ≤ 허용 작업 경사({allow:.2f}°) 확인"
        elif key == "wind":
            if equip == "이동식 크레인":
                label = f"풍속이 크레인 한계(18 m/s) 미만인지 확인"
            elif equip == "스카이(고소작업차)":
                label = f"풍속이 고소작업차 한계(10 m/s) 미만인지 확인"
            else:
                label = "풍속이 장비 한계 미만인지 확인"
        items_display.append((key, label))

    # 2열 체크리스트
    cols = st.columns(2)
    states = {}
    for i, (key, label) in enumerate(items_display):
        with cols[i % 2]:
            states[key] = st.checkbox(
                label, key=f"chk_{user['id']}_{key}",
                help=f"점검 항목: {key}"
            )

    # 추가 메모
    note = st.text_area(
        "📝 추가 메모 (선택)",
        placeholder="현장 특이사항, 점검자 소견, 사진 ID 등 자유 입력…",
        height=80,
    )

    # ── 종합 결과
    passed = sum(1 for v in states.values() if v)
    total = len(items_display)
    ratio = passed / total if total else 0

    if ratio >= 0.9:
        result_label = "✅ 점검 통과"
        result_color = "#2ECC71"
        result_advice = (
            "모든 핵심 항목이 확인되었습니다. 작업을 시작해도 됩니다."
        )
    elif ratio >= 0.6:
        result_label = "⚠️ 조건부 통과 (재확인 필요)"
        result_color = "#F1C40F"
        result_advice = (
            "확인되지 않은 항목이 있습니다. 책임자 승인 후 미확인 "
            "항목을 현장에서 재확인하고 진행하세요."
        )
    else:
        result_label = "🛑 점검 미흡 — 작업 중지 권고"
        result_color = "#E74C3C"
        result_advice = (
            "필수 안전 항목 다수가 미확인 상태입니다. "
            "추가 확인 전에는 작업을 시작하지 마세요."
        )

    st.progress(ratio)
    st.markdown(
        f"""
        <div style="
            background: {result_color}22;
            border: 2px solid {result_color};
            border-radius: 10px;
            padding: 16px;
            text-align: center;
            margin: 8px 0;
        ">
            <div style="
                font-size: 24px;
                font-weight: 700;
                color: {result_color};
            ">{result_label}</div>
            <div style="
                font-size: 13px;
                color: #333;
                margin-top: 6px;
                line-height: 1.5;
            ">{result_advice}</div>
            <div style="
                font-size: 12px;
                color: #666;
                margin-top: 6px;
            ">통과 {passed} / {total} ({ratio:.0%})</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 미체크 항목 경고
    unchecked = [label for (k, label), v in zip(items_display,
                                                 states.values()) if not v]
    if unchecked:
        with st.expander(f"⚠️ 미확인 항목 {len(unchecked)}개 보기",
                         expanded=(len(unchecked) >= total // 2)):
            for u in unchecked:
                st.write(f"- {u}")

    # ── 제출
    st.divider()
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1:
        st.write(f"위험도 점수(자동 판정)와 별개로 **책임자 수기 점검**을 기록합니다.")
    with c2:
        st.metric("통과율", f"{ratio:.0%}")
    with c3:
        submitted = st.button(
            "📝 점검 기록 제출", type="primary",
            use_container_width=True,
        )

    if submitted:
        record = {
            "submitted_at": login_time.strftime("%Y-%m-%d %H:%M"),
            "worker_id":     user["id"],
            "worker_name":   user["name"],
            "branch":        user["branch"],
            "equipment":     user["equipment"],
            "passed":        passed,
            "total":         total,
            "ratio":         f"{ratio:.0%}",
            "result":        result_label,
            "note":          note.strip(),
        }
        log = st.session_state.setdefault("safety_check_log", [])
        log.append(record)
        st.success(
            f"점검 기록 저장 완료 — {result_label} "
            f"({passed}/{total}, {ratio:.0%})"
        )

    # ── 오늘의 점검 이력
    st.divider()
    st.markdown("#### 📋 오늘의 점검 이력 (현장 세션)")
    log = st.session_state.get("safety_check_log", [])
    today = login_time.strftime("%Y-%m-%d")
    today_log = [r for r in log if r["submitted_at"].startswith(today)]
    if today_log:
        st.dataframe(
            pd.DataFrame(today_log),
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("아직 오늘 점검 기록이 없습니다. 위 항목을 체크하고 제출하세요.")

    with st.expander(" 점검 항목 정의 보기"):
        for k, label in SAFETY_CHECK_ITEMS:
            st.write(f"- **{k}** — {label}")


# ============================================================
# 7. 메인
# ============================================================
def _requested_mode() -> str:
    """URL 쿼리파라미터 ?m=worker 를 읽어 모드 반환. 기본 'auto'."""
    try:
        qp = st.query_params
        m = qp.get("m", "auto")
    except Exception:
        qp = st.experimental_get_query_params()
        vals = qp.get("m", ["auto"])
        m = vals[0] if vals else "auto"
    if isinstance(m, list):
        m = m[0] if m else "auto"
    return (m or "auto").lower()


def main():
    if "user" not in st.session_state:
        render_login()
        return

    user = st.session_state["user"]
    login_time: datetime = st.session_state["login_time"]

    # ─ v6: 역할 기반 라우팅 ─
    #   worker 역할     → 모바일 근로자 앱 (worker_app.render)
    #   admin  역할     → 관리자 대시보드 (아래 기존 코드)
    #   쿼리파라미터로 수동 전환 가능:  ?m=worker, ?m=admin
    mode = _requested_mode()
    role = user.get("role", "worker")
    if mode == "worker" or (mode == "auto" and role == "worker"):
        # 모바일 근로자 라우트
        try:
            import worker_app
        except Exception as e:
            st.error(f"모바일 모듈 로드 실패: {e}")
            st.stop()
        worker_app.render(user, login_time)
        return
    if mode == "admin" and role != "admin":
        st.warning(
            "관리자 대시보드는 관리자 계정(admin01)만 접근할 수 있습니다. "
            "모바일 홈으로 이동합니다."
        )
        try:
            import worker_app
            worker_app.render(user, login_time)
        except Exception as e:
            st.error(f"모바일 모듈 로드 실패: {e}")
        return
    # fallthrough → 관리자 대시보드 (role=='admin' 또는 ?m=admin)

    # 데이터 로드
    try:
        weather = load_weather()
    except Exception as e:
        st.error(f"날씨 데이터 로드 실패: {e}")
        st.stop()

    try:
        equip = load_equipment()
    except Exception as e:
        st.error(f"장비 데이터 로드 실패: {e}")
        st.stop()

    tilt_df = generate_ground_tilt(n=600)

    # 요구사항 7: 소속 + 로그인 시간으로 엑셀 값 대조 → 별도 저장
    matched_weather = filter_weather_for_user(weather, user["branch"],
                                              login_time)
    st.session_state["matched_weather"] = matched_weather  # 별도 저장
    equip_limits_df = equipment_limits(equip, user["equipment"])

    # 사이드바
    with st.sidebar:
        st.header("🔐 로그인 정보")
        st.write(f"**이름**: {user['name']}")
        st.write(f"**아이디**: `{user['id']}`")
        st.write(f"**소속**: {user['branch']}지점")
        st.write(f"**장비**: {user['equipment']}")
        st.write(f"**로그인 시각**:")
        st.code(login_time.strftime("%Y-%m-%d %H:%M:%S"))
        st.caption("※ 2018~2025, 06:00~17:00 범위에서 임의 지정")

        st.divider()
        if st.button("🚪 로그아웃", use_container_width=True):
            st.session_state.clear()
            st.rerun()

    # 상단 헤더
    st.title("🏗️ 중장비 전도 예방 대시보드")
    st.caption(
        f"재해 유형: **{ACCIDENT_TYPE}** / "
        f"분석 대상 장비 {len(EQUIPMENT_LIST)}종"
    )

    # 📣 금일 건설기계장비 작업 가능 여부 — 부제목 바로 밑, 탭 메뉴 위
    verdict_payload = compute_work_verdict(
        user, login_time, matched_weather, tilt_df, equip_limits_df
    )
    render_work_verdict_banner(user, verdict_payload)

    # KPI
    kpi_row(user, login_time, len(matched_weather), equip_limits_df)

    # 요구사항 8: 사용자 정보 화면 + 대시보드 화면 + 장비 한계표
    # 추가 4: 작업 전 안전 점검 체크리스트
    tab1, tab2, tab3, tab4 = st.tabs([
        "👤 로그인 정보 화면",
        "📊 대시보드 화면",
        "📚 장비 7종 전도 한계표",
        "✅ 작업 전 안전 점검",
    ])

    with tab1:
        render_user_info_tab(user, login_time, matched_weather,
                             equip_limits_df)

    with tab2:
        render_dashboard_tab(user, login_time, matched_weather,
                             tilt_df, equip_limits_df)

    with tab3:
        st.subheader("📚 건설장비 지반 경사도·전도 한계 종합 데이터표")
        st.caption("출처: equipment_slope_data.csv (KOSHA, 건설기계 안전기준, MFR 등)")
        st.dataframe(equip, hide_index=True, use_container_width=True)

    with tab4:
        render_safety_check_tab(user, login_time, equip_limits_df)


if __name__ == "__main__":
    main()
