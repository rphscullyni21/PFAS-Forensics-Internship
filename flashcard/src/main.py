import base64
import os
import pandas as pd
import streamlit as st

from datetime import datetime, timedelta
from src.constants import DATE_ADDED, DEFAULT_TAGS, ID, NEXT_APPEARANCE, QUESTION, ANSWER, SYSTEM_COLUMNS, TAGS
from src.data_loader import concat_df, load_all_flashcards, prepare_flashcard_df, save_flashcards
from src.ui_helpers import search, view_flashcards, get_question


# -------------- App Configuration --------------
st.set_page_config(
    page_title="PFAS/PFOA Forensic Training Dashboard",
    page_icon="🧬",
    layout="centered",
)

# -------------- Background Image Injection --------------
BACKGROUND_IMAGE_PATH = os.path.join(os.path.dirname(__file__), "assets", "identifying-and-characterizing-pfas-compounds-382099-960x540.jpg")


def apply_custom_background(image_path: str):
    """
    Encodes the local background image to Base64 and embeds it directly into
    Streamlit's main view containers with correct transparency overrides.
    """
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode()
            
            st.markdown(
                f"""
                <style>
                [data-testid="stAppViewContainer"] {{
                    background: linear-gradient(rgba(27, 32, 44, 0.91), rgba(27, 32, 44, 0.91)), 
                                url("data:image/jpeg;base64,{encoded_string}");
                    background-size: cover;
                    background-position: center;
                    background-repeat: no-repeat;
                    background-attachment: fixed !important;
                }}
                
                /* Override Streamlit container backgrounds to make them transparent */
                [data-testid="stHeader"], .main, [data-testid="stMainViewContainer"] {{
                    background-color: transparent !important;
                    background: transparent !important;
                }}
                </style>
                """,
                unsafe_allow_html=True,
            )
        except Exception as e:
            st.sidebar.error(f"Error encoding background image: {e}")
    else:
        # Dynamic fallback notifier
        st.sidebar.warning(
            f"Background image not found at root path: '{image_path}'. "
            "Ensure the background JPEG file is placed alongside main.py."
        )


# Execute background rendering
apply_custom_background(BACKGROUND_IMAGE_PATH)


# -------------- Session State Setup --------------
if "flashcards_df" not in st.session_state:
    st.session_state.flashcards_df = load_all_flashcards()


# -------------- Style Sheets Ingestion --------------
def local_css(file_name: str):
    if os.path.exists(file_name):
        with open(file_name) as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


local_css("style.css")


# -------------- Stateful Helper Methods --------------
def update_flashcards(new_flashcard_df: pd.DataFrame):
    if not new_flashcard_df.empty:
        st.session_state.flashcards_df = concat_df(
            st.session_state.flashcards_df, new_flashcard_df
        )
        save_flashcards(st.session_state.flashcards_df)


def update_next_appearance(id: int, next_appearance: datetime):
    if next_appearance is not None:
        st.session_state.flashcards_df.loc[
            st.session_state.flashcards_df[ID] == id, NEXT_APPEARANCE
        ] = next_appearance
        save_flashcards(st.session_state.flashcards_df)


# -------------- Sidebar Control Panel --------------
with st.sidebar:
    st.markdown("### 🧬 Study Controller")

    # 1. Study Mode Selector
    study_strategy = st.radio(
        "Practice Strategy:",
        options=["Spaced Repetition (Due Only)", "Cram Mode (Study All)"],
        index=0,
        help="Spaced Repetition tracks scheduling data. Cram Mode lets you practice the entire deck instantly.",
    )
    is_cram_mode = study_strategy == "Cram Mode (Study All)"

    # 2. Hard Reset Action
    st.markdown("---")
    if st.button("🔄 Reset Practice Schedules", use_container_width=True):
        st.session_state.flashcards_df[NEXT_APPEARANCE] = pd.to_datetime(
            "2020-01-01"
        )
        save_flashcards(st.session_state.flashcards_df)
        st.toast("Practice schedule timeline has been cleared successfully!")
        st.rerun()

    # 3. Dynamic Metadata Sidebar Filters (Sourced from Gerrad's Excel sheet)
    st.markdown("---")
    st.markdown("### 🎛️ Forensic Filters")

    # Filter out internal variables to capture the true chemical classification columns
    metadata_cols = [
        col
        for col in st.session_state.flashcards_df.columns
        if col not in SYSTEM_COLUMNS and col != "Structure Image"
    ]

    selected_filters = {}
    if metadata_cols:
        for col in metadata_cols:
            # Drop NaN rows to present clean classification sets
            unique_vals = sorted(
                st.session_state.flashcards_df[col].dropna().unique().astype(str)
            )
            if unique_vals:
                selected_vals = st.multiselect(
                    f"Filter by {col}", options=unique_vals, key=f"filter_{col}"
                )
                if selected_vals:
                    selected_filters[col] = selected_vals

    # Tag multiselect fallback (Handles comma-separated string arrays safely)
    available_tags = set()
    for item in st.session_state.flashcards_df[TAGS].dropna():
        if isinstance(item, list):
            available_tags.update(item)
        elif isinstance(item, str):
            available_tags.update(
                [t.strip().lower() for t in item.split(",") if t.strip()]
            )

    selected_tags = st.multiselect(
        "Filter by Keyword/Tag",
        options=sorted(list(available_tags)),
        key="filter_core_tags",
    )

