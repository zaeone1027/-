import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="생활관 종합 결산 시스템", layout="wide")

# ⚠️ 스키마 변경에 따른 충돌 방지를 위해 새로운 DB 파일(v3) 사용
DB_NAME = 'squad_v3.db'

# 1. DB 초기화 및 만료 데이터 자동 삭제
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # 자리 번호(seat_number)를 주키(Primary Key)로 하는 새로운 인원 테이블
    c.execute('CREATE TABLE IF NOT EXISTS members (seat_number INTEGER PRIMARY KEY, rank TEXT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS outings (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, type TEXT, start_date TEXT, end_date TEXT, leave_type TEXT, dest TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, reason TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, v_date TEXT, v_time TEXT, loc TEXT, visitor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS haircuts (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS religions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, religion TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, d_date TEXT, d_time TEXT, menu TEXT, members TEXT)')
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

# 선택된 자리 상태 관리 (State Management)
if 'active_seat' not in st.session_state:
    st.session_state.active_seat = None

# 등록된 인원 데이터 불러오기 및 주소(자리) 매핑
conn = sqlite3.connect(DB_NAME)
members_df = pd.read_sql_query("SELECT * FROM members", conn)
conn.close()

# 자리 번호를 키(Key)로 하는 딕셔너리 생성 (검색 속도 최적화)
seat_map = {}
member_names = []
for _, row in members_df.iterrows():
    full_name = f"{row['rank']} {row['name']}"
    seat_map[row['seat_number']] = full_name
    member_names.append(full_name)

st.title("📋 생활관 종합 결산 대시보드")

# --- 1. 생활관 자리 배치도 (2x5 Matrix Grid) ---
st.markdown("### 🛏️ 생활관 자리 배치도 (2열 10자리)")
st.write("자리를 클릭하여 인원을 배치하거나, 배치된 인원을 클릭하여 결산 현황을 입력하세요.")

# 2열(Row) x 5칸(Column) 반복문
for row_idx in range(2):
    cols = st.columns(5)
    for col_idx in range(5):
        # 1번부터 10번까지의 고유 번호 계산
        seat_num = row_idx * 5 + col_idx + 1 
        
        with cols[col_idx]:
            if seat_num in seat_map:
                # 데이터가 쓰여진(Occupied) 자리
                member_name = seat_map[seat_num]
                if st.button(f"🛏️ 자리 {seat_num}\n\n**{member_name}**", key=f"seat_{seat_num}", use_container_width=True):
                    st.session_state.active_seat = seat_num
            else:
                # 비어있는(Empty) 자리
                if st.button(f"🪑 자리 {seat_num}\n\n(비어있음)", key=f"seat_{seat_num}", use_container_width=True):
                    st.session_state.active_seat = seat_num

st.markdown("---")

# --- 2. 동적 입력 폼 (Selected Seat Logic) ---
if st.session_state.active_seat:
    seat = st.session_state.active_seat
    
    if seat in seat_map:
        # [데이터가 있는 자리를 클릭했을 때] -> 결산 제어 및 자리 비우기
        member = seat_map[seat]
        st.markdown(f"### 👉 [자리 {seat}] 선택된 인원: **{member}**")
        
        # 자리 데이터 삭제(초기화) 버튼
        if st.button(f"🗑️ 이 자리 비우기 ({member} 삭제)", type="secondary"):
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
                start_d = out_date
                end_d = out_date
            else:
                c_d1, c_d2 = st.columns(2)
                with c_d1:
                    start_d = st.date_input("시작일")
                with c_d2:
                    end_d = st.date_input("종료일")
                    
            leave_t = st.text_input("휴가 종류 (예: 정기, 포상)")
            dest = st.text_input("행선지")
            
            if st.button("출타 저장", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO outings (member, type, start_date, end_date, leave_type, dest) VALUES (?,?,?,?,?,?)", 
                             (member, out_type, str(start_d), str(end_d), leave_t, dest))
                conn.commit()
                conn.close()
                st.success("출타 저장 완료!")

        with col2:
            st.error("🚫 열외 등록")
            reason = st.selectbox("사유", ["근무", "휴가", "외출", "외박", "상황병", "입실", "파견"])
            if st.button("열외 저장", type="primary"):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO exceptions (member, reason) VALUES (?,?)", (member, reason))
                conn.commit()
                conn.close()
                st.success("열외 저장 완료!")
                
        with st.expander(f"🤝 {member}의 면회 및 종교 등록"):
            c_v, c_r = st.columns(2)
            with c_v:
                st.write("**면회 등록**")
                v_date = st.date_input("일자", key="vd")
                v_time = st.time_input("시간", key="vt")
                v_loc = st.radio("장소", ["영내", "영외"], horizontal=True)
                visitor = st.text_input("면회객")
                if st.button("면회 저장"):
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO visits (member, v_date, v_time, loc, visitor) VALUES (?,?,?,?,?)", 
                                 (member, str(v_date), str(v_time), v_loc, visitor))
                    conn.commit()
                    conn.close()
                    st.success("저장됨")
            with c_r:
                st.write("**종교 등록**")
                rel = st.selectbox("종교", ["불교", "기독교", "천주교"])
                if st.button("종교 저장"):
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (member, rel))
                    conn.commit()
                    conn.close()
                    st.success("저장됨")

    else:
        # [비어있는 자리를 클릭했을 때] -> 데이터 쓰기(Write) 모드
        st.markdown(f"### 🪑 [자리 {seat}] 인원 배치")
        c1, c2 = st.columns(2)
        with c1:
            new_rank = st.selectbox("계급", ["이병", "일병", "상병", "병장"])
            new_name = st.text_input("이름")
            if st.button("이 자리에 인원 저장", type="primary"):
                if new_name:
                    conn = sqlite3.connect(DB_NAME)
                    conn.execute("INSERT OR REPLACE INTO members (seat_number, rank, name) VALUES (?, ?, ?)", (seat, new_rank, new_name))
                    conn.commit()
                    conn.close()
                    st.success(f"자리 {seat}에 {new_rank} {new_name} 배치 완료!")
                    st.rerun()
