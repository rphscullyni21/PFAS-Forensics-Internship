import os
from datetime import datetime
from typing import Callable, List, Tuple

import pandas as pd
import streamlit as st

FLASHCARDS_CSV = "flashcards.csv"
EXCEL_FILE = "EPA_1633A_PFAS_Learning_Database_v1 (1).xlsx"

# Standardized Core System Columns
ID = "id"
QUESTION = "question"
ANSWER = "answer"
DATE_ADDED = "date_added"
NEXT_APPEARANCE = "next_appearance"
TAGS = "tags"

SYSTEM_COLUMNS = [ID, QUESTION, ANSWER, DATE_ADDED, NEXT_APPEARANCE, TAGS]
N_CARDS_PER_ROW = 2

DEFAULT_TAGS = [
    "pfas",
    "pfca",
    "pfsa",
    "afff",
    "precursor",
    "terminal",
    "intermediate",
    "remediation",
    "forensics",
    "other",
]


def get_empty_df() -> pd.DataFrame:
    """Returns an empty stateful DataFrame with correct system columns."""
    return pd.DataFrame(
        columns=[ID, QUESTION, ANSWER, DATE_ADDED, NEXT_APPEARANCE, TAGS, "Structure Image"]
    )


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


def load_all_flashcards() -> pd.DataFrame:
    """
    Ingests Gerrad's Excel file (or CSV fallback) and merges it with the localized
    practice progress (next_appearance, date_added) stored in flashcards.csv.
    Appends custom-created flashcards that are not part of the database.
    """
    db_df = pd.DataFrame()
    metadata_cols = []

    # 1. Attempt Excel Ingestion
    if os.path.exists(EXCEL_FILE):
        try:
            excel_sheets = pd.ExcelFile(EXCEL_FILE).sheet_names
            target_sheet = (
                "Flashcard_Seeds" if "Flashcard_Seeds" in excel_sheets else excel_sheets[0]
            )
            raw_df = pd.read_excel(EXCEL_FILE, sheet_name=target_sheet)
            db_df, metadata_cols = map_columns_safely(raw_df)
        except Exception as e:
            st.error(f"Failed to ingest chemical Excel database: {str(e)}")
            db_df = get_empty_df()
    else:
        # Fallback to mapped localized seed files in directory
        seed_csv = "EPA_1633A_PFAS_Learning_Database_v1 (1).xlsx - Flashcard_Seeds.csv"
        master_csv = "EPA_1633A_PFAS_Learning_Database_v1 (1).xlsx - 1633_Master.csv"
        
        if os.path.exists(seed_csv):
            raw_df = pd.read_csv(seed_csv)
            db_df, metadata_cols = map_columns_safely(raw_df)
        elif os.path.exists(master_csv):
            raw_df = pd.read_csv(master_csv)
            db_df, metadata_cols = map_columns_safely(raw_df)
        elif os.path.exists("1633_Master.csv"):
            raw_df = pd.read_csv("1633_Master.csv")
            db_df, metadata_cols = map_columns_safely(raw_df)

    # 2. Stateful Synchronization and Progression Merging
    if os.path.exists(FLASHCARDS_CSV):
        try:
            user_df = pd.read_csv(
                FLASHCARDS_CSV, parse_dates=[DATE_ADDED, NEXT_APPEARANCE]
            )

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


def concat_df(df1: pd.DataFrame, df2: pd.DataFrame) -> pd.DataFrame:
    """Concatenates two DataFrames while preventing duplicates and preserving typing."""
    if df1.empty:
        return df2
    if df2.empty:
        return df1
    combined = pd.concat([df1, df2], ignore_index=True)
    return combined.drop_duplicates(subset=[QUESTION], keep="first")


def get_due_flashcards(df: pd.DataFrame) -> pd.DataFrame:
    """Filters cards that are scheduled for review."""
    if len(df) > 0:
        due_mask = pd.to_datetime(df[NEXT_APPEARANCE]) <= datetime.now()
        return df[due_mask]
    return get_empty_df()


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


def get_question(filtered_df: pd.DataFrame, force_all: bool = False):
    """
    Generator that yields cards in need of study.
    If force_all is True, acts as 'Cram Mode' and yields cards regardless of date.
    """
    due_source = filtered_df if force_all else get_due_flashcards(filtered_df)
    for i, row in due_source.iterrows():
        yield i, row


def search(text_search: str, df: pd.DataFrame) -> Callable:
    """Constructs dynamic visual UI panels for searching cards."""

    def search_df():
        if df.empty:
            st.warning("No cards found to search.")
            return

        search_mask = df[QUESTION].str.contains(text_search, case=False, na=False) | df[
            ANSWER
        ].str.contains(text_search, case=False, na=False)
        matching_rows = df[search_mask]

        if matching_rows.empty:
            st.info(f"No results match your search term '{text_search}'.")
            return

        for n_row, (_, row) in enumerate(matching_rows.iterrows()):
            i = n_row % N_CARDS_PER_ROW
            if i == 0:
                st.write("---")
                cols = st.columns(N_CARDS_PER_ROW, gap="large")
            with cols[i]:
                st.caption(f"Question No. {int(row[ID])}")
                st.markdown(f"**{row[QUESTION]}**")
                
                # Render Image if available in search results
                if "Structure Image" in row and pd.notna(row["Structure Image"]) and str(row["Structure Image"]).strip() != "":
                    st.markdown(
                        f"""
                        <div class="formula-image-container">
                            <img class="formula-image" src="{str(row["Structure Image"]).strip()}" alt="Molecular Formula Structure" />
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                with st.expander("Reveal System Answer"):
                    st.markdown(f"*{row[ANSWER]}*")

    return search_df


@st.cache_data(ttl=3600)
def convert_df(df: pd.DataFrame):
    """Encodes a DataFrame into a downloadable CSV string."""
    df_copy = df.copy()
    if TAGS in df_copy.columns:
        df_copy[TAGS] = df_copy[TAGS].apply(
            lambda x: ",".join(x) if isinstance(x, list) else x
        )
    return df_copy.to_csv(index=False).encode("utf-8")


def view_flashcards(df: pd.DataFrame):
    """Displays the interactive table of current cards."""
    if not df.empty:
        display_df = df.copy()

        # Format list tags cleanly for tabular view
        display_df[TAGS] = display_df[TAGS].apply(
            lambda x: ", ".join(x) if isinstance(x, list) else x
        )

        st.dataframe(
            display_df,
            use_container_width=True,
            column_order=[QUESTION, ANSWER, ID, DATE_ADDED, NEXT_APPEARANCE, TAGS],
        )
        st.download_button(
            label="Download Current Deck as CSV",
            data=convert_df(df),
            file_name="pfas_flashcards_export.csv",
            mime="text/csv",
        )
    else:
        st.info("No records are currently matching this selection.")