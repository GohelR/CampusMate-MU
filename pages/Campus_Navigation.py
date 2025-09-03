# navigation.py
import pandas as pd
import networkx as nx
import math
from typing import List, Tuple

# -------------------------
# Load data (paths relative to working dir)
# -------------------------
ROOMS_CSV = "rooms.csv"
EDGES_CSV = "edges.csv"

rooms_df = pd.read_csv(ROOMS_CSV)
edges_df = pd.read_csv(EDGES_CSV)

# Build graph
G = nx.Graph()
for _, row in rooms_df.iterrows():
    # store lat/lon/floor/name/type/building in node attrs
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
    # distance fallback
    dist = float(row.get("distance", 1.0))
    etype = row.get("type", "walk")
    # optional left/right descriptors
    left_desc = row.get("left_desc", None) if "left_desc" in row.index else None
    right_desc = row.get("right_desc", None) if "right_desc" in row.index else None
    G.add_edge(a, b, weight=dist, type=etype, left_desc=left_desc, right_desc=right_desc)

# -------------------------
# Helpers
# -------------------------
def get_room_label(room_id: str) -> str:
    row = rooms_df[rooms_df["room"] == room_id]
    if row.empty:
        return str(room_id)
    r = row.iloc[0]
    if "name" in row.index and pd.notna(r.get("name", None)) and str(r.get("name", "")).strip():
        return f"{room_id} ({r['name']})"
    return str(room_id)

def turn_direction(a_row, b_row, c_row) -> str:
    """Return 'Go straight' / 'Turn left' / 'Turn right' using bearing change."""
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

def shortest_indoor_path(start: str, end: str) -> Tuple[List[str], List[str]]:
    """
    Compute shortest path (by distance weight) between start and end nodes inside graph G.
    Returns (path_node_list, human_readable_instructions_list).
    """
    start = str(start); end = str(end)
    if start not in G.nodes:
        raise ValueError(f"Start node '{start}' not found in graph.")
    if end not in G.nodes:
        raise ValueError(f"End node '{end}' not found in graph.")

    # Try to compute shortest path
    try:
        path_nodes = nx.shortest_path(G, source=start, target=end, weight="weight")
    except nx.NetworkXNoPath:
        return [], [f"No path found between {start} and {end}."]
    except Exception as exc:
        return [], [f"Path finding error: {exc}"]

    instructions = []
    # Build instructions step-by-step
    for i in range(len(path_nodes) - 1):
        a = path_nodes[i]
        b = path_nodes[i + 1]
        edge = G.get_edge_data(a, b) or {}
        edge_type = edge.get("type", "walk")
        dist = int(edge.get("weight", 0))
        frm_label = get_room_label(a)
        to_label = get_room_label(b)

        # If stairs/elevator, special instructions
        if edge_type == "stairs":
            instructions.append(f"Take stairs from {frm_label} to {to_label}.")
        elif edge_type == "elevator":
            instructions.append(f"Take elevator from {frm_label} to {to_label}.")
        else:
            # compute turn if next point exists
            if i < len(path_nodes) - 2:
                a_row = rooms_df[rooms_df["room"] == a].iloc[0]
                b_row = rooms_df[rooms_df["room"] == b].iloc[0]
                c_row = rooms_df[rooms_df["room"] == path_nodes[i + 2]].iloc[0]
                turn = turn_direction(a_row, b_row, c_row)
                # include left/right context if present
                ctx = []
                if edge.get("right_desc"):
                    ctx.append(f"Right: {edge.get('right_desc')}")
                if edge.get("left_desc"):
                    ctx.append(f"Left: {edge.get('left_desc')}")
                ctx_text = (" | " + " | ".join(ctx)) if ctx else ""
                instructions.append(f"{turn} towards {to_label} ({dist} m).{ctx_text}")
            else:
                # final segment
                ctx = []
                if edge.get("right_desc"):
                    ctx.append(f"Right: {edge.get('right_desc')}")
                if edge.get("left_desc"):
                    ctx.append(f"Left: {edge.get('left_desc')}")
                ctx_text = (" | " + " | ".join(ctx)) if ctx else ""
                instructions.append(f"Walk from {frm_label} to {to_label} ({dist} m).{ctx_text}")

    return path_nodes, instructions

# -------------------------
# CLI demo (when run directly)
# -------------------------
if __name__ == "__main__":
    # Basic demo for quick test
    demo_start = "MB101"
    demo_end = "LIB202"
    try:
        path, steps = shortest_indoor_path(demo_start, demo_end)
        if not path:
            print("\n".join(steps))
        else:
            print("Path:", " → ".join(path))
            print("\nInstructions:")
            for idx, s in enumerate(steps, 1):
                print(f"{idx}. {s}")
    except Exception as e:
        print("Error:", e)
