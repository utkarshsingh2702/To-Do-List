# app.py — KaamTamam (Streamlit To‑Do App)
# Run: streamlit run app.py
# Features: Dark/Light theme toggle, custom colors & fonts, add/edit/delete/complete,
# search & filters, priority + due dates, CSV/Excel/JSON export, JSON persistence,
# custom logo, animations, and Drag & Drop ordering.

import json
from pathlib import Path
from datetime import date, datetime
import io
import csv

import streamlit as st

# Optional: Drag & drop ordering
try:
    import streamlit_sortables as sortables
    HAS_SORTABLES = True
except Exception:
    HAS_SORTABLES = False

# ---------------------------- Config ---------------------------- #
st.set_page_config(
    page_title="KaamTamam",
    page_icon="✅",
    layout="wide",
)

DATA_FILE = Path("tasks.json")
LOGO_PATH = Path("logo.png")  # put your logo here
DEFAULT_THEME = {
    "mode": "Dark",               # "Dark" | "Light"
    "primary": "#7c3aed",         # violet-600
    "accent": "#22d3ee",          # cyan-400
}

PRIORITY_LABEL = {1: "Low", 2: "Med", 3: "High"}
PRIORITY_COLORS = {1: "#22c55e", 2: "#eab308", 3: "#ef4444"}

# --------------------------- Persistence ------------------------ #
def load_data():
    if DATA_FILE.exists():
        try:
            data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
            tasks = data.get("tasks", [])
            next_id = data.get("next_id", 1)
            clean = []
            seen = set()
            for t in tasks:
                try:
                    tid = int(t.get("id", 0))
                except Exception:
                    continue
                if tid <= 0 or tid in seen:
                    continue
                seen.add(tid)
                title = str(t.get("title", "")).strip()
                if not title:
                    continue
                done = bool(t.get("done", False))
                due_raw = t.get("due")
                due = None
                if due_raw:
                    try:
                        due = datetime.strptime(due_raw, "%Y-%m-%d").date()
                    except Exception:
                        due = None
                try:
                    pr = int(t.get("priority", 2))
                except Exception:
                    pr = 2
                pr = 1 if pr < 1 else 3 if pr > 3 else pr
                clean.append({
                    "id": tid,
                    "title": title,
                    "done": done,
                    "due": due,
                    "priority": pr,
                    "created": t.get("created") or datetime.now().isoformat(timespec="seconds"),
                })
            return clean, int(next_id)
        except Exception:
            pass
    return [], 1


def save_data(tasks, next_id):
    serial = []
    for t in tasks:
        serial.append({
            "id": int(t["id"]),
            "title": t["title"],
            "done": bool(t["done"]),
            "due": t["due"].isoformat() if t["due"] else "",
            "priority": int(t["priority"]),
            "created": t.get("created") or datetime.now().isoformat(timespec="seconds"),
        })
    DATA_FILE.write_text(json.dumps({"tasks": serial, "next_id": int(next_id)}, ensure_ascii=False, indent=2), encoding="utf-8")


# --------------------------- Session State ---------------------- #
if "tasks" not in st.session_state:
    st.session_state.tasks, st.session_state.next_id = load_data()
if "theme" not in st.session_state:
    st.session_state.theme = DEFAULT_THEME.copy()


# ------------------------- Theming / CSS ------------------------ #

