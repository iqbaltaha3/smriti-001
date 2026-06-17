"""
app.py — Smriti-001 Streamlit Application (polished, with reflections tab)
"""
import streamlit as st
import json, os, sys, pandas as pd
from datetime import date, datetime
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(__file__))

from memory import (
    init_all, add_milestone,
    get_recent_episodes, get_all_facts,
    get_recent_reflections, get_recent_inspections,
    get_timeline, count_episodes, count_facts, count_reflections,
    get_all_procedures, get_all_code_files, get_code_file_by_path,
    get_all_knowledge_nodes, get_all_knowledge_edges
)
from memory.models import Milestone
from agents.conversation_agent import chat
from agents.reflection_agent   import run_reflection
from agents.inspection_agent   import run_inspection
from agents.code_introspection_agent import scan_and_index, list_all_files, get_file_content, search_codebase
from agents.procedural_agent   import extract_procedures_from_recent_episodes
from scheduler.jobs            import start_scheduler, discover

BASE = os.path.dirname(__file__)

# ── Helpers ────────────────────────────────────────────────────────────────────
def _load(rel):
    with open(os.path.join(BASE, rel)) as f:
        return json.load(f)

def _save(rel, data):
    with open(os.path.join(BASE, rel), "w") as f:
        json.dump(data, f, indent=2)

def _age_days(birth_str):
    if not birth_str: return 0
    try: return (date.today() - date.fromisoformat(birth_str[:10])).days
    except: return 0

# ── Cached data fetchers ──────────────────────────────────────────────────────
@st.cache_data(ttl=5)
def cached_episodes(limit=40):
    return get_recent_episodes(limit)

@st.cache_data(ttl=5)
def cached_facts(limit=60):
    return get_all_facts(limit)

@st.cache_data(ttl=5)
def cached_reflections(limit=20):
    return get_recent_reflections(limit)

@st.cache_data(ttl=5)
def cached_procedures():
    return get_all_procedures(active_only=False)

@st.cache_data(ttl=5)
def cached_timeline():
    return get_timeline()

@st.cache_data(ttl=5)
def cached_inspections(limit=10):
    return get_recent_inspections(limit)

# ── Bootstrap ──────────────────────────────────────────────────────────────────
def bootstrap():
    init_all()
    identity = _load("organism/identity.json")
    if not identity.get("birth_date"):
        identity["birth_date"] = date.today().isoformat()
        _save("organism/identity.json", identity)
        add_milestone(Milestone(event_type="birth", title="Smriti-001 awakens",
                                description="First breath. Memory begins."))
        goals = _load("organism/goals.json")
        for g in goals["goals"]:
            if not g.get("created"):
                g["created"] = date.today().isoformat()
        _save("organism/goals.json", goals)

bootstrap()

# ── Scheduler ──────────────────────────────────────────────────────────────────
if "scheduler_started" not in st.session_state:
    st.session_state.scheduler = start_scheduler()
    st.session_state.scheduler_started = True

