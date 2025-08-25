import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from rapidfuzz import fuzz, process

# can delete this after development
from dotenv import load_dotenv
load_dotenv()

from src.db.vectorstore import get_vector_store

OUTPUT_FIELDS = ['cardName', 'faceName', 'type', 'manaCost', 'manaValue', 'colorIdentity', 'text', 'power', 'toughness', 'side', 'layout', 'legalities.commander']
HEADER = '|'.join(OUTPUT_FIELDS) + '\n'

vectordb = get_vector_store()

def normalize(metadata, fields=OUTPUT_FIELDS, just_values=False):
    output = {}
    for field in fields:
        output[field] = metadata.get(field, "")
        if type(output[field]) == str:
            output[field] = output[field].replace('\n', '\t')
    return [v for v in output.values()] if just_values else output


def retrieve_by_text(
    user_input: str, 
    K: int = 50, 
    output_fields: list = OUTPUT_FIELDS, 
    ) -> str:
    
    results = vectordb.similarity_search_with_score(
        query=user_input, 
        k=K, 
    )
    
    # normalize results
    normalized_results = [normalize(result[0].metadata, fields=output_fields, just_values=True) for result in results]
    
    # filter for results & merge metadata 
    return normalized_results # '\n'.join(['|'.join([str(r) for r in result]) for result in normalized_results])


def retrieve_by_name(
        card_name, 
        output_fields: list = OUTPUT_FIELDS,
        k=3,
        rerank=False
    ):
    
    results = vectordb.similarity_search_with_score(
        query=card_name,  # Empty string, since we're not doing semantic search
        k=k,
    )
    
    # normalize results
    normalized_results = [normalize(result[0].metadata, fields=output_fields) for result in results]
    scores = [result[-1] for result in results]
    
    card_name_lower = card_name.lower()

    def hybrid_score(card):
        # exact match boost
        exact_match = 10 if card_name_lower in card['name'].lower() else 0
        # fuzz ratio on full combined name
        name_score = fuzz.ratio(card_name_lower, card['name'].lower())
        # fuzz ratio on face name (exact face)
        face_name_score = fuzz.ratio(card_name_lower, card['faceName'].lower())
        # Weighted average or max - you can tweak weights here
        legality_score = 10 if card['legalities.commander'] == 'Legal' else 0 
        return (face_name_score * 0.4) + (name_score * 0.2) + legality_score

    # hybrid name score based on best match
    best_match = max((normalized_results), key=hybrid_score) if rerank else normalized_results[0]
    return best_match # '|'.join([v for v in best_match.values()]) 



if __name__ == "__main__":
    # test it
    names = ['Rhystic Study', 'Delver of Secrets', 'Chatterfang']
    for n in names:
        a = retrieve_by_name(n, rerank=False)
        print(len(a))
        print(a, '\n')