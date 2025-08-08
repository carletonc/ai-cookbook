import openai
from typing import List, Dict

SYSTEM_PROMPT = F"""
Analyze this Magic: The Gathering search query: "{original_query}"
        
Return a JSON with:
1. "keywords": List of exact Magic terms to search for
2. "concepts": List of broader concepts/mechanics
3. "card_types": Relevant card types
4. "synonyms": Alternative phrasings

Example for "cards that make zombies stronger":
{{
    "keywords": ["zombie", "+1/+1", "anthem", "lord"],
    "concepts": ["tribal synergy", "creature buffs", "zombie tribal"],
    "card_types": ["creature", "enchantment", "instant", "sorcery"],
    "synonyms": ["zombie lord", "zombie anthem", "undead tribal"]
}}
"""


class MagicQueryExpander:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def expand_query(self, original_query: str) -> Dict:
        response = self.llm.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": SYSTEM_PROMPT}],
            temperature=0.1
        )
        return json.loads(response.choices[0].message.content)



# Enhanced retrieval
def enhanced_search(query: str, chroma_collection, query_expander):
    # 1. Expand the query
    expanded = query_expander.expand_query(query)
    
    # 2. Multiple retrieval strategies
    results = {}
    
    # Original semantic search
    results['semantic'] = chroma_collection.query(
        query_texts=[query],
        n_results=20
    )
    
    # Keyword-focused searches
    for keyword in expanded['keywords'][:3]:  # Top 3 keywords
        results[f'keyword_{keyword}'] = chroma_collection.query(
            query_texts=[keyword],
            n_results=10
        )
    
    # Concept searches
    for concept in expanded['concepts'][:2]:
        results[f'concept_{concept}'] = chroma_collection.query(
            query_texts=[concept],
            n_results=10
        )
    
    # 3. Merge and deduplicate
    all_ids = set()
    merged_results = []
    
    for search_type, result in results.items():
        weight = get_weight(search_type)  # semantic=0.4, keywords=0.3, concepts=0.3
        
        for i, card_id in enumerate(result['ids'][0]):
            if card_id not in all_ids:
                score = (1.0 / (i + 1)) * weight  # Reciprocal rank with weight
                merged_results.append({
                    'id': card_id,
                    'score': score,
                    'source': search_type
                })
                all_ids.add(card_id)
    
    # 4. Re-rank by combined score
    merged_results.sort(key=lambda x: x['score'], reverse=True)
    
    return merged_results[:10]



def get_weight(search_type: str) -> float:
    weights = {
        'semantic': 0.4,
        'keyword': 0.3,
        'concept': 0.3
    }
    for key in weights:
        if search_type.startswith(key):
            return weights[key]
    return 0.1


# FOR "CARDS SIMILAR TO" FUNCTIONALITY
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