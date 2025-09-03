if start not in G.nodes:
    st.error(f"⚠️ Start room {start} not found in campus graph!")
elif end not in G.nodes:
    st.error(f"⚠️ Destination room {end} not found in campus graph!")
else:
    try:
        path = nx.shortest_path(G, source=start, target=end, weight="distance")
        st.success(" ➝ ".join(path))

        # Map visualization
        route_coords = [coords.get(node, [22.303, 70.783]) for node in path]
        m = folium.Map(location=route_coords[0], zoom_start=18)

        folium.PolyLine(route_coords, color="blue", weight=5).add_to(m)
        folium.Marker(route_coords[0], popup="Start", icon=folium.Icon(color="green")).add_to(m)
        folium.Marker(route_coords[-1], popup="End", icon=folium.Icon(color="red")).add_to(m)

        st_folium(m, width=700, height=500)

        st.subheader("📝 Step-by-step Directions")
        for i in range(len(path)-1):
            st.write(f"➡️ Walk from **{path[i]}** to **{path[i+1]}**")

    except nx.NetworkXNoPath:
        st.error("⚠️ No path found between selected rooms.")
