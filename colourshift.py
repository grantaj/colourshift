import streamlit as st
import numpy as np
from skimage.color import rgb2lab, deltaE_ciede2000

# --- Sidebar ---
st.sidebar.title("Colourshift")
feature = st.sidebar.selectbox(
    "Tool",
    ["Maximal Shift", 
     "Compensation", 
     "Compare", 
     "Gradient", 
     "Reversibility", 
     "Export"]
)

base_color = st.sidebar.color_picker("Base Color", "#ff0000")
surround_color = st.sidebar.color_picker("Surround Color", "#ffffff")

bg_option = st.sidebar.selectbox("Background", ["Neutral Gray", "White", "Black"])
bg_color = {"Neutral Gray": "#808080", "White": "#ffffff", "Black": "#000000"}[bg_option]
text_color = {"Neutral Gray": "#e0e0e0", "White": "#808080", "Black": "#e0e0e0"}[bg_option]  # Lower contrast

diversity_metric = st.sidebar.selectbox("Diversity Metric", ["ΔE2000", "Hue Angle", "RGB Distance"])

# Adjust threshold label and range depending on metric
if diversity_metric == "Hue Angle":
    diversity_threshold = st.sidebar.slider("Minimum Hue Angle Difference (°)", 0.0, 180.0, 30.0, 1.0)
elif diversity_metric == "RGB Distance":
    diversity_threshold = st.sidebar.slider("Minimum RGB Distance (0–1 scale)", 0.0, 1.5, 0.2, 0.01)
else:
    diversity_threshold = st.sidebar.slider("Minimum ΔE2000 Difference", 0.0, 50.0, 5.0, 0.5)

solve = st.sidebar.button("Solve")
st.sidebar.button("Reset")

# --- Set background and text color to cover entire viewport and hide Streamlit header ---
st.markdown(
    f"""
    <style>
    html, body, .block-container, .main, .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        height: 100%;
        min-height: 100vh;
    }}

    header[data-testid="stHeader"] {{
        display: none;
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# --- Main UI ---
st.title("Color Appearance Simulator")

st.header(f"{feature}")
st.write("This tool simulates how color perception changes depending on the surrounding color context.")

col1, col2 = st.columns(2)
with col1:
    st.subheader("Base Color")
    st.markdown(
        f"<div style='width:150px; height:150px; background-color:{base_color}; border:0px solid #000;'></div>",
        unsafe_allow_html=True
    )

with col2:
    st.subheader("Surround Color")
    st.markdown(
        f"<div style='width:150px; height:150px; background-color:{surround_color}; border:0px solid #000;'></div>",
        unsafe_allow_html=True
    )

st.markdown("---")
st.subheader("Results")

if feature == "Maximal Shift" and solve:
    def hex_to_rgb(h):
        h = h.lstrip('#')
        return [int(h[i:i+2], 16)/255.0 for i in (0, 2, 4)]

    def rgb_to_hue(rgb):
        r, g, b = rgb
        max_c = max(rgb)
        min_c = min(rgb)
        if max_c == min_c:
            return 0.0
        if max_c == r:
            hue = (g - b) / (max_c - min_c) % 6
        elif max_c == g:
            hue = (b - r) / (max_c - min_c) + 2
        else:
            hue = (r - g) / (max_c - min_c) + 4
        return (hue * 60.0) % 360

    def hue_distance(h1, h2):
        return min(abs(h1 - h2), 360 - abs(h1 - h2))

    base_rgb = np.array(hex_to_rgb(base_color)).reshape(1, 1, 3)
    base_lab = rgb2lab(base_rgb)

    candidates = []
    for r in np.linspace(0, 1, 12):
        for g in np.linspace(0, 1, 12):
            for b in np.linspace(0, 1, 12):
                surround_rgb = np.array([[[r, g, b]]])
                surround_lab = rgb2lab(surround_rgb)
                delta = deltaE_ciede2000(base_lab, surround_lab)[0][0]
                candidates.append(((r, g, b), delta))

    candidates.sort(key=lambda x: -x[1])
    top_colours = []
    for rgb, delta in candidates:
        def is_diverse(new_rgb):
            if diversity_metric == "ΔE2000":
                lab = rgb2lab(np.array([[new_rgb]]))
                return all(deltaE_ciede2000(lab, rgb2lab(np.array([[c]])))[0][0] > diversity_threshold for c, _ in top_colours)
            elif diversity_metric == "Hue Angle":
                hue = rgb_to_hue(new_rgb)
                return all(hue_distance(rgb_to_hue(c), hue) > diversity_threshold for c, _ in top_colours)
            elif diversity_metric == "RGB Distance":
                return all(np.linalg.norm(np.array(new_rgb) - np.array(c)) > diversity_threshold for c, _ in top_colours)
            return True

        if is_diverse(rgb):
            top_colours.append((rgb, delta))
        if len(top_colours) == 3:
            break

    st.write("### Top 3 Surrounds Causing Maximal Shift")
    for i, (rgb, delta) in enumerate(top_colours):
        hex_code = '#{:02x}{:02x}{:02x}'.format(*(int(255*x) for x in rgb))
        st.markdown(f"**{i+1}. ΔE = {delta:.2f}** – {hex_code}")
        st.markdown(
            f"<div style='width:150px; height:50px; background-color:{hex_code}; border:1px solid #fff;'></div>",
            unsafe_allow_html=True
        )
else:
    st.write("ΔE, computed results, or image outputs will appear here based on feature.")