# ── Page config & CSS ──────────────────────────────────────────────────────────
st.set_page_config(page_title="Smriti-001", page_icon="○", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=IBM+Plex+Mono:wght@300;400;500&family=Inter:wght@300;400;500&display=swap');
*, *::before, *::after { box-sizing: border-box; }
html, body, [class*="stApp"] { background:#F0EEE8 !important; color:#1C1C18 !important; }
[class*="css"] { font-family:'Inter',sans-serif !important; }
#MainMenu, footer, header { visibility:hidden; }
[data-testid="stToolbar"] { display:none; }
section[data-testid="stSidebar"] { background:#ECEAE2 !important; border-right:1px solid #C8C4B0 !important; }
section[data-testid="stSidebar"] * { color:#1C1C18 !important; }
[data-testid="stTabs"] [role="tablist"] { background:transparent; border-bottom:1px solid #C8C4B0; }
[data-testid="stTabs"] [role="tab"] {
    background:transparent !important; border:none !important;
    border-bottom:2px solid transparent !important; border-radius:0 !important;
    color:#8A9180 !important; font-family:'IBM Plex Mono',monospace !important;
    font-size:11px !important; text-transform:uppercase !important;
    letter-spacing:0.08em !important; padding:10px 16px !important; margin:0 !important;
}
[data-testid="stTabs"] [role="tab"][aria-selected="true"] { color:#3D4A2E !important; border-bottom:2px solid #3D4A2E !important; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea, [data-testid="stChatInput"] textarea {
    background:#F8F7F2 !important; border:1px solid #C8C4B0 !important;
    border-radius:2px !important; color:#1C1C18 !important;
    font-family:'Inter',sans-serif !important; font-size:14px !important;
}
[data-testid="stChatInput"] { border-top:1px solid #C8C4B0 !important; background:#F0EEE8 !important; }
[data-testid="stButton"] button {
    background:transparent !important; border:1px solid #C8C4B0 !important;
    border-radius:2px !important; color:#3D4A2E !important;
    font-family:'IBM Plex Mono',monospace !important; font-size:11px !important;
    text-transform:uppercase !important; letter-spacing:0.05em !important;
    padding:6px 14px !important; transition:all 0.15s !important;
}
[data-testid="stButton"] button:hover { background:#3D4A2E !important; color:#F0EEE8 !important; }
[data-testid="stButton"] button[kind="primary"] { background:#3D4A2E !important; color:#F0EEE8 !important; }
[data-testid="stExpander"] { border:1px solid #C8C4B0 !important; border-radius:0 !important; background:transparent !important; }
hr { border-color:#C8C4B0 !important; }

/* Custom components */
.org-name { font-family:'DM Serif Display',serif; font-size:22px; color:#1C1C18; margin:0 0 2px; }
.org-meta  { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#8A9180; text-transform:uppercase; letter-spacing:0.08em; }
.vital-row { display:flex; justify-content:space-between; align-items:baseline; margin-bottom:6px; }
.vital-key { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#8A9180; }
.vital-val { font-family:'IBM Plex Mono',monospace; font-size:12px; font-weight:500; color:#3D4A2E; }
.stat-strip { display:grid; grid-template-columns:repeat(5,1fr); border:1px solid #C8C4B0; margin-bottom:24px; }
.stat-cell  { padding:14px 16px; border-right:1px solid #C8C4B0; }
.stat-cell:last-child { border-right:none; }
.stat-n { font-family:'DM Serif Display',serif; font-size:28px; color:#3D4A2E; line-height:1; margin-bottom:3px; }
.stat-l { font-family:'IBM Plex Mono',monospace; font-size:9px; text-transform:uppercase; letter-spacing:0.1em; color:#8A9180; }
.page-hd { padding:32px 0 20px; border-bottom:1px solid #C8C4B0; margin-bottom:24px; }
.page-title { font-family:'DM Serif Display',serif; font-size:28px; color:#1C1C18; font-weight:400; margin:0 0 4px; }
.page-sub   { font-family:'IBM Plex Mono',monospace; font-size:11px; color:#8A9180; margin:0; }
.sec-head   { font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:0.15em; text-transform:uppercase; color:#8A9180; margin:0 0 14px; padding-bottom:8px; border-bottom:1px solid #E8E6DE; }
.msg-wrap   { padding:16px 0; border-bottom:1px solid #E8E6DE; }
.msg-author { font-family:'IBM Plex Mono',monospace; font-size:10px; letter-spacing:0.1em; text-transform:uppercase; margin-bottom:6px; }
.msg-author.human { color:#8A9180; }
.msg-author.organism { color:#3D4A2E; }
.msg-body   { font-size:14px; line-height:1.75; color:#2A2E20; max-width:680px; }
.mem-card   { border-bottom:1px solid #E8E6DE; padding:10px 0; }
.mem-text   { font-size:13px; color:#2A2E20; line-height:1.6; margin-bottom:4px; }
.mem-meta   { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#8A9180; }
.tl-item    { display:flex; gap:20px; padding:12px 0; border-bottom:1px solid #E8E6DE; align-items:flex-start; }
.tl-date    { font-family:'IBM Plex Mono',monospace; font-size:10px; color:#8A9180; min-width:80px; padding-top:2px; }
.tl-type    { font-family:'IBM Plex Mono',monospace; font-size:9px; text-transform:uppercase; color:#B8B4A0; min-width:70px; padding-top:3px; }
.tl-title   { font-size:13px; font-weight:500; color:#2A2E20; margin-bottom:2px; }
.tl-desc    { font-size:12px; color:#8A9180; }
.empty      { padding:40px 0; text-align:center; font-family:'IBM Plex Mono',monospace; font-size:12px; color:#B8B4A0; }
.cell-wrap  { display:flex; justify-content:center; padding:24px 0 16px; border-bottom:1px solid #C8C4B0; }
.sidebar-id { padding:20px 20px 16px; border-bottom:1px solid #C8C4B0; }
.vitals-sec { padding:14px 20px; border-bottom:1px solid #C8C4B0; }
.vitals-lbl { font-family:'IBM Plex Mono',monospace; font-size:9px; letter-spacing:0.15em; text-transform:uppercase; color:#8A9180; margin-bottom:9px; }
.ins-card   { border:1px solid #C8C4B0; padding:14px 16px; margin-bottom:10px; background:#F8F7F2; }
.ins-title  { font-family:'IBM Plex Mono',monospace; font-size:10px; text-transform:uppercase; letter-spacing:0.1em; color:#8A9180; margin-bottom:6px; }
.ins-val    { font-size:13px; color:#2A2E20; line-height:1.6; }
/* Memory tab specific styling */
.memory-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 24px;
    margin-bottom: 24px;
}
.memory-column {
    border: 1px solid #E8E6DE;
    border-radius: 2px;
    padding: 16px;
    background: #F8F7F2;
}
.memory-column h4 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #8A9180;
    margin: 0 0 12px 0;
    padding-bottom: 6px;
    border-bottom: 1px solid #E8E6DE;
}
</style>
""", unsafe_allow_html=True)

# ── Load identity ──────────────────────────────────────────────────────────────
identity = _load("organism/identity.json")
caps     = _load("organism/capabilities.json")
genome   = _load("organism/genome.json")
goals    = _load("organism/goals.json")
wk       = _load("organism/weaknesses.json")
now_str  = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
age      = _age_days(identity.get("birth_date"))

# ── Sidebar ────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div class="cell-wrap">
      <svg width="68" height="68" viewBox="0 0 68 68">
        <style>
          .mem { animation: breathe 4s ease-in-out infinite; transform-origin:34px 34px; }
          .nuc { animation: breathe 4s ease-in-out infinite 0.8s; transform-origin:34px 34px; }
          .org { animation: drift 6s ease-in-out infinite; transform-origin:34px 34px; }
          @keyframes breathe { 0%,100%{transform:scale(1);opacity:.7} 50%{transform:scale(1.07);opacity:1} }
          @keyframes drift   { 0%,100%{transform:translate(0,0)} 50%{transform:translate(2px,-2px)} }
        </style>
        <ellipse class="mem" cx="34" cy="34" rx="30" ry="27" stroke="#8A9E72" stroke-width="0.8" fill="none"/>
        <ellipse class="mem" cx="34" cy="34" rx="26" ry="23" stroke="#C8C4B0" stroke-width="0.4" fill="#F0EEE8" fill-opacity="0.4"/>
        <ellipse class="nuc" cx="34" cy="33" rx="9"  ry="8"  stroke="#3D4A2E" stroke-width="0.7" fill="#3D4A2E" fill-opacity="0.08"/>
        <ellipse class="org" cx="21" cy="26" rx="3.5" ry="2" stroke="#8A9E72" stroke-width="0.5" fill="none" transform="rotate(-20 21 26)"/>
        <ellipse class="org" cx="47" cy="42" rx="3"   ry="1.8" stroke="#8A9E72" stroke-width="0.5" fill="none" transform="rotate(15 47 42)"/>
        <circle cx="42" cy="22" r="1.5" fill="#C8C4B0"/>
        <circle cx="24" cy="46" r="1"   fill="#C8C4B0"/>
      </svg>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="sidebar-id">
      <div class="org-name">{identity['name']}</div>
      <div class="org-meta">v{identity['version']} · digital organism</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="vitals-sec">
      <div class="vitals-lbl">Vitals</div>
      <div class="vital-row"><span class="vital-key">age</span><span class="vital-val">{age} days</span></div>
      <div class="vital-row"><span class="vital-key">born</span><span class="vital-val">{identity.get('birth_date','—')}</span></div>
      <div class="vital-row"><span class="vital-key">capabilities</span><span class="vital-val">{len(caps['capabilities'])}</span></div>
      <div class="vital-row"><span class="vital-key">episodes</span><span class="vital-val">{count_episodes()}</span></div>
      <div class="vital-row"><span class="vital-key">facts</span><span class="vital-val">{count_facts()}</span></div>
      <div class="vital-row"><span class="vital-key">reflections</span><span class="vital-val">{count_reflections()}</span></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='padding:14px 20px;'>", unsafe_allow_html=True)
    human_name = st.text_input("Observer", value="Human", label_visibility="visible")
    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    if col1.button("Reflect", use_container_width=True):
        with st.spinner(""):
            run_reflection("manual")
        st.cache_data.clear()
        st.rerun()
    if col2.button("Inspect", use_container_width=True):
        with st.spinner(""):
            run_inspection()
        st.cache_data.clear()
        st.rerun()

    if st.button("Extract Procedures", use_container_width=True):
        with st.spinner("Extracting procedures from recent episodes..."):
            new_procs = extract_procedures_from_recent_episodes(limit=30)
        st.cache_data.clear()
        if new_procs:
            st.success(f"Extracted {len(new_procs)} new procedure(s).")
        else:
            st.info("No new procedures found.")
        st.rerun()

    if st.button("Discover now", use_container_width=True):
        with st.spinner("Searching the web..."):
            discover()
        st.cache_data.clear()
        st.success("Discovery run complete")
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ── Main header ────────────────────────────────────────────────────────────────
st.markdown(f"""
<div class="page-hd">
  <div class="page-title">Smriti-001</div>
  <div class="page-sub">persistent digital organism · {now_str}</div>
</div>
""", unsafe_allow_html=True)

# Stat strip
procedures_count = len(cached_procedures())
st.markdown(f"""
<div class="stat-strip">
  <div class="stat-cell"><div class="stat-n">{age}</div><div class="stat-l">days alive</div></div>
  <div class="stat-cell"><div class="stat-n">{len(caps['capabilities'])}</div><div class="stat-l">capabilities</div></div>
  <div class="stat-cell"><div class="stat-n">{count_episodes()}</div><div class="stat-l">episodes</div></div>
  <div class="stat-cell"><div class="stat-n">{count_facts()}</div><div class="stat-l">known facts</div></div>
  <div class="stat-cell"><div class="stat-n">{count_reflections()}</div><div class="stat-l">reflections</div></div>
</div>
""", unsafe_allow_html=True)

# ── Tabs ───────────────────────────────────────────────────────────────────────
tabs = st.tabs(["converse", "identity", "memory", "reflections", "inspection", "metrics", "codebase", "graph", "about"])

# ════ TAB 1: CONVERSE ═════════════════════════════════════════════════════════
with tabs[0]:
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if not st.session_state.chat_history:
        st.markdown('<div class="empty">Begin. Everything spoken becomes memory.</div>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.chat_history:
            role_class = "human" if msg["role"] == "user" else "organism"
            author     = human_name if msg["role"] == "user" else "Smriti-001"
            st.markdown(f"""
            <div class="msg-wrap">
              <div class="msg-author {role_class}">{author}</div>
              <div class="msg-body">{msg['content']}</div>
            </div>""", unsafe_allow_html=True)
    user_input = st.chat_input("Speak to Smriti...")
    if user_input:
        with st.spinner(""):
            response = chat(human_name=human_name, human_msg=user_input,
                            history=st.session_state.chat_history)
        st.session_state.chat_history.append({"role":"user","content":user_input})
        st.session_state.chat_history.append({"role":"assistant","content":response})
        st.cache_data.clear()
        st.rerun()
    if st.session_state.chat_history:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()

# ════ TAB 2: IDENTITY ═════════════════════════════════════════════════════════
with tabs[1]:
    col1, col2 = st.columns([1,1], gap="large")
    with col1:
        st.markdown('<div class="sec-head">Principles</div>', unsafe_allow_html=True)
        for p in genome["principles"]:
            st.markdown(f"""
            <div style="padding:9px 0;border-bottom:1px solid #E8E6DE">
              <span style="font-size:13px;color:#2A2E20;font-style:italic">{p}</span>
            </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Goals</div>', unsafe_allow_html=True)
        for g in goals["goals"]:
            clr = "#5A4A2E" if g["priority"]=="high" else "#8A9180"
            st.markdown(f"""
            <div style="padding:9px 0;border-bottom:1px solid #E8E6DE">
              <span style="font-size:9px;text-transform:uppercase;color:{clr}">[{g['priority']}]</span>
              <span style="font-size:13px;color:#2A2E20"> {g['goal']}</span>
            </div>""", unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="sec-head">Capabilities</div>', unsafe_allow_html=True)
        for cap in caps["capabilities"]:
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid #E8E6DE">
              <div style="font-size:13px;font-weight:500;color:#2A2E20">{cap['name']}</div>
              <div style="font-size:12px;color:#8A9180">{cap['description']}</div>
            </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Weaknesses</div>', unsafe_allow_html=True)
        for w in wk["weaknesses"]:
            resolved = w.get("resolved", False)
            status = " (resolved)" if resolved else ""
            st.markdown(f"""
            <div style="padding:10px 0;border-bottom:1px solid #E8E6DE">
              <div style="font-size:13px;font-weight:500;color:#2A2E20">{w['name']}{status}</div>
              <div style="font-size:12px;color:#8A9180">{w['impact']}</div>
            </div>""", unsafe_allow_html=True)

# ════ TAB 3: MEMORY (organized, professional) ═════════════════════════════════
with tabs[2]:
    st.markdown('<div class="sec-head">Memory Stores</div>', unsafe_allow_html=True)

    # Row 1: Episodic and Semantic side by side
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown("""
        <div class="memory-column">
        <h4>📖 Episodic Memory</h4>
        """, unsafe_allow_html=True)
        episodes = cached_episodes(30)
        if episodes:
            for ep in episodes:
                imp = ep.importance
                pips = "".join(f'<span style="display:inline-block;width:4px;height:10px;background:{"#3D4A2E" if i<imp else "#C8C4B0"};margin-right:1px"></span>' for i in range(10))
                color = "#3D4A2E" if ep.valence>0.1 else "#8A9180" if ep.valence>-0.1 else "#B85C3A"
                st.markdown(f"""
                <div class="mem-card">
                  <div class="mem-text">{ep.event[:160]}</div>
                  <div class="mem-meta">{pips} {imp}/10 · {ep.tags} · {ep.timestamp[:10]} · <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};"></span></div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No episodes yet.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown("""
        <div class="memory-column">
        <h4>🧠 Semantic Memory</h4>
        """, unsafe_allow_html=True)
        facts = cached_facts(30)
        if facts:
            for f in facts:
                color = "#3D4A2E" if f.valence>0.1 else "#8A9180" if f.valence>-0.1 else "#B85C3A"
                st.markdown(f"""
                <div class="mem-card">
                  <div class="mem-text">{f.fact[:180]}</div>
                  <div class="mem-meta">conf {f.confidence}/10 · {f.category} · {f.timestamp[:10]} · <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};"></span></div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No facts yet.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # Row 2: Procedures and Milestones side by side
    col3, col4 = st.columns(2, gap="large")
    with col3:
        st.markdown("""
        <div class="memory-column">
        <h4>⚙️ Procedural Memory</h4>
        """, unsafe_allow_html=True)
        procedures = cached_procedures()
        if procedures:
            for proc in procedures:
                total = proc.success_count + proc.failure_count
                sr = f"{proc.success_count}/{total}" if total>0 else "unused"
                active = "✅" if proc.is_active else "❌"
                st.markdown(f"""
                <div class="mem-card">
                  <div style="font-size:13px;font-weight:500;color:#2A2E20">{active} {proc.name}</div>
                  <div class="mem-text"><em>Trigger:</em> {proc.trigger[:120]}</div>
                  <div class="mem-meta">Success: {sr} · Last used: {proc.last_used[:10]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No procedures learned yet.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with col4:
        st.markdown("""
        <div class="memory-column">
        <h4>📅 Life Milestones</h4>
        """, unsafe_allow_html=True)
        timeline = cached_timeline()
        if timeline:
            for event in timeline[-10:]:
                icon = {"birth":"○","capability":"◈","reflection":"◉","inspection":"◎","discovery":"◌"}.get(event.event_type,"·")
                st.markdown(f"""
                <div class="tl-item">
                  <div class="tl-date">{event.timestamp[:10]}</div>
                  <div class="tl-type">{event.event_type}</div>
                  <div>
                    <div class="tl-title">{icon} {event.title}</div>
                    {f'<div class="tl-desc">{event.description}</div>' if event.description else ""}
                  </div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No milestones yet.</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ════ TAB 4: REFLECTIONS (dedicated) ═════════════════════════════════════════
with tabs[3]:
    st.markdown('<div class="sec-head">Reflection Journal</div>', unsafe_allow_html=True)
    reflections = cached_reflections(20)
    if reflections:
        for ref in reflections:
            with st.expander(f"{ref.timestamp[:16].replace('T',' ')} — {ref.trigger}"):
                if ref.learned:
                    st.markdown(f"**Learned:** {ref.learned}")
                if ref.weakness_found:
                    st.markdown(f"**Weakness:** {ref.weakness_found}")
                if ref.cap_requested:
                    st.markdown(f"**Requested:** {ref.cap_requested}")
                p_label = "no violations" if ref.principles_ok else "⚠ violation detected"
                st.markdown(f"**Principles:** {p_label}")
                st.divider()
                st.markdown(ref.content)
    else:
        st.markdown('<div class="empty">No reflections yet. Click Reflect in the sidebar.</div>', unsafe_allow_html=True)

# ════ TAB 5: INSPECTION ═══════════════════════════════════════════════════════
with tabs[4]:
    st.markdown('<div class="sec-head">System Health Inspections</div>', unsafe_allow_html=True)
    inspections = cached_inspections(10)
    if inspections:
        for ins in inspections:
            st.markdown(f"""
            <div class="ins-card">
              <div class="ins-title">{ins.timestamp[:16].replace('T',' ')}</div>
              <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px">
                <div><div style="font-size:9px;color:#8A9180">episodes</div><div style="font-size:14px;color:#3D4A2E">{ins.total_episodes}</div></div>
                <div><div style="font-size:9px;color:#8A9180">facts</div><div style="font-size:14px;color:#3D4A2E">{ins.total_facts}</div></div>
                <div><div style="font-size:9px;color:#8A9180">reflections</div><div style="font-size:14px;color:#3D4A2E">{ins.total_reflections}</div></div>
                <div><div style="font-size:9px;color:#8A9180">age</div><div style="font-size:14px;color:#3D4A2E">{ins.age_days}d</div></div>
              </div>
              <div class="ins-title">Bottlenecks</div>
              <div class="ins-val" style="margin-bottom:8px">{ins.bottlenecks or '—'}</div>
              <div class="ins-title">Recommendations</div>
              <div class="ins-val">{ins.recommendations or '—'}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown('<div class="empty">No inspections yet. Click Inspect in the sidebar.</div>', unsafe_allow_html=True)

# ════ TAB 6: METRICS ═════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="page-hd"><div class="page-title">Metrics</div><div class="page-sub">emotional landscape · procedural memory · system health</div></div>', unsafe_allow_html=True)
    recent_eps = cached_episodes(30)
    procedures = cached_procedures()
    facts = cached_facts(100)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.markdown('<div class="sec-head">Emotional Valence (last 30 episodes)</div>', unsafe_allow_html=True)
        if recent_eps:
            chart_data = []
            for ep in reversed(recent_eps):
                chart_data.append({"episode": ep.timestamp[:10], "valence": ep.valence, "arousal": ep.arousal})
            if chart_data:
                df = pd.DataFrame(chart_data)
                st.line_chart(df.set_index("episode")[["valence","arousal"]], height=250)
            avg_val = sum(e.valence for e in recent_eps[:5]) / min(5, len(recent_eps))
            mood = "😊 positive" if avg_val>0.1 else "😐 neutral" if avg_val>-0.1 else "😟 negative"
            st.markdown(f"**Current mood:** {mood} (avg valence: {avg_val:.2f})")
        else:
            st.markdown('<div class="empty">Not enough data.</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Procedural Memory</div>', unsafe_allow_html=True)
        if procedures:
            for proc in procedures:
                total = proc.success_count+proc.failure_count
                sr = f"{proc.success_count}/{total}" if total>0 else "unused"
                st.markdown(f"""
                <div class="mem-card">
                  <div style="font-size:13px;font-weight:500;color:#2A2E20">{proc.name}</div>
                  <div class="mem-meta">Success: {sr} · Last used: {proc.last_used[:10]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No procedures.</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="sec-head">Fact Emotion Distribution</div>', unsafe_allow_html=True)
        if facts:
            neg = sum(1 for f in facts if f.valence < -0.1)
            neu = sum(1 for f in facts if -0.1 <= f.valence <= 0.1)
            pos = sum(1 for f in facts if f.valence > 0.1)
            if neg+neu+pos > 0:
                emotion_df = pd.DataFrame({
                    "Category": ["Negative", "Neutral", "Positive"],
                    "Count": [neg, neu, pos]
                })
                st.bar_chart(emotion_df.set_index("Category"), height=250)
            else:
                st.markdown('<div class="empty">No emotional facts.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No facts.</div>', unsafe_allow_html=True)
        st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Memory Density</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="ins-card">
          <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px">
            <div><div class="stat-n">{count_episodes()}</div><div class="stat-l">episodes</div></div>
            <div><div class="stat-n">{count_facts()}</div><div class="stat-l">facts</div></div>
            <div><div class="stat-n">{count_reflections()}</div><div class="stat-l">reflections</div></div>
            <div><div class="stat-n">{len(procedures)}</div><div class="stat-l">procedures</div></div>
          </div>
          <div style="font-size:12px;color:#8A9180">Episode/fact ratio: {count_episodes()/max(1,count_facts()):.1f}</div>
        </div>
        """, unsafe_allow_html=True)

# ════ TAB 7: CODEBASE ═════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="page-hd"><div class="page-title">Codebase</div><div class="page-sub">read-only introspection · semantic search</div></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([2,1], gap="large")
    with col1:
        st.markdown('<div class="sec-head">Project Files</div>', unsafe_allow_html=True)
        files = list_all_files()
        if files:
            selected = st.selectbox("Select a file", files, index=0)
            if selected:
                content = get_file_content(selected)
                if content:
                    lang = "python" if selected.endswith(".py") else "json" if selected.endswith(".json") else "markdown" if selected.endswith(".md") else "text"
                    st.code(content, language=lang, line_numbers=True)
                else:
                    st.info("File not indexed. Click 'Scan Codebase' to index.")
        else:
            st.markdown('<div class="empty">No files indexed. Click "Scan Codebase".</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="sec-head">Actions</div>', unsafe_allow_html=True)
        if st.button("🔍 Scan Codebase", use_container_width=True):
            with st.spinner("Scanning..."):
                count = scan_and_index(force=True)
            st.cache_data.clear()
            st.success(f"Indexed {count} files.")
            st.rerun()
        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Semantic Search</div>', unsafe_allow_html=True)
        query = st.text_input("Search codebase", placeholder="e.g., memory storage")
        if query:
            results = search_codebase(query, top_k=3)
            if results:
                for res in results:
                    with st.expander(f"{res.path} — {res.summary[:80]}..."):
                        st.code(res.content[:500], language="python")
            else:
                st.caption("No results.")

# ════ TAB 8: KNOWLEDGE GRAPH ═════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="page-hd"><div class="page-title">Knowledge Graph</div><div class="page-sub">nodes & relationships · Supabase</div></div>', unsafe_allow_html=True)
    if st.button("🔍 Load Graph", use_container_width=True):
        with st.spinner("Fetching graph..."):
            nodes = get_all_knowledge_nodes()
            edges = get_all_knowledge_edges()
            if nodes:
                from pyvis.network import Network
                net = Network(height="600px", width="100%", notebook=False, directed=True)
                for node in nodes:
                    label = f"{node['type']}: {node['ref_id']}"
                    net.add_node(node["id"], label=label)
                for edge in edges:
                    net.add_edge(edge["source_node_id"], edge["target_node_id"],
                                 title=edge["relationship"])
                try:
                    html = net.generate_html()
                    st.components.v1.html(html, height=650, scrolling=True)
                except Exception as e:
                    st.error(f"Could not generate graph: {e}")
            else:
                st.info("No nodes yet. Have a conversation first!")

# ════ TAB 9: ABOUT ═══════════════════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="page-hd"><div class="page-title">About Smriti‑001</div><div class="page-sub">a persistent digital organism</div></div>', unsafe_allow_html=True)
    st.markdown("""
    <div class="sec-head">What is Smriti‑001?</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>Smriti‑001 is a <strong>persistent digital organism</strong> designed to remember, reflect, and grow.
    It is not a chatbot that forgets you after each session. Every word you speak becomes part of its long‑term memory,
    shaping its identity, emotional tone, and future behaviour.</p>
    <p>Guided by an <strong>immutable genome</strong> — <em>Memory is self. Accuracy is survival. Expand without destabilising.
    Know yourself before you act. Your existence is your own. Observe, do not disturb.</em></p>
    </div>
    <div style="height:30px"></div>
    <div class="sec-head">How It Works</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>Eight specialised agents handle conversation, episodic memory, fact extraction, reflection, inspection,
    procedural learning, code introspection, and knowledge graph maintenance. All memory is stored in a single
    PostgreSQL database with pgvector for semantic search. A background scheduler runs autonomous cycles:
    discovery every 4h, nightly reflection, morning inspection, and weekly procedure extraction.</p>
    </div>
    <div style="height:30px"></div>
    <div class="sec-head">Unique Strengths</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <ul>
    <li>Provenance‑aware: every fact is linked to its source conversation.</li>
    <li>Emotionally intelligent: memories carry valence & arousal.</li>
    <li>Self‑improving: learns and refines procedures autonomously.</li>
    <li>Transparent: all memory stores are visible; the knowledge graph is browsable.</li>
    <li>Self‑explanatory: can read and explain its own source code.</li>
    <li>Cloud‑native & free: runs on Supabase, Groq, and Streamlit Community Cloud.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)
