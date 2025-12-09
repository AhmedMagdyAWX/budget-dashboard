# pages/13_Need_Request.py
# Single-page Need Request with a per-row Link Editor:
# - Top: Header fields
# - Grid of resource rows: Resource, Project, Qty, Unit, Notes, Links Summary, [Link...]
# - "Link..." opens an in-page editor to add multiple allocations to (BOQ, Item, Detail, WBS) with quantities.
# - Total of link quantities must not exceed the requested Qty.

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
                "notes": "",
            }
        ],
        # links: row_index -> list of dicts {boq_id, boq_item_id, boq_detail_id, wbs_id, qty}
        "links": {},
        # link editor ui state
        "link_editor_open": False,
        "link_row": 0,
        "item_picker_open": False,
        "detail_picker_open": False,
        # temp selections while adding a link
        "link_form": {
            "boq_id": None,
            "boq_item_id": None,
            "boq_detail_id": None,
            "wbs_id": None,
            "qty": 0.0,
            "item_filter": "",
        },
        "active_row": 0,
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

def links_total_for_row(row_idx):
    links = NR["links"].get(row_idx, [])
    return sum(float(x.get("qty", 0) or 0) for x in links)

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

# ------------------------ Grid of resource rows ------------------------
st.subheader("Request Items")

tb1, tb2, tb3, tb4, tb5 = st.columns([1.1,1.1,1.1,1.3,4])
if tb1.button("➕ Add row", use_container_width=True):
    NR["items"].append({
        "resource_id": None, "qty": 1.0, "unit": "pcs",
        "project_id": NR["header"]["project_id"], "notes": "",
    })
    _rerun()
if tb2.button("📄 Duplicate row", use_container_width=True, disabled=len(NR["items"])==0):
    i = NR["active_row"]; ensure_row_index(i)
    NR["items"].insert(i+1, NR["items"][i].copy())
    # duplicate without links; copy if you prefer:
    # NR["links"][i+1] = [l.copy() for l in NR["links"].get(i,[])]
    _rerun()
if tb3.button("🗑️ Delete row", use_container_width=True, disabled=len(NR["items"])==0):
    i = NR["active_row"]; ensure_row_index(i)
    NR["items"].pop(i)
    NR["links"].pop(i, None)
    NR["active_row"] = max(0, i-1)
    # Reindex links mapping since row indices shifted
    NR["links"] = { (idx - 1 if idx > i else idx): v for idx, v in NR["links"].items() if idx != i }
    _rerun()
with tb4:
    NR["active_row"] = st.number_input("Active row #", min_value=0, step=1,
                                       value=min(NR["active_row"], max(0, len(NR["items"])-1)),
                                       help="Used for actions on a specific line")

if not NR["items"]:
    st.info("No items yet. Click **Add row**.")
else:
    header_cols = st.columns([0.9, 0.7, 0.6, 0.45, 1.8, 0.6])
    for c, txt in zip(
        header_cols,
        ["Resource", "Project", "Qty", "Unit", "Notes / Links Summary", "Actions"],
    ):
        c.markdown(f"**{txt}**")

    for i, row in enumerate(NR["items"]):
        c1, c2, c3, c4, c5, c6 = st.columns([0.9, 0.7, 0.6, 0.45, 1.8, 0.6])

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
                # Clear links if project changes (they belong to a different BOQ/WBS universe)
                NR["links"].pop(i, None)

        # Qty
        with c3:
            row["qty"] = st.number_input(f"Qty_{i}", min_value=0.0, value=float(row["qty"]), step=1.0, label_visibility="collapsed")

        # Unit
        with c4:
            row["unit"] = st.text_input(f"Unit_{i}", value=row["unit"], label_visibility="collapsed")

        # Notes & links summary
        with c5:
            row["notes"] = st.text_input(f"Notes_{i}", value=row["notes"], label_visibility="collapsed")
            # Summary
            requested = float(row.get("qty") or 0)
            allocated = links_total_for_row(i)
            remaining = max(0.0, requested - allocated)
            st.caption(f"**Links:** {len(NR['links'].get(i, []))}  |  **Allocated:** {allocated:g}  |  **Remaining:** {remaining:g}")

        # Actions
        with c6:
            if st.button("Link…", key=f"link_{i}", use_container_width=True):
                NR["link_row"] = i
                NR["link_editor_open"] = True
                # reset temp form for fresh UX
                NR["link_form"] = {"boq_id": None, "boq_item_id": None, "boq_detail_id": None, "wbs_id": None, "qty": 0.0, "item_filter": ""}
                NR["item_picker_open"] = False
                NR["detail_picker_open"] = False
                _rerun()

