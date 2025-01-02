# search.py
import re
import math

class SearchEngine:
    @staticmethod
    def prepare_query(query):
        terms = query.split()
        patterns = []
        
        for term in terms:
            if term.isdigit() and len(term) == 4:
                patterns.append(f'.*{term}.*')
            else:
                escaped_term = re.escape(term)
                patterns.append(f'.*{escaped_term}.*')
        
        final_pattern = ''.join(f'(?=.*{p})' for p in patterns)
        return f'^{final_pattern}.*$' if final_pattern else '.*'