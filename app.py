import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="대표병 결산 프로그램", layout="wide")

def init_db():
    conn = sqlite3.connect('squad.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS members (id INTEGER PRIMARY KEY AUTOINCREMENT, rank TEXT, name TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS outings (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, type TEXT, period TEXT, leave_type TEXT, dest TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS visits (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, v_date TEXT, v_time TEXT, loc TEXT, visitor TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS haircuts (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS religions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, religion TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS deliveries (id INTEGER PRIMARY KEY AUTOINCREMENT, d_date TEXT, d_time TEXT, menu TEXT, members TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS exceptions (id INTEGER PRIMARY KEY AUTOINCREMENT, member TEXT, reason TEXT)')
    conn.commit()
    conn.close()

init_db()

def get_members():
    conn = sqlite3.connect('squad.db')
    df = pd.read_sql_query("SELECT rank, name FROM members", conn)
    conn.close()
    return df

st.title("📋 대표병 결산 생성 프로그램 (Google Cloud 배포용)")

tabs = st.tabs(["👥 인원", "출타", "면회", "이발", "종교", "배달", "열외", "📊 종합"])
members_df = get_members()
member_names = (members_df['rank'] + " " + members_df['name']).tolist() if not members_df.empty else []

with tabs[0]:
    st.subheader("인원 관리 (최대 10명)")
    col1, col2 = st.columns(2)
    with col1:
        rank = st.selectbox("계급", ["이병", "일병", "상병", "병장"])
        name = st.text_input("이름")
        if st.button("추가"):
            if len(members_df) >= 10:
                st.error("10명 초과 불가")
            elif name:
                conn = sqlite3.connect('squad.db')
                conn.execute("INSERT INTO members (rank, name) VALUES (?, ?)", (rank, name))
                conn.commit()
                conn.close()
                st.rerun()
    with col2:
        st.dataframe(members_df, hide_index=True)

with tabs[1]:
    if member_names:
        m = st.selectbox("출타자", member_names, key='out_m')
        t = st.selectbox("종류", ["휴가", "평일외출", "주말외출", "주말외박"])
        p = st.text_input("기간 (예: 26.09.11~26.09.15)")
        l = st.text_input("휴가종류")
        d = st.text_input("행선지")
        if st.button("출타 저장"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO outings (member, type, period, leave_type, dest) VALUES (?,?,?,?,?)", (m,t,p,l,d))
            conn.commit()
            conn.close()
            st.success("저장 완료")

with tabs[2]:
    if member_names:
        m = st.selectbox("면회자", member_names, key='vis_m')
        vd = st.date_input("일자")
        vt = st.time_input("시간")
        loc = st.radio("장소", ["영내", "영외"])
        vis = st.text_input("면회객")
        if st.button("면회 저장"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO visits (member, v_date, v_time, loc, visitor) VALUES (?,?,?,?,?)", (m, str(vd), str(vt), loc, vis))
            conn.commit()
            conn.close()
            st.success("저장 완료")

with tabs[3]:
    if member_names:
        hm = st.multiselect("이발자", member_names)
        if st.button("이발 저장"):
            conn = sqlite3.connect('squad.db')
            for p in hm:
                conn.execute("INSERT INTO haircuts (member) VALUES (?)", (p,))
            conn.commit()
            conn.close()
            st.success("저장 완료")

with tabs[4]:
    if member_names:
        rm = st.selectbox("참석자", member_names, key='rel_m')
        rel = st.selectbox("종교", ["불교", "기독교", "천주교"])
        if st.button("종교 저장"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO religions (member, religion) VALUES (?,?)", (rm, rel))
            conn.commit()
            conn.close()
            st.success("저장 완료")

with tabs[5]:
    if member_names:
        dd = st.date_input("배달일자")
        dt = st.time_input("배달시간")
        menu = st.text_input("메뉴")
        dm = st.multiselect("취식인원", member_names, key='del_m')
        if st.button("배달 저장"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO deliveries (d_date, d_time, menu, members) VALUES (?,?,?,?)", (str(dd), str(dt), menu, ",".join(dm)))
            conn.commit()
            conn.close()
            st.success("저장 완료")
            
with tabs[6]:
    if member_names:
        em = st.selectbox("열외자", member_names, key='exc_m')
        rs = st.selectbox("사유", ["근무", "휴가", "외출", "외박", "상황병", "입실", "파견"])
        if st.button("열외 저장"):
            conn = sqlite3.connect('squad.db')
            conn.execute("INSERT INTO exceptions (member, reason) VALUES (?,?)", (em, rs))
            conn.commit()
            conn.close()
            st.success("저장 완료")

with tabs[7]:
    st.subheader("결산 종합")
    if st.button("데이터 새로고침"):
        st.rerun()
    conn = sqlite3.connect('squad.db')
    tables = ['outings', 'visits', 'haircuts', 'religions', 'deliveries', 'exceptions']
    for t in tables:
        st.markdown(f"**{t.upper()}**")
        df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
        st.dataframe(df, hide_index=True)
    conn.close()
