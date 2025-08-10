def handle_similarity_query(query: str, chroma_collection):
    # Extract card name
    card_name = extract_card_name(query)  # "Rhystic Study"
    
    if card_name:
        # Get the specific card's embedding
        card_result = chroma_collection.query(
            query_texts=[card_name],
            n_results=1
        )
        
        if card_result['ids'][0]:
            # Use that card's text for similarity
            card_text = card_result['documents'][0][0]
            
            # Multi-angle similarity search
            similarity_searches = [
                f"cards with similar mechanics to {card_text}",
                f"cards that work like {card_name}",
                f"functional reprints of {card_name}",
                card_text  # Direct text similarity
            ]
            
            results = []
            for search_text in similarity_searches:
                result = chroma_collection.query(
                    query_texts=[search_text],
                    n_results=8
                )
                results.extend(result['ids'][0])
            
            # Deduplicate and return
            return list(dict.fromkeys(results))[:10]
    
    # Fallback to expanded search
    return enhanced_search(query, chroma_collection, query_expander)