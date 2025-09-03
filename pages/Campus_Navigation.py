if start not in G.nodes:
    st.error(f"⚠️ Start room {start} not found in campus graph!")
elif end not in G.nodes:
    st.error(f"⚠️ Destination room {end} not found in campus graph!")
else:
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")
        st.success(" ➝ ".join(path))

        # Show map here ...
    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")
