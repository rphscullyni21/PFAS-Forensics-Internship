import streamlit as st
import pandas as pd

from typing import Callable

from src.constants import (
    ID, 
    N_CARDS_PER_ROW, 
    QUESTION, 
    ANSWER, 
    TAGS, 
    DATE_ADDED, 
    NEXT_APPEARANCE
    )

from src.data_loader import (
    convert_df, 
    get_due_flashcards, 
    )


# =======================================================================================


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
            width=True,
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

def get_question(filtered_df: pd.DataFrame, force_all: bool = False):
    """
    Generator that yields cards in need of study.
    If force_all is True, acts as 'Cram Mode' and yields cards regardless of date.
    """
    due_source = filtered_df if force_all else get_due_flashcards(filtered_df)
    for i, row in due_source.iterrows():
        yield i, row