# -------------- Data Filtering Engine --------------
filtered_df = st.session_state.flashcards_df.copy()

# A. Apply Dynamic Categorization Dropdowns (Excel columns)
for col, vals in selected_filters.items():
    filtered_df = filtered_df[filtered_df[col].astype(str).isin(vals)]

# B. Apply Tag Keywords Array Checks
if selected_tags:
    filtered_df = filtered_df[
        filtered_df[TAGS].apply(
            lambda x: any(tag in x for tag in selected_tags)
            if isinstance(x, list)
            else False
        )
    ]



# -------------- Header Metrics --------------
st.subheader("Welcome to the PFAS/PFOAS FlashCard helper!")

total_deck_size = len(filtered_df)
due_questions_df = filtered_df[
    pd.to_datetime(filtered_df[NEXT_APPEARANCE]) <= datetime.now()
]
due_deck_size = len(due_questions_df) if not is_cram_mode else total_deck_size

metric_col1, metric_col2 = st.columns(2)
with metric_col1:
    st.metric(label="Active Filtered Deck Size", value=total_deck_size)
with metric_col2:
    st.metric(
        label="Due for Review" if not is_cram_mode else "Cram Mode Cards",
        value=due_deck_size,
    )


# -------------- Tabs Architecture --------------
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    [
        "🎯 Review Cards",
        "➕ Add Concept",
        "✏️ Manage Deck",
        "🔍 Search Database",
        "📊 View Deck Data",
    ]
)


# Initialize session state for navigation
if "deck_order" not in st.session_state:
    st.session_state.deck_order = filtered_df.index.tolist()
if "current_index" not in st.session_state:
    st.session_state.current_index = 0