def inject_css(mode: str, primary: str, accent: str):
    dark = (mode == "Dark")
    bg = "#0B1220" if dark else "#ffffff"
    panel = "#0f172a" if dark else "#f8fafc"
    text = "#e5e7eb" if dark else "#111827"
    sub = "#9CA3AF" if dark else "#475569"

    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=JetBrains+Mono:wght@400;600&display=swap');
        html, body, [class*="css"]  {{
            font-family: 'Inter', system-ui, -apple-system, Segoe UI, Roboto, 'Helvetica Neue', Arial, 'Noto Sans', 'Apple Color Emoji', 'Segoe UI Emoji';
        }}
        .app-bg {{ background: linear-gradient(120deg, {bg}, {panel}); }}
        .headline {{ color:{text}; letter-spacing: -0.3px; }}
        .subtle {{ color:{sub}; }}
        .card {{ background:{panel}; border-radius:18px; padding:18px; border:1px solid rgba(255,255,255,0.06); box-shadow: 0 8px 24px rgba(0,0,0,0.25); }}
        .pill {{ display:inline-block; padding:4px 10px; border-radius:999px; font-size:12px; font-weight:600; color:white; }}
        .btn-prim {{ background:{primary}; color:white; padding:8px 14px; border-radius:10px; text-decoration:none; font-weight:700; }}
        .btn-ghost {{ background:transparent; border:1px solid {accent}33; color:{accent}; padding:8px 14px; border-radius:10px; font-weight:600; }}
        .task-title.done {{ text-decoration: line-through; opacity:0.6; }}
        .task-card {{ border:1px solid rgba(255,255,255,0.08); border-radius:16px; padding:12px; transition: all .15s ease-in-out; }}
        .task-card:hover {{ background: rgba(255,255,255,0.05); transform: scale(1.01); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }}
        .kbd {{ font-family:'JetBrains Mono', monospace; font-size:12px; padding:2px 6px; border-radius:6px; border:1px solid #64748b44; }}
        .accent {{ color:{accent}; }}
        </style>
        """,
        unsafe_allow_html=True,
    )


inject_css(st.session_state.theme["mode"], st.session_state.theme["primary"], st.session_state.theme["accent"])

# --------------------------- Helpers ---------------------------- #

def add_task(title: str, due: date | None, priority: int):
    title = (title or "").strip()
    if not title:
        st.warning("Empty title not allowed.")
        return
    for t in st.session_state.tasks:
        if t["title"].lower() == title.lower():
            st.warning("Task already exists.")
            return
    task = {
        "id": st.session_state.next_id,
        "title": title,
        "done": False,
        "due": due,
        "priority": int(priority),
        "created": datetime.now().isoformat(timespec="seconds"),
    }
    st.session_state.tasks.append(task)
    st.session_state.next_id += 1
    save_data(st.session_state.tasks, st.session_state.next_id)
    st.toast("Added ✅")


def mark_done(tid: int, value: bool = True):
    for t in st.session_state.tasks:
        if t["id"] == tid:
            t["done"] = bool(value)
            save_data(st.session_state.tasks, st.session_state.next_id)
            st.toast("Updated ✅")
            return


def delete_task(tid: int):
    st.session_state.tasks = [t for t in st.session_state.tasks if t["id"] != tid]
    save_data(st.session_state.tasks, st.session_state.next_id)
    st.toast("Deleted 🗑️")


def edit_title(tid: int, new_title: str):
    new_title = (new_title or "").strip()
    if not new_title:
        st.warning("Title cannot be empty.")
        return
    for t in st.session_state.tasks:
        if t["id"] == tid:
            t["title"] = new_title
            save_data(st.session_state.tasks, st.session_state.next_id)
            st.toast("Edited ✏️")
            return


def set_due(tid: int, due: date | None):
    for t in st.session_state.tasks:
        if t["id"] == tid:
            t["due"] = due
            save_data(st.session_state.tasks, st.session_state.next_id)
            st.toast("Due updated 🗓️")
            return


def clear_due(tid: int):
    set_due(tid, None)


def set_priority(tid: int, p: int):
    p = max(1, min(3, int(p)))
    for t in st.session_state.tasks:
        if t["id"] == tid:
            t["priority"] = p
            save_data(st.session_state.tasks, st.session_state.next_id)
            st.toast("Priority set ⬆️")
            return


def days_left(d: date | None):
    if not d:
        return None
    return (d - date.today()).days


def badge_for_due(d: date | None):
    if not d:
        return ""
    dl = days_left(d)
    if dl is None:
        return ""
    if dl < 0:
        return "🔴 OVERDUE"
    if dl == 0:
        return "🟡 TODAY"
    return f"🟢 in {dl}d"


# --------------------------- Sidebar ---------------------------- #
with st.sidebar:
    st.markdown("## 🎨 Theme")
    mode = st.radio("Appearance", ["Dark", "Light"], index=0 if st.session_state.theme["mode"]=="Dark" else 1)
    colA, colB = st.columns(2)
    with colA:
        prim = st.color_picker("Primary", st.session_state.theme["primary"])
    with colB:
        acc = st.color_picker("Accent", st.session_state.theme["accent"])

    changed = (mode != st.session_state.theme["mode"]) or (prim != st.session_state.theme["primary"]) or (acc != st.session_state.theme["accent"]) 
    if changed:
        st.session_state.theme.update({"mode": mode, "primary": prim, "accent": acc})
        inject_css(mode, prim, acc)
        st.toast("Theme updated ✨")

    st.markdown("---")
    st.markdown("## 🔍 Filters")
    status = st.radio("Status", ("All","Pending","Done"), index=0)
    search = st.text_input("Search title")
    sort_by = st.selectbox("Sort by", ["ID","Title","Due","Priority","Created"], index=0)

    st.markdown("---")
    st.markdown("## ⬇️ Export")
    exp_col1, exp_col2, exp_col3 = st.columns(3)
    with exp_col1:
        do_csv = st.button("CSV")
    with exp_col2:
        do_xlsx = st.button("Excel")
    with exp_col3:
        do_json = st.button("JSON")

# ----------------------------- Header --------------------------- #
if LOGO_PATH.exists():
    logo_col1, logo_col2 = st.columns([1,8])
    with logo_col1:
        st.image(str(LOGO_PATH), width=56)
    with logo_col2:
        st.markdown("""
        <div class="app-bg" style="padding: 8px 14px; border-radius: 20px;">
          <h1 class="headline">✅ KaamTamam</h1>
          <div class="subtle">Beautiful. Funny. Professional.</div>
        </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
    <div class="app-bg" style="padding: 8px 14px; border-radius: 20px;">
      <h1 class="headline">✅ KaamTamam</h1>
      <div class="subtle">Beautiful. Funny. Professional.</div>
    </div>
    """, unsafe_allow_html=True)

st.write("")

# ------------------------------ Input --------------------------- #
with st.container(border=True):
    st.markdown("### ✍️ Add a task")
    c1, c2, c3, c4, c5 = st.columns([5, 2, 1.5, 1.8, 2])
    with c1:
        title_in = st.text_input("Title", placeholder="What do you need to do?")
    with c2:
        due_default = date.today()
        due_checkbox = st.checkbox("No due date", value=True)
        due_in = None if due_checkbox else st.date_input("Due", value=due_default, format="YYYY-MM-DD")
    with c3:
        prio_in = st.selectbox("Priority", options=[1,2,3], index=1, format_func=lambda x: f"{x} · {PRIORITY_LABEL[x]}")
    with c4:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Add Task", use_container_width=True):
            add_task(title_in, due_in, prio_in)
            st.rerun()
    with c5:
        st.caption("Tip: Use sidebar → Theme to tweak colors ✨")

# ------------------------------ Ordering ------------------------ #
if HAS_SORTABLES:
    st.markdown("#### ↕️ Drag to reorder (affects display order)")
    # Apply same filtering/search as view list to drag only visible tasks
    drag_view = st.session_state.tasks[:]
    if status == "Pending":
        drag_view = [t for t in drag_view if not t["done"]]
    elif status == "Done":
        drag_view = [t for t in drag_view if t["done"]]
    if search:
        q = search.lower()
        drag_view = [t for t in drag_view if q in t["title"].lower()]

    ids = [str(t["id"]) for t in drag_view]
    new_order = sortables.sort_items(ids, direction="vertical", key="sortables")

    if new_order and new_order != ids:
        # Rebuild global order: keep non-visible tasks in their relative order, reorder visible block
        id_to_task = {str(t["id"]): t for t in st.session_state.tasks}
        # Extract blocks
        visible_ids_set = set(ids)
        visible_tasks = [id_to_task[i] for i in new_order if i in id_to_task]
        hidden_tasks = [t for t in st.session_state.tasks if str(t["id"]) not in visible_ids_set]
        # Merge: put reordered visible first, then hidden (keeps stable for hidden)
        st.session_state.tasks = visible_tasks + hidden_tasks
        save_data(st.session_state.tasks, st.session_state.next_id)
        st.rerun()
else:
    st.caption("Install drag & drop: `pip install streamlit-sortables` and restart app.")

# ------------------------------ List ---------------------------- #
# Filter + search + sort for rendering
view = st.session_state.tasks
if status == "Pending":
    view = [t for t in view if not t["done"]]
elif status == "Done":
    view = [t for t in view if t["done"]]

if search:
    q = search.lower()
    view = [t for t in view if q in t["title"].lower()]

if sort_by == "ID":
    view = sorted(view, key=lambda t: t["id"])
elif sort_by == "Title":
    view = sorted(view, key=lambda t: t["title"].lower())
elif sort_by == "Due":
    view = sorted(view, key=lambda t: (t["due"] is None, t["due"] or date.max))
elif sort_by == "Priority":
    view = sorted(view, key=lambda t: -t["priority"])  # High first
elif sort_by == "Created":
    view = sorted(view, key=lambda t: t.get("created",""))

st.markdown("#### 📋 Your Tasks")

if not view:
    st.info("No tasks match this view. Add one above ✨")
else:
    for t in view:
        with st.container(border=False):
            st.markdown("<div class='task-card'>", unsafe_allow_html=True)
            a,b,c,d,e,f,g = st.columns([6,1.5,1.8,2.4,2.8,2,1.6])
            with a:
                title_cls = "task-title done" if t["done"] else "task-title"
                st.markdown(f"<div class='{title_cls}'><span class='accent'>#{t['id']}</span> · {t['title']}</div>", unsafe_allow_html=True)
                chips = []
                chips.append(f"<span class='pill' style='background:{PRIORITY_COLORS[t['priority']]};'>{PRIORITY_LABEL[t['priority']]}</span>")
                if t["due"]:
                    chips.append(f"<span class='pill' style='background:#64748b;'>📅 {t['due'].isoformat()}</span>")
                    bd = badge_for_due(t["due"]) or ""
                    if bd:
                        chips.append(f"<span class='pill' style='background:#334155;'>{bd}</span>")
                st.markdown(" ".join(chips), unsafe_allow_html=True)
            with b:
                st.write("Done?")
                done_chk = st.checkbox(" ", value=t["done"], key=f"done-{t['id']}")
                if done_chk != t["done"]:
                    mark_done(t["id"], done_chk)
                    st.rerun()
            with c:
                st.write("Priority")
                pr_new = st.selectbox(" ", [1,2,3], index=t["priority"]-1, key=f"prio-{t['id']}", format_func=lambda x: PRIORITY_LABEL[x])
                if pr_new != t["priority"]:
                    set_priority(t["id"], pr_new)
                    st.rerun()
            with d:
                st.write("Due date")
                due_val = t["due"] or date.today()
                due_new = st.date_input(" ", value=due_val, key=f"due-{t['id']}", format="YYYY-MM-DD")
                if t["due"] != due_new:
                    set_due(t["id"], due_new)
                    st.rerun()
            with e:
                new_title = st.text_input("Edit title", value=t["title"], key=f"title-{t['id']}")
                if new_title != t["title"]:
                    edit_title(t["id"], new_title)
                    st.rerun()
            with f:
                if st.button("Clear due", key=f"clear-{t['id']}"):
                    clear_due(t["id"])
                    st.rerun()
            with g:
                if st.button("🗑️ Delete", key=f"del-{t['id']}"):
                    delete_task(t["id"])
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------- Footer Bar ------------------------ #

c1, c2, c3, c4 = st.columns(4)
with c1:
    if st.button("✅ Mark all done"):
        for t in st.session_state.tasks:
            t["done"] = True
        save_data(st.session_state.tasks, st.session_state.next_id)
        st.rerun()
with c2:
    if st.button("🧹 Clear completed"):
        st.session_state.tasks = [t for t in st.session_state.tasks if not t["done"]]
        save_data(st.session_state.tasks, st.session_state.next_id)
        st.rerun()
with c3:
    if st.button("🔔 Due today"):
        today = date.today()
        due_today = [f"#{t['id']} · {t['title']}" for t in st.session_state.tasks if t["due"] == today and not t["done"]]
        if due_today:
            st.success("\n".join(due_today))
        else:
            st.info("Nothing due today. 🎉")
with c4:
    if st.button("♻️ Reload from disk"):
        st.session_state.tasks, st.session_state.next_id = load_data()
        st.rerun()

# ----------------------------- Export --------------------------- #
if do_csv:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=["ID","Title","Done","Priority","Due","Created"])
    writer.writeheader()
    for t in st.session_state.tasks:
        writer.writerow({
            "ID": t["id"],
            "Title": t["title"],
            "Done": t["done"],
            "Priority": PRIORITY_LABEL[t["priority"]],
            "Due": t["due"].isoformat() if t["due"] else "",
            "Created": t.get("created",""),
        })
    st.download_button("Download CSV", data=buf.getvalue(), file_name="tasks.csv", mime="text/csv")

if do_xlsx:
    try:
        import pandas as pd
        df_rows = []
        for t in st.session_state.tasks:
            df_rows.append({
                "ID": t["id"],
                "Title": t["title"],
                "Done": t["done"],
                "Priority": PRIORITY_LABEL[t["priority"]],
                "Due": t["due"].isoformat() if t["due"] else "",
                "Created": t.get("created",""),
            })
        df = pd.DataFrame(df_rows)
        bio = io.BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Tasks")
        st.download_button(
            "Download Excel",
            data=bio.getvalue(),
            file_name="tasks.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    except Exception as e:
        st.error(f"Excel export failed. Try: pip install pandas openpyxl.\n{e}")

if do_json:
    st.download_button(
        "Download JSON",
        data=json.dumps({"tasks": st.session_state.tasks, "next_id": st.session_state.next_id}, default=str, ensure_ascii=False, indent=2),
        file_name="tasks.json",
        mime="application/json",
    )
