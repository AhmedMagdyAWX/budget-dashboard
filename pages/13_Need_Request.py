# pages/13_Need_Request.py
# Need Request wizard (Header -> Items) with BOQ picker dialog (boq -> item -> detail)

import streamlit as st
import pandas as pd
from datetime import date

st.set_page_config(page_title="Need Request", layout="wide")

# -------- version-safe rerun --------
def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        # older Streamlit
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
BOQS = {
    "PRJ-001": [
        {
            "boq_id": "B-001",
            "boq_name": "Concrete Works",
            "items": [
                {
                    "item_id": "B-001-10",
                    "item_code": "CW-010",
                    "item_desc": "Footings concrete C30 (incl. pumping)",
                    "details": [
                        {"detail_id":"B-001-10-a","detail_desc":"Concrete 30 MPa"},
                        {"detail_id":"B-001-10-b","detail_desc":"Formwork & ties"},
                        {"detail_id":"B-001-10-c","detail_desc":"Rebar Ø10, Ø16"},
                    ],
                },
                {
                    "item_id": "B-001-20",
                    "item_code": "CW-020",
                    "item_desc": "Slab on grade C25",
                    "details": [
                        {"detail_id":"B-001-20-a","detail_desc":"Concrete 25 MPa"},
                        {"detail_id":"B-001-20-b","detail_desc":"Compaction & gravel"},
                    ],
                },
            ],
        },
        {
            "boq_id": "B-002",
            "boq_name": "Finishes",
            "items": [
                {
                    "item_id": "B-002-10",
                    "item_code": "FN-010",
                    "item_desc": "Ceramic tiling 60×60",
                    "details": [
                        {"detail_id":"B-002-10-a","detail_desc":"Tiles supply"},
                        {"detail_id":"B-002-10-b","detail_desc":"Adhesive & spacers"},
                    ],
                }
            ],
        }
    ],
    "PRJ-002": [
        {
            "boq_id": "B-101",
            "boq_name": "Site Setup",
            "items": [
                {
                    "item_id": "B-101-10",
                    "item_code": "SS-010",
                    "item_desc": "Temporary fencing",
                    "details": [
                        {"detail_id":"B-101-10-a","detail_desc":"Fencing panels"},
                        {"detail_id":"B-101-10-b","detail_desc":"Concrete blocks"},
                    ],
                }
            ],
        }
    ],
}

PROJECT_MAP = {p["id"]: p["name"] for p in PROJECTS}
RESOURCE_MAP = {r["id"]: r["name"] for r in RESOURCES}

