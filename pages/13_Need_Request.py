# pages/13_Need_Request.py
# Single-page Need Request:
# - Header fields at top
# - Separator
# - Grid for items with BOQ dropdown + Item/Detail pickers + WBS

import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Need Request", layout="wide")

# -------- version-safe rerun --------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()  # type: ignore[attr-defined]

# ------------------------ Demo master data ------------------------
USERS = ["Ahmed", "Lina", "Omar", "Sara", "Amr"]
PROJECTS = [
    {"id": "PRJ-001", "name": "Project Phoenix"},
    {"id": "PRJ-002", "name": "Project Atlas"},
]
RESOURCES = [
    {"id": "R-STEEL-10", "name": "Steel Rebar Ø10"},
    {"id": "R-STEEL-16", "name": "Steel Rebar Ø16"},
    {"id": "R-CEM-42",   "name": "Cement 42.5N"},
    {"id": "R-SAND",     "name": "Sand Medium"},
    {"id": "R-PLY-18",   "name": "Plywood 18mm"},
]
WBS = {
    "PRJ-001": [
        {"id":"1", "code":"1", "name":"Phase 1"},
        {"id":"1.1","code":"1.1","name":"Planning"},
        {"id":"1.2","code":"1.2","name":"Model Setup"},
        {"id":"2", "code":"2", "name":"Phase 2"},
        {"id":"2.1","code":"2.1","name":"Field Scanning"},
        {"id":"2.2","code":"2.2","name":"Modeling"},
    ],
    "PRJ-002": [
        {"id":"1","code":"1","name":"Kickoff & Setup"},
        {"id":"1.1","code":"1.1","name":"Mobilization"},
    ],
}
# BOQ structure per project: BOQ -> Items -> Details
BOQS = {
    "PRJ-001": [
        {
            "boq_id": "B-001",
            "boq_name": "Concrete Works",
            "items": [
                {"item_id": "B-001-10","item_code": "CW-010","item_desc": "Footings concrete C30 (incl. pumping)",
                 "details": [
                     {"detail_id":"B-001-10-a","detail_desc":"Concrete 30 MPa"},
                     {"detail_id":"B-001-10-b","detail_desc":"Formwork & ties"},
                     {"detail_id":"B-001-10-c","detail_desc":"Rebar Ø10, Ø16"},
                 ]},
                {"item_id": "B-001-20","item_code": "CW-020","item_desc": "Slab on grade C25",
                 "details": [
                     {"detail_id":"B-001-20-a","detail_desc":"Concrete 25 MPa"},
                     {"detail_id":"B-001-20-b","detail_desc":"Compaction & gravel"},
                 ]},
            ],
        },
        {
            "boq_id": "B-002",
            "boq_name": "Finishes",
            "items": [
                {"item_id":"B-002-10","item_code":"FN-010","item_desc":"Ceramic tiling 60×60",
                 "details": [
                     {"detail_id":"B-002-10-a","detail_desc":"Tiles supply"},
                     {"detail_id":"B-002-10-b","detail_desc":"Adhesive & spacers"},
                 ]},
            ],
        }
    ],
    "PRJ-002": [
        {
            "boq_id": "B-101",
            "boq_name": "Site Setup",
            "items": [
                {"item_id":"B-101-10","item_code":"SS-010","item_desc":"Temporary fencing",
                 "details": [
                     {"detail_id":"B-101-10-a","detail_desc":"Fencing panels"},
                     {"detail_id":"B-101-10-b","detail_desc":"Concrete blocks"},
                 ]},
            ],
        }
    ],
}

PROJECT_MAP = {p["id"]: p["name"] for p in PROJECTS}
RESOURCE_MAP = {r["id"]: r["name"] for r in RESOURCES}

# ------------------------ Session state ------------------------
if "nr" not in st.session_state:
    st.session_state.nr = {
        "header": {
            "title": "",
            "requester": USERS[0],
            "date": date.today(),
            "project_id": PROJECTS[0]["id"],  # default for new rows
            "notes": "",
        },
        "items": [
            {
                "resource_id": None,
                "qty": 1.0,
                "unit": "pcs",
                "project_id": PROJECTS[0]["id"],
                "wbs_id": None,
                "boq_id": None,
                "boq_item_id": None,
                "boq_detail_id": None,
                "notes": "",
            }
        ],
        "active_row": 0,
        "item_picker_open": False,    # drawer for BOQ Item
        "detail_picker_open": False,  # drawer for BOQ Detail
    }
