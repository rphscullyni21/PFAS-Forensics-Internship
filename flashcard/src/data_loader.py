import os
import streamlit as st
import pandas as pd

from datetime import datetime
from typing import Callable, List, Tuple

from src.constants import (
    ANSWER, 
    DATE_ADDED, 
    EXCEL_FILE, 
    ID, 
    NEXT_APPEARANCE, 
    QUESTION, 
    TAGS, 
    FLASHCARDS_CSV, 
    SYSTEM_COLUMNS
    )

# =======================================================================================

def get_empty_df() -> pd.DataFrame:
    """Returns an empty stateful DataFrame with correct system columns."""
    from src.constants import SYSTEM_COLUMNS
    # Adding 'Structure Image' to columns as per your original code
    return pd.DataFrame(columns=SYSTEM_COLUMNS + ["Structure Image"])

# @st.cache_data(ttl=3600)
def save_flashcards(flashcards_df: pd.DataFrame):
    """Saves the stateful flashcards to local CSV safely."""
    df_to_save = flashcards_df.copy()

    # Safeguard: Ensure tags are serialized cleanly to a comma-separated string
    if TAGS in df_to_save.columns:
        df_to_save[TAGS] = df_to_save[TAGS].apply(
            lambda x: ",".join(t.strip().lower() for t in x)
            if isinstance(x, list)
            else (str(x).lower() if pd.notna(x) else "other")
        )

    # Force correct datetime formatting on save
    if DATE_ADDED in df_to_save.columns:
        df_to_save[DATE_ADDED] = pd.to_datetime(df_to_save[DATE_ADDED])
    if NEXT_APPEARANCE in df_to_save.columns:
        df_to_save[NEXT_APPEARANCE] = pd.to_datetime(df_to_save[NEXT_APPEARANCE])

    df_to_save.to_csv(FLASHCARDS_CSV, index=False, quotechar='"', quoting=1)


def map_columns_safely(df: pd.DataFrame) -> Tuple[pd.DataFrame, List[str]]:
    """
    Scans incoming columns and maps exactly ONE unique column to each system column.
    All non-system columns are left completely untouched to serve as dynamic metadata filters.
    This guarantees zero duplicate columns.
    """
    cols = list(df.columns)
    mapped_rename = {}
    assigned_cols = set()

    # 1. Map ID Column
    id_options = ["id", "index", "card number", "card_id", "chemical_id"]
    for col in cols:
        if col.lower().strip() in id_options:
            mapped_rename[col] = ID
            assigned_cols.add(col)
            break

    # 2. Map QUESTION Column (Prioritized exact to fuzzy match)
    question_exact = [
        "common exam/flashcard question",
        "question",
        "prompt",
        "concept",
    ]
    question_found = False
    for target in question_exact:
        for col in cols:
            if col not in assigned_cols and col.lower().strip() == target:
                mapped_rename[col] = QUESTION
                assigned_cols.add(col)
                question_found = True
                break
        if question_found:
            break

    if not question_found:
        # Fallback to fuzzy substring check
        for col in cols:
            if (
                col not in assigned_cols
                and any(x in col.lower() for x in ["question", "prompt", "concept"])
                and not any(x in col.lower() for x in ["key", "answer"])
            ):
                mapped_rename[col] = QUESTION
                assigned_cols.add(col)
                question_found = True
                break

    # 3. Map ANSWER Column (Prioritized exact to fuzzy match)
    answer_exact = [
        "answer",
        "key learning point",
        "key forensic interpretation",
        "response",
    ]
    answer_found = False
    for target in answer_exact:
        for col in cols:
            if col not in assigned_cols and col.lower().strip() == target:
                mapped_rename[col] = ANSWER
                assigned_cols.add(col)
                answer_found = True
                break
        if answer_found:
            break

    if not answer_found:
        # Fallback to fuzzy substring check
        for col in cols:
            if col not in assigned_cols and any(
                x in col.lower() for x in ["answer", "response", "explanation"]
            ):
                mapped_rename[col] = ANSWER
                assigned_cols.add(col)
                answer_found = True
                break

    # 4. Map TAGS Column
    for col in cols:
        if col not in assigned_cols and col.lower().strip() in ["tags", "tag", "keywords"]:
            mapped_rename[col] = TAGS
            assigned_cols.add(col)
            break

    # Rename matched columns safely
    df_renamed = df.rename(columns=mapped_rename)

    # Ensure system columns exist with fallback empty data if missing
    if ID not in df_renamed.columns:
        df_renamed[ID] = range(1, len(df_renamed) + 1)
    if QUESTION not in df_renamed.columns:
        # If no question column is identified, we use the first column as a fallback
        remaining_cols = [c for c in df_renamed.columns if c not in SYSTEM_COLUMNS]
        if remaining_cols:
            df_renamed = df_renamed.rename(columns={remaining_cols[0]: QUESTION})
        else:
            df_renamed[QUESTION] = "Empty Question Placeholder"
    if ANSWER not in df_renamed.columns:
        df_renamed[ANSWER] = "No details populated."
    if TAGS not in df_renamed.columns:
        df_renamed[TAGS] = "other"

    # Capture metadata columns (all columns that are NOT core system properties)
    metadata_cols = [c for c in df_renamed.columns if c not in SYSTEM_COLUMNS]

    return df_renamed, metadata_cols