# ------------------------ Session state ------------------------
if "nr" not in st.session_state:
    st.session_state.nr = {
        "step": 1,
        "header": {
            "title": "",
            "requester": USERS[0],
            "date": date.today(),
            "project_id": PROJECTS[0]["id"],
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
        "boq_picker_open": False,
    }

NR = st.session_state.nr

# ------------------------ Helpers ------------------------
def wbs_options(project_id):
    rows = WBS.get(project_id, [])
    return {row["id"]: f'{row["code"]} — {row["name"]}' for row in rows}

def boq_flat(project_id):
    boqs, items, details = [], [], []
    for b in BOQS.get(project_id, []):
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

# ------------------------ Header Step ------------------------
st.title("🧾 Need Request")
tabs = st.tabs(["1) Header", "2) Items"])

with tabs[0]:
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
        h["project_id"] = st.selectbox("Project", [p["id"] for p in PROJECTS],
                                       index=[p["id"] for p in PROJECTS].index(h["project_id"]),
                                       format_func=lambda pid: PROJECT_MAP.get(pid, pid))
    with coln:
        h["notes"] = st.text_input("Header notes (optional)", h["notes"])

    st.divider()
    c1, c2 = st.columns([1,5])
    with c1:
        if st.button("➡️ Next (Items)", type="primary", use_container_width=True):
            NR["step"] = 2
            _rerun()
    with c2:
        st.caption("Tip: Project here becomes the default project for new item rows.")

# ------------------------ Items Step ------------------------
with tabs[1]:
    st.markdown("#### Items")
    st.caption("Each row is a requested resource. Use **Pick BOQ…** to choose BOQ → Item → Detail via a popup.")

    # Toolbar
    tb1, tb2, tb3, tb4, tb5 = st.columns([1.1,1.1,1.1,1.4,4])
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
                                           help="Row used when you click ‘Pick BOQ…’")

    # Grid-like editor
    if not NR["items"]:
        st.info("No items yet. Click **Add row**.")
    else:
        header_cols = st.columns([0.6, 0.5, 0.35, 0.9, 0.9, 0.7, 0.9, 0.7, 0.6, 0.3])
        for c, txt in zip(header_cols, ["Resource", "Project", "WBS", "BOQ", "BOQ Item", "Detail", "Qty", "Unit", "Notes", "BOQ Picker"]):
            c.markdown(f"**{txt}**")

        for i, row in enumerate(NR["items"]):
            c1, c2, c3, c4, c5, c6, c7, c8, c9, c10 = st.columns([0.6, 0.5, 0.35, 0.9, 0.9, 0.7, 0.9, 0.7, 0.6, 0.3])
            with c1:
                # build options list first, then find a safe index
                res_options = [None] + [r["id"] for r in RESOURCES]
                res_index = res_options.index(row.get("resource_id")) if row.get("resource_id") in res_options else 0
                row["resource_id"] = st.selectbox(
                    f"Resource_{i}",
                    res_options,
                    index=res_index,
                    format_func=lambda rid: "— Select —" if rid is None else RESOURCE_MAP[rid],
                    label_visibility="collapsed",
                )

            with c2:
                row["project_id"] = st.selectbox(
                    f"Proj_{i}", [p["id"] for p in PROJECTS],
                    index=[p["id"] for p in PROJECTS].index(row["project_id"]) if row["project_id"] else 0,
                    format_func=lambda pid: PROJECT_MAP.get(pid, pid),
                    label_visibility="collapsed",
                )
            with c3:
                wopt = wbs_options(row["project_id"])
                keys = [None] + list(wopt.keys())
                row["wbs_id"] = st.selectbox(
                    f"WBS_{i}", keys,
                    index=keys.index(row["wbs_id"]) if row["wbs_id"] in keys else 0,
                    format_func=lambda wid: "— (optional) —" if wid is None else wopt.get(wid, wid),
                    label_visibility="collapsed",
                )
            with c4:
                st.text_input(f"BOQ_{i}", value=row["boq_id"] or "", placeholder="(none)", label_visibility="collapsed", disabled=True)
            with c5:
                st.text_input(f"BOQItem_{i}", value=row["boq_item_id"] or "", placeholder="(none)", label_visibility="collapsed", disabled=True)
            with c6:
                st.text_input(f"BOQDet_{i}", value=row["boq_detail_id"] or "", placeholder="(none)", label_visibility="collapsed", disabled=True)
            with c7:
                row["qty"] = st.number_input(f"Qty_{i}", min_value=0.0, value=float(row["qty"]), step=1.0, label_visibility="collapsed")
            with c8:
                row["unit"] = st.text_input(f"Unit_{i}", value=row["unit"], label_visibility="collapsed")
            with c9:
                row["notes"] = st.text_input(f"Notes_{i}", value=row["notes"], label_visibility="collapsed")
            with c10:
                if st.button("Pick…", key=f"pick_{i}", use_container_width=True):
                    NR["active_row"] = i
                    NR["boq_picker_open"] = True
                    _rerun()

    st.divider()

    # ------------------------ BOQ Picker Popup ------------------------
    if NR["boq_picker_open"] and len(NR["items"]) > 0:
        i = NR["active_row"]; ensure_row_index(i)
        active = NR["items"][i]
        project_id = active["project_id"] or NR["header"]["project_id"]
        boqs_df, items_df, details_df = boq_flat(project_id)

        with st.dialog("Select BOQ → Item → Detail", width="large"):
            st.caption(f"Project: **{PROJECT_MAP.get(project_id, project_id)}**")
            if boqs_df.empty:
                st.warning("No BOQs for this project.")
                if st.button("Close"):
                    NR["boq_picker_open"] = False
                    _rerun()
            else:
                colA, colB = st.columns([0.5, 0.5])
                with colA:
                    st.markdown("**BOQs**")
                    ids = boqs_df["boq_id"].tolist()
                    idx = 0 if active.get("boq_id") not in ids else ids.index(active["boq_id"])
                    b_choice = st.radio("BOQ", ids, index=idx,
                        format_func=lambda bid: f'{bid} — {boqs_df.set_index("boq_id").loc[bid,"boq_name"]}',
                        label_visibility="collapsed",
                    )
                    subset_items = items_df[items_df["boq_id"] == b_choice].copy()

                with colB:
                    st.markdown("**Search items**")
                    q = st.text_input("Filter", "", label_visibility="collapsed", placeholder="Type to filter…")
                    if q:
                        mask = subset_items["item_code"].str.contains(q, case=False) | subset_items["item_desc"].str.contains(q, case=False)
                        subset_items = subset_items[mask]

                st.markdown("**BOQ Items**")
                st.dataframe(subset_items[["item_id", "item_code", "item_desc"]], use_container_width=True, height=180)
                item_ids = subset_items["item_id"].tolist()
                idx2 = 0 if active.get("boq_item_id") not in item_ids else item_ids.index(active["boq_item_id"])
                item_choice = st.selectbox("Choose BOQ Item", item_ids, index=idx2)

                st.markdown("**Item Details**")
                sub_det = details_df[details_df["item_id"] == item_choice].copy()
                st.dataframe(sub_det[["detail_id", "detail_desc"]], use_container_width=True, height=140)
                det_ids = sub_det["detail_id"].tolist()
                det_choice = st.selectbox("Choose Detail (optional)", [None] + det_ids,
                                          index=0 if active.get("boq_detail_id") not in det_ids else det_ids.index(active["boq_detail_id"])+1)

                c1, c2, c3 = st.columns([1,1,4])
                if c1.button("Use selection", type="primary"):
                    active["boq_id"] = b_choice
                    active["boq_item_id"] = item_choice
                    active["boq_detail_id"] = det_choice
                    NR["boq_picker_open"] = False
                    _rerun()
                if c2.button("Clear"):
                    active["boq_id"] = None
                    active["boq_item_id"] = None
                    active["boq_detail_id"] = None
                    NR["boq_picker_open"] = False
                    _rerun()
                if c3.button("Close"):
                    NR["boq_picker_open"] = False
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
            st.success("Need Request submitted (demo). Replace with your API call.")
    with col_preview:
        st.json(payload, expanded=False)

st.caption("Demo only. Replace lookups with your APIs. The BOQ dialog filters by the selected Project per row.")
