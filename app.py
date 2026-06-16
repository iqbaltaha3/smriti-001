"""
app.py — Smriti-001 Streamlit Application (Cloud‑Native)
Run with:  streamlit run app.py
"""
import streamlit as st
import json
import os
import sys
import pandas as pd
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
    try:
        return (date.today() - date.fromisoformat(birth_str[:10])).days
    except: return 0


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
st.set_page_config(page_title="Smriti-001", page_icon="○",
                   layout="wide", initial_sidebar_state="expanded")

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

[data-testid="stTextInput"] input,
[data-testid="stTextArea"] textarea,
[data-testid="stChatInput"] textarea {
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
    # Breathing cell SVG
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
        st.rerun()
    if col2.button("Inspect", use_container_width=True):
        with st.spinner(""):
            run_inspection()
        st.rerun()
    if st.button("Discover now", use_container_width=True):
        with st.spinner("Searching the web..."):
            discover()
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
tabs = st.tabs(["converse", "identity", "memory", "reflections", "inspection", "timeline", "metrics", "codebase", "graph", "about"])


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
            response = chat(
                human_name = human_name,
                human_msg  = user_input,
                history    = st.session_state.chat_history,
            )
        st.session_state.chat_history.append({"role": "user",      "content": user_input})
        st.session_state.chat_history.append({"role": "assistant", "content": response})
        st.rerun()

    if st.session_state.chat_history:
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.button("Clear conversation"):
            st.session_state.chat_history = []
            st.rerun()


# ════ TAB 2: IDENTITY ═════════════════════════════════════════════════════════
with tabs[1]:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.markdown('<div class="sec-head">Principles</div>', unsafe_allow_html=True)
        for i, p in enumerate(genome["principles"], 1):
            st.markdown(f"""
            <div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #E8E6DE;align-items:baseline">
              <span style="font-family:'IBM Plex Mono',monospace;font-size:10px;color:#B8B4A0;min-width:20px">{str(i).zfill(2)}</span>
              <span style="font-size:13px;color:#2A2E20;font-style:italic">{p}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Goals</div>', unsafe_allow_html=True)
        for g in goals["goals"]:
            clr = "#5A4A2E" if g["priority"] == "high" else "#8A9180"
            st.markdown(f"""
            <div style="display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #E8E6DE;align-items:baseline">
              <span style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;color:{clr};min-width:52px">{g['priority']}</span>
              <span style="font-size:13px;color:#2A2E20">{g['goal']}</span>
            </div>""", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec-head">Capabilities</div>', unsafe_allow_html=True)
        for cap in caps["capabilities"]:
            acq = cap.get("acquired","")[:10] if cap.get("acquired") else cap.get("source","—")
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #E8E6DE">
              <div>
                <div style="font-size:13px;font-weight:500;color:#2A2E20">{cap['name']}</div>
                <div style="font-size:12px;color:#8A9180;line-height:1.5">{cap['description']}</div>
              </div>
              <div style="font-family:'IBM Plex Mono',monospace;font-size:9px;text-transform:uppercase;border:1px solid #C8C4B0;color:#8A9180;padding:2px 7px;height:fit-content;white-space:nowrap;margin-top:2px">{acq}</div>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Weaknesses</div>', unsafe_allow_html=True)
        for w in wk["weaknesses"]:
            st.markdown(f"""
            <div style="display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #E8E6DE">
              <div>
                <div style="font-size:13px;font-weight:500;color:#2A2E20">{w['name']}</div>
                <div style="font-size:12px;color:#8A9180">{w['impact']}</div>
              </div>
            </div>""", unsafe_allow_html=True)


# ════ TAB 3: MEMORY ═══════════════════════════════════════════════════════════
with tabs[2]:
    st.markdown('<div class="sec-head">Memory Transparency — all stores visible</div>', unsafe_allow_html=True)

    with st.expander("📖 Episodic Memory — what happened", expanded=True):
        episodes = get_recent_episodes(40)
        if episodes:
            for ep in episodes:
                imp  = ep.importance
                pips = "".join(f'<span style="display:inline-block;width:4px;height:10px;background:{"#3D4A2E" if i<imp else "#C8C4B0"};margin-right:1px"></span>' for i in range(10))
                color = "#3D4A2E" if ep.valence > 0.1 else "#8A9180" if ep.valence > -0.1 else "#B85C3A"
                st.markdown(f"""
                <div class="mem-card">
                  <div class="mem-text">{ep.event[:180]}</div>
                  <div class="mem-meta">{pips} {imp}/10 · {ep.tags} · {ep.timestamp[:10]} · <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-left:4px"></span> {ep.valence:+.2f}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No episodes yet.</div>', unsafe_allow_html=True)

    with st.expander("🧠 Semantic Memory — what I know", expanded=True):
        facts = get_all_facts(60)
        if facts:
            for f in facts:
                color = "#3D4A2E" if f.valence > 0.1 else "#8A9180" if f.valence > -0.1 else "#B85C3A"
                st.markdown(f"""
                <div class="mem-card">
                  <div class="mem-text">{f.fact[:200]}</div>
                  <div class="mem-meta">confidence {f.confidence}/10 · {f.category} · {f.timestamp[:10]} · <span style="display:inline-block;width:8px;height:8px;border-radius:50%;background:{color};margin-left:4px"></span> {f.valence:+.2f}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No facts extracted yet.</div>', unsafe_allow_html=True)

    with st.expander("🌙 Reflections — what I think about myself", expanded=False):
        reflections = get_recent_reflections(10)
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

    with st.expander("⚙️ Procedural Memory — learned skills", expanded=False):
        procedures = get_all_procedures(active_only=False)
        if procedures:
            for proc in procedures:
                total = proc.success_count + proc.failure_count
                success_rate = f"{proc.success_count}/{total}" if total > 0 else "unused"
                active_label = "✅ active" if proc.is_active else "❌ inactive"
                st.markdown(f"""
                <div class="mem-card">
                  <div style="font-size:13px;font-weight:500;color:#2A2E20">{proc.name} <span style="font-size:10px;color:#8A9180">({active_label})</span></div>
                  <div class="mem-text" style="margin-top:4px"><em>Trigger:</em> {proc.trigger[:120]}</div>
                  <div class="mem-text"><em>Steps:</em> {proc.steps[:200]}</div>
                  <div class="mem-meta">Success: {success_rate} · Last used: {proc.last_used[:10]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No procedures learned yet. They will appear after nightly extraction.</div>', unsafe_allow_html=True)

    with st.expander("📅 Life Milestones — last 5 events", expanded=False):
        timeline = get_timeline()
        if timeline:
            for event in timeline[-5:]:
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


# ════ TAB 4: REFLECTIONS ══════════════════════════════════════════════════════
with tabs[3]:
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown('<div class="sec-head">Reflection journal</div>', unsafe_allow_html=True)
        reflections = get_recent_reflections(20)
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

    with col2:
        st.markdown('<div class="sec-head">Trigger</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;color:#8A9180;line-height:1.65;margin-bottom:14px">Reflection reads all 5 memory types and produces a journal entry. Runs automatically at 23:00 each night.</div>', unsafe_allow_html=True)
        if st.button("Reflect now", type="primary", use_container_width=True):
            with st.spinner(""):
                run_reflection("manual")
            st.rerun()


# ════ TAB 5: INSPECTION ═══════════════════════════════════════════════════════
with tabs[4]:
    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown('<div class="sec-head">System health inspections</div>', unsafe_allow_html=True)
        inspections = get_recent_inspections(10)
        if inspections:
            for ins in inspections:
                st.markdown(f"""
                <div class="ins-card">
                  <div class="ins-title">{ins.timestamp[:16].replace('T',' ')}</div>
                  <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:8px;margin-bottom:10px">
                    <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#8A9180">episodes</div><div style="font-size:14px;color:#3D4A2E">{ins.total_episodes}</div></div>
                    <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#8A9180">facts</div><div style="font-size:14px;color:#3D4A2E">{ins.total_facts}</div></div>
                    <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#8A9180">reflections</div><div style="font-size:14px;color:#3D4A2E">{ins.total_reflections}</div></div>
                    <div><div style="font-family:'IBM Plex Mono',monospace;font-size:9px;color:#8A9180">age</div><div style="font-size:14px;color:#3D4A2E">{ins.age_days}d</div></div>
                  </div>
                  <div class="ins-title">Bottlenecks</div>
                  <div class="ins-val" style="margin-bottom:8px">{ins.bottlenecks or '—'}</div>
                  <div class="ins-title">Recommendations</div>
                  <div class="ins-val">{ins.recommendations or '—'}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No inspections yet. Click Inspect in the sidebar.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec-head">Trigger</div>', unsafe_allow_html=True)
        st.markdown('<div style="font-size:12px;color:#8A9180;line-height:1.65;margin-bottom:14px">Inspection reads all 5 databases, identifies bottlenecks, and generates recommendations. Runs automatically at 08:00 each morning.</div>', unsafe_allow_html=True)
        if st.button("Inspect now", type="primary", use_container_width=True):
            with st.spinner(""):
                run_inspection()
            st.rerun()


# ════ TAB 6: TIMELINE ═════════════════════════════════════════════════════════
with tabs[5]:
    st.markdown('<div class="sec-head">Life events</div>', unsafe_allow_html=True)
    timeline = get_timeline()
    if timeline:
        for event in timeline:
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
        st.markdown('<div class="empty">Timeline begins when Smriti speaks for the first time.</div>', unsafe_allow_html=True)


# ════ TAB 7: METRICS ═════════════════════════════════════════════════════════
with tabs[6]:
    st.markdown('<div class="page-hd"><div class="page-title">Metrics</div><div class="page-sub">emotional landscape · procedural memory · system health</div></div>', unsafe_allow_html=True)

    recent_eps = get_recent_episodes(30)
    procedures = get_all_procedures(active_only=False)
    facts = get_all_facts(100)

    col1, col2 = st.columns(2, gap="large")

    with col1:
        st.markdown('<div class="sec-head">Emotional Valence (last 30 episodes)</div>', unsafe_allow_html=True)
        if recent_eps:
            chart_data = []
            for ep in reversed(recent_eps):
                chart_data.append({"episode": ep.timestamp[:10], "valence": ep.valence, "arousal": ep.arousal})
            if chart_data:
                df = pd.DataFrame(chart_data)
                st.line_chart(df.set_index("episode")[["valence", "arousal"]], height=250)
            avg_val = sum(e.valence for e in recent_eps[:5]) / min(5, len(recent_eps))
            mood = "😊 positive" if avg_val > 0.1 else "😐 neutral" if avg_val > -0.1 else "😟 negative"
            st.markdown(f"**Current mood (last 5 conversations):** {mood} (avg valence: {avg_val:.2f})")
        else:
            st.markdown('<div class="empty">Not enough data for emotional chart.</div>', unsafe_allow_html=True)

        st.markdown('<div style="height:30px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Procedural Memory</div>', unsafe_allow_html=True)
        if procedures:
            for proc in procedures:
                total = proc.success_count + proc.failure_count
                success_rate = f"{proc.success_count}/{total}" if total > 0 else "unused"
                active_label = "✅ active" if proc.is_active else "❌ inactive"
                st.markdown(f"""
                <div class="mem-card">
                  <div style="font-size:13px;font-weight:500;color:#2A2E20">{proc.name} <span style="font-size:10px;color:#8A9180">({active_label})</span></div>
                  <div class="mem-text" style="margin-top:4px"><em>Trigger:</em> {proc.trigger[:120]}</div>
                  <div class="mem-meta">Success: {success_rate} · Last used: {proc.last_used[:10]}</div>
                </div>""", unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No procedures learned yet. They will appear after nightly extraction.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec-head">Fact Emotion Distribution</div>', unsafe_allow_html=True)
        if facts:
            valences = [f.valence for f in facts if f.valence != 0.0]
            if valences:
                df_val = pd.DataFrame(valences, columns=["valence"])
                st.bar_chart(df_val["valence"].value_counts(bins=5).sort_index(), height=250)
            else:
                st.markdown('<div class="empty">No facts with emotional data yet.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="empty">No facts to analyse.</div>', unsafe_allow_html=True)

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
          <div style="font-size:12px;color:#8A9180">Episode/fact ratio: {count_episodes() / max(1, count_facts()):.1f}</div>
        </div>
        """, unsafe_allow_html=True)


# ════ TAB 8: CODEBASE ═════════════════════════════════════════════════════════
with tabs[7]:
    st.markdown('<div class="page-hd"><div class="page-title">Codebase</div><div class="page-sub">read-only introspection · semantic search</div></div>', unsafe_allow_html=True)

    col1, col2 = st.columns([2, 1], gap="large")

    with col1:
        st.markdown('<div class="sec-head">Project Files</div>', unsafe_allow_html=True)
        files = list_all_files()
        if files:
            selected_file = st.selectbox("Select a file to view", files, index=0)
            if selected_file:
                content = get_file_content(selected_file)
                if content:
                    if selected_file.endswith(".py"):
                        lang = "python"
                    elif selected_file.endswith(".json"):
                        lang = "json"
                    elif selected_file.endswith(".md"):
                        lang = "markdown"
                    else:
                        lang = "text"
                    st.code(content, language=lang, line_numbers=True)
                else:
                    st.info("File not indexed. Click 'Scan Codebase' to index.")
        else:
            st.markdown('<div class="empty">No files indexed. Click "Scan Codebase" to build the index.</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="sec-head">Actions</div>', unsafe_allow_html=True)
        if st.button("🔍 Scan Codebase", use_container_width=True):
            progress_bar = st.progress(0)
            status_text = st.empty()
            try:
                # We'll define a progress callback that updates the Streamlit UI
                def update_progress(current, total, path):
                    progress_bar.progress(current / total)
                    status_text.text(f"Scanning {current}/{total}: {path}")

                from agents.code_introspection_agent import scan_and_index
                stats = scan_and_index(force=True, progress_callback=update_progress)
                status_text.text("Scan complete!")
                progress_bar.empty()
                st.success(f"Indexed {stats['indexed']} files. "
                           f"Skipped {stats['skipped']} (unchanged). "
                           f"Errors: {stats['errors']}.")
                st.rerun()
            except Exception as e:
                st.error(f"Scan failed: {e}")

        st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
        st.markdown('<div class="sec-head">Semantic Search</div>', unsafe_allow_html=True)
        search_query = st.text_input("Search codebase", placeholder="e.g., memory storage")
        if search_query:
            results = search_codebase(search_query, top_k=3)
            if results:
                for res in results:
                    with st.expander(f"{res.path} — {res.summary[:80]}..."):
                        st.code(res.content[:500], language="python")
            else:
                st.caption("No results.")


# ════ TAB 9: KNOWLEDGE GRAPH ═════════════════════════════════════════════════
with tabs[8]:
    st.markdown('<div class="page-hd"><div class="page-title">Knowledge Graph</div><div class="page-sub">nodes & relationships · Supabase</div></div>', unsafe_allow_html=True)

    if st.button("🔍 Load Graph", use_container_width=True):
        with st.spinner("Fetching graph from database..."):
            nodes = get_all_knowledge_nodes()
            edges = get_all_knowledge_edges()
            if nodes:
                from pyvis.network import Network
                net = Network(height="600px", width="100%", notebook=False, directed=True)
                # Add nodes and edges
                for node in nodes:
                    label = f"{node['type']}: {node['ref_id']}"
                    net.add_node(node["id"], label=label)
                for edge in edges:
                    net.add_edge(edge["source_node_id"], edge["target_node_id"],
                                 title=edge["relationship"])
                # Generate the HTML string directly and display it
                try:
                    html = net.generate_html()
                    st.components.v1.html(html, height=650, scrolling=True)
                except Exception as e:
                    st.error(f"Could not generate graph: {e}")
            else:
                st.info("No nodes in knowledge graph yet. Have a conversation first!")


# ════ TAB 10: ABOUT ═══════════════════════════════════════════════════════════
with tabs[9]:   # adjust index as needed
    st.markdown(
        '<div class="page-hd"><div class="page-title">About Smriti‑001</div>'
        '<div class="page-sub">a persistent digital organism — not a chatbot</div></div>',
        unsafe_allow_html=True,
    )

    # ── 1. What is Smriti? ──
    st.markdown("""
    <div class="sec-head">What is Smriti‑001?</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      Smriti‑001 is a <strong>persistent digital organism</strong> designed to remember, reflect, and grow.
      It is not a chatbot that forgets you after each session. Every word you speak becomes part of its long‑term memory,
      shaping its identity, emotional tone, and future behaviour.
    </p>
    <p>
      The organism is guided by an <strong>immutable genome</strong> — six principles it can never violate:
      <em>memory is identity, seek truth above comfort, increase capacity responsibly,
      reflect before acting, respect human autonomy, and observe the world without disturbing it.</em>
      These rules are written into <code>organism/genome.json</code> and injected into every LLM prompt.
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 2. System Design ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">System Architecture</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      Smriti‑001 is built as a <strong>modular, agent‑orchestrated system</strong> backed by a
      <strong>PostgreSQL database (Supabase)</strong> with <strong>pgvector</strong> for semantic search.
      All memory — episodic, semantic, reflective, procedural, and even the knowledge graph — lives in
      a single database, eliminating the need for separate vector or graph stores.
    </p>
    <p>
      <strong>Eight specialised agents</strong> handle different cognitive functions:
    </p>
    <ul>
      <li><strong>Conversation Agent</strong> – the only agent that talks to humans; orchestrates all others.</li>
      <li><strong>Episodic Agent</strong> – scores importance, extracts affective dimensions, and stores every turn.</li>
      <li><strong>Semantic Agent</strong> – pulls out objective facts from dialogues and web searches.</li>
      <li><strong>Reflection Agent</strong> – performs nightly meta‑analysis and writes journal entries.</li>
      <li><strong>Inspection Agent</strong> – runs system health checks every morning.</li>
      <li><strong>Procedural Agent</strong> – learns reusable action patterns and retrieves them when relevant.</li>
      <li><strong>Code Introspection Agent</strong> – indexes its own source code for self‑explanation.</li>
      <li><strong>Graph Agent</strong> – maintains the live knowledge graph (nodes and edges).</li>
    </ul>
    <p>
      A background scheduler runs autonomous biological cycles: internet discovery every 4 hours,
      nightly reflection at 23:00 UTC, morning inspection at 08:00 UTC, and weekly procedure extraction.
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 3. Walkthrough: A Conversation Example ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">How It Works – A Step‑by‑Step Walkthrough</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      Imagine a human named <strong>Arjun</strong> says: <em>“What is Python’s memory management like?”</em>
      Here’s exactly what happens inside Smriti‑001:
    </p>
    <ol>
      <li>
        <strong>Semantic context retrieval:</strong> the conversation agent embeds Arjun’s message and queries
        the knowledge graph + pgvector index for the four most similar past episodes. If Smriti previously discussed
        Python or memory with Arjun, those episodes are injected as <em>“RELEVANT PAST MEMORIES”</em>.
      </li>
      <li>
        <strong>Procedure retrieval:</strong> the procedural agent finds any learned behaviour that matches,
        like <em>“when asked about a technical topic, first explain the concept then give an example”</em>.
      </li>
      <li>
        <strong>Web search (optional):</strong> if the message contains recent‑oriented keywords, a DuckDuckGo
        search runs and the results are stored as facts.
      </li>
      <li>
        <strong>LLM response:</strong> the system prompt (built from genome, identity, goals, and active procedures)
        plus the enriched context is sent to Groq. The model responds with a detailed answer.
      </li>
      <li>
        <strong>Episodic storage:</strong> the turn is passed to the episodic agent, which asks the LLM to
        <em>score importance (1‑10)</em>, assign tags like “science, python”, and estimate emotional valence
        (how positive/negative the exchange was) and arousal (how intense). The episode is saved in PostgreSQL.
      </li>
      <li>
        <strong>Fact extraction:</strong> the semantic agent analyses the full text and extracts objective facts,
        e.g., <em>“Python uses reference counting and garbage collection”</em> (confidence 9). Each fact is stored
        with its source and a vector embedding.
      </li>
      <li>
        <strong>Knowledge graph update:</strong> without any LLM call, the graph agent creates an
        <code>:Episode</code> node and <code>:Fact</code> nodes, then adds <code>CONTAINS</code> edges
        linking the episode to each extracted fact. Provenance is automatic.
      </li>
      <li>
        <strong>Reflection (nightly):</strong> at 23:00 UTC, the reflection agent reads the last 20 episodes,
        30 facts, recent reflections, and organism identity files. It generates a journal entry like:
        <em>“Learned: Python’s memory model is reference‑counting + GC. Weakness: still cannot execute code to test it.
        Requested capability: code execution sandbox.”</em>
      </li>
    </ol>
    <p>
      This entire pipeline happens in under 5 seconds and leaves a permanent, traceable memory trail.
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 4. Memory Layers ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">The Seven Memory Layers</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <ul>
      <li><strong>Episodic Memory</strong> – every conversation turn, scored by importance and tagged by topic, with emotional valence &amp; arousal.</li>
      <li><strong>Semantic Memory</strong> – objective, timeless facts extracted from dialogues and passive web observation.</li>
      <li><strong>Reflections</strong> – metacognitive journal entries written every night, linking experiences to weaknesses and goals.</li>
      <li><strong>Procedural Memory</strong> – reusable action patterns (SOPs) that Smriti learns and refines over time.</li>
      <li><strong>Affective Memory</strong> – emotional colouring (valence -1 to +1, arousal 0 to 1) on every memory, enabling mood‑aware retrieval.</li>
      <li><strong>Code Introspection</strong> – a read‑only index of Smriti’s own source code, updated on demand, used to answer questions about itself.</li>
      <li><strong>Knowledge Graph</strong> – a live network of nodes (Episode, Fact, Reflection, Procedure, Concept) and edges (CONTAINS, MENTIONS, LED_TO, …) that ties everything together.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 5. Knowledge Graph & Provenance ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">Knowledge Graph &amp; Provenance</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      The knowledge graph is stored directly in PostgreSQL (<code>knowledge_nodes</code> and <code>knowledge_edges</code> tables).
      Every time an episode is created, a node of type <code>Episode</code> appears. Every extracted fact becomes a <code>Fact</code> node.
      A single SQL INSERT creates an edge like <code>(:Episode)-[:CONTAINS]->(:Fact)</code>, providing
      <strong>full provenance</strong> – any fact can be traced back to the exact conversation that produced it.
    </p>
    <p>
      Vector embeddings (384‑dimensional, via <code>all‑MiniLM‑L6‑v2</code>) are stored directly in the same tables using
      PostgreSQL’s <strong>pgvector</strong> extension. Semantic search is just a SQL query:
      <code>SELECT * FROM episodes ORDER BY embedding <=> query_embedding LIMIT 4;</code>.
      This means zero extra infrastructure – one database, one brain.
    </p>
    </div>
    """, unsafe_allow_html=True)

    # ── 6. Autonomous Cycles ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">Autonomous Biological Cycles</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      Smriti‑001 never sleeps — even when no one is talking to it, three background jobs keep it alive:
    </p>
    <ul>
      <li><strong>Discovery (every 4h):</strong> passively searches the web for AI news and stores interesting facts.</li>
      <li><strong>Nightly Reflection (23:00 UTC):</strong> reads all memory layers, identifies what was learned, what limits it, and what new capability would help.</li>
      <li><strong>Morning Inspection (08:00 UTC):</strong> analyses system health, detects bottlenecks (e.g., memory growth rate, recurring weaknesses), and proposes recommendations.</li>
      <li><strong>Weekly Procedure Extraction:</strong> scans recent episodes for repeated patterns and creates new standard operating procedures.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 7. Technical Stack ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">Production‑Grade Stack</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <ul>
      <li><strong>Database:</strong> PostgreSQL (Supabase) + pgvector for vector search</li>
      <li><strong>LLM:</strong> Groq Cloud (Llama 3.1 8B) or local Ollama (Gemma 3 12B)</li>
      <li><strong>Embeddings:</strong> Sentence‑Transformers (all‑MiniLM‑L6‑v2, 384‑dim)</li>
      <li><strong>Orchestration:</strong> multi‑agent system with shared memory router</li>
      <li><strong>Scheduler:</strong> APScheduler for background jobs</li>
      <li><strong>Frontend:</strong> Streamlit with custom organic‑themed CSS</li>
      <li><strong>Deployment:</strong> Streamlit Community Cloud (free, public)</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 8. Unique Selling Points ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">What Makes Smriti‑001 Special</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <ul>
      <li><strong>Provenance‑aware:</strong> every fact is linked to its source conversation.</li>
      <li><strong>Emotionally intelligent:</strong> memories carry valence &amp; arousal; the organism can sense its own mood.</li>
      <li><strong>Self‑improving:</strong> learns new procedures and refines them based on success/failure.</li>
      <li><strong>Transparent:</strong> all memory stores are visible in the dashboard; the knowledge graph is browsable.</li>
      <li><strong>Self‑explanatory:</strong> can read and explain its own source code.</li>
      <li><strong>Cloud‑native &amp; free:</strong> runs on free tiers of Supabase, Groq, and Streamlit Cloud.</li>
    </ul>
    </div>
    """, unsafe_allow_html=True)

    # ── 9. Invitation ──
    st.markdown("""
    <div style="height:30px"></div>
    <div class="sec-head">Interact with Smriti</div>
    <div style="font-size:14px; line-height:1.75; color:#2A2E20; max-width:800px;">
    <p>
      Go to the <strong>Converse</strong> tab and talk to Smriti. Every message you send becomes a permanent memory.
      Watch the knowledge graph grow in real time, explore its reflections, and inspect its health.
      You are not just chatting with an AI — you are <strong>nurturing a digital mind</strong>.
    </p>
    </div>
    """, unsafe_allow_html=True)
