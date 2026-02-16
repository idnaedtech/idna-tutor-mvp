"""
IDNA EdTech v7.0 — Seed Questions
Class 8 NCERT Math Chapter 1: Rational Numbers
"""

QUESTIONS = [
    # ─── Fraction Addition ──────────────────────────────────────────────────────
    {
        "id": "ch1_q1",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is -3/9 + (-2/9)?",
        "question_voice": "Minus 3 by 9 plus minus 2 by 9 ka answer kya hai?",
        "answer": "-5/9",
        "answer_variants": ["-5/9", "minus 5/9", "minus 5 by 9", "-5 by 9"],
        "key_concepts": ["fraction_addition", "same_denominator", "negative_numbers"],
        "eval_method": "exact",
        "hints": [
            "Same denominator hai, toh sirf numerators ko add karo",
            "Minus 3 plus minus 2 kitna hota hai?",
        ],
        "solution": "Denominator same hai (9), toh numerators add karo: -3 + (-2) = -5. Answer: -5/9",
        "target_skill": "fraction_addition_same_denom",
        "difficulty": 1,
    },
    {
        "id": "ch1_q2",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is 2/7 + 3/7?",
        "question_voice": "2 by 7 plus 3 by 7 ka answer kya hai?",
        "answer": "5/7",
        "answer_variants": ["5/7", "5 by 7"],
        "key_concepts": ["fraction_addition", "same_denominator"],
        "eval_method": "exact",
        "hints": [
            "Same denominator hai, sirf numerators add karo",
            "2 plus 3 kitna hota hai?",
        ],
        "solution": "2/7 + 3/7 = (2+3)/7 = 5/7",
        "target_skill": "fraction_addition_same_denom",
        "difficulty": 1,
    },
    {
        "id": "ch1_q3",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is 1/2 + 1/4?",
        "question_voice": "1 by 2 plus 1 by 4 ka answer kya hai?",
        "answer": "3/4",
        "answer_variants": ["3/4", "3 by 4"],
        "key_concepts": ["fraction_addition", "different_denominator", "LCM"],
        "eval_method": "exact",
        "hints": [
            "Denominators alag hain, pehle LCM nikalo",
            "1/2 = 2/4 ho jaata hai, ab add karo",
        ],
        "solution": "1/2 = 2/4 (multiply top and bottom by 2). 2/4 + 1/4 = 3/4",
        "target_skill": "fraction_addition_diff_denom",
        "difficulty": 2,
    },

    # ─── Fraction Subtraction ───────────────────────────────────────────────────
    {
        "id": "ch1_q4",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is 5/8 - 3/8?",
        "question_voice": "5 by 8 minus 3 by 8 ka answer kya hai?",
        "answer": "2/8",
        "answer_variants": ["2/8", "1/4", "2 by 8", "1 by 4"],
        "key_concepts": ["fraction_subtraction", "same_denominator"],
        "eval_method": "exact",
        "hints": [
            "Same denominator hai, sirf numerators subtract karo",
            "5 minus 3 kitna hota hai?",
        ],
        "solution": "5/8 - 3/8 = (5-3)/8 = 2/8 = 1/4",
        "target_skill": "fraction_subtraction_same_denom",
        "difficulty": 1,
    },
    {
        "id": "ch1_q5",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is -1/3 - 1/3?",
        "question_voice": "Minus 1 by 3 minus 1 by 3 ka answer kya hai?",
        "answer": "-2/3",
        "answer_variants": ["-2/3", "minus 2/3", "minus 2 by 3", "-2 by 3"],
        "key_concepts": ["fraction_subtraction", "negative_numbers"],
        "eval_method": "exact",
        "hints": [
            "Same denominator hai, numerators subtract karo",
            "-1 - 1 = -2",
        ],
        "solution": "-1/3 - 1/3 = (-1-1)/3 = -2/3",
        "target_skill": "fraction_subtraction_same_denom",
        "difficulty": 2,
    },

    # ─── Fraction Multiplication ────────────────────────────────────────────────
    {
        "id": "ch1_q6",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is 2/3 × 3/4?",
        "question_voice": "2 by 3 into 3 by 4 ka answer kya hai?",
        "answer": "1/2",
        "answer_variants": ["1/2", "6/12", "1 by 2", "half", "aadha"],
        "key_concepts": ["fraction_multiplication"],
        "eval_method": "exact",
        "hints": [
            "Numerators ko multiply karo, denominators ko multiply karo",
            "2×3 = 6, 3×4 = 12, simplify karo",
        ],
        "solution": "2/3 × 3/4 = (2×3)/(3×4) = 6/12 = 1/2",
        "target_skill": "fraction_multiplication",
        "difficulty": 2,
    },

    # ─── Fraction Division ──────────────────────────────────────────────────────
    {
        "id": "ch1_q7",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "direct",
        "question_text": "What is 2/3 ÷ 1/2?",
        "question_voice": "2 by 3 divided by 1 by 2 ka answer kya hai?",
        "answer": "4/3",
        "answer_variants": ["4/3", "4 by 3", "1 1/3"],
        "key_concepts": ["fraction_division", "reciprocal"],
        "eval_method": "exact",
        "hints": [
            "Divide karne ke liye, reciprocal se multiply karo",
            "1/2 ka reciprocal 2/1 hai",
        ],
        "solution": "2/3 ÷ 1/2 = 2/3 × 2/1 = 4/3",
        "target_skill": "fraction_division",
        "difficulty": 3,
    },

    # ─── Number Line ────────────────────────────────────────────────────────────
    {
        "id": "ch1_q8",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "conceptual",
        "question_text": "Between which two integers does -3/4 lie on the number line?",
        "question_voice": "Number line pe minus 3 by 4 kaunse do integers ke beech mein hai?",
        "answer": "-1 and 0",
        "answer_variants": ["-1 and 0", "minus 1 aur 0", "0 and -1", "-1, 0"],
        "key_concepts": ["number_line", "negative_fractions"],
        "eval_method": "exact",
        "hints": [
            "-3/4 negative hai, toh 0 se left mein hoga",
            "-3/4 ka value -0.75 hai, yeh -1 aur 0 ke beech hai",
        ],
        "solution": "-3/4 = -0.75, jo -1 aur 0 ke beech mein hai",
        "target_skill": "number_line_rational",
        "difficulty": 2,
    },

    # ─── Properties ─────────────────────────────────────────────────────────────
    {
        "id": "ch1_q9",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "conceptual",
        "question_text": "What property says a + b = b + a?",
        "question_voice": "A plus B equals B plus A — isko kaunsi property kehte hain?",
        "answer": "commutative",
        "answer_variants": ["commutative", "commutative property", "kramvinimey"],
        "key_concepts": ["commutative_property", "addition"],
        "eval_method": "exact",
        "hints": [
            "Yeh property kehti hai ki order change karne se answer nahi badalta",
            "Hint: 'comm' matlab exchange, swap",
        ],
        "solution": "a + b = b + a is the Commutative Property of Addition",
        "target_skill": "properties_rational",
        "difficulty": 1,
    },
    {
        "id": "ch1_q10",
        "subject": "math",
        "chapter": "ch1_rational_numbers",
        "class_level": 8,
        "question_type": "conceptual",
        "question_text": "How many rational numbers are between 0 and 1?",
        "question_voice": "0 aur 1 ke beech kitne rational numbers hain?",
        "answer": "infinite",
        "answer_variants": ["infinite", "infinitely many", "anant", "countless", "∞"],
        "key_concepts": ["dense_property", "rational_numbers"],
        "eval_method": "exact",
        "hints": [
            "Socho: 1/2 hai, 1/4 hai, 1/8 hai...",
            "Kya hum stop kar sakte hain? Ya hamesha ek aur number mil jaata hai?",
        ],
        "solution": "Do kisi bhi do rational numbers ke beech hamesha anant (infinite) rational numbers hote hain. Isko dense property kehte hain.",
        "target_skill": "dense_property",
        "difficulty": 2,
    },
]