# Get the directory one level above src to ensure we can locate the Excel and CSV files correctly
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_all_flashcards() -> pd.DataFrame:
# Construct absolute paths
    excel_path = os.path.join(BASE_DIR, EXCEL_FILE)
    csv_path = os.path.join(BASE_DIR, FLASHCARDS_CSV)
    
    db_df = pd.DataFrame()

    # 1. Attempt Excel Ingestion with the absolute path
    if os.path.exists(excel_path):
        try:
            excel_file_obj = pd.ExcelFile(excel_path)
            excel_sheets = excel_file_obj.sheet_names
            
            # Define target_sheet safely BEFORE using it
            target_sheet = "Flashcard_Seeds" if "Flashcard_Seeds" in excel_sheets else excel_sheets[0]
            
            raw_df = pd.read_excel(excel_path, sheet_name=target_sheet)
            db_df, metadata_cols = map_columns_safely(raw_df)
        except Exception as e:
            st.error(f"Failed to ingest chemical Excel database: {str(e)}")
            db_df = get_empty_df()
    else:
        # Debug: Tell us exactly where it looked
        st.sidebar.error(f"Excel file not found at: {excel_path}")
        # ... fallback logic ...

    # 2. Stateful Synchronization using the absolute path
    if os.path.exists(csv_path):
        try:
            user_df = pd.read_csv(csv_path, parse_dates=[DATE_ADDED, NEXT_APPEARANCE])

            # Standardize structural properties
            for col in SYSTEM_COLUMNS:
                if col not in user_df.columns:
                    user_df[col] = (
                        pd.to_datetime("2020-01-01")
                        if col in [DATE_ADDED, NEXT_APPEARANCE]
                        else ""
                    )

            if not db_df.empty:
                merged_rows = []
                matched_questions = set()

                for _, db_row in db_df.iterrows():
                    db_q_clean = str(db_row[QUESTION]).strip().lower()
                    match = user_df[
                        user_df[QUESTION].astype(str).str.strip().str.lower()
                        == db_q_clean
                    ]

                    if not match.empty:
                        # Retain existing progress logs
                        merged_row = db_row.copy()
                        merged_row[NEXT_APPEARANCE] = match.iloc[0][NEXT_APPEARANCE]
                        merged_row[DATE_ADDED] = match.iloc[0][DATE_ADDED]
                        merged_row[ID] = match.iloc[0][ID]
                        
                        # Retain customized images if available
                        if "Structure Image" in match.columns:
                            merged_row["Structure Image"] = match.iloc[0]["Structure Image"]
                        else:
                            merged_row["Structure Image"] = ""
                            
                        matched_questions.add(db_q_clean)
                    else:
                        # New addition from database seed sheet
                        merged_row = db_row.copy()
                        merged_row[NEXT_APPEARANCE] = pd.to_datetime("2020-01-01")
                        merged_row[DATE_ADDED] = datetime.now()
                        merged_row["Structure Image"] = ""

                    # Safe tags conversion
                    raw_tags = merged_row[TAGS]
                    if isinstance(raw_tags, str):
                        merged_row[TAGS] = [
                            t.strip().lower() for t in raw_tags.split(",") if t.strip()
                        ]
                    elif not isinstance(raw_tags, list):
                        merged_row[TAGS] = ["other"]

                    merged_rows.append(merged_row)

                # FIX: Find and preserve user-added cards that do NOT exist in the Excel database
                for _, user_row in user_df.iterrows():
                    user_q_clean = str(user_row[QUESTION]).strip().lower()
                    if user_q_clean not in matched_questions:
                        custom_row = user_row.copy()
                        
                        # Clean tags array formatting for memory alignment
                        raw_tags = custom_row[TAGS]
                        if isinstance(raw_tags, str):
                            custom_row[TAGS] = [
                                t.strip().lower() for t in raw_tags.split(",") if t.strip()
                            ]
                        elif not isinstance(raw_tags, list):
                            custom_row[TAGS] = ["other"]
                            
                        if "Structure Image" not in custom_row:
                            custom_row["Structure Image"] = ""
                            
                        merged_rows.append(custom_row)

                final_df = pd.DataFrame(merged_rows)
                final_df[ID] = range(1, len(final_df) + 1)
                return final_df
            else:
                user_df[TAGS] = user_df[TAGS].apply(
                    lambda x: [t.strip().lower() for t in x.split(",")]
                    if isinstance(x, str)
                    else x
                )
                if "Structure Image" not in user_df.columns:
                    user_df["Structure Image"] = ""
                return user_df
        except Exception as e:
            st.warning(f"Error parsing local progress, regenerating: {str(e)}")
            if not db_df.empty:
                db_df[NEXT_APPEARANCE] = pd.to_datetime("2020-01-01")
                db_df[DATE_ADDED] = datetime.now()
                db_df["Structure Image"] = ""
                return db_df
            return get_empty_df()
    else:
        # First-time app initialization writeout
        if not db_df.empty:
            db_df[NEXT_APPEARANCE] = pd.to_datetime("2020-01-01")
            db_df[DATE_ADDED] = datetime.now()
            db_df["Structure Image"] = ""
            db_df[TAGS] = db_df[TAGS].apply(
                lambda x: [t.strip().lower() for t in x.split(",") if t.strip()]
                if isinstance(x, str)
                else ["other"]
            )
            save_flashcards(db_df)
            return db_df
        return get_empty_df()
    