NR = st.session_state.nr

# ------------------------ Helpers ------------------------
def wbs_options(project_id):
    rows = WBS.get(project_id, [])
    return {row["id"]: f'{row["code"]} — {row["name"]}' for row in rows}

def boq_flat(project_id):
    pack = BOQS.get(project_id, [])
    boqs, items, details = [], [], []
    for b in pack:
        boqs.append({"boq_id": b["boq_id"], "boq_name": b["boq_name"]})
        for it in b["items"]:
            items.append({
                "boq_id": b["boq_id"],
                "item_id": it["item_id"],
                "item_code": it["item_code"],
                "item_desc": it["item_desc"],
            })
            for d in it["details"]:
                details.append({
                    "item_id": it["item_id"],
                    "detail_id": d["detail_id"],
                    "detail_desc": d["detail_desc"],
                })
    return pd.DataFrame(boqs), pd.DataFrame(items), pd.DataFrame(details)

def ensure_row_index(idx):
    if idx < 0 or idx >= len(NR["items"]):
        st.stop()

# ------------------------ Header ------------------------
st.title("🧾 Need Request")

h = NR["header"]
col1, col2, col3 = st.columns([2,1.1,1.2])
with col1:
    h["title"] = st.text_input("Request title / description", h["title"], placeholder="e.g., Site concrete materials")
with col2:
    h["requester"] = st.selectbox("Requester", USERS, index=USERS.index(h["requester"]) if h["requester"] in USERS else 0)
with col3:
    h["date"] = st.date_input("Request date", h["date"])
colp, coln = st.columns([1.4,1])
with colp:
    h["project_id"] = st.selectbox("Default Project for new lines", [p["id"] for p in PROJECTS],
                                   index=[p["id"] for p in PROJECTS].index(h["project_id"]),
                                   format_func=lambda pid: PROJECT_MAP.get(pid, pid))
with coln:
    h["notes"] = st.text_input("Header notes (optional)", h["notes"])

st.divider()

# ------------------------ Items Grid ------------------------
st.subheader("Request Items")

# Toolbar
tb1, tb2, tb3, tb4, tb5 = st.columns([1.1,1.1,1.1,1.3,4])
if tb1.button("➕ Add row", use_container_width=True):
    NR["items"].append({
        "resource_id": None, "qty": 1.0, "unit": "pcs",
        "project_id": NR["header"]["project_id"], "wbs_id": None,
        "boq_id": None, "boq_item_id": None, "boq_detail_id": None,
        "notes": "",
    })
    _rerun()
if tb2.button("📄 Duplicate row", use_container_width=True, disabled=len(NR["items"])==0):
    i = NR["active_row"]; ensure_row_index(i)
    NR["items"].insert(i+1, NR["items"][i].copy())
    _rerun()
if tb3.button("🗑️ Delete row", use_container_width=True, disabled=len(NR["items"])==0):
    i = NR["active_row"]; ensure_row_index(i)
    NR["items"].pop(i); NR["active_row"] = max(0, i-1)
    _rerun()
with tb4:
    NR["active_row"] = st.number_input("Active row #", min_value=0, step=1,
                                       value=min(NR["active_row"], max(0, len(NR["items"])-1)),
                                       help="Used when clicking ‘Pick Item…’ / ‘Pick Detail…’")

# Header labels
if not NR["items"]:
    st.info("No items yet. Click **Add row**.")