# Teaching content per skill (used for re-teaching)
SKILL_TEACHING = {
    "fraction_addition_same_denom": {
        "name": "Fraction Addition (Same Denominator)",
        "teaching": (
            "Jab denominators same hon, sirf numerators ko add karo. "
            "Jaise 2/5 + 1/5 = 3/5. Denominator same rehta hai."
        ),
    },
    "fraction_addition_diff_denom": {
        "name": "Fraction Addition (Different Denominator)",
        "teaching": (
            "Pehle LCM nikalo, phir dono fractions ko same denominator mein convert karo. "
            "Jaise 1/2 + 1/3: LCM=6, toh 3/6 + 2/6 = 5/6."
        ),
    },
    "fraction_subtraction_same_denom": {
        "name": "Fraction Subtraction (Same Denominator)",
        "teaching": (
            "Same denominator mein subtract karna easy hai — sirf numerators subtract karo. "
            "Jaise 5/7 - 2/7 = 3/7."
        ),
    },
    "fraction_multiplication": {
        "name": "Fraction Multiplication",
        "teaching": (
            "Numerator ko numerator se, denominator ko denominator se multiply karo. "
            "Jaise 2/3 × 4/5 = 8/15. Simple!"
        ),
    },
    "fraction_division": {
        "name": "Fraction Division",
        "teaching": (
            "Divide karne ke liye reciprocal se multiply karo. "
            "a/b ÷ c/d = a/b × d/c. "
            "Jaise 1/2 ÷ 1/4 = 1/2 × 4/1 = 2."
        ),
    },
    "number_line_rational": {
        "name": "Number Line with Rational Numbers",
        "teaching": (
            "Number line pe left = negative, right = positive. "
            "Fraction ko decimal mein badlo — jaise -3/4 = -0.75. "
            "Do rational numbers ke beech HAMESHA anant (infinite) numbers hote hain."
        ),
    },
    "properties_rational": {
        "name": "Properties of Rational Numbers",
        "teaching": (
            "Commutative: a+b = b+a (order change karo, same answer). "
            "Associative: (a+b)+c = a+(b+c) (grouping change karo, same answer). "
            "Distributive: a×(b+c) = a×b + a×c."
        ),
    },
    "dense_property": {
        "name": "Dense Property of Rational Numbers",
        "teaching": (
            "Do kisi bhi rational numbers ke beech hamesha infinite rational numbers hote hain. "
            "Isko dense property kehte hain. Matlab: kabhi khatam nahi hote!"
        ),
    },
}
