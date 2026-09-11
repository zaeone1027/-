import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

st.set_page_config(page_title="생활관 종합 결산 시스템", layout="wide")

# 1. DB 초기화 및 만료 데이터 자동 삭제 (DB Init & Auto-Cleanup)
def init_db():
    conn = sqlite3.connect('squad.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, rank TEXT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS outings (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, type TEXT, start_date TEXT, end_date TEXT, leave_type TEXT, dest TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, reason TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, v_date TEXT, v_time TEXT, loc TEXT, visitor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS haircuts (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS religions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, religion TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, d_date TEXT, d_time TEXT, menu TEXT, members TEXT)')
    conn.commit()
    conn.close()

def clean_past_data():
    # 현재 날짜 기준, 종료일이 지난 출타 기록은 DB에서 자동 삭제합니다. (Garbage Collection)
    today_str = datetime.now().date().strftime("%Y-%m-%d")
    conn = sqlite3.connect('squad.db')
    conn.execute("DELETE FROM outings WHERE end_date < ?", (today_str,))
    conn.commit()
    conn.close()

init_db()
clean_past_data()

# 상태 관리 (State Management)
if 'selected_member' not in st.session_state:
    st.session_state.selected_member = None

# 등록된 인원 데이터 불러오기
conn = sqlite3.connect('squad.db')
members_df = pd.read_sql_query("SELECT rank, name FROM members", conn)
conn.close()
member_names = (members_df['rank'] + " " + members_df['name']).tolist() if not members_df.empty else []

st.title("📋 생활관 종합 결산 대시보드")

# --- 1. 인원 관리 및 선택 그리드 (Member Selection Grid) ---
st.markdown("### 👥 인원 선택 (클릭하여 현황 입력)")

if members_df.empty:
    st.warning("등록된 인원이 없습니다. 아래에서 인원을 먼저 추가해주세요.")
else:
    cols = st.columns(5) # 5명씩 배치
    for i, row in members_df.iterrows():
        full_name = f"{row['rank']} {row['name']}"
        # 버튼 클릭 시 해당 인원을 세션에 저장
        if cols[i % 5].button(full_name, use_container_width=True):
            st.session_state.selected_member = full_name

with st.expander("➕ 새 인원 추가 / 전체 인원 관리"):
    c1, c2 = st.columns(2)
    with c1:
        new_rank = st.selectbox("계급", ["이병", "일병", "상병", "병장"])
        new_name = st.text_input("이름")
        if st.button("인원 추가"):
            if len(members_df) >= 10:
                st.error("최대 10명까지만 추가 가능합니다.")
            elif new_name:
                conn = sqlite3.connect('squad.db')
                conn.execute("INSERT INTO members (rank, name) VALUES (?, ?)", (new_rank, new_name))
                conn.commit()
                conn.close()
                st.rerun()
    with c2:
        st.write("현재 인원 목록")
        st.dataframe(members_df, hide_index=True)

st.markdown("---")

# --- 2. 개별 현황 입력 폼 (Input Form for Selected Member) ---
if st.session_state.selected_member:
    st.markdown(f"### 👉 선택된 인원: **{st.session_state.selected_member}**")
    
    col1, col2 = st.columns(2)
    
    # [출타 폼]
    with col1:
        st.info("✈️ 출타 등록")
        out_type = st.selectbox("출타 종류", ["휴가", "평일외출", "주말외출", "주말외박"])
        start_d = st.date_input("시작일")
        end_d = st.date_input("종료일")
        leave_t = st.text_input("휴가 종류 (예: 정기, 포상)")
        dest = st.text_input("행선지")
        
        if st.button("출타 저장", type="primary"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO outings (member, type, start_date, end_date, leave_type, dest) VALUES (?,?,?,?,?,?)", 
                         (st.session_state.selected_member, out_type, str(start_d), str(end_d), leave_t, dest))
            conn.commit()
            conn.close()
            st.success("출타 저장 완료!")

    # [열외 폼]
    with col2:
        st.error("🚫 열외 등록")
        reason = st.selectbox("사유", ["근무", "휴가", "외출", "외박", "상황병", "입실", "파견"])
        if st.button("열외 저장", type="primary"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO exceptions (member, reason) VALUES (?,?)", (st.session_state.selected_member, reason))
            conn.commit()
            conn.close()
            st.success("열외 저장 완료!")
            
    # [기타 개별 현황 아코디언]
    with st.expander(f"🤝 {st.session_state.selected_member}의 면회 및 종교 등록"):
        c_v, c_r = st.columns(2)
        with c_v:
            st.write("**면회 등록**")
            v_date = st.date_input("일자", key="vd")
            v_time = st.time_input("시간", key="vt")
            v_loc = st.radio("장소", ["영내", "영외"], horizontal=True)
            visitor = st.text_input("면회객")
            if st.button("면회 저장"):
                conn = sqlite3.connect('squad.db')
                conn.execute("INSERT INTO visits (member, v_date, v_time, loc, visitor) VALUES (?,?,?,?,?)", 
                             (st.session_state.selected_member, str(v_date), str(v_time), v_loc, visitor))
                conn.commit()
                conn.close()
                st.success("저장됨")
        with c_r:
            st.write("**종교 등록**")
            rel = st.selectbox("종교", ["불교", "기독교", "천주교"])
            if st.button("종교 저장"):
                conn = sqlite3.connect('squad.db')
                conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (st.session_state.selected_member, rel))
                conn.commit()
                conn.close()
                st.success("저장됨")
