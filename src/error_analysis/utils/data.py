import pandas as pd
import os
from pathlib import Path
from typing import List, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent 
DATA_DIR = PROJECT_ROOT / "data"

def load_csv_files() -> List[str]:
    """
    Load all CSV files ending with 'request_response.csv' from the data directory.

    Returns:
        List[str]: List of file paths to matching CSV files.
    """
    data_dir = Path(DATA_DIR)
    if not data_dir.exists():
        return []
    csv_files = list(data_dir.glob("*request_response.csv"))
    return [str(f) for f in csv_files]

def load_annotations(file_path: str) -> pd.DataFrame:
    """
    Load existing annotations if they exist.

    Args:
        file_path (str): Path to the main CSV file.
    Returns:
        pd.DataFrame: DataFrame of annotations, or empty DataFrame if not found or error.
    """
    annotations_file = file_path.replace('.csv', '-annotations.csv')
    if os.path.exists(annotations_file):
        try:
            return pd.read_csv(annotations_file)
        except Exception:
            return pd.DataFrame()
    return pd.DataFrame()

def save_annotations(annotations_df: pd.DataFrame, file_path: str) -> None:
    """
    Save annotations to a separate file.

    Args:
        annotations_df (pd.DataFrame): DataFrame of annotations to save.
        file_path (str): Path to the main CSV file.
    """
    annotations_file = file_path.replace('.csv', '-annotations.csv')
    annotations_df.to_csv(annotations_file, index=False)

def load_binary_labels(file_path: str) -> List[str]:
    """
    Load binary labels configuration from a text file.

    Args:
        file_path (str): Path to the main CSV file.
    Returns:
        List[str]: List of binary label names.
    """
    labels_file = file_path.replace('.csv', '-labels.txt')
    if os.path.exists(labels_file):
        try:
            with open(labels_file, 'r') as f:
                labels = [line.strip() for line in f.readlines() if line.strip()]
            return labels
        except Exception:
            return []
    return []

def save_binary_labels(labels: List[str], file_path: str) -> None:
    """
    Save binary labels configuration to a text file.

    Args:
        labels (List[str]): List of binary label names.
        file_path (str): Path to the main CSV file.
    """
    labels_file = file_path.replace('.csv', '-labels.txt')
    with open(labels_file, 'w') as f:
        for label in labels:
            f.write(f"{label}\n")

def initialize_annotations_with_labels(
    annotations_df: pd.DataFrame,
    df_length: int,
    labels: List[str]
) -> pd.DataFrame:
    """
    Initialize or update annotations dataframe with binary label columns.

    Args:
        annotations_df (pd.DataFrame): Existing annotation DataFrame (may be empty).
        df_length (int): Number of records in the main data.
        labels (List[str]): List of binary label names.
    Returns:
        pd.DataFrame: Updated annotation DataFrame with all required columns and rows.
    """
    # Initialize annotations dataframe if it doesn't exist
    if annotations_df.empty:
        annotations_df = pd.DataFrame({
            'index': range(df_length),
            'notes': [''] * df_length
        })
    # Add missing binary label columns
    for label in labels:
        if label not in annotations_df.columns:
            annotations_df[label] = False
    # Ensure we have all rows
    while len(annotations_df) < df_length:
        new_row = {'index': len(annotations_df), 'notes': ''}
        for label in labels:
            new_row[label] = False
        annotations_df = pd.concat([
            annotations_df, 
            pd.DataFrame([new_row])
        ], ignore_index=True)
    return annotations_df