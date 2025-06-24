import streamlit as st
from utils.ui import (
    select_csv_file,
    load_data,
    record_navigation,
    display_record,
    manage_binary_labels,
    export_annotations
)

def main():
    """
    Main entry point for the Streamlit app. Handles page setup and orchestrates the annotation workflow.
    """
    st.set_page_config(
        page_title="Data Annotation Tool",
        page_icon="📝",
        layout="wide"
    )
    st.title("📝 Data Annotation Tool")
    st.markdown("Review and annotate your request-response data")

    # --- File selection ---
    selected_file = select_csv_file()
    if not selected_file:
        return

    # --- Data loading ---
    df, binary_labels, annotations_df = load_data(selected_file)
    if df is None or df.empty:
        return

    # --- Record navigation and annotation ---
    record_index = record_navigation(df)
    annotations_df = display_record(df, annotations_df, record_index, binary_labels, selected_file)

    # --- Label management ---
    binary_labels, annotations_df = manage_binary_labels(annotations_df, binary_labels, selected_file)

    # --- Export section ---
    export_annotations(df, annotations_df, binary_labels, selected_file)

if __name__ == "__main__":
    main()