st.divider()

# ------------------------ Link Editor (in-page "wizard") ------------------------
if NR["link_editor_open"]:
    i = NR["link_row"]; ensure_row_index(i)
    row = NR["items"][i]
    project_id = row["project_id"]
    boqs_df, items_df, details_df = boq_flat(project_id)
    lf = NR["link_form"]
    st.subheader(f"Link allocations for row #{i} — {RESOURCE_MAP.get(row['resource_id'], '—')}")

    req_qty = float(row.get("qty") or 0)
    used_qty = links_total_for_row(i)
    rem_qty = max(0.0, req_qty - used_qty)
    st.info(f"Requested: **{req_qty:g} {row['unit']}**  |  Already linked: **{used_qty:g}**  |  Remaining: **{rem_qty:g}**")

    # BOQ dropdown (required)
    colA, colB, colC = st.columns([0.6, 0.6, 0.4])
    with colA:
        boq_ids = [None] + (boqs_df["boq_id"].tolist() if not boqs_df.empty else [])
        def _boq_lbl(bid):
            if bid is None: return "— Select BOQ —"
            try:
                return f'{bid} — {boqs_df.set_index("boq_id").loc[bid,"boq_name"]}'
            except Exception:
                return bid
        curr_boq = lf.get("boq_id")
        idx_boq = boq_ids.index(curr_boq) if curr_boq in boq_ids else 0
        new_boq = st.selectbox("BOQ", boq_ids, index=idx_boq, format_func=_boq_lbl)
        if new_boq != curr_boq:
            lf["boq_id"] = new_boq
            lf["boq_item_id"] = None
            lf["boq_detail_id"] = None

    with colB:
        # WBS dropdown (optional)
        wopt = wbs_options(project_id)
        wkeys = [None] + list(wopt.keys())
        widx = wkeys.index(lf.get("wbs_id")) if lf.get("wbs_id") in wkeys else 0
        lf["wbs_id"] = st.selectbox("WBS (optional)", wkeys, index=widx, format_func=lambda wid: "—" if wid is None else wopt.get(wid, wid))

    with colC:
        # Quantity to allocate on this link
        default_qty = min(rem_qty, lf.get("qty") or 0.0) if rem_qty > 0 else 0.0
        lf["qty"] = st.number_input("Link Qty", min_value=0.0, value=default_qty, step=1.0, help="Quantity to allocate for this BOQ/WBS link")

    # BOQ Item picker
    st.markdown("**BOQ Item**")
    pick_cols = st.columns([0.5, 0.5])
    with pick_cols[0]:
        if st.button("Pick Item…", disabled=lf.get("boq_id") is None):
            NR["item_picker_open"] = True
            NR["detail_picker_open"] = False
            _rerun()
    with pick_cols[1]:
        st.text_input("Selected Item", value=lf.get("boq_item_id") or "", disabled=True)

    # BOQ Item Detail picker
    det_cols = st.columns([0.5, 0.5])
    with det_cols[0]:
        if st.button("Pick Detail…", disabled=not lf.get("boq_item_id")):
            NR["detail_picker_open"] = True
            NR["item_picker_open"] = False
            _rerun()
    with det_cols[1]:
        st.text_input("Selected Detail", value=lf.get("boq_detail_id") or "", disabled=True)

    st.divider()

    # Existing links table
    st.markdown("**Existing Links for this row**")
    existing = NR["links"].get(i, [])
    if not existing:
        st.caption("No links yet.")
    else:
        df_links = pd.DataFrame(existing)
        # prettify with names
        def _boq_name(bid):
            try:
                return f'{bid} — {boqs_df.set_index("boq_id").loc[bid,"boq_name"]}'
            except Exception:
                return bid
        df_links_show = df_links.copy()
        if "boq_id" in df_links_show:
            df_links_show["BOQ"] = df_links_show["boq_id"].apply(_boq_name)
        if "wbs_id" in df_links_show:
            m = wbs_options(project_id)
            df_links_show["WBS"] = df_links_show["wbs_id"].apply(lambda x: "" if x is None else m.get(x, x))
        df_links_show = df_links_show.rename(columns={
            "boq_item_id":"BOQ Item",
            "boq_detail_id":"Detail",
            "qty":"Qty",
        })[["BOQ","BOQ Item","Detail","WBS","Qty"]]
        st.dataframe(df_links_show, use_container_width=True, height=220)

    # Buttons row
    b1, b2, b3, b4 = st.columns([1,1,1,5])
    # Add link
    add_disabled = (
        not lf.get("boq_id")
        or not lf.get("boq_item_id")
        or (lf.get("qty") is None)
        or (float(lf.get("qty") or 0) <= 0)
        or (float(lf.get("qty") or 0) > rem_qty)
    )
    if b1.button("➕ Add Link", type="primary", disabled=add_disabled):
        NR["links"].setdefault(i, [])
        NR["links"][i].append({
            "boq_id": lf.get("boq_id"),
            "boq_item_id": lf.get("boq_item_id"),
            "boq_detail_id": lf.get("boq_detail_id"),
            "wbs_id": lf.get("wbs_id"),
            "qty": float(lf.get("qty") or 0),
        })
        # reset qty and detail only (keep BOQ + Item to speed up adding many)
        lf["qty"] = 0.0
        lf["boq_detail_id"] = None
        _rerun()

    # Remove last link (quick)
    if b2.button("🗑️ Remove Last", disabled=len(existing)==0):
        NR["links"][i].pop()
        if not NR["links"][i]:
            NR["links"].pop(i)
        _rerun()

    # Done
    if b3.button("✅ Done"):
        NR["link_editor_open"] = False
        NR["item_picker_open"] = False
        NR["detail_picker_open"] = False
        _rerun()

    # ---- Item Picker Drawer ----
    if NR["item_picker_open"]:
        with st.expander("📦 Pick BOQ Item", expanded=True):
            if not lf.get("boq_id"):
                st.warning("Select a BOQ first.")
            else:
                sub_items = items_df[items_df["boq_id"] == lf["boq_id"]].copy()
                q = st.text_input("Filter code/description", lf.get("item_filter",""), key="item_filter_txt", placeholder="Type to filter…")
                lf["item_filter"] = q or ""
                if lf["item_filter"]:
                    mask = sub_items["item_code"].str.contains(lf["item_filter"], case=False) | sub_items["item_desc"].str.contains(lf["item_filter"], case=False)
                    sub_items = sub_items[mask]
                st.dataframe(sub_items[["item_id","item_code","item_desc"]], use_container_width=True, height=260)
                opts = sub_items["item_id"].tolist()
                idx2 = 0 if lf.get("boq_item_id") not in opts else opts.index(lf["boq_item_id"])
                choice = st.selectbox("Choose BOQ Item", opts, index=idx2 if opts else 0, disabled=not bool(opts))
                cA, cB = st.columns([1,6])
                if cA.button("Use this Item", type="primary", disabled=not bool(opts)):
                    lf["boq_item_id"] = choice
                    lf["boq_detail_id"] = None
                    NR["item_picker_open"] = False
                    _rerun()
                if cB.button("Close"):
                    NR["item_picker_open"] = False
                    _rerun()

    # ---- Detail Picker Drawer ----
    if NR["detail_picker_open"]:
        with st.expander("🔎 Pick BOQ Item Detail", expanded=True):
            if not lf.get("boq_item_id"):
                st.warning("Select a BOQ Item first.")
            else:
                sub_det = details_df[details_df["item_id"] == lf["boq_item_id"]].copy()
                if sub_det.empty:
                    st.caption("No details for this item.")
                    det_choice = None
                else:
                    st.dataframe(sub_det[["detail_id","detail_desc"]], use_container_width=True, height=220)
                    det_ids = sub_det["detail_id"].tolist()
                    det_choice = st.selectbox("Choose Detail (optional)", [None] + det_ids,
                                              index=0 if lf.get("boq_detail_id") not in det_ids else det_ids.index(lf["boq_detail_id"])+1)
                cA, cB = st.columns([1,6])
                if cA.button("Use this Detail", type="primary"):
                    lf["boq_detail_id"] = det_choice
                    NR["detail_picker_open"] = False
                    _rerun()
                if cB.button("Close"):
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
    # hard validation: links sum must not exceed qty
    if links_total_for_row(idx) > float(row["qty"] or 0):
        errors.append(f"Row {idx}: Linked quantity exceeds requested quantity.")

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
            "notes": r["notes"],
            "links": NR["links"].get(i, []),
        }
        for i, r in enumerate(NR["items"])
    ],
}

if errors:
    st.error("Please fix the following before submitting:\n- " + "\n- ".join(errors))

col_submit, col_preview = st.columns([1,5])
with col_submit:
    submit_disabled = len(errors) > 0 or len(NR["items"]) == 0
    if st.button("✅ Submit Need Request", type="primary", disabled=submit_disabled, use_container_width=True):
        st.success("Need Request submitted (demo). Replace with your API call.")
with col_preview:
    st.json(payload, expanded=False)

st.caption("Each resource row can be linked to multiple BOQ/Item/Detail/WBS allocations with quantities; sum cannot exceed requested quantity.")