else:
    st.info("👆 위에서 인원 이름을 클릭하면 개별 현황 입력 창이 나타납니다.")

st.markdown("---")

# --- 3. 그룹 현황 입력 (Group Input Forms) ---
with st.expander("✂️ 이발 및 🍔 배달음식 종합 등록 (다수 인원 선택 가능)"):
    g1, g2 = st.columns(2)
    with g1:
        st.write("**이발 실시 인원**")
        h_members = st.multiselect("이발자 선택", member_names)
        if st.button("이발 명단 저장"):
            conn = sqlite3.connect('squad.db')
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
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO deliveries (d_date, d_time, menu, members) VALUES (?,?,?,?)", 
                         (str(d_date), str(d_time), d_menu, ", ".join(d_members)))
            conn.commit()
            conn.close()
            st.success("배달 현황 저장됨")

st.markdown("---")

# --- 4. 최종 메시지 생성 및 필터링 (Message Generation & Output) ---
st.markdown("### 📩 일일 종합 결산 메시지 (자동 생성)")

# 전체 데이터 불러오기
conn = sqlite3.connect('squad.db')
out_df = pd.read_sql_query("SELECT * FROM outings", conn)
exc_df = pd.read_sql_query("SELECT * FROM exceptions", conn)
vis_df = pd.read_sql_query("SELECT * FROM visits", conn)
rel_df = pd.read_sql_query("SELECT * FROM religions", conn)
hair_df = pd.read_sql_query("SELECT * FROM haircuts", conn)
del_df = pd.read_sql_query("SELECT * FROM deliveries", conn)
conn.close()

# 출타 2주(14일) 필터링
today = datetime.now().date()
two_weeks_later = today + timedelta(days=14)

filtered_outings = []
if not out_df.empty:
    out_df['start_dt'] = pd.to_datetime(out_df['start_date']).dt.date
    mask = (out_df['start_dt'] <= two_weeks_later)
    filtered_outings = out_df[mask].to_dict('records')

# 문자열(결산 메시지) 포매팅
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
        msg += f"- {out['member']} : {out['type']} ({out['start_date']} ~ {out['end_date']}) / {out['leave_type']} / {out['dest']}\n"
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

# 텍스트 복사 영역 출력
st.text_area("아래 내용을 복사(Ctrl+C)하여 카카오톡이나 체계망에 보고하세요:", value=msg, height=400)

# (관리자용) 일일 데이터 초기화 기능
if st.button("⚠️ 일일 데이터 초기화 (출타/인원 제외)"):
    conn = sqlite3.connect('squad.db')
    conn.execute("DELETE FROM exceptions")
    conn.execute("DELETE FROM visits")
    conn.execute("DELETE FROM haircuts")
    conn.execute("DELETE FROM religions")
    conn.execute("DELETE FROM deliveries")
    conn.commit()
    conn.close()
    st.success("출타와 인원 명단을 제외한 오늘자 결산 데이터가 모두 초기화되었습니다.")
    st.rerun()