else:
    header_cols = st.columns([0.65, 0.55, 0.55, 0.9, 0.95, 0.95, 0.7, 0.8, 0.7, 0.6])
    for c, txt in zip(
        header_cols,
        ["Resource", "Project", "WBS", "BOQ", "BOQ Item", "BOQ Item Detail", "Qty", "Unit", "Notes", "Actions"],
    ):
        c.markdown(f"**{txt}**")

    for i, row in enumerate(NR["items"]):
        c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([0.65, 0.55, 0.55, 0.9, 0.95, 0.95, 0.7, 0.8, 0.7, 0.6])

        # Resource
        with c1:
            res_options = [None] + [r["id"] for r in RESOURCES]
            res_index = res_options.index(row.get("resource_id")) if row.get("resource_id") in res_options else 0
            row["resource_id"] = st.selectbox(
                f"Resource_{i}", res_options, index=res_index,
                format_func=lambda rid: "— Select —" if rid is None else RESOURCE_MAP[rid],
                label_visibility="collapsed",
            )

        # Project (per row)
        with c2:
            prev_proj = row["project_id"]
            row["project_id"] = st.selectbox(
                f"Proj_{i}", [p["id"] for p in PROJECTS],
                index=[p["id"] for p in PROJECTS].index(row["project_id"]) if row["project_id"] else 0,
                format_func=lambda pid: PROJECT_MAP.get(pid, pid),
                label_visibility="collapsed",
            )
            if row["project_id"] != prev_proj:
                row["wbs_id"] = None
                row["boq_id"] = None
                row["boq_item_id"] = None
                row["boq_detail_id"] = None

        # WBS
        with c3:
            wopt = wbs_options(row["project_id"])
            keys = [None] + list(wopt.keys())
            row["wbs_id"] = st.selectbox(
                f"WBS_{i}", keys,
                index=keys.index(row["wbs_id"]) if row["wbs_id"] in keys else 0,
                format_func=lambda wid: "— (optional) —" if wid is None else wopt.get(wid, wid),
                label_visibility="collapsed",
            )

        # BOQ (dropdown)
        with c4:
            boqs_df, items_df, details_df = boq_flat(row["project_id"])
            boq_ids = [None] + (boqs_df["boq_id"].tolist() if not boqs_df.empty else [])
            def _boq_lbl(bid):
                if bid is None: return "— Select —"
                try:
                    return f'{bid} — {boqs_df.set_index("boq_id").loc[bid,"boq_name"]}'
                except Exception:
                    return bid
            curr_boq = row.get("boq_id")
            idx_boq = boq_ids.index(curr_boq) if curr_boq in boq_ids else 0
            new_boq = st.selectbox(f"BOQ_{i}", boq_ids, index=idx_boq, format_func=_boq_lbl, label_visibility="collapsed")
            if new_boq != curr_boq:
                row["boq_id"] = new_boq
                row["boq_item_id"] = None
                row["boq_detail_id"] = None

        # BOQ Item (display + picker)
        with c5:
            st.text_input(f"BOQItem_{i}", value=row["boq_item_id"] or "", placeholder="(none)", label_visibility="collapsed", disabled=True)
            pick_item = st.button("Pick Item…", key=f"pick_item_{i}", use_container_width=True)
            if pick_item:
                NR["active_row"] = i
                NR["item_picker_open"] = True
                NR["detail_picker_open"] = False
                _rerun()

        # BOQ Item Detail (display + picker)
        with c6:
            st.text_input(f"BOQDet_{i}", value=row["boq_detail_id"] or "", placeholder="(none)", label_visibility="collapsed", disabled=True)
            pick_det = st.button("Pick Detail…", key=f"pick_det_{i}", use_container_width=True)
            if pick_det:
                NR["active_row"] = i
                NR["detail_picker_open"] = True
                NR["item_picker_open"] = False
                _rerun()

        # Qty, Unit, Notes
        with c7:
            row["qty"] = st.number_input(f"Qty_{i}", min_value=0.0, value=float(row["qty"]), step=1.0, label_visibility="collapsed")
        with c8:
            row["unit"] = st.text_input(f"Unit_{i}", value=row["unit"], label_visibility="collapsed")
        with c9:
            row["notes"] = st.text_input(f"Notes_{i}", value=row["notes"], label_visibility="collapsed")

        # Actions
        with c10:
            if st.button("Set Active", key=f"active_{i}", use_container_width=True):
                NR["active_row"] = i
                _rerun()

st.divider()

# ------------------------ BOQ ITEM Picker (drawer) ------------------------
if NR["item_picker_open"] and len(NR["items"]) > 0:
    i = NR["active_row"]; ensure_row_index(i)
    active = NR["items"][i]
    project_id = active["project_id"] or NR["header"]["project_id"]
    boqs_df, items_df, details_df = boq_flat(project_id)

    with st.expander(f"📦 Pick BOQ Item — Project: {PROJECT_MAP.get(project_id, project_id)}", expanded=True):
        if active.get("boq_id") is None:
            st.warning("Select a BOQ first.")
            if st.button("Close"):
                NR["item_picker_open"] = False
                _rerun()
        else:
            subset_items = items_df[items_df["boq_id"] == active["boq_id"]].copy()
            st.markdown("**Search items**")
            q = st.text_input("Filter by code/description", "", label_visibility="collapsed", placeholder="Type to filter…")
            if q:
                mask = subset_items["item_code"].str.contains(q, case=False) | subset_items["item_desc"].str.contains(q, case=False)
                subset_items = subset_items[mask]

            st.dataframe(subset_items[["item_id", "item_code", "item_desc"]], use_container_width=True, height=220)
            item_ids = subset_items["item_id"].tolist()
            if not item_ids:
                st.info("No items under this BOQ (after filtering).")
                item_choice = None
            else:
                idx2 = 0 if active.get("boq_item_id") not in item_ids else item_ids.index(active["boq_item_id"])
                item_choice = st.selectbox("Choose BOQ Item", item_ids, index=idx2)

            c1, c2, c3 = st.columns([1,1,4])
            if c1.button("Use selection", type="primary", disabled=item_choice is None):
                active["boq_item_id"] = item_choice
                active["boq_detail_id"] = None
                NR["item_picker_open"] = False
                _rerun()
            if c2.button("Clear"):
                active["boq_item_id"] = None
                active["boq_detail_id"] = None
                NR["item_picker_open"] = False
                _rerun()
            if c3.button("Close"):
                NR["item_picker_open"] = False
                _rerun()

