import streamlit as st
import json
import os
import glob

st.set_page_config(
    page_title="Browse Scraped Reviews",
    layout="wide",
)

st.title("Browse Scraped Reviews")

for _ in range(2):
    st.sidebar.write("")

st.sidebar.markdown("""
**by Ngoc My Nguyen**  
Master's Program Data Science – FH Kiel  
Capstone Project – Social Media Analytics
""")

data_folder = "data"
json_files = sorted(glob.glob(os.path.join(data_folder, "*.json")))

if not json_files:
    st.error("No JSON files found in data/")
else:
    file_names = [os.path.basename(f) for f in json_files]
    selected_file = st.selectbox("Select reviews file", file_names)
    data_path = os.path.join(data_folder, selected_file)

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    reviews = []
    for url, review_list in data.items():
        reviews.extend(review_list)

    employee_types = sorted({r.get("employee_type") for r in reviews if r.get("employee_type")})
    selected_type = st.selectbox("Filter by Employee Type", ["All"] + employee_types)

    review_number = st.number_input(
    "Search for Review ID (number, e.g. 23 for bosch-gruppe_23, 0 for all)",
    min_value=0,
    step=1,
    value=0
)

    filtered = [r for r in reviews if (selected_type == "All" or r.get("employee_type") == selected_type)]

    if review_number > 0:
        review_id_str = f"bosch-gruppe_{review_number}"
        filtered = [r for r in filtered if r.get("review_id") == review_id_str]

    st.write(f"Showing {len(filtered)} reviews.")

    for r in filtered:
        st.markdown(f"**{r.get('title', 'No Title')}**")
        st.caption(
            f"Score: {r.get('overall_score', 'N/A')} | "
            f"Type: {r.get('employee_type', '')} | "
            f"Date: {r.get('year', '')}-{str(r.get('month', '')).zfill(2)} | "
            f"Review ID: {r.get('review_id', '')}"
        )
        subcats = r.get("subcategories", [])
        for subcat in subcats:
            for cat, text in subcat.items():
                st.markdown(f"- *{cat}*: {text}")
        st.markdown("---")
