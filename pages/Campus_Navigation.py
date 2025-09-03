# navigation_app.py
import streamlit as st
import pandas as pd
import networkx as nx
import math

# ======================================================
# 1) Load Data
# ======================================================
ROOMS_CSV = "rooms.csv"
EDGES_CSV = "edges.csv"

rooms_df = pd.read_csv(ROOMS_CSV)
edges_df = pd.read_csv(EDGES_CSV)

# ======================================================
# 2) Build Graph
# ======================================================
G = nx.Graph()
for _, row in rooms_df.iterrows():
    node_attrs = {
        "name": row.get("name", ""),
        "building": row.get("building", ""),
        "floor": int(row.get("floor", 0)) if not pd.isna(row.get("floor", None)) else 0,
        "lat": float(row.get("lat", 0)),
        "lon": float(row.get("lon", 0)),
        "type": row.get("type", "room"),
    }
    G.add_node(str(row["room"]), **node_attrs)

for _, row in edges_df.iterrows():
    a = str(row["from"])
    b = str(row["to"])
    dist = float(row.get("distance", 1.0))
    etype = row.get("type", "walk")
    left_desc = row.get("left_desc", None) if "left_desc" in row.index else None
    right_desc = row.get("right_desc", None) if "right_desc" in row.index else None
    G.add_edge(a, b, weight=dist, type=etype, left_desc=left_desc, right_desc=right_desc)

# ======================================================
# 3) Helpers
# ======================================================
def get_room_label(room_id: str) -> str:
    row = rooms_df[rooms_df["room"] == room_id]
    if row.empty:
        return str(room_id)
    r = row.iloc[0]
    if "name" in row.index and pd.notna(r.get("name", None)) and str(r.get("name", "")).strip():
        return f"{room_id} ({r['name']})"
    return str(room_id)

def turn_direction(a_row, b_row, c_row) -> str:
    ax, ay = float(a_row["lon"]), float(a_row["lat"])
    bx, by = float(b_row["lon"]), float(b_row["lat"])
    cx, cy = float(c_row["lon"]), float(c_row["lat"])
    v1 = (bx - ax, by - ay)
    v2 = (cx - bx, cy - by)
    ang1 = math.atan2(v1[1], v1[0])
    ang2 = math.atan2(v2[1], v2[0])
    diff = math.degrees(ang2 - ang1)
    while diff > 180:
        diff -= 360
    while diff < -180:
        diff += 360
    if abs(diff) < 25:
        return "Go straight"
    elif diff > 0:
        return "Turn left"
    else:
        return "Turn right"

def shortest_indoor_path(start: str, end: str):
    start = str(start); end = str(end)
    if start not in G.nodes:
        return [], [f"Start node '{start}' not found."]
    if end not in G.nodes:
        return [], [f"End node '{end}' not found."]

    try:
        path_nodes = nx.shortest_path(G, source=start, target=end, weight="weight")
    except nx.NetworkXNoPath:
        return [], [f"No path between {start} and {end}."]
    except Exception as exc:
        return [], [f"Error: {exc}"]

    instructions = []
    for i in range(len(path_nodes) - 1):
        a = path_nodes[i]
        b = path_nodes[i + 1]
        edge = G.get_edge_data(a, b) or {}
        edge_type = edge.get("type", "walk")
        dist = int(edge.get("weight", 0))
        frm_label = get_room_label(a)
        to_label = get_room_label(b)

        if edge_type == "stairs":
            instructions.append(f"Take stairs from {frm_label} to {to_label}.")
        elif edge_type == "elevator":
            instructions.append(f"Take elevator from {frm_label} to {to_label}.")
        else:
            if i < len(path_nodes) - 2:
                a_row = rooms_df[rooms_df["room"] == a].iloc[0]
                b_row = rooms_df[rooms_df["room"] == b].iloc[0]
                c_row = rooms_df[rooms_df["room"] == path_nodes[i + 2]].iloc[0]
                turn = turn_direction(a_row, b_row, c_row)
                ctx = []
                if edge.get("right_desc"):
                    ctx.append(f"Right: {edge.get('right_desc')}")
                if edge.get("left_desc"):
                    ctx.append(f"Left: {edge.get('left_desc')}")
                ctx_text = (" | " + " | ".join(ctx)) if ctx else ""
                instructions.append(f"{turn} towards {to_label} ({dist} m).{ctx_text}")
            else:
                ctx = []
                if edge.get("right_desc"):
                    ctx.append(f"Right: {edge.get('right_desc')}")
                if edge.get("left_desc"):
                    ctx.append(f"Left: {edge.get('left_desc')}")
                ctx_text = (" | " + " | ".join(ctx)) if ctx else ""
                instructions.append(f"Walk from {frm_label} to {to_label} ({dist} m).{ctx_text}")
    return path_nodes, instructions

# ======================================================
# 4) Streamlit App
# ======================================================
st.set_page_config(page_title="Marwadi Indoor Navigation", layout="wide", page_icon="🗺️")
st.title("🏫 Marwadi University — Indoor Navigation")
st.markdown("Select start and destination rooms.")

rooms = rooms_df["room"].astype(str).tolist()
labels = {r: get_room_label(r) for r in rooms}

col1, col2 = st.columns(2)
with col1:
    start = st.selectbox("Start room", options=rooms, format_func=lambda x: labels[x])
with col2:
    end = st.selectbox("Destination room", options=rooms, index=min(1, len(rooms)-1), format_func=lambda x: labels[x])

if st.button("Compute route"):
    path, instrs = shortest_indoor_path(start, end)
    if not path:
        st.error(" ".join(instrs))
    else:
        st.success(f"Path: {' → '.join([get_room_label(p) for p in path])}")
        st.markdown("### 📝 Instructions")
        for i, s in enumerate(instrs, 1):
            st.write(f"{i}. {s}")

        # Simple XY map (planar coords)
        df_nodes = rooms_df.set_index("room").loc[path].copy()
        df_nodes["order"] = range(len(df_nodes))
        lons = df_nodes["lon"].tolist()
        lats = df_nodes["lat"].tolist()

        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(6, 6))
        ax.plot(lons, lats, linewidth=3)
        ax.scatter(lons, lats, s=60)
        for i, (x, y, node) in enumerate(zip(lons, lats, path)):
            ax.text(x, y, f"{i+1} {node}", fontsize=9, verticalalignment='bottom', horizontalalignment='right')
        ax.set_xlabel("lon (planar)")
        ax.set_ylabel("lat (planar)")
        ax.set_title("Indoor Route")
        ax.set_aspect('equal', adjustable='box')
        st.pyplot(fig)

st.markdown("---")
st.markdown("📁 Edit `rooms.csv` and `edges.csv` to expand the Marwadi campus.")
