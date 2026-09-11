import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime, timedelta

# 모바일 화면 비율을 고려하여 layout="centered" 또는 기본값 사용
st.set_page_config(page_title="생활관 종합 결산", page_icon="📱")

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

if 'active_seat' not in st.session_state:
    st.session_state.active_seat = None

conn = sqlite3.connect(DB_NAME)
members_df = pd.read_sql_query("SELECT * FROM members", conn)
conn.close()

seat_map = {}
member_names = []
for _, row in members_df.iterrows():
    full_name = f"{row['rank']} {row['name']}"
    seat_map[row['seat_number']] = full_name
    member_names.append(full_name)

st.title("📱 생활관 결산 대시보드")

# --- 1. 생활관 자리 배치도 ---
st.markdown("### 🛏️ 자리 선택")

for row_idx in range(5):
    c_left, c_right = st.columns(2)
    seat_left = row_idx * 2 + 1   
    seat_right = row_idx * 2 + 2  
    
    with c_left:
        if seat_left in seat_map:
            if st.button(f"자리 {seat_left}\n\n**{seat_map[seat_left]}**", key=f"s_{seat_left}", use_container_width=True):
                st.session_state.active_seat = seat_left
        else:
            if st.button(f"자리 {seat_left}\n\n(비어있음)", key=f"s_{seat_left}", use_container_width=True):
                st.session_state.active_seat = seat_left
                
    with c_right:
        if seat_right in seat_map:
            if st.button(f"자리 {seat_right}\n\n**{seat_map[seat_right]}**", key=f"s_{seat_right}", use_container_width=True):
                st.session_state.active_seat = seat_right
        else:
            if st.button(f"자리 {seat_right}\n\n(비어있음)", key=f"s_{seat_right}", use_container_width=True):
                st.session_state.active_seat = seat_right

st.markdown("---")

