import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="생활관 종합 결산 시스템", layout="wide")

# ⚠️ 병기본 등 스키마 추가로 인한 버전 업데이트
DB_NAME = 'squad_v4.db'

def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS members (seat_number INTEGER PRIMARY KEY, rank TEXT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS outings (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, type TEXT, start_date TEXT, end_date TEXT, leave_type TEXT, dest TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, reason TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, v_date TEXT, v_time TEXT, loc TEXT, visitor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS haircuts (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS religions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, religion TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, d_date TEXT, d_time TEXT, menu TEXT, members TEXT)')
    # 새롭게 추가된 병기본 테이블
    c.execute('CREATE TABLE IF NOT EXISTS trainings (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, subject TEXT)')
    conn.commit()
    conn.close()

def clean_past_data():
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM outings WHERE end_date < ?", (today_str,))
    conn.commit()
    conn.close()

init_db()
clean_past_data()

# 상태 관리
if 'active_seat' not in st.session_state:
    st.session_state.active_seat = None

# 등록된 인원 데이터 불러오기
conn = sqlite3.connect(DB_NAME)
members_df = pd.read_sql_query("SELECT * FROM members", conn)
conn.close()

seat_map = {}
member_names = []
for _, row in members_df.iterrows():
    full_name = f"{row['rank']} {row['name']}"
    seat_map[row['seat_number']] = full_name
    member_names.append(full_name)

st.title("📋 생활관 종합 결산 대시보드")

# --- 1. 생활관 자리 배치도 (좌우 2열 구조) ---
st.markdown("### 🛏️ 생활관 자리 배치도 (좌우 2열)")

# 5행 2열 (총 10자리) 렌더링
for row_idx in range(5):
    c_left, c_right = st.columns(2)
    seat_left = row_idx * 2 + 1   # 1, 3, 5, 7, 9
    seat_right = row_idx * 2 + 2  # 2, 4, 6, 8, 10
    
    with c_left:
        if seat_left in seat_map:
            if st.button(f"자리 {seat_left} : **{seat_map[seat_left]}**", key=f"s_{seat_left}", use_container_width=True):
                st.session_state.active_seat = seat_left
        else:
            if st.button(f"자리 {seat_left} : (비어있음)", key=f"s_{seat_left}", use_container_width=True):
                st.session_state.active_seat = seat_left
                
    with c_right:
        if seat_right in seat_map:
            if st.button(f"자리 {seat_right} : **{seat_map[seat_right]}**", key=f"s_{seat_right}", use_container_width=True):
                st.session_state.active_seat = seat_right
        else:
            if st.button(f"자리 {seat_right} : (비어있음)", key=f"s_{seat_right}", use_container_width=True):
                st.session_state.active_seat = seat_right

st.markdown("---")

# --- 2. 개별 현황 동적 폼 ---
if st.session_state.active_seat:
    seat = st.session_state.active_seat
    if seat in seat_map:
        member = seat_map[seat]
        st.markdown(f"### 👉 [자리 {seat}] **{member}** 현황 입력")
        
        if st.button("🗑️ 이 자리 비우기", type="secondary"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM members WHERE seat_number = ?", (seat,))
            conn.commit()
            conn.close()
            st.session_state.active_seat = None
            st.rerun()
            
        col1, col2 = st.columns(2)
        with col1:
            st.info("✈️ 출타 등록")
            out_type = st.selectbox("출타 종류", ["휴가", "평일외출", "주말외출", "주말외박"])
            if out_type in ["평일외출", "주말외출"]:
                out_date = st.date_input("출타일")
                start_d = end_d = out_date
            else:
                c_d1, c_d2 = st.columns(2)
                start_d = c_d1.date_input("시작일")
                end_d = c_d2.date_input("종료일")
            leave_t = st.text_input("휴가 종류")
            dest = st.text_input("행선지")
            
            if st.button("출타 저장", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO outings (member, type, start_date, end_date, leave_type, dest) VALUES (?,?,?,?,?,?)", 
                             (member, out_type, str(start_d), str(end_d), leave_t, dest))
                conn.commit()
                conn.close()
                st.success("출타 저장 완료")

        with col2:
            st.error("🚫 열외 및 면회 등록")
            reason = st.selectbox("열외 사유", ["근무", "휴가", "외출", "외박", "상황병", "입실", "파견"])
            if st.button("열외 저장", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO exceptions (member, reason) VALUES (?,?)", (member, reason))
                conn.commit()
                conn.close()
                st.success("열외 저장 완료")
                
            st.write("---")
            v_date = st.date_input("면회 일자", key="vd")
            v_time = st.time_input("면회 시간", key="vt")
            v_loc = st.radio("장소", ["영내", "영외"], horizontal=True)
            visitor = st.text_input("면회객")
            if st.button("면회 저장"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO visits (member, v_date, v_time, loc, visitor) VALUES (?,?,?,?,?)", 
                             (member, str(v_date), str(v_time), v_loc, visitor))
                conn.commit()
                conn.close()
                st.success("면회 저장 완료")

    else:
        st.markdown(f"### 🪑 [자리 {seat}] 인원 배치")
        c1, c2 = st.columns(2)
        new_rank = c1.selectbox("계급", ["이병", "일병", "상병", "병장"])
        new_name = c2.text_input("이름")
        if st.button("인원 저장", type="primary") and new_name:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT OR REPLACE INTO members (seat_number, rank, name) VALUES (?, ?, ?)", (seat, new_rank, new_name))
            conn.commit()
            conn.close()
            st.rerun()

st.markdown("---")

# --- 3. 그룹 현황 입력 (병기본, 종교, 이발, 배달) ---
with st.expander("⬆️ 병기본 훈련 및 종교 종합 등록"):
    t1, t2 = st.columns(2)
    with t1:
        pt_members = st.multiselect("🏃 체력측정", member_names)
        tccc_members = st.multiselect("🚑 TCCC", member_names)
        rel_chr = st.multiselect("✝️ 기독교", member_names)
        rel_bud = st.multiselect("🧘 불교", member_names)
    with t2:
        cbr_members = st.multiselect("☣️ 화생방", member_names)
        mental_members = st.multiselect("📖 정신전력", member_names)
        rel_cath = st.multiselect("⛪ 천주교", member_names)
        
    if st.button("병기본 및 종교 일괄 저장"):
        conn = sqlite3.connect(DB_NAME)
        # 병기본 저장
        for m in pt_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '체력측정'))
        for m in tccc_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, 'TCCC'))
        for m in cbr_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '화생방'))
        for m in mental_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '정신전력'))
        # 종교 저장
        for m in rel_chr: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '기독교'))
        for m in rel_bud: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '불교'))
        for m in rel_cath: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '천주교'))
        conn.commit()
        conn.close()
        st.success("저장 완료")