# TAB 1: CARD PRACTICE SYSTEM
with tab1:
    if total_deck_size == 0:
        st.info("No chemical cards match your current sidebar filters.")
    else:
            # 1. Ensure the index is valid
            if st.session_state.current_index >= len(st.session_state.deck_order):
                st.session_state.current_index = 0
                
            # 2. Get the row directly from the dataframe
            current_idx = st.session_state.deck_order[st.session_state.current_index]
            row = filtered_df.loc[current_idx]
            
            # 3. Look up if a custom molecular structure image exists for this card
            img_html = ""
            if "Structure Image" in row and pd.notna(row["Structure Image"]) and str(row["Structure Image"]).strip() != "":
                img_data = str(row["Structure Image"]).strip()
                img_html = f"""
                    <div class="formula-image-container">
                        <img class="formula-image" src="{img_data}" alt="Molecular Formula Structure" />
                    </div>
                    """
            st.markdown(
                f"""
                <div class="blockquote-wrapper">
                <div class="blockquote">
                <h1>
                    <span style="color:#ffffff">{row[QUESTION]}</span>
                    {img_html}
                </h1>
                <h4>&mdash; Question no. {row[ID]}</em></h4></div></div>
                """,
                unsafe_allow_html=True,
            )
            
            # 4. Add the navigation controls
            nav_col1, nav_col2, nav_col3 = st.columns([1, 2, 1])
            with nav_col1:
                if st.button("⬅️ Back"):
                    if st.session_state.current_index > 0:
                        st.session_state.current_index -= 1
                        st.rerun()
            with nav_col3:
                if st.button("Next ➡️"):
                    if st.session_state.current_index < len(st.session_state.deck_order) - 1:
                        st.session_state.current_index += 1
                        st.rerun()

            # Answer revealing wrapper
            with st.expander("Reveal Answer"):
                st.markdown(
                    f"""
                    <div class="answer">
                    {str(row[ANSWER]).replace('\\n', '<br>')}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            next_appearance = None
            col1, col2, col3 = st.columns(3, gap="large")

            # Easy button logic
            with col1:
                easy_submit_button = st.button(label="Easy", use_container_width=True)
                if easy_submit_button:
                    prev_time_diff = (
                        pd.to_datetime(row[NEXT_APPEARANCE])
                        - pd.to_datetime(row[DATE_ADDED])
                    )
                    next_appearance_days = min(max(prev_time_diff.days, 1) + 2, 60)
                    next_appearance = datetime.now() + timedelta(
                        days=next_appearance_days
                    )

            # Medium button logic
            with col2:
                medium_submit_button = st.button(
                    label="Medium", use_container_width=True
                )
                if medium_submit_button:
                    next_appearance = datetime.now() + timedelta(days=2)

            # Hard button logic
            with col3:
                hard_submit_button = st.button(label="Hard", use_container_width=True)
                if hard_submit_button:
                    next_appearance = datetime.now() + timedelta(days=1)

            if next_appearance is not None:
                update_next_appearance(row[ID], next_appearance)
                st.toast(
                    f"Scheduled for review on: {next_appearance.strftime('%m/%d/%Y')}"
                )
                st.rerun()


# TAB 2: MANUAL DATA INGESTION
with tab2:
    with st.form("add_flashcard_form", clear_on_submit=True):
        question = st.text_input("Core Study Question")
        
        # Captured Image Upload Control
        uploaded_image = st.file_uploader(
            "Upload Chemical Structure / Formula Image (Optional)",
            type=["png", "jpg", "jpeg", "webp"],
            key="add_img_uploader"
        )
        
        answer = st.text_area("Detailed Forensic Answer / Key Concept Details")
        tags = st.multiselect(
            "Keywords / Tags", DEFAULT_TAGS, default=DEFAULT_TAGS[0], key="add_tag_selector"
        )
        submit_button = st.form_submit_button("Add Flashcard to Local Storage")

        if submit_button:
            if question and answer:
                date_added = datetime.now()
                
                # Encode custom uploaded chemical formula to Base64 cleanly
                encoded_image_string = ""
                if uploaded_image is not None:
                    try:
                        file_bytes = uploaded_image.getvalue()
                        mime_type = uploaded_image.type
                        b64_data = base64.b64encode(file_bytes).decode("utf-8")
                        encoded_image_string = f"data:{mime_type};base64,{b64_data}"
                    except Exception as img_err:
                        st.error(f"Failed to process uploaded image: {img_err}")
                
                new_flashcard = prepare_flashcard_df(
                    question,
                    answer,
                    id=int(len(st.session_state.flashcards_df) + 1),
                    date_added=date_added,
                    next_appearance=(date_added + timedelta(days=-1)),
                    tags=tags if isinstance(tags, list) else [tags],
                )
                
                # Append molecular structure image safely to row
                new_flashcard["Structure Image"] = encoded_image_string
                
                update_flashcards(new_flashcard)
                st.success("Custom flashcard with chemical formula successfully added!")
                st.rerun()
            else:
                st.warning(
                    "Action Required: Please populate both the Question and Answer fields."
                )


# TAB 3: MANAGE / EDIT / DELETE DECK CARDS
with tab3:
    st.markdown("### ✏️ Manage and Edit Deck Database")
    st.markdown(
        "Select any card from our database below to edit its questions, answers, keywords, "
        "or swap/remove its formula structures."
    )
    
    if st.session_state.flashcards_df.empty:
        st.info("The deck is currently empty.")
    else:
        # Create a selectbox that displays the card ID and Question slice
        deck_cards = st.session_state.flashcards_df.copy()
        
        card_options = deck_cards[ID].tolist()
        
        def format_card_label(card_id):
            row_match = deck_cards[deck_cards[ID] == card_id]
            if not row_match.empty:
                q_text = str(row_match.iloc[0][QUESTION])
                return f"Card #{card_id}: {q_text[:65]}..."
            return f"Card #{card_id}"
            
        selected_card_id = st.selectbox(
            "Choose a card to edit/delete:",
            options=card_options,
            format_func=format_card_label,
            key="manage_card_selector"
        )
        
        # Pull selected card data
        target_card_row = deck_cards[deck_cards[ID] == selected_card_id].iloc[0]
        
        # Draw inline Editor Forms
        with st.form("edit_flashcard_form", clear_on_submit=False):
            st.markdown(f"#### Editing Card ID: `{selected_card_id}`")
            
            edit_question = st.text_input("Question Text", value=str(target_card_row[QUESTION]))
            edit_answer = st.text_area("Answer Detail", value=str(target_card_row[ANSWER]))
            
            # Map current tags correctly
            current_tags = target_card_row[TAGS]
            if isinstance(current_tags, str):
                current_tags_list = [t.strip().lower() for t in current_tags.split(",") if t.strip()]
            elif isinstance(current_tags, list):
                current_tags_list = current_tags
            else:
                current_tags_list = []
                
            # Filter multiselect selection down to default tags, but allow custom tags if present
            available_edit_tags = sorted(list(set(DEFAULT_TAGS + current_tags_list)))
            edit_tags_selected = st.multiselect(
                "Keywords / Tags",
                options=available_edit_tags,
                default=current_tags_list
            )
            
            # Handle molecular structure updates
            edit_uploaded_image = st.file_uploader(
                "Upload Replacement Formula Image (Optional)",
                type=["png", "jpg", "jpeg", "webp"],
                key="edit_img_uploader"
            )
            
            # Checkbox to explicitly clear the existing image
            current_img_data = target_card_row["Structure Image"] if "Structure Image" in target_card_row else ""
            has_image = pd.notna(current_img_data) and str(current_img_data).strip() != ""
            
            clear_image = False
            if has_image:
                st.markdown("**Current Molecular Image Preview:**")
                st.markdown(
                    f"""
                    <div class="formula-image-container" style="margin-top: 5px; max-width: 150px;">
                        <img class="formula-image" src="{current_img_data}" style="max-height: 100px;" />
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                clear_image = st.checkbox("🗑️ Remove image from this card entirely", value=False)
            
            save_edits_button = st.form_submit_button("Save Updates")
            
            if save_edits_button:
                # Get the precise row index of our card inside the dataframe
                idx = st.session_state.flashcards_df[st.session_state.flashcards_df[ID] == selected_card_id].index[0]
                
                # 1. Update text variables using robust .at coordinate lookup
                st.session_state.flashcards_df.at[idx, QUESTION] = edit_question
                st.session_state.flashcards_df.at[idx, ANSWER] = edit_answer
                st.session_state.flashcards_df.at[idx, TAGS] = edit_tags_selected
                
                # 2. Update Image Payload
                if edit_uploaded_image is not None:
                    try:
                        file_bytes = edit_uploaded_image.getvalue()
                        mime_type = edit_uploaded_image.type
                        b64_data = base64.b64encode(file_bytes).decode("utf-8")
                        new_encoded_img = f"data:{mime_type};base64,{b64_data}"
                        st.session_state.flashcards_df.at[idx, "Structure Image"] = new_encoded_img
                    except Exception as err:
                        st.error(f"Image processing failed: {err}")
                elif clear_image:
                    st.session_state.flashcards_df.at[idx, "Structure Image"] = ""
                
                # Force Save and Refresh
                save_flashcards(st.session_state.flashcards_df)
                st.toast("Card successfully updated!", icon="✏️")
                st.rerun()

        # Dynamic Deletion Action
        st.markdown("---")
        st.markdown("⚠️ **Danger Zone**")
        if st.button("🗑️ Delete This Card Permanently", use_container_width=True, key="delete_card_btn"):
            # Drop row, re-index rest of the IDs, save to local csv storage, then refresh
            df_dropped = st.session_state.flashcards_df[st.session_state.flashcards_df[ID] != selected_card_id]
            df_dropped[ID] = range(1, len(df_dropped) + 1) # re-index ids
            st.session_state.flashcards_df = df_dropped
            save_flashcards(st.session_state.flashcards_df)
            st.toast("Card permanently deleted from database.", icon="🗑️")
            st.rerun()


# TAB 4: NON-TARGET KEYWORD SEARCH
with tab4:
    text_search = st.text_input("Enter Search Terms (e.g. AFFF, precursor, ECF):", value="")
    if text_search:
        search(text_search, filtered_df)()


# TAB 5: METADATA SHEET VIEWER & EXPORT
with tab5:
    show_all = st.checkbox("Show Entire Active Deck List", value=True)
    if show_all:
        view_flashcards(filtered_df)
    elif selected_tags:
        try:
            filtered_by_tags = filtered_df[
                filtered_df[TAGS].apply(
                    lambda x: any(tag in x for tag in selected_tags)
                )
            ]
            view_flashcards(filtered_by_tags)
        except KeyError:
            st.warning("No records matched your specific selections.")