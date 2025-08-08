# THIS MODULE WILL FUNCTION AS A REPOSITORY FOR VARIOUS SEARCH FUNCTIONS & ROUTING

# IF A CARD NAME, RETRIEVE THE CARD NAME AND ITS DATA FROM THE WAREHOUSE
# THEN SEARCH VECTOR DB BASED ON CARD TEXT AND RANK
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# can delete this after development
from dotenv import load_dotenv
load_dotenv()

from src.db.utils import get_vector_store

vectordb = get_vector_store()

#vectordb.as_retriever(
#        search_kwargs={'filter': {'paper_title':'GPT-4 Technical Report'}}
#    )

name = 'chatterfang'
a = vectordb.get(where={'name': name})
vectordb.get
print(a)