with st.expander("🍔 배달음식 및 ✂️ 이발 종합 등록"):
    g1, g2 = st.columns(2)
    with g1:
        d_date = st.date_input("배달 일자")
        d_time = st.time_input("배달 시간")
        d_menu = st.text_input("메뉴")
        d_members = st.multiselect("같이 먹는 인원", member_names)
        if st.button("배달 저장"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT INTO deliveries (d_date, d_time, menu, members) VALUES (?,?,?,?)", 
                         (str(d_date), str(d_time), d_menu, ", ".join(d_members)))
            conn.commit()
            conn.close()
            st.success("저장 완료")
    with g2:
        h_members = st.multiselect("이발 실시자", member_names)
        if st.button("이발 저장"):
            conn = sqlite3.connect(DB_NAME)
            for hm in h_members: conn.execute("INSERT INTO haircuts (member) VALUES (?)", (hm,))
            conn.commit()
            conn.close()
            st.success("저장 완료")

st.markdown("---")

# --- 4. 자동 생성 결산 메시지 (카카오톡 포맷 완벽 동기화) ---
st.markdown("### 📩 일일 종합 결산 메시지")

conn = sqlite3.connect(DB_NAME)
out_df = pd.read_sql_query("SELECT * FROM outings", conn)
exc_df = pd.read_sql_query("SELECT * FROM exceptions", conn)
vis_df = pd.read_sql_query("SELECT * FROM visits", conn)
rel_df = pd.read_sql_query("SELECT * FROM religions", conn)
trn_df = pd.read_sql_query("SELECT * FROM trainings", conn)
del_df = pd.read_sql_query("SELECT * FROM deliveries", conn)
conn.close()

