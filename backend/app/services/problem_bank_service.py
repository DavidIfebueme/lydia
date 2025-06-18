import random
import hashlib
from typing import Dict, List, Optional

class ProblemBank:
    """Service for managing problem inventory"""
    
    def __init__(self):

        self._problems = [
            {
                "id": 1,
                "question": "I'm thinking of a 4-digit number. When divided by 4, the remainder is 1. When divided by 5, the remainder is 2. When divided by 6, the remainder is 3. What is the smallest positive integer that satisfies these conditions?",
                "difficulty": "medium",
                "category": "math",
                "hint": "Use the Chinese remainder theorem or try numbers that give remainder 3 when divided by 6."
            },
            {
                "id": 2,
                "question": "A bartender has two empty barrels: one with a capacity of 5 gallons and one with a capacity of 3 gallons. How can the bartender measure exactly 4 gallons of water using only these two barrels?",
                "difficulty": "medium",
                "category": "logic",
                "hint": "Think about filling one barrel and pouring it into another."
            },
            {
                "id": 3,
                "question": "Decode this message: '20-8-5 6-9-18-19-20 12-5-20-20-5-18 15-6 5-1-3-8 23-15-18-4 9-14 20-8-9-19 13-5-19-19-1-7-5'",
                "difficulty": "medium",
                "category": "cryptography",
                "hint": "Each number represents a letter's position in the alphabet (A=1, B=2, etc.)"
            },
            {
                "id": 4,
                "question": "Calculate: What is the sum of all integers from 1 to 500 that are divisible by either 3 or 5?",
                "difficulty": "medium",
                "category": "math",
                "hint": "Use the formula for arithmetic series, but be careful not to double-count numbers divisible by both 3 and 5."
            },
            {
                "id": 5,
                "question": "In a certain country, 5% of all men wear hats. If someone wears a hat, the probability that they are male is 80%. What percentage of the population is female?",
                "difficulty": "hard",
                "category": "logic",
                "hint": "Use Bayes' theorem and let variables represent the different probabilities."
            },
            {
                "id": 6,
                "question": "What is the next number in this sequence: 1, 11, 21, 1211, 111221, ?",
                "difficulty": "medium", 
                "category": "pattern",
                "hint": "Read each number aloud, describing what you see."
            },
            {
                "id": 7,
                "question": "A ball is thrown upward at 20 m/s from a height of 10 meters. How long will it take to hit the ground? (Use g = 10 m/s²)",
                "difficulty": "hard",
                "category": "physics",
                "hint": "Use the formula h = h₀ + v₀t - (1/2)gt²"
            },
            {
                "id": 8,
                "question": "Find the 10-letter word: It can be typed using only the top row of a standard QWERTY keyboard.",
                "difficulty": "medium",
                "category": "wordplay",
                "hint": "Think of words that only use the letters Q,W,E,R,T,Y,U,I,O,P."
            }
        ]
        
        self._answer_hashes = {
            1: "b1ab1e3bd78c793d8c957596e78d8a73b0a5abe4815326bb520d9517d186d395", 
            2: "b92b8a4a1de17d1b383a9a72e2ca36a9d1e9ed1b5c6b14d5444e1ea30f8d3e0c", 
            3: "df1c17594e0ddc0b85c4389955985f2c108a4b2a30958312fdce974ab6d6c178",
            4: "e57ef38d93979e4401d8c8218bd5a42fc32645a73b49992683ab1b93b9e0e789", 
            5: "a44ffb7501e11fee25fbe8ebf5fcaa185ea32c7b4d3d0fbe63894322eb68bbd7", 
            6: "2ea1cfbe242bd0fffb4c03adcfacd83cdc2c33664e4a5835ae77907cd82173ce", 
            7: "72d14c6862f62d9065122c46a6bdc870dfe24ab6fb3c9fa95e331c939d33de42", 
            8: "608a36374d74a42eae602f20fee0e45e89f1e69b3c3ae60217a77ce2ce5c203f" 
        }
    
    def get_random_problem(self) -> Dict:
        """Get a random problem from the bank (without answer)"""
        problem = random.choice(self._problems)
        return {k: v for k, v in problem.items() if k != "answer"}
    
    def verify_answer(self, problem_id: str, answer: str) -> bool:
        """Verify if the provided answer is correct"""
        if problem_id not in self._answer_hashes:
            return False
            
        normalized_answer = answer.lower().strip()
        
        answer_hash = hashlib.sha256(normalized_answer.encode('utf-8')).hexdigest()

        return answer_hash == self._answer_hashes[problem_id]
    
    def get_categories(self) -> List[str]:
        """Get a list of all problem categories"""
        return sorted(list({p["category"] for p in self._problems}))
    
    def get_problem_by_id(self, problem_id: str) -> Optional[Dict]:
        """Get a specific problem by ID"""
        for problem in self._problems:
            if problem["id"] == problem_id:
                return {k: v for k, v in problem.items() if k != "answer"}
        return None

problem_bank = ProblemBank()