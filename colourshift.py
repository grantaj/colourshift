import streamlit as st

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

if feature == "Maximal Shift":
    st.sidebar.button("Solve")

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
st.write("ΔE, computed results, or image outputs will appear here based on feature.")