# --- 2. 개별 현황 동적 폼 ---
if st.session_state.active_seat:
    seat = st.session_state.active_seat
    if seat in seat_map:
        member = seat_map[seat]
        st.markdown(f"### 👉 [자리 {seat}] **{member}**")
        
        with st.expander("✈️ 출타 등록 및 조회", expanded=True):
            # [입력 폼 영역]
            out_type = st.selectbox("출타 종류", ["휴가", "평일외출", "주말외출", "주말외박"])
            
            # 조건부 렌더링 및 날짜 자동 연산
            if out_type in ["평일외출", "주말외출"]:
                out_date = st.date_input("출타일")
                start_d = end_d = out_date
            elif out_type == "주말외박":
                out_date = st.date_input("출타일 (복귀일은 내일로 자동설정)")
                start_d = out_date
                end_d = out_date + timedelta(days=1) # 1일 자동 덧셈 연산
                st.info(f"💡 복귀일: {end_d.strftime('%Y-%m-%d')}")
            else:
                c_d1, c_d2 = st.columns(2)
                start_d = c_d1.date_input("시작일")
                end_d = c_d2.date_input("종료일")
                
            leave_t = st.text_input("휴가 종류 (예: 연가, 포상)")
            dest = st.text_input("행선지")
            
            if st.button("출타 추가", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO outings (member, type, start_date, end_date, leave_type, dest) VALUES (?,?,?,?,?,?)", 
                             (member, out_type, str(start_d), str(end_d), leave_t, dest))
                conn.commit()
                conn.close()
                # 저장 후 화면을 새로고침하여 입력칸을 초기화하고 하단 목록을 갱신
                st.rerun()
                
            st.markdown("---")
            
            # [디스플레이 (피드백) 영역]
            st.write(f"📋 **등록된 출타 목록 ({member})**")
            conn = sqlite3.connect(DB_NAME)
            member_outings = pd.read_sql_query("SELECT id, type, start_date, end_date, leave_type, dest FROM outings WHERE member=?", conn, params=(member,))
            conn.close()
            
            if not member_outings.empty:
                for _, row in member_outings.iterrows():
                    # 기간 문자열 포매팅
                    d_str = f"({row['start_date']})" if row['start_date'] == row['end_date'] else f"({row['start_date']}~{row['end_date']})"
                    
                    # 삭제 버튼과 내용을 가로로 배치 (모바일 최적화)
                    col_txt, col_btn = st.columns([4, 1])
                    with col_txt:
                        st.caption(f"{row['type']} {d_str} / {row['leave_type']} / {row['dest']}")
                    with col_btn:
                        # 잘못 등록한 출타를 개별적으로 지울 수 있도록 고유 Key를 가진 삭제 버튼 추가
                        if st.button("❌", key=f"del_out_{row['id']}", help="삭제"):
                            conn = sqlite3.connect(DB_NAME)
                            conn.execute("DELETE FROM outings WHERE id=?", (row['id'],))
                            conn.commit()
                            conn.close()
                            st.rerun()
            else:
                st.caption("현재 등록된 출타가 없습니다.")

        with st.expander("🚫 열외 등록"):
            reason = st.selectbox("열외 사유", ["근무", "휴가", "외출", "외박", "상황병", "입실", "파견"])
            if st.button("열외 저장", type="primary", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO exceptions (member, reason) VALUES (?,?)", (member, reason))
                conn.commit()
                conn.close()
                st.success("저장 완료")
                
        with st.expander("🤝 면회 등록"):
            v_date = st.date_input("면회 일자", key="vd")
            v_time = st.time_input("면회 시간", key="vt")
            v_loc = st.radio("장소", ["영내", "영외"], horizontal=True)
            visitor = st.text_input("면회객")
            if st.button("면회 저장", use_container_width=True):
                conn = sqlite3.connect(DB_NAME)
                conn.execute("INSERT INTO visits (member, v_date, v_time, loc, visitor) VALUES (?,?,?,?,?)", 
                             (member, str(v_date), str(v_time), v_loc, visitor))
                conn.commit()
                conn.close()
                st.success("저장 완료")
                
        if st.button("🗑️ 이 자리 비우기 (삭제)", type="secondary", use_container_width=True):
            conn = sqlite3.connect(DB_NAME)
            conn.execute("DELETE FROM members WHERE seat_number = ?", (seat,))
            conn.commit()
            conn.close()
            st.session_state.active_seat = None
            st.rerun()

    else:
        st.markdown(f"### 🪑 [자리 {seat}] 인원 배치")
        new_rank = st.selectbox("계급", ["이병", "일병", "상병", "병장"])
        new_name = st.text_input("이름")
        if st.button("이 자리에 인원 저장", type="primary", use_container_width=True) and new_name:
            conn = sqlite3.connect(DB_NAME)
            conn.execute("INSERT OR REPLACE INTO members (seat_number, rank, name) VALUES (?, ?, ?)", (seat, new_rank, new_name))
            conn.commit()
            conn.close()
            st.rerun()
else:
    st.info("👆 자리를 터치하면 폼이 나타납니다.")

st.markdown("---")

# --- 3. 그룹 현황 입력 ---
st.markdown("### 📝 종합 현황 등록")

with st.expander("⬆️ 병기본 훈련 등록"):
    pt_members = st.multiselect("🏃 체력측정", member_names)
    tccc_members = st.multiselect("🚑 TCCC", member_names)
    cbr_members = st.multiselect("☣️ 화생방", member_names)
    mental_members = st.multiselect("📖 정신전력", member_names)
    if st.button("병기본 저장", key="btn_train", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        for m in pt_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '체력측정'))
        for m in tccc_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, 'TCCC'))
        for m in cbr_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '화생방'))
        for m in mental_members: conn.execute("INSERT INTO trainings (member, subject) VALUES (?,?)", (m, '정신전력'))
        conn.commit()
        conn.close()
        st.success("저장 완료")

