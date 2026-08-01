"""
Demo: search_knowledge_base answering a question the structured tools
(get_account_summary, list_support_tickets, get_equipment_diagnostics)
cannot answer, because the answer is engineering *procedure*, not a
row in a database table.
"""

from tool import handle_search_knowledge_base

if __name__ == "__main__":
    print("=== Demo query: agent sees ERR-204 in equipment diagnostics ===")
    print("Query: 'ERR-204 modem keeps failing PPPoE authentication'\n")
    result = handle_search_knowledge_base(
        query="ERR-204 modem keeps failing PPPoE authentication",
        top_k=3,
        session_role="any",
    )
    print(result)

    print("\n\n=== Demo query: is this an RMA-eligible failure? ===")
    print("Query: 'equipment marked FAILED, water damage, can we RMA it'\n")
    result = handle_search_knowledge_base(
        query="equipment marked FAILED water damage RMA eligible",
        top_k=2,
        session_role="any",
    )
    print(result)

    print("\n\n=== Control: query with no real keyword overlap in the KB ===")
    print("Query: 'karaoke night signup sheet'\n")
    result = handle_search_knowledge_base(
        query="karaoke night signup sheet",
        top_k=2,
        session_role="any",
    )
    print(result)