# 요일 변환 함수
def format_date_kor(date_str):
    if not date_str: return ""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    return f"{dt.month}/{dt.day}({weekdays[dt.weekday()]})"

msg = ""

# 1. 상단: 출타 및 열외 (기존 유지)
msg += "[ 열외 현황 ]\n"
if not exc_df.empty:
    for _, row in exc_df.iterrows():
        msg += f"- {row['member']} : {row['reason']}\n"
else:
    msg += "특이사항 없음\n"

msg += "\n[ 출타 현황 (2주 이내 예정 포함) ]\n"
today = datetime.now().date()
two_weeks_later = today + timedelta(days=14)
filtered_outings = []
if not out_df.empty:
    out_df['start_dt'] = pd.to_datetime(out_df['start_date']).dt.date
    mask = (out_df['start_dt'] <= two_weeks_later)
    filtered_outings = out_df[mask].to_dict('records')

if filtered_outings:
    for out in filtered_outings:
        d_str = f"({out['start_date']})" if out['start_date'] == out['end_date'] else f"({out['start_date']} ~ {out['end_date']})"
        msg += f"- {out['member']} : {out['type']} {d_str} / {out['leave_type']} / {out['dest']}\n"
else:
    msg += "특이사항 없음\n"
msg += "\n"

# 2. 면회 (사진 양식 적용: 날짜 / 시간 / 이름 / 장소 / 면회객)
if not vis_df.empty:
    for _, row in vis_df.iterrows():
        v_date_kor = format_date_kor(row['v_date'])
        v_t = row['v_time'][:5] if isinstance(row['v_time'], str) else row['v_time']
        msg += f"{v_date_kor} / {v_t} / {row['member']} / {row['loc']} / {row['visitor']}\n"
    msg += "\n"

# 3. 종교 (사진 양식 적용)
msg += "⛪ 종교\n\n"
for rel_name, emoji in zip(["기독교", "불교", "천주교"], ["✝️", "🧘", "⛪"]):
    if not rel_df.empty:
        m_list = rel_df[rel_df['religion'] == rel_name]['member'].tolist()
        if m_list:
            msg += f"{emoji} {rel_name}\n"
            msg += ", ".join(m_list) + "\n\n"

# 4. 병기본 (사진 양식 적용)
msg += "⬆️ 병기본\n\n"
for subj, emoji in zip(["체력측정", "TCCC", "화생방", "정신전력"], ["🏃", "🚑", "☣️", "📖"]):
    if not trn_df.empty:
        m_list = trn_df[trn_df['subject'] == subj]['member'].tolist()
        if m_list:
            msg += f"{emoji} {subj}\n"
            msg += ", ".join(m_list) + "\n\n"

# 5. 배달음식 (사진 양식 적용: 슬래시 구분)
if not del_df.empty:
    for _, row in del_df.iterrows():
        eaters = row['members'].replace(", ", "/")
        msg += f"배달음식 취식인원: {eaters}\n"
    msg += "\n"

# 6. 특이사항 하단 고정 (사진 양식 적용)
msg += "⚠️ 병력 특이사항 확인\n"
msg += "자살징후, 구타 및 가혹행위, 언어폭력 등 1번 항목 특이사항 없습니다.\n\n"
msg += "분대원 면담 및 관찰 결과 특이사항 없습니다."

st.text_area("아래 텍스트를 복사하여 보고하세요:", value=msg, height=500)

if st.button("⚠️ 일일 데이터 초기화 (출타/인원 제외)"):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM exceptions")
    conn.execute("DELETE FROM visits")
    conn.execute("DELETE FROM haircuts")
    conn.execute("DELETE FROM religions")
    conn.execute("DELETE FROM deliveries")
    conn.execute("DELETE FROM trainings")
    conn.commit()
    conn.close()
    st.success("초기화 완료")
    st.rerun()