with st.expander("✂️ 이발 등록"):
    h_members = st.multiselect("이발 실시자", member_names)
    if st.button("이발 저장", key="btn_hair", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        for hm in h_members: conn.execute("INSERT INTO haircuts (member) VALUES (?)", (hm,))
        conn.commit()
        conn.close()
        st.success("저장 완료")

with st.expander("⛪ 종교 행사 등록"):
    rel_chr = st.multiselect("✝️ 기독교", member_names)
    rel_bud = st.multiselect("🧘 불교", member_names)
    rel_cath = st.multiselect("⛪ 천주교", member_names)
    if st.button("종교 저장", key="btn_rel", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        for m in rel_chr: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '기독교'))
        for m in rel_bud: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '불교'))
        for m in rel_cath: conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (m, '천주교'))
        conn.commit()
        conn.close()
        st.success("저장 완료")

with st.expander("🍔 배달음식 등록"):
    cd1, cd2 = st.columns(2)
    d_date = cd1.date_input("배달 일자")
    d_time = cd2.time_input("배달 시간")
    d_menu = st.text_input("메뉴")
    d_members = st.multiselect("같이 먹는 인원", member_names)
    if st.button("배달 저장", key="btn_del", use_container_width=True):
        conn = sqlite3.connect(DB_NAME)
        conn.execute("INSERT INTO deliveries (d_date, d_time, menu, members) VALUES (?,?,?,?)", 
                     (str(d_date), str(d_time), d_menu, ", ".join(d_members)))
        conn.commit()
        conn.close()
        st.success("저장 완료")

st.markdown("---")

# --- 4. 자동 생성 결산 메시지 ---
st.markdown("### 📩 결산 메시지 복사")

conn = sqlite3.connect(DB_NAME)
out_df = pd.read_sql_query("SELECT * FROM outings", conn)
exc_df = pd.read_sql_query("SELECT * FROM exceptions", conn)
vis_df = pd.read_sql_query("SELECT * FROM visits", conn)
rel_df = pd.read_sql_query("SELECT * FROM religions", conn)
trn_df = pd.read_sql_query("SELECT * FROM trainings", conn)
del_df = pd.read_sql_query("SELECT * FROM deliveries", conn)
conn.close()

def format_date_kor(date_str):
    if not date_str: return ""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    weekdays = ['월', '화', '수', '목', '금', '토', '일']
    return f"{dt.month}/{dt.day}({weekdays[dt.weekday()]})"

msg = ""

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

if not vis_df.empty:
    for _, row in vis_df.iterrows():
        v_date_kor = format_date_kor(row['v_date'])
        v_t = row['v_time'][:5] if isinstance(row['v_time'], str) else row['v_time']
        msg += f"{v_date_kor} / {v_t} / {row['member']} / {row['loc']} / {row['visitor']}\n"
    msg += "\n"

msg += "⛪ 종교\n\n"
for rel_name, emoji in zip(["기독교", "불교", "천주교"], ["✝️", "🧘", "⛪"]):
    if not rel_df.empty:
        m_list = rel_df[rel_df['religion'] == rel_name]['member'].tolist()
        if m_list:
            msg += f"{emoji} {rel_name}\n"
            msg += ", ".join(m_list) + "\n\n"

msg += "⬆️ 병기본\n\n"
for subj, emoji in zip(["체력측정", "TCCC", "화생방", "정신전력"], ["🏃", "🚑", "☣️", "📖"]):
    if not trn_df.empty:
        m_list = trn_df[trn_df['subject'] == subj]['member'].tolist()
        if m_list:
            msg += f"{emoji} {subj}\n"
            msg += ", ".join(m_list) + "\n\n"

if not del_df.empty:
    for _, row in del_df.iterrows():
        eaters = row['members'].replace(", ", "/")
        msg += f"배달음식 취식인원: {eaters}\n"
    msg += "\n"

msg += "⚠️ 병력 특이사항 확인\n"
msg += "자살징후, 구타 및 가혹행위, 언어폭력 등 1번 항목 특이사항 없습니다.\n\n"
msg += "분대원 면담 및 관찰 결과 특이사항 없습니다."

st.text_area("텍스트 창을 길게 눌러 복사하세요:", value=msg, height=450)

if st.button("⚠️ 일일 데이터 초기화 (출타/인원 제외)", use_container_width=True):
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
