from auth import GoogleAuthManager
from docs_parser import DocsParser

def main():
    auth_mgr = GoogleAuthManager()
    docs = auth_mgr.build_docs_service()
    parser = DocsParser(docs_service=docs)

    doc_ids = [
        ("Korean 7th", "1ad8rSq1aPGR4Cf9KlYp-Cz2x1G87y20TYZ1zN65Vo8o"),
        ("History 9th", "1OqVeo9FUPILpjfkET2gSY9UxPntBMupwX0bbujs2kbU"),
        ("Science 6th", "1FRkQyxtuCLZ1vcenMtVUgtLIkcItPUpzDfPdbUCICT4"),
    ]

    for label, d_id in doc_ids:
        print(f"\n==================== {label} ====================")
        doc_data = parser.get_document_content(d_id)
        rows = parser.extract_table_rows(doc_data)
        print(f"Total Rows: {len(rows)}")
        for idx, r in enumerate(rows):
            print(f"Row {idx:02d}: {[c[:40] for c in r if c.strip()]}")

if __name__ == "__main__":
    main()
