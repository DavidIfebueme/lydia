import random
from typing import Dict, List, Optional

class ProblemBank:
    """Service for managing problem inventory"""
    
    def get_random_problem(self) -> Dict:
        """Get a random problem from the bank"""
        all_problems = [
            {
                "question": "What comes next in this sequence: 1, 1, 2, 3, 5, 8, 13, ?",
                "answer": "21"
            },
            {
                "question": "If 2+3=10, 7+2=63, 6+5=66, then 8+4=?",
                "answer": "96"
            },
            {
                "question": "I have branches but no fruit, trunk but no luggage, bark but no dog. What am I?",
                "answer": "tree"
            },
            {
                "question": "What has keys but no locks, space but no room, and you can enter but not go inside?",
                "answer": "keyboard"
            },
            {
                "question": "What 5-letter word becomes shorter when you add two letters to it?",
                "answer": "short"
            },
            {
                "question": "The more you take away from me, the bigger I become. What am I?",
                "answer": "hole"
            },
            {
                "question": "What can travel around the world while staying in a corner?",
                "answer": "stamp"
            },
            {
                "question": "If you count from 1 to 100, how many 7's will you pass on the way?",
                "answer": "20"
            }
        ]
        
        return random.choice(all_problems)

problem_bank = ProblemBank()