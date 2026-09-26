from auth import GoogleAuthManager
from docs_parser import DocsParser

def main():
    auth_mgr = GoogleAuthManager()
    docs = auth_mgr.build_docs_service()
    parser = DocsParser(docs_service=docs)

    doc_id = "1ad8rSq1aPGR4Cf9KlYp-Cz2x1G87y20TYZ1zN65Vo8o"  # Korean 7th grade
    doc_data = parser.get_document_content(doc_id)
    print(f"Title: {doc_data.get('title')}")
    rows = parser.extract_table_rows(doc_data)
    print(f"Extracted Table Rows: {len(rows)}")
    for i, r in enumerate(rows[:5]):
        print(f"Row {i}: {r}")

if __name__ == "__main__":
    main()
