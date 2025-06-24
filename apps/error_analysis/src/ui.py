import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Optional, Tuple, List
from .data import (
    load_csv_files, 
    load_annotations, 
    save_annotations, 
    load_binary_labels, 
    save_binary_labels, 
    initialize_annotations_with_labels
)

def select_csv_file() -> Optional[str]:
    """
    Display a selectbox for available CSV files and return the selected file path.

    Returns:
        Optional[str]: The path to the selected CSV file, or None if no file is selected.
    """
    csv_files = load_csv_files()
    if not csv_files:
        st.error("No CSV files found in the 'data' directory!")
        return None
    selected_file = st.selectbox(
        "Select a CSV file to annotate:",
        csv_files,
        help="Choose the CSV file you want to review and annotate"
    )
    if not selected_file:
        return None
    return selected_file

def load_data(selected_file: str) -> Tuple[Optional[pd.DataFrame], List[str], pd.DataFrame]:
    """
    Load the main data, binary labels, and annotations for the selected file.

    Args:
        selected_file (str): Path to the selected CSV file.
    Returns:
        tuple: (df, binary_labels, annotations_df)
            df (Optional[pd.DataFrame]): Main data or None if loading fails.
            binary_labels (List[str]): List of binary label names.
            annotations_df (pd.DataFrame): Annotation data.
    """
    try:
        df = pd.read_csv(selected_file)
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None, [], pd.DataFrame()
    if df.empty:
        st.warning("The selected file is empty!")
        return None, [], pd.DataFrame()
    binary_labels = load_binary_labels(selected_file)
    annotations_df = load_annotations(selected_file)
    annotations_df = initialize_annotations_with_labels(annotations_df, len(df), binary_labels)
    return df, binary_labels, annotations_df

def record_navigation(df: pd.DataFrame) -> int:
    """
    Display navigation controls for records and return the current record index.

    Args:
        df (pd.DataFrame): Main data.
    Returns:
        int: Current record index.
    """
    if 'record_index' not in st.session_state:
        st.session_state.record_index = 0
    # Ensure record_index is within bounds
    if st.session_state.record_index >= len(df):
        st.session_state.record_index = len(df) - 1
    elif st.session_state.record_index < 0:
        st.session_state.record_index = 0
    st.markdown(f"**Total Records:** {len(df)}")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        new_index = st.selectbox(
            "Select Record:",
            range(len(df)),
            index=st.session_state.record_index,
            format_func=lambda x: f"Record {x + 1} of {len(df)}",
            help="Navigate through the records",
            key="record_selectbox"
        )
        # Update session state if selectbox changed
        if new_index != st.session_state.record_index:
            st.session_state.record_index = new_index
    record_index = st.session_state.record_index
    # Navigation buttons
    nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 1])
    with nav_col1:
        if st.button("⏮️ First", disabled=(record_index == 0)):
            st.session_state.record_index = 0
            st.rerun()
    with nav_col2:
        if st.button("⏪ Previous", disabled=(record_index == 0)):
            st.session_state.record_index = max(0, record_index - 1)
            st.rerun()
    with nav_col3:
        st.metric("Progress", f"{record_index + 1}/{len(df)}")
    with nav_col4:
        if st.button("Next ⏩", disabled=(record_index >= len(df) - 1)):
            st.session_state.record_index = min(len(df) - 1, record_index + 1)
            st.rerun()
    with nav_col5:
        if st.button("Last ⏭️", disabled=(record_index >= len(df) - 1)):
            st.session_state.record_index = len(df) - 1
            st.rerun()
    # Progress bar
    progress = (record_index + 1) / len(df)
    st.progress(progress)
    return record_index

