FLASHCARDS_CSV = "flashcards.csv"
EXCEL_FILE = "EPA_1633A_PFAS_Learning_Database_v1 (1).xlsx"

# Standardized Core System Columns
ID = "id"
QUESTION = "question"
ANSWER = "answer"
DATE_ADDED = "date_added"
NEXT_APPEARANCE = "next_appearance"
TAGS = "tags"
STRUCTURE_IMAGE = "structure_image"

SYSTEM_COLUMNS = [ID, QUESTION, ANSWER, DATE_ADDED, NEXT_APPEARANCE, TAGS, STRUCTURE_IMAGE]
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