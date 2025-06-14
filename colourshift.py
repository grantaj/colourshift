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

if feature == "Maximal Shift":
    st.sidebar.button("Solve")

st.sidebar.button("Reset")

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