def get_due_flashcards(df: pd.DataFrame) -> pd.DataFrame:
    """Filters cards that are scheduled for review."""
    if len(df) > 0:
        due_mask = pd.to_datetime(df[NEXT_APPEARANCE]) <= datetime.now()
        return df[due_mask]
    return get_empty_df()

def concat_df(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """Concatenates two DataFrames while preventing duplicates and preserving typing."""
    if df1.empty:
        return df2
    if df2.empty:
        return df1
    combined = pd.concat([df1, df2], ignore_index=True)
    return combined.drop_duplicates(subset=[QUESTION], keep="first")

def prepare_flashcard_df(
    question: str,
    answer: str,
    id: int,
    date_added: datetime,
    next_appearance: datetime,
    tags: list,
    ) -> pd.DataFrame:
    """Creates a standardized DataFrame row for manual card additions."""
    row = {
        ID: id,
        QUESTION: question,
        ANSWER: answer,
        DATE_ADDED: date_added,
        NEXT_APPEARANCE: next_appearance,
        TAGS: tags,
        "Structure Image": ""
    }
    return pd.DataFrame([row])

# @st.cache_data(ttl=3600)
def convert_df(df: pd.DataFrame):
    """Encodes a DataFrame into a downloadable CSV string."""
    df_copy = df.copy()
    if TAGS in df_copy.columns:
        df_copy[TAGS] = df_copy[TAGS].apply(
            lambda x: ",".join(x) if isinstance(x, list) else x
        )
    return df_copy.to_csv(index = False).encode("utf-8")