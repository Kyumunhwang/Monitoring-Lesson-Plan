import json
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

    out = {}
    for label, d_id in doc_ids:
        doc_data = parser.get_document_content(d_id)
        # Check all tables in the document!
        body = doc_data.get("body", {})
        content = body.get("content", [])
        tables = []
        for el in content:
            if "table" in el:
                t_rows = []
                for row in el["table"].get("tableRows", []):
                    r_cells = []
                    for cell in row.get("tableCells", []):
                        parts = []
                        for cp in cell.get("content", []):
                            if "paragraph" in cp:
                                for pe in cp["paragraph"].get("elements", []):
                                    if "textRun" in pe:
                                        parts.append(pe["textRun"].get("content", ""))
                        r_cells.append("".join(parts).strip())
                    t_rows.append(r_cells)
                tables.append(t_rows)
        out[label] = {
            "title": doc_data.get("title"),
            "table_count": len(tables),
            "tables": tables
        }

    with open("doc_dump.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print("Dumped structure to doc_dump.json successfully")

if __name__ == "__main__":
    main()