else:
    st.info("👆 위에서 생활관 자리를 클릭하면 입력 폼이 나타납니다.")

st.markdown("---")

# --- 3. 그룹 현황 입력 (이발, 배달) ---
with st.expander("✂️ 이발 및 🍔 배달음식 종합 등록 (다수 인원 선택 가능)"):
    g1, g2 = st.columns(2)
    with g1:
        st.write("**이발 실시 인원**")
        h_members = st.multiselect("이발자 선택", member_names)
        if st.button("이발 명단 저장"):
            conn = sqlite3.connect(DB_NAME)
            for hm in h_members:
                conn.execute("INSERT INTO haircuts (member) VALUES (?)", (hm,))
            conn.commit()
            conn.close()
            st.success("이발 인원 저장됨")
            
    with g2:
        st.write("**배달음식 등록**")
        d_date = st.date_input("취식 일자")
        d_time = st.time_input("취식 시간")
        d_menu = st.text_input("메뉴")
        d_members = st.multiselect("같이 먹는 인원", member_names)
        if st.button("배달음식 저장"):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT INTO deliveries (d_date, d_time, menu, members) VALUES (?,?,?,?)", 
                         (str(d_date), str(d_time), d_menu, ", ".join(d_members)))
            conn.commit()
            conn.close()
            st.success("배달 현황 저장됨")

st.markdown("---")

# --- 4. 자동 생성 결산 메시지 ---
st.markdown("### 📩 일일 종합 결산 메시지 (자동 생성)")

conn = sqlite3.connect(DB_NAME)
out_df = pd.read_sql_query("SELECT * FROM outings", conn)
exc_df = pd.read_sql_query("SELECT * FROM exceptions", conn)
vis_df = pd.read_sql_query("SELECT * FROM visits", conn)
rel_df = pd.read_sql_query("SELECT * FROM religions", conn)
hair_df = pd.read_sql_query("SELECT * FROM haircuts", conn)
del_df = pd.read_sql_query("SELECT * FROM deliveries", conn)
conn.close()

# 출타 2주 필터링
today = datetime.now().date()
two_weeks_later = today + timedelta(days=14)

filtered_outings = []
if not out_df.empty:
    out_df['start_dt'] = pd.to_datetime(out_df['start_date']).dt.date
    mask = (out_df['start_dt'] <= two_weeks_later)
    filtered_outings = out_df[mask].to_dict('records')

msg = "충성! 일일 생활관 결산 내역을 보고드립니다.\n\n"

msg += "[ 열외 현황 ]\n"
if not exc_df.empty:
    for _, row in exc_df.iterrows():
        msg += f"- {row['member']} : {row['reason']}\n"
else:
    msg += "특이사항 없음\n"

msg += "\n[ 출타 현황 (2주 이내 예정 포함) ]\n"
if filtered_outings:
    for out in filtered_outings:
        if out['start_date'] == out['end_date']:
            date_str = f"({out['start_date']})"
        else:
            date_str = f"({out['start_date']} ~ {out['end_date']})"
        msg += f"- {out['member']} : {out['type']} {date_str} / {out['leave_type']} / {out['dest']}\n"
else:
    msg += "특이사항 없음\n"

msg += "\n[ 면회 현황 ]\n"
if not vis_df.empty:
    for _, row in vis_df.iterrows():
        msg += f"- {row['member']} : {row['v_date']} {row['v_time']} / {row['loc']} / {row['visitor']}\n"
else:
    msg += "해당 없음\n"

msg += "\n[ 이발 및 종교 ]\n"
hair_str = ", ".join(hair_df['member'].tolist()) if not hair_df.empty else "없음"
msg += f"- 이발 실시 : {hair_str}\n"
if not rel_df.empty:
    for _, row in rel_df.iterrows():
        msg += f"- 종교 참석 ({row['religion']}) : {row['member']}\n"
else:
    msg += "- 종교 참석 : 없음\n"

msg += "\n[ 배달음식 현황 ]\n"
if not del_df.empty:
    for _, row in del_df.iterrows():
        msg += f"- {row['d_date']} {row['d_time']} / {row['menu']} / 취식자: {row['members']}\n"
else:
    msg += "해당 없음\n"

st.text_area("아래 내용을 복사하여 보고하세요:", value=msg, height=400)

if st.button("⚠️ 일일 데이터 초기화 (출타/인원 제외)"):
    conn = sqlite3.connect(DB_NAME)
    conn.execute("DELETE FROM exceptions")
    conn.execute("DELETE FROM visits")
    conn.execute("DELETE FROM haircuts")
    conn.execute("DELETE FROM religions")
    conn.execute("DELETE FROM deliveries")
    conn.commit()
    conn.close()
    st.success("오늘자 결산 데이터가 초기화되었습니다.")
    st.rerun()