# ------------------------ BOQ ITEM DETAIL Picker (drawer) ------------------------
if NR["detail_picker_open"] and len(NR["items"]) > 0:
    i = NR["active_row"]; ensure_row_index(i)
    active = NR["items"][i]
    project_id = active["project_id"] or NR["header"]["project_id"]
    boqs_df, items_df, details_df = boq_flat(project_id)

    with st.expander(f"🔎 Pick BOQ Item Detail — Project: {PROJECT_MAP.get(project_id, project_id)}", expanded=True):
        if not active.get("boq_item_id"):
            st.warning("Select a BOQ Item first.")
            if st.button("Close"):
                NR["detail_picker_open"] = False
                _rerun()
        else:
            sub_det = details_df[details_df["item_id"] == active["boq_item_id"]].copy()
            if sub_det.empty:
                st.info("This item has no details.")
                det_choice = None
            else:
                st.dataframe(sub_det[["detail_id", "detail_desc"]], use_container_width=True, height=200)
                det_ids = sub_det["detail_id"].tolist()
                det_choice = st.selectbox(
                    "Choose Detail (optional)",
                    [None] + det_ids,
                    index=0 if not active.get("boq_detail_id") or active["boq_detail_id"] not in det_ids
                          else det_ids.index(active["boq_detail_id"]) + 1
                )

            c1, c2, c3 = st.columns([1,1,4])
            if c1.button("Use selection", type="primary"):
                active["boq_detail_id"] = det_choice
                NR["detail_picker_open"] = False
                _rerun()
            if c2.button("Clear"):
                active["boq_detail_id"] = None
                NR["detail_picker_open"] = False
                _rerun()
            if c3.button("Close"):
                NR["detail_picker_open"] = False
                _rerun()

# ------------------------ Submit & Preview ------------------------
st.subheader("Submit")
errors = []
for idx, row in enumerate(NR["items"]):
    if not row["resource_id"]:
        errors.append(f"Row {idx}: Resource is required.")
    if row["qty"] is None or float(row["qty"]) <= 0:
        errors.append(f"Row {idx}: Quantity must be > 0.")
    if not row["project_id"]:
        errors.append(f"Row {idx}: Project is required.")

if errors:
    st.error("Please fix the following before submitting:\n- " + "\n- ".join(errors))

payload = {
    "header": {
        "title": NR["header"]["title"],
        "requester": NR["header"]["requester"],
        "date": str(NR["header"]["date"]),
        "project_id": NR["header"]["project_id"],
        "notes": NR["header"]["notes"],
    },
    "items": [
        {
            "resource_id": r["resource_id"],
            "qty": float(r["qty"]),
            "unit": r["unit"],
            "project_id": r["project_id"],
            "wbs_id": r["wbs_id"],
            "boq_id": r["boq_id"],
            "boq_item_id": r["boq_item_id"],
            "boq_detail_id": r["boq_detail_id"],
            "notes": r["notes"],
        }
        for r in NR["items"]
    ],
}

col_submit, col_preview = st.columns([1,5])
with col_submit:
    submit_disabled = len(errors) > 0 or len(NR["items"]) == 0
    if st.button("✅ Submit Need Request", type="primary", disabled=submit_disabled, use_container_width=True):
        st.success("Need Request submitted (demo). Replace this with your API call.")
with col_preview:
    st.json(payload, expanded=False)

st.caption("Single page: header at top, then items grid. BOQ is dropdown; Item/Detail use drawers. All lists filter by the row’s Project.")