def display_record(
    df: pd.DataFrame,
    annotations_df: pd.DataFrame,
    record_index: int,
    binary_labels: List[str],
    selected_file: str
) -> pd.DataFrame:
    """
    Display the current record's user input, LLM response, notes, and binary labels.
    Handles saving notes and label changes.

    Args:
        df (pd.DataFrame): Main data.
        annotations_df (pd.DataFrame): Annotation data.
        record_index (int): Current record index.
        binary_labels (List[str]): List of binary label names.
        selected_file (str): Path to the selected CSV file.
    Returns:
        pd.DataFrame: Updated annotation data.
    """
    if record_index < len(df):
        current_record = df.iloc[record_index]
        # --- Main content columns ---
        left_col, middle_col, right_col = st.columns([1, 2, 1])
        with left_col:
            st.subheader("📄 User Input")
            user_input = current_record.get('User Input', '')
            st.text_area(
                "User Input Content:",
                value=str(user_input),
                height=400,
                key=f"user_input_{record_index}",
                help="Read-only view of the user input"
            )
        with middle_col:
            st.subheader("🤖 LLM Response")
            llm_response = current_record.get('LLM Response', '')
            st.text_area(
                "LLM Response Content:",
                value=str(llm_response),
                height=400,  # More space for longer responses
                key=f"llm_response_{record_index}",
                help="Read-only view of the LLM response"
            )
        with right_col:
            st.subheader("📝 Notes & Labels")
            # Get current notes for this record
            current_notes = ''
            if record_index < len(annotations_df):
                current_notes = annotations_df.iloc[record_index]['notes']
            # Notes text area
            notes = st.text_area(
                "Add your notes for this record:",
                value=current_notes,
                height=300,
                placeholder="Write your annotations, observations, or feedback here...",
                key=f"notes_{record_index}",
                help="Your notes will be automatically saved"
            )
            # Auto-save notes when they change
            if notes != current_notes:
                annotations_df.iloc[record_index, annotations_df.columns.get_loc('notes')] = notes
                save_annotations(annotations_df, selected_file)
                st.success("Notes saved automatically!")
            # --- Binary Labels Section ---
            if binary_labels:
                st.markdown("**Binary Labels:**")
                labels_changed = False
                # Create two columns for checkboxes
                checkbox_col1, checkbox_col2 = st.columns(2)
                mid_point = len(binary_labels) // 2 + len(binary_labels) % 2
                left_labels = binary_labels[:mid_point]
                right_labels = binary_labels[mid_point:]
                # Left column checkboxes
                with checkbox_col1:
                    for label in left_labels:
                        current_value = bool(annotations_df.iloc[record_index].get(label, False))
                        new_value = st.checkbox(
                            label,
                            value=current_value,
                            key=f"label_{label}_{record_index}"
                        )
                        if new_value != current_value:
                            annotations_df.iloc[record_index, annotations_df.columns.get_loc(label)] = new_value
                            labels_changed = True
                # Right column checkboxes
                with checkbox_col2:
                    for label in right_labels:
                        current_value = bool(annotations_df.iloc[record_index].get(label, False))
                        new_value = st.checkbox(
                            label,
                            value=current_value,
                            key=f"label_{label}_{record_index}"
                        )
                        if new_value != current_value:
                            annotations_df.iloc[record_index, annotations_df.columns.get_loc(label)] = new_value
                            labels_changed = True
                if labels_changed:
                    save_annotations(annotations_df, selected_file)
                    st.success("Labels saved!")
                st.markdown("---")
    return annotations_df

def manage_binary_labels(
    annotations_df: pd.DataFrame,
    binary_labels: List[str],
    selected_file: str
) -> Tuple[List[str], pd.DataFrame]:
    """
    Display UI for adding/removing binary labels and update the annotations DataFrame.

    Args:
        annotations_df (pd.DataFrame): Annotation data.
        binary_labels (List[str]): List of binary label names.
        selected_file (str): Path to the selected CSV file.
    Returns:
        tuple: (binary_labels, annotations_df) - updated label list and annotation data.
    """
    st.markdown("---")
    st.subheader("🏷️ Manage Binary Labels")
    label_col1, label_col2 = st.columns([2, 1])
    with label_col1:
        if binary_labels:
            st.write("**Current Labels:**")
            label_counts = []
            for label in binary_labels:
                if label in annotations_df.columns:
                    count = annotations_df[label].sum()
                else:
                    count = 0
                label_counts.append((label, count))
            label_counts.sort(key=lambda x: x[1], reverse=True)
            for i, (label, count) in enumerate(label_counts):
                label_display_col1, label_display_col2 = st.columns([3, 1])
                with label_display_col1:
                    total_records = len(annotations_df)
                    st.write(f"• {label} ({count}/{total_records})")
                with label_display_col2:
                    original_index = binary_labels.index(label)
                    if st.button("🗑️", key=f"remove_{original_index}", help=f"Remove '{label}' label"):
                        binary_labels.remove(label)
                        if label in annotations_df.columns:
                            annotations_df = annotations_df.drop(columns=[label])
                        save_binary_labels(binary_labels, selected_file)
                        save_annotations(annotations_df, selected_file)
                        st.rerun()
        else:
            st.write("No binary labels defined yet.")
    with label_col2:
        new_label = st.text_input("New Label Name:", placeholder="e.g., Good, Relevant, Accurate")
        if st.button("➕ Add Label"):
            if new_label and new_label not in binary_labels:
                binary_labels.append(new_label)
                annotations_df[new_label] = False
                save_binary_labels(binary_labels, selected_file)
                save_annotations(annotations_df, selected_file)
                st.success(f"Added label: '{new_label}'")
                st.rerun()
            elif new_label in binary_labels:
                st.warning("Label already exists!")
            else:
                st.warning("Please enter a label name!")
    return binary_labels, annotations_df

def export_annotations(
    df: pd.DataFrame,
    annotations_df: pd.DataFrame,
    binary_labels: List[str],
    selected_file: str
) -> None:
    """
    Handle the export/download section for annotated data.

    Args:
        df (pd.DataFrame): Main data.
        annotations_df (pd.DataFrame): Annotation data.
        binary_labels (List[str]): List of binary label names.
        selected_file (str): Path to the selected CSV file.
    """
    st.markdown("---")
    st.subheader("💾 Export")
    if st.button("📥 Download Annotations"):
        # Create a dataframe with the specified columns plus binary labels
        export_data = {
            'user input': df.get('User Input', ''),
            'LLM response': df.get('LLM Response', ''),
            'notes': annotations_df['notes']
        }
        # Add binary label columns, converting boolean to int (0/1)
        for label in binary_labels:
            if label in annotations_df.columns:
                export_data[label] = annotations_df[label].astype(int)
        export_df = pd.DataFrame(export_data)
        csv = export_df.to_csv(index=False)
        st.download_button(
            label="Download CSV with Annotations",
            data=csv,
            file_name=f"{Path(selected_file).stem}-with_notes.csv",
            mime="text/csv"
        )