"""
IDNA EdTech — Chapter 1: A Square and A Cube
NCERT Ganita Prakash, Class 8 Mathematics (New Syllabus 2025)

Complete question bank, skill lessons, answer checking rules,
hints, common mistakes, and teaching scripts.

Version: 7.0.1
Chapter mapping: ch1_square_and_cube
Total questions: 50
Difficulty split: 18 Easy, 18 Medium, 14 Hard
Skills covered: 14 distinct skills

Usage:
    from ch1_square_and_cube import QUESTIONS, SKILL_LESSONS, CHAPTER_META
"""

# ============================================================
# CHAPTER METADATA
# ============================================================

CHAPTER_META = {
    "id": "ch1_square_and_cube",
    "title": "A Square and A Cube",
    "title_hi": "Varg aur Ghan",
    "ncert_book": "Ganita Prakash",
    "class": 8,
    "topics": [
        "perfect_squares",
        "properties_of_squares",
        "square_roots",
        "perfect_cubes",
        "properties_of_cubes",
        "cube_roots",
    ],
    "teaching_order": [
        "perfect_square_concept",
        "square_factor_pairs",
        "squares_table_1_to_30",
        "square_units_digit",
        "square_zeros_parity",
        "square_odd_pattern",
        "triangular_square_relation",
        "square_root_concept",
        "sqrt_prime_factorisation",
        "sqrt_estimation",
        "perfect_cube_concept",
        "cubes_table_1_to_20",
        "cube_units_digit",
        "taxicab_ramanujan",
        "cube_odd_pattern",
        "cube_root_concept",
        "cbrt_prime_factorisation",
        "make_perfect_square",
        "make_perfect_cube",
        "successive_differences",
    ],
    "pre_reqs": [
        "Multiplication tables up to 20",
        "Factors and multiples (Class 6)",
        "Prime factorisation (Class 6-7)",
        "3D shapes basics (Class 7)",
    ],
    "story_hook": (
        "Ek rani thi — Queen Ratnamanjuri. Usne apni will mein ek puzzle "
        "rakha. 100 lockers hain, 100 log hain. Har insaan apne number ke "
        "multiples wale lockers toggle karta hai. Aakhir mein kaunse lockers "
        "khule rahenge? Yeh puzzle solve karne ke liye humein perfect squares "
        "samajhne honge!"
    ),
}


# ============================================================
# SKILL LESSONS — Teaching content for each skill
# ============================================================

SKILL_LESSONS = {

    # --- SQUARES ---

    "perfect_square_concept": {
        "skill": "perfect_square_concept",
        "title": "What is a Perfect Square?",
        "title_hi": "Perfect Square kya hota hai?",
        "pre_teach": (
            "Dekhiye, jab hum ek number ko khud se multiply karte hain, "
            "toh jo answer aata hai woh perfect square kehlata hai. "
            "Jaise 3 times 3 = 9. Toh 9 ek perfect square hai. "
            "Isko hum 3 ka square ya 3 squared bolte hain."
        ),
        "indian_example": (
            "Sochiye aapke ghar mein square tiles lagi hain. Ek taraf 4 tiles, "
            "doosri taraf bhi 4 tiles. Total kitni tiles? 4 times 4 = 16! "
            "Toh 16 ek perfect square hai kyunki 4 × 4 = 16."
        ),
        "key_insight": (
            "Perfect squares ke factors ki sankhya odd hoti hai. Kyunki ek "
            "factor apne aap se pair banata hai. Jaise 9 ke factors: 1, 3, 9. "
            "Teen factors — odd number!"
        ),
        "locker_puzzle_connection": (
            "Isliye locker puzzle mein sirf square number wale lockers khule "
            "rehte hain — 1, 4, 9, 16, 25, 36, 49, 64, 81, 100. "
            "Kyunki inke factors odd hain, toh odd baar toggle hone se "
            "yeh open rehte hain!"
        ),
        "common_errors": [
            "Student thinks all even numbers are perfect squares",
            "Student confuses 'square of 3' (=9) with '3 squared' (=9) — same thing but confusing terminology",
            "Student thinks 0 is not a perfect square (it is: 0 = 0×0)",
        ],
    },

    "square_factor_pairs": {
        "skill": "square_factor_pairs",
        "title": "Factor Pairs and Odd Factors",
        "title_hi": "Factor ke jode aur odd factors",
        "pre_teach": (
            "Har number ke factors pairs mein aate hain. Jaise 6 ke factors: "
            "1 aur 6 ek pair, 2 aur 3 doosra pair. Total 4 factors — even. "
            "Par 4 ke factors dekhiye: 1 aur 4 ek pair, 2 aur 2 doosra pair. "
            "Par 2 aur 2 same hain! Toh unique factors: 1, 2, 4. Teen — odd!"
        ),
        "key_insight": (
            "Perfect squares mein ek factor apne aap se pair banata hai. "
            "Isliye total factors odd hote hain. Aur isliye locker puzzle "
            "mein sirf square lockers open rehte hain."
        ),
        "common_errors": [
            "Student forgets to count the repeated factor only once",
            "Student thinks all numbers have even factors",
        ],
    },

    "squares_table_1_to_30": {
        "skill": "squares_table_1_to_30",
        "title": "Squares of 1 to 30",
        "title_hi": "1 se 30 tak ke squares",
        "pre_teach": (
            "Ab hum 1 se 30 tak ke squares likhenge. Pehle 10 yaad karo: "
            "1, 4, 9, 16, 25, 36, 49, 64, 81, 100. "
            "Ab 11 se 20: 121, 144, 169, 196, 225, 256, 289, 324, 361, 400. "
            "Aur 21 se 30: 441, 484, 529, 576, 625, 676, 729, 784, 841, 900."
        ),
        "tips": (
            "Trick: 11 se 19 tak ke squares ke liye — 11 squared = 121, "
            "12 squared = 144. Pattern dekho: 21, 44, 69, 96, 25, 56, 89, 24, 61. "
            "Last two digits ka apna pattern hai!"
        ),
        "common_errors": [
            "Confusing 15²=225 with 25²=625",
            "Forgetting 20²=400 (students often say 200)",
        ],
    },

    "square_units_digit": {
        "skill": "square_units_digit",
        "title": "Units Digit Pattern of Squares",
        "title_hi": "Squares ke last digit ka pattern",
        "pre_teach": (
            "Dekho pattern: 1 ka square 1, 2 ka 4, 3 ka 9, 4 ka 16, "
            "5 ka 25, 6 ka 36, 7 ka 49, 8 ka 64, 9 ka 81, 10 ka 100. "
            "Last digits: 1, 4, 9, 6, 5, 6, 9, 4, 1, 0. "
            "Sirf 0, 1, 4, 5, 6, 9 aate hain. 2, 3, 7, 8 kabhi nahi!"
        ),
        "rule": (
            "Agar koi number 2, 3, 7, ya 8 pe end hota hai, toh woh "
            "pakka perfect square nahi hai. Par agar 0, 1, 4, 5, 6, 9 pe "
            "end ho, toh ho sakta hai — guarantee nahi. Jaise 26 mein 6 hai "
            "par 26 square nahi hai."
        ),
        "extension": (
            "Aur dekho: agar number 1 ya 9 pe end hota hai, uska square "
            "1 pe end hoga. Agar 4 ya 6 pe end ho, square 6 pe end hoga."
        ),
        "common_errors": [
            "Student assumes number ending in 6 must be a square",
            "Student forgets 0 is a valid last digit for squares",
        ],
    },

    "square_zeros_parity": {
        "skill": "square_zeros_parity",
        "title": "Zeros at End & Odd/Even Property",
        "title_hi": "Squares mein zeros aur odd-even",
        "pre_teach": (
            "10 ka square 100 — ek zero se do zeros. 100 ka square 10000 — "
            "do zeros se chaar zeros. Pattern: number mein kitne zeros hain, "
            "uske square mein double zeros honge. Toh squares mein hamesha "
            "even number of zeros hote hain end mein."
        ),
        "parity_rule": (
            "Aur ek aur rule: even number ka square even hota hai, "
            "odd number ka square odd. Simple!"
        ),
        "common_errors": [
            "Student thinks 40²=800 (wrong: 40²=1600)",
            "Student doesn't realize odd zeros means NOT a square",
        ],
    },

    "square_odd_pattern": {
        "skill": "square_odd_pattern",
        "title": "Sum of Odd Numbers = Perfect Square",
        "title_hi": "Odd numbers ka sum = Perfect Square",
        "pre_teach": (
            "Yeh bahut khoobsurat pattern hai! Dekhiye: "
            "1 = 1, jo 1 ka square hai. "
            "1 + 3 = 4, jo 2 ka square hai. "
            "1 + 3 + 5 = 9, jo 3 ka square hai. "
            "1 + 3 + 5 + 7 = 16, jo 4 ka square hai. "
            "Pehle n odd numbers ka sum = n ka square!"
        ),
        "indian_example": (
            "Rangoli banate waqt sochiye: pehle 1 dot, phir 3 dots ka "
            "L-shape add karo, phir 5 dots ka. Har baar ek bada square "
            "banta jaata hai!"
        ),
        "inverse_test": (
            "Isko ulta bhi use kar sakte hain. Kya 25 perfect square hai? "
            "25 se 1 ghatao = 24, phir 3 = 21, phir 5 = 16, phir 7 = 9, "
            "phir 9 = 0. Zero aaya! Toh 25 perfect square hai, aur 5 baar "
            "subtract kiya toh root 5 hai."
        ),
        "application": (
            "Agar 35 ka square 1225 hai, toh 36 ka square? "
            "36th odd number = 2 times 36 minus 1 = 71. "
            "Toh 36 ka square = 1225 + 71 = 1296!"
        ),
        "common_errors": [
            "Student adds even numbers instead of odd",
            "Student forgets the series starts from 1",
            "Student confuses nth odd number formula: it's 2n-1, not 2n+1",
        ],
    },

    "triangular_square_relation": {
        "skill": "triangular_square_relation",
        "title": "Triangular Numbers and Squares",
        "title_hi": "Triangular numbers aur squares ka rishta",
        "pre_teach": (
            "Triangular numbers yaad hain Class 6 se? 1, 3, 6, 10, 15, 21... "
            "Ab magic dekhiye: do consecutive triangular numbers jodo — "
            "1 + 3 = 4 = 2 ka square. "
            "3 + 6 = 9 = 3 ka square. "
            "6 + 10 = 16 = 4 ka square. "
            "10 + 15 = 25 = 5 ka square. Hamesha square banta hai!"
        ),
        "common_errors": [
            "Student confuses triangular numbers with odd numbers",
        ],
    },

    "square_root_concept": {
        "skill": "square_root_concept",
        "title": "What is a Square Root?",
        "title_hi": "Square root kya hota hai?",
        "pre_teach": (
            "Agar ek square ka area 49 square cm hai, toh uski side kitni? "
            "Hum jaante hain 7 times 7 = 49. Toh side 7 cm hai. "
            "7 ko hum 49 ka square root kehte hain. "
            "Square root matlab: woh number jisko khud se multiply karo "
            "toh original number aaye."
        ),
        "both_roots": (
            "Dhyaan dena: 8 times 8 = 64, aur minus 8 times minus 8 bhi 64. "
            "Toh 64 ke do square roots hain: plus 8 aur minus 8. "
            "Par hum abhi sirf positive root use karenge."
        ),
        "common_errors": [
            "Student confuses square root with half (√64 ≠ 32)",
            "Student thinks only perfect squares have square roots",
        ],
    },

    "sqrt_prime_factorisation": {
        "skill": "sqrt_prime_factorisation",
        "title": "Square Root by Prime Factorisation",
        "title_hi": "Prime factorisation se square root nikalna",
        "pre_teach": (
            "324 ka square root nikalna hai. Pehle prime factors nikalte hain: "
            "324 ÷ 2 = 162. 162 ÷ 2 = 81. 81 ÷ 3 = 27. 27 ÷ 3 = 9. "
            "9 ÷ 3 = 3. 3 ÷ 3 = 1. "
            "Toh 324 = 2 × 2 × 3 × 3 × 3 × 3. "
            "Ab pairs banao: (2 × 3 × 3) × (2 × 3 × 3) = 18 × 18. "
            "Toh square root of 324 = 18!"
        ),
        "checking_if_square": (
            "Agar sab prime factors pairs mein aa jayein, toh number perfect "
            "square hai. Agar koi akela reh jaaye, toh nahi hai. "
            "Jaise 156 = 2 × 2 × 3 × 13. 3 aur 13 akele hain — not a square!"
        ),
        "common_errors": [
            "Student makes error in prime factorisation itself",
            "Student pairs factors incorrectly (pairs across different primes)",
            "Student forgets to multiply one from each pair for the root",
        ],
    },

    "sqrt_estimation": {
        "skill": "sqrt_estimation",
        "title": "Estimating Square Roots",
        "title_hi": "Square root ka andaza lagana",
        "pre_teach": (
            "250 ka square root chahiye. Exact nahi milega kyunki 250 perfect "
            "square nahi hai. Par andaza laga sakte hain! "
            "15 ka square = 225. 16 ka square = 256. "
            "250, 225 aur 256 ke beech hai. Toh root 15 aur 16 ke beech hai. "
            "256 zyada close hai 250 ke, toh lagbhag 16 hoga, par 16 se kam."
        ),
        "method_for_perfect_squares": (
            "1936 ka root nikalna hai. Step 1: 40 ka square 1600, 50 ka 2500. "
            "Toh 40 aur 50 ke beech. Step 2: Last digit 6, toh root 4 ya 6 "
            "pe end hoga — 44 ya 46. Step 3: 45 ka square = 2025 > 1936. "
            "Toh root 40-45 ke beech, matlab 44. Verify: 44 × 44 = 1936!"
        ),
        "common_errors": [
            "Student tries to guess without narrowing the range",
            "Student forgets the units digit trick for narrowing",
        ],
    },

    # --- CUBES ---

    "perfect_cube_concept": {
        "skill": "perfect_cube_concept",
        "title": "What is a Perfect Cube?",
        "title_hi": "Perfect Cube kya hota hai?",
        "pre_teach": (
            "Ab 3D mein sochiye! Jab hum ek number ko teen baar multiply "
            "karte hain, toh perfect cube banta hai. "
            "2 × 2 × 2 = 8. Toh 8 ek perfect cube hai. "
            "Isko 2 ka cube ya 2 cubed kehte hain."
        ),
        "indian_example": (
            "Laddoo ke dabba sochiye! 3 laddoo ek line mein, 3 lines ek "
            "layer mein, 3 layers. Total = 3 × 3 × 3 = 27 laddoos. "
            "27 ek perfect cube hai kyunki 3 × 3 × 3 = 27!"
        ),
        "key_property": (
            "Perfect cube ke prime factorisation mein har prime factor "
            "teen-teen ke groups mein aata hai. Agar koi factor teen ke "
            "group mein nahi aaya, toh woh perfect cube nahi hai."
        ),
        "common_errors": [
            "Student confuses cube (n³) with triple (3n)",
            "Student thinks 9 is a cube (it's not: 2³=8, 3³=27)",
        ],
    },

    "cubes_table_1_to_20": {
        "skill": "cubes_table_1_to_20",
        "title": "Cubes of 1 to 20",
        "title_hi": "1 se 20 tak ke cubes",
        "pre_teach": (
            "Important cubes yaad karo: "
            "1 ka cube 1, 2 ka 8, 3 ka 27, 4 ka 64, 5 ka 125, "
            "6 ka 216, 7 ka 343, 8 ka 512, 9 ka 729, 10 ka 1000. "
            "11 ka 1331, 12 ka 1728, 13 ka 2197, 14 ka 2744, 15 ka 3375, "
            "16 ka 4096, 17 ka 4913, 18 ka 5832, 19 ka 6859, 20 ka 8000."
        ),
        "common_errors": [
            "Confusing 5³=125 with 5²=25",
            "Confusing 12³=1728 with 12²=144",
        ],
    },

    "cube_units_digit": {
        "skill": "cube_units_digit",
        "title": "Units Digit of Cubes",
        "title_hi": "Cubes ke last digit ka pattern",
        "pre_teach": (
            "Squares sirf 0,1,4,5,6,9 pe end hote hain. Par cubes? "
            "Cubes KISI BHI digit pe end ho sakte hain — 0 se 9 tak! "
            "Par ek pattern hai: "
            "1 ka cube 1 pe end, 2 ka 8 pe, 3 ka 7 pe, 4 ka 4 pe, "
            "5 ka 5 pe, 6 ka 6 pe, 7 ka 3 pe, 8 ka 2 pe, 9 ka 9 pe, "
            "10 ka 0 pe. Yeh pattern cube root guess karne mein kaam aata hai!"
        ),
        "cube_zeros": (
            "Aur ek baat: cube mein end ke zeros hamesha 3 ke multiples mein "
            "hote hain. 10 ka cube 1000 — 3 zeros. 100 ka cube 1000000 — 6 zeros. "
            "Toh 2 zeros pe end hone wala number perfect cube nahi ho sakta!"
        ),
        "common_errors": [
            "Student assumes cubes have same digit restrictions as squares",
        ],
    },

    "taxicab_ramanujan": {
        "skill": "taxicab_ramanujan",
        "title": "Taxicab Numbers — Ramanujan's Story",
        "title_hi": "Taxicab Numbers — Ramanujan ki kahani",
        "pre_teach": (
            "Srinivasa Ramanujan — India ke sabse mahaan mathematician! "
            "Ek baar unke dost Hardy hospital mein milne aaye. Hardy ne kaha "
            "meri taxi ka number 1729 tha, boring number hai. Ramanujan turant "
            "bole: Nahi! Yeh bahut special hai! Yeh sabse chhota number hai "
            "jo do cubes ke sum se do alag tarike se ban sakta hai. "
            "1729 = 1 ka cube + 12 ka cube = 1 + 1728. "
            "Aur 1729 = 9 ka cube + 10 ka cube = 729 + 1000. "
            "Ramanujan ke liye har number ek dost tha!"
        ),
        "extension": (
            "Agle taxicab numbers: 4104 = 2 cube + 16 cube = 9 cube + 15 cube. "
            "13832 = 2 cube + 24 cube = 18 cube + 20 cube."
        ),
        "teaching_purpose": "Inspiration, love for numbers. Not tested — shared as a story.",
    },

    "cube_odd_pattern": {
        "skill": "cube_odd_pattern",
        "title": "Cubes and Consecutive Odd Numbers",
        "title_hi": "Cubes aur consecutive odd numbers",
        "pre_teach": (
            "Squares mein odd numbers ka pattern tha. Cubes mein bhi hai! "
            "1 = 1 ka cube. "
            "3 + 5 = 8 = 2 ka cube. "
            "7 + 9 + 11 = 27 = 3 ka cube. "
            "13 + 15 + 17 + 19 = 64 = 4 ka cube. "
            "21 + 23 + 25 + 27 + 29 = 125 = 5 ka cube. "
            "n consecutive odd numbers (sahi jagah se shuru karke) = n ka cube!"
        ),
        "application": (
            "Toh 91 + 93 + 95 + 97 + 99 + 101 + 103 + 105 + 107 + 109 "
            "mein 10 numbers hain. Toh answer = 10 ka cube = 1000!"
        ),
        "common_errors": [
            "Student confuses starting point of odd numbers for each cube",
        ],
    },

    "cube_root_concept": {
        "skill": "cube_root_concept",
        "title": "What is a Cube Root?",
        "title_hi": "Cube root kya hota hai?",
        "pre_teach": (
            "8 = 2 × 2 × 2 = 2 ka cube. Toh 2 ko 8 ka cube root kehte hain. "
            "Symbol hai: cube root sign ke andar 8 likho, answer 2. "
            "Jaise square root mein pair banate the, cube root mein "
            "teen-teen ke groups banate hain."
        ),
        "common_errors": [
            "Student confuses cube root with dividing by 3",
            "Student thinks cube root of 27 is 9 (actually 3)",
        ],
    },

    "cbrt_prime_factorisation": {
        "skill": "cbrt_prime_factorisation",
        "title": "Cube Root by Prime Factorisation",
        "title_hi": "Prime factorisation se cube root nikalna",
        "pre_teach": (
            "3375 ka cube root nikalna hai. Prime factors: "
            "3375 ÷ 3 = 1125. 1125 ÷ 3 = 375. 375 ÷ 3 = 125. "
            "125 ÷ 5 = 25. 25 ÷ 5 = 5. 5 ÷ 5 = 1. "
            "Toh 3375 = 3 × 3 × 3 × 5 × 5 × 5. "
            "Teen-teen ke groups: (3 × 5) × (3 × 5) × (3 × 5) = 15 ka cube. "
            "Cube root of 3375 = 15!"
        ),
        "guessing_trick": (
            "Cube root guess karne ka trick: last digit se pata chalta hai "
            "root ka last digit. 1→1, 8→2, 7→3, 4→4, 5→5, 6→6, 3→7, 2→8, "
            "9→9, 0→0. Phir range narrow karo."
        ),
        "common_errors": [
            "Student groups in pairs instead of triplets",
            "Student confuses the last-digit mapping",
        ],
    },

    "make_perfect_square": {
        "skill": "make_perfect_square",
        "title": "Making a Number a Perfect Square",
        "title_hi": "Number ko perfect square banana",
        "pre_teach": (
            "9408 ko perfect square banana hai. Pehle prime factorize karo: "
            "9408 = 2 × 2 × 2 × 2 × 2 × 2 × 3 × 7 × 7. "
            "Yaani 2 ki power 6 (3 pairs), 7 ki power 2 (1 pair), par 3 akela hai! "
            "Ek aur 3 chahiye. 9408 × 3 = 28224. "
            "28224 = 2 power 6 × 3 squared × 7 squared = (2 cube × 3 × 7) squared "
            "= 168 squared. Square root = 168!"
        ),
        "method": (
            "Step 1: Prime factorize. "
            "Step 2: Jo prime akela hai (pair nahi bana), usse multiply karo. "
            "Step 3: Ab sab pairs mein hain — perfect square ban gaya!"
        ),
        "common_errors": [
            "Student multiplies by the full missing prime instead of completing the pair",
            "Student forgets to find the square root after making it a square",
        ],
    },

    "make_perfect_cube": {
        "skill": "make_perfect_cube",
        "title": "Making a Number a Perfect Cube",
        "title_hi": "Number ko perfect cube banana",
        "pre_teach": (
            "1323 ko perfect cube banana hai. Prime factors: "
            "1323 = 3 × 3 × 3 × 7 × 7. "
            "3 ka triplet complete hai. Par 7 sirf 2 baar hai — ek aur chahiye! "
            "1323 × 7 = 9261. "
            "9261 = 3 cube × 7 cube = 21 cube. Cube root = 21!"
        ),
        "method": (
            "Step 1: Prime factorize. "
            "Step 2: Jo prime ka triplet incomplete hai, utne multiply karo. "
            "Step 3: Ab sab triplets complete — perfect cube ban gaya!"
        ),
        "common_errors": [
            "Student multiplies by 7² instead of 7 (they want 3 total, have 2, need 1 more)",
        ],
    },

    "successive_differences": {
        "skill": "successive_differences",
        "title": "Successive Differences Pattern",
        "title_hi": "Successive differences ka pattern",
        "pre_teach": (
            "Squares ke differences dekho: 4-1=3, 9-4=5, 16-9=7, 25-16=9. "
            "First differences: 3, 5, 7, 9 — odd numbers! "
            "Second differences: 2, 2, 2 — constant! "
            "Do levels mein constant aa gaya. "
            "Cubes ke liye? 8-1=7, 27-8=19, 64-27=37, 125-64=61. "
            "First: 7, 19, 37, 61. Second: 12, 18, 24. Third: 6, 6, 6. "
            "Teen levels mein constant! Pattern bahut powerful hai!"
        ),
        "common_errors": [
            "Student makes arithmetic errors in the subtraction chain",
        ],
    },
}


# ============================================================
# QUESTIONS — Complete question bank
# ============================================================

QUESTIONS = [

    # ========================================
    # PERFECT SQUARES — EASY (6)
    # ========================================

    {
        "id": "sq_e01",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "easy",
        "question": "Kya 49 ek perfect square hai?",
        "question_en": "Is 49 a perfect square?",
        "answer": "haan",
        "answer_en": "yes",
        "explanation": "49 = 7 × 7 = 7 ka square. Toh haan, 49 perfect square hai.",
        "hints": [
            "Sochiye: kaunsa number khud se multiply karke 49 dega?",
            "7 times 7 kitna hota hai?",
        ],
        "accept_patterns": ["haan", "yes", "ha", "sahi", "true", "7 ka square"],
        "common_mistakes": ["Student says no because 49 is odd"],
        "target_skill": "perfect_square_concept",
    },
    {
        "id": "sq_e02",
        "chapter": "ch1_square_and_cube",
        "type": "compute",
        "difficulty": "easy",
        "question": "12 ka square kitna hota hai?",
        "question_en": "What is 12 squared?",
        "answer": "144",
        "hints": [
            "12 times 12 calculate karo.",
            "12 times 10 = 120, 12 times 2 = 24. Dono jodo.",
        ],
        "accept_patterns": ["144", "ek sau chawalees", "one forty four"],
        "common_mistakes": ["Student says 24 (12×2 instead of 12×12)"],
        "target_skill": "squares_table_1_to_30",
    },
    {
        "id": "sq_e03",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "easy",
        "question": "Kya 2048 ek perfect square ho sakta hai? Sirf last digit dekh ke batao.",
        "question_en": "Can 2048 be a perfect square? Just look at the last digit.",
        "answer": "nahi",
        "answer_en": "no",
        "explanation": "2048 ka last digit 8 hai. Perfect squares kabhi 8 pe end nahi hote.",
        "hints": [
            "2048 ka last digit kya hai?",
            "Perfect squares kin digits pe end hote hain? 0, 1, 4, 5, 6, 9.",
        ],
        "accept_patterns": ["nahi", "no", "nah", "galat", "false", "nahi ho sakta"],
        "common_mistakes": ["Student thinks 2048 is a square because 2^11 = 2048"],
        "target_skill": "square_units_digit",
    },
    {
        "id": "sq_e04",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "easy",
        "question": "In mein se kaunse numbers perfect squares NAHI hain: 2032, 2048, 1027, 1089?",
        "question_en": "Which of these are NOT perfect squares: 2032, 2048, 1027, 1089?",
        "answer": "2032, 2048, 1027",
        "explanation": "2032 ends in 2, 2048 in 8, 1027 in 7 — none can be squares. 1089 = 33².",
        "hints": [
            "Pehle last digits check karo. Kaunse 2, 3, 7, ya 8 pe end ho rahe?",
            "1089 ka root try karo: 33 × 33 = ?",
        ],
        "accept_patterns": ["2032", "2048", "1027", "2032 2048 1027", "pehle teen"],
        "common_mistakes": ["Student includes 1089 (it IS a square: 33²)"],
        "target_skill": "square_units_digit",
    },
    {
        "id": "sq_e05",
        "chapter": "ch1_square_and_cube",
        "type": "count",
        "difficulty": "easy",
        "question": "16 ke square aur 17 ke square ke beech mein kitne numbers hain?",
        "question_en": "How many numbers lie between 16² and 17²?",
        "answer": "32",
        "explanation": "16² = 256, 17² = 289. Beech mein: 289 - 256 - 1 = 32 numbers.",
        "hints": [
            "Pehle 16 ka square aur 17 ka square nikaalo.",
            "289 minus 256 minus 1 = ?",
        ],
        "accept_patterns": ["32", "battis", "thirty two"],
        "common_mistakes": ["Says 33 (forgets to subtract 1)", "Says 256 or 289"],
        "target_skill": "perfect_square_concept",
    },
    {
        "id": "sq_e06",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "easy",
        "question": "Kya 156 ek perfect square hai?",
        "question_en": "Is 156 a perfect square?",
        "answer": "nahi",
        "explanation": "156 = 2 × 2 × 3 × 13. 3 aur 13 akele hain, pair nahi bana. Not a square.",
        "hints": [
            "156 ke prime factors nikaliye.",
            "2 × 2 × 3 × 13. Kya sab pairs mein hain?",
        ],
        "accept_patterns": ["nahi", "no", "nah", "false", "galat"],
        "common_mistakes": ["Student says yes because 156 ends in 6"],
        "target_skill": "sqrt_prime_factorisation",
    },

    # ========================================
    # PERFECT SQUARES — MEDIUM (6)
    # ========================================

    {
        "id": "sq_m01",
        "chapter": "ch1_square_and_cube",
        "type": "pattern",
        "difficulty": "medium",
        "question": "125 ka square 15625 hai. Toh 126 ka square kitna hoga?",
        "question_en": "Given 125² = 15625, what is 126²?",
        "answer": "15876",
        "explanation": "126² = 125² + 125 + 126 = 15625 + 251 = 15876.",
        "hints": [
            "Pattern: (n+1)² = n² + n + (n+1). Yahan n = 125.",
            "15625 + 125 + 126 = 15625 + 251 = ?",
        ],
        "accept_patterns": ["15876", "15,876"],
        "common_mistakes": [
            "Adds only 126 (gets 15751)",
            "Adds 252 instead of 251",
        ],
        "target_skill": "square_odd_pattern",
    },
    {
        "id": "sq_m02",
        "chapter": "ch1_square_and_cube",
        "type": "sqrt",
        "difficulty": "medium",
        "question": "Ek square ka area 441 square meter hai. Side kitni hai?",
        "question_en": "Find the side of a square with area 441 m².",
        "answer": "21",
        "explanation": "441 = 3 × 3 × 7 × 7 = (3×7)² = 21². Side = 21 m.",
        "hints": [
            "441 ke prime factors nikaliye.",
            "441 = 3 × 3 × 7 × 7. Ab pairs banao.",
        ],
        "accept_patterns": ["21", "21 m", "21 meter", "ekkees", "twenty one"],
        "common_mistakes": ["Says 22 or 20 from guessing"],
        "target_skill": "sqrt_prime_factorisation",
    },
    {
        "id": "sq_m03",
        "chapter": "ch1_square_and_cube",
        "type": "sqrt",
        "difficulty": "medium",
        "question": "Kya 324 perfect square hai? Agar haan, toh square root batao.",
        "question_en": "Is 324 a perfect square? If yes, find its square root.",
        "answer": "18",
        "explanation": "324 = 2×2×3×3×3×3. Pairs: (2×3×3) = 18. So 324 = 18².",
        "hints": [
            "324 ke prime factors: 2 × 2 × 3 × 3 × 3 × 3.",
            "Sab pairs mein hain? Agar haan, toh ek-ek pick karke multiply karo.",
        ],
        "accept_patterns": ["18", "haan 18", "yes 18", "athaara"],
        "common_mistakes": ["Gets factors wrong", "Says 16 or 20"],
        "target_skill": "sqrt_prime_factorisation",
    },
    {
        "id": "sq_m04",
        "chapter": "ch1_square_and_cube",
        "type": "estimate",
        "difficulty": "medium",
        "question": "250 ka square root kiske beech mein aayega?",
        "question_en": "Between which two integers does √250 lie?",
        "answer": "15 aur 16",
        "explanation": "15² = 225, 16² = 256. 225 < 250 < 256. Root is between 15 and 16.",
        "hints": [
            "15 ka square kitna hai? 16 ka?",
            "225 < 250 < 256. Toh root 15 aur 16 ke beech.",
        ],
        "accept_patterns": [
            "15 aur 16", "15 and 16", "between 15 and 16",
            "approximately 16", "lagbhag 16", "15 16",
        ],
        "common_mistakes": ["Says 12 and 13", "Says 25 (confusing with 250/10)"],
        "target_skill": "sqrt_estimation",
    },
    {
        "id": "sq_m05",
        "chapter": "ch1_square_and_cube",
        "type": "pattern",
        "difficulty": "medium",
        "question": "Pattern complete karo: 4² + 5² + 20² = (____)²",
        "question_en": "Fill in: 4² + 5² + 20² = (____)²",
        "answer": "21",
        "explanation": "16 + 25 + 400 = 441 = 21².",
        "hints": [
            "Pehle calculate karo: 16 + 25 + 400 = ?",
            "441 kiska square hai?",
        ],
        "accept_patterns": ["21", "ekkees", "twenty one", "441"],
        "common_mistakes": ["Says 29 (adding 4+5+20)"],
        "target_skill": "square_odd_pattern",
    },
    {
        "id": "sq_m06",
        "chapter": "ch1_square_and_cube",
        "type": "application",
        "difficulty": "medium",
        "question": "Akhil ke paas 125 sq cm ka kapda hai. Maximum kitni side ka square handkerchief kaata ja sakta hai (integer side)?",
        "question_en": "Cloth area is 125 cm². What's the max integer side for a square handkerchief?",
        "answer": "11",
        "explanation": "11² = 121 ≤ 125 < 144 = 12². So max side = 11 cm.",
        "hints": [
            "11 ka square kitna? 12 ka square kitna?",
            "121 < 125 < 144. Toh 11 cm ka handkerchief katega.",
        ],
        "accept_patterns": ["11", "11 cm", "gyarah", "eleven"],
        "common_mistakes": ["Says 12 (12²=144 > 125)", "Says 62 or 63 (divides by 2)"],
        "target_skill": "sqrt_estimation",
    },

    # ========================================
    # PERFECT SQUARES — HARD (5)
    # ========================================

    {
        "id": "sq_h01",
        "chapter": "ch1_square_and_cube",
        "type": "lcm_square",
        "difficulty": "hard",
        "question": "Sabse chhota perfect square number batao jo 4, 9 aur 10 teeno se divisible ho.",
        "question_en": "Find the smallest square number divisible by 4, 9, and 10.",
        "answer": "900",
        "explanation": "LCM(4,9,10) = 180 = 2²×3²×5. 5 akela hai → ×5 = 900 = 30².",
        "hints": [
            "Pehle 4, 9 aur 10 ka LCM nikaliye.",
            "LCM = 180. Ab 180 ke prime factors: 2²×3²×5. 5 akela hai!",
            "180 × 5 = 900. Verify: 900 = 30². Sab se divide ho raha?",
        ],
        "sub_steps": [
            {"step": "Find LCM(4,9,10)", "answer": "180"},
            {"step": "Factorize 180", "answer": "2² × 3² × 5"},
            {"step": "Which prime is unpaired?", "answer": "5"},
            {"step": "Multiply: 180 × 5", "answer": "900"},
        ],
        "accept_patterns": ["900", "nau sau", "nine hundred"],
        "common_mistakes": ["Says 180 (LCM but not a square)", "Says 3600 (multiplies by 20)"],
        "target_skill": "make_perfect_square",
    },
    {
        "id": "sq_h02",
        "chapter": "ch1_square_and_cube",
        "type": "factor",
        "difficulty": "hard",
        "question": "9408 ko kis chhote se chhote number se multiply karein ki perfect square ban jaaye? Square root bhi batao.",
        "question_en": "Find smallest multiplier for 9408 to become a perfect square. Also find the square root.",
        "answer": "3",
        "answer_part2": "168",
        "explanation": "9408 = 2⁶×3×7². 3 is unpaired → ×3 = 28224 = 168².",
        "hints": [
            "9408 ke prime factors: bahut baar 2 se divide hoga.",
            "9408 = 2⁶ × 3 × 7². Kaunsa factor akela hai?",
            "3 akela hai. 9408 × 3 = 28224. Square root = 2³×3×7 = 168.",
        ],
        "sub_steps": [
            {"step": "Factorize 9408", "answer": "2⁶ × 3 × 7²"},
            {"step": "Which prime is unpaired?", "answer": "3"},
            {"step": "Multiply: 9408 × 3", "answer": "28224"},
            {"step": "Square root of 28224", "answer": "168"},
        ],
        "accept_patterns": ["3", "teen", "three"],
        "common_mistakes": ["Says 7 (7 is already paired)", "Can't factorize 9408"],
        "target_skill": "make_perfect_square",
    },
    {
        "id": "sq_h03",
        "chapter": "ch1_square_and_cube",
        "type": "pattern",
        "difficulty": "hard",
        "question": "Pattern complete karo: 9² + 10² + (____)² = (____)²",
        "question_en": "Fill in: 9² + 10² + (____)² = (____)²",
        "answer": "90, 91",
        "explanation": "Pattern: n²+(n+1)²+(n(n+1))² = (n(n+1)+1)². Here n=9: 9×10=90, 90+1=91.",
        "hints": [
            "Pehle ke patterns dekho: 1²+2²+2²=3², 2²+3²+6²=7², 3²+4²+12²=13².",
            "Pattern: teesra number = pehle do ka product. 9×10 = ?",
            "90 squared + baaki = 91 squared. Verify: 81+100+8100 = 8281 = 91².",
        ],
        "accept_patterns": ["90 91", "90 aur 91", "90 and 91"],
        "common_mistakes": ["Can't identify the n(n+1) pattern"],
        "target_skill": "square_odd_pattern",
    },
    {
        "id": "sq_h04",
        "chapter": "ch1_square_and_cube",
        "type": "sqrt",
        "difficulty": "hard",
        "question": "1936 ka square root nikalo.",
        "question_en": "Find √1936.",
        "answer": "44",
        "explanation": "40²=1600, 50²=2500. Last digit 6→root ends in 4 or 6. 45²=2025>1936. So 44.",
        "hints": [
            "1936 kahan aata hai? 40²=1600 aur 50²=2500 ke beech.",
            "Last digit 6 hai. Root 4 ya 6 pe end hoga: 44 ya 46.",
            "45²=2025 > 1936. Toh root 40-45 ke beech. 44 try karo!",
        ],
        "sub_steps": [
            {"step": "Narrow range: between 40² and 50²", "answer": "40-50"},
            {"step": "Last digit 6 → root ends in?", "answer": "4 or 6"},
            {"step": "45²=2025 > 1936, so root is?", "answer": "40-45"},
            {"step": "Must be 44. Verify: 44×44", "answer": "1936 ✓"},
        ],
        "accept_patterns": ["44", "chawalees", "forty four"],
        "common_mistakes": ["Says 46 (doesn't check 45²)"],
        "target_skill": "sqrt_estimation",
    },
    {
        "id": "sq_h05",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "hard",
        "question": "Kya 1156 perfect square hai? Prime factorisation se check karo.",
        "question_en": "Is 1156 a perfect square? Check by prime factorisation.",
        "answer": "haan, 34",
        "explanation": "1156 = 2²×17². All paired. √1156 = 2×17 = 34.",
        "hints": [
            "1156 ÷ 2 = 578. 578 ÷ 2 = 289. Ab 289 ka factor?",
            "289 = 17 × 17. Toh 1156 = 2² × 17². Sab pairs mein!",
        ],
        "accept_patterns": ["haan", "yes", "34", "haan 34", "yes 34"],
        "common_mistakes": ["Stops at 289 without recognizing 17²"],
        "target_skill": "sqrt_prime_factorisation",
    },

    # ========================================
    # PERFECT CUBES — EASY (6)
    # ========================================

    {
        "id": "cb_e01",
        "chapter": "ch1_square_and_cube",
        "type": "compute",
        "difficulty": "easy",
        "question": "5 ka cube kitna hota hai?",
        "question_en": "What is 5³?",
        "answer": "125",
        "hints": [
            "5 × 5 = 25. Ab 25 × 5 = ?",
        ],
        "accept_patterns": ["125", "ek sau pachchees", "one twenty five"],
        "common_mistakes": ["Says 15 (5×3)", "Says 25 (5²)"],
        "target_skill": "perfect_cube_concept",
    },
    {
        "id": "cb_e02",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "easy",
        "question": "64 ka cube root kitna hai?",
        "question_en": "What is the cube root of 64?",
        "answer": "4",
        "explanation": "4 × 4 × 4 = 64.",
        "hints": [
            "Kaunsa number teen baar multiply karke 64 dega?",
            "4 × 4 = 16. 16 × 4 = ?",
        ],
        "accept_patterns": ["4", "chaar", "four"],
        "common_mistakes": ["Says 8 (confusing with √64)", "Says 21 (64÷3)"],
        "target_skill": "cube_root_concept",
    },
    {
        "id": "cb_e03",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "easy",
        "question": "512 ka cube root batao.",
        "question_en": "Find the cube root of 512.",
        "answer": "8",
        "hints": [
            "8 × 8 = 64. 64 × 8 = ?",
        ],
        "accept_patterns": ["8", "aath", "eight"],
        "common_mistakes": ["Says 170 (512÷3)"],
        "target_skill": "cube_root_concept",
    },
    {
        "id": "cb_e04",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "easy",
        "question": "729 ka cube root kitna hai?",
        "question_en": "Find the cube root of 729.",
        "answer": "9",
        "hints": [
            "9 × 9 = 81. 81 × 9 = ?",
        ],
        "accept_patterns": ["9", "nau", "nine"],
        "common_mistakes": ["Says 27 (confusing with √729)", "Says 243 (729÷3)"],
        "target_skill": "cube_root_concept",
    },
    {
        "id": "cb_e05",
        "chapter": "ch1_square_and_cube",
        "type": "true_false",
        "difficulty": "easy",
        "question": "Sahi ya galat: Kisi bhi odd number ka cube even hota hai.",
        "question_en": "True or false: The cube of any odd number is even.",
        "answer": "galat",
        "explanation": "Odd × odd × odd = odd. Example: 3³ = 27, which is odd.",
        "hints": [
            "3 odd hai. 3 × 3 × 3 = 27. Kya 27 even hai?",
        ],
        "accept_patterns": ["galat", "false", "nahi", "wrong", "no"],
        "common_mistakes": ["Confuses with addition rule (odd+odd=even)"],
        "target_skill": "perfect_cube_concept",
    },
    {
        "id": "cb_e06",
        "chapter": "ch1_square_and_cube",
        "type": "true_false",
        "difficulty": "easy",
        "question": "Sahi ya galat: Koi bhi perfect cube 8 pe end nahi ho sakta.",
        "question_en": "True or false: No perfect cube ends with 8.",
        "answer": "galat",
        "explanation": "2³ = 8 ends with 8. 12³ = 1728 also ends with 8.",
        "hints": [
            "2 ka cube kitna hai?",
        ],
        "accept_patterns": ["galat", "false", "nahi", "wrong"],
        "common_mistakes": ["Confuses cube digit rules with square digit rules"],
        "target_skill": "cube_units_digit",
    },

    # ========================================
    # PERFECT CUBES — MEDIUM (6)
    # ========================================

    {
        "id": "cb_m01",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "medium",
        "question": "27000 ka cube root nikalo.",
        "question_en": "Find the cube root of 27000.",
        "answer": "30",
        "explanation": "27000 = 27 × 1000 = 3³ × 10³ = 30³.",
        "hints": [
            "27000 ko 27 × 1000 mein tod do.",
            "27 ka cube root 3, 1000 ka cube root 10. Multiply karo!",
        ],
        "accept_patterns": ["30", "tees", "thirty"],
        "common_mistakes": ["Says 300 (extra zero)", "Says 3000"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "cb_m02",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "medium",
        "question": "10648 ka cube root nikalo.",
        "question_en": "Find the cube root of 10648.",
        "answer": "22",
        "explanation": "10648 = 2³ × 11³ = 22³.",
        "hints": [
            "10648 ke prime factors nikaliye. 2 se shuru karo.",
            "10648 = 8 × 1331. 8 = 2³, 1331 = 11³. Cube root = 2×11 = 22.",
        ],
        "accept_patterns": ["22", "baees", "twenty two"],
        "common_mistakes": ["Gets stuck on factorising 1331"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "cb_m03",
        "chapter": "ch1_square_and_cube",
        "type": "guess",
        "difficulty": "medium",
        "question": "1331 perfect cube hai. Bina factorisation ke cube root guess karo.",
        "question_en": "1331 is a perfect cube. Guess its cube root without factorisation.",
        "answer": "11",
        "explanation": "Last digit 1 → root ends in 1. 10³=1000, 20³=8000. Between 10-20. Try 11.",
        "hints": [
            "1331 ka last digit 1 hai. Kaun sa digit cube karke 1 dega?",
            "10 ka cube 1000, 20 ka 8000. 1331 beech mein hai. Toh 11!",
        ],
        "accept_patterns": ["11", "gyarah", "eleven"],
        "common_mistakes": ["Says 13 or 31 (digit confusion)"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "cb_m04",
        "chapter": "ch1_square_and_cube",
        "type": "true_false",
        "difficulty": "medium",
        "question": "Sahi ya galat: Kisi 2-digit number ka cube 3-digit ho sakta hai.",
        "question_en": "True or false: The cube of a 2-digit number can be a 3-digit number.",
        "answer": "galat",
        "explanation": "Smallest 2-digit number: 10. 10³ = 1000, which is 4 digits. So never 3 digits.",
        "hints": [
            "Sabse chhota 2-digit number kaunsa hai?",
            "10 ka cube 1000 hai. Kya 1000 three digit hai?",
        ],
        "accept_patterns": ["galat", "false", "nahi", "wrong"],
        "common_mistakes": ["Doesn't think about the minimum 2-digit number"],
        "target_skill": "perfect_cube_concept",
    },
    {
        "id": "cb_m05",
        "chapter": "ch1_square_and_cube",
        "type": "pattern",
        "difficulty": "medium",
        "question": "91+93+95+97+99+101+103+105+107+109 ka sum kya hai? Calculate mat karo, pattern use karo.",
        "question_en": "What is 91+93+95+...+109? Use the cube-odd pattern, don't calculate.",
        "answer": "1000",
        "explanation": "10 consecutive odd numbers starting from right position = 10³ = 1000.",
        "hints": [
            "Kitne numbers hain? Gino.",
            "10 numbers hain. Pattern: n consecutive odd numbers = n ka cube. 10³ = ?",
        ],
        "accept_patterns": ["1000", "ek hazaar", "one thousand", "10 ka cube"],
        "common_mistakes": ["Tries to add all 10 numbers manually"],
        "target_skill": "cube_odd_pattern",
    },
    {
        "id": "cb_m06",
        "chapter": "ch1_square_and_cube",
        "type": "true_false",
        "difficulty": "medium",
        "question": "Sahi ya galat: Kisi 2-digit number ka cube 7 ya usse zyada digits ka ho sakta hai.",
        "question_en": "True or false: The cube of a 2-digit number can have 7+ digits.",
        "answer": "galat",
        "explanation": "Largest 2-digit: 99. 99³ = 970299, which is 6 digits. Never 7.",
        "hints": [
            "Sabse bada 2-digit number kaunsa hai?",
            "99³ = 970299. Kitne digits?",
        ],
        "accept_patterns": ["galat", "false", "nahi", "wrong"],
        "common_mistakes": ["Doesn't calculate 99³"],
        "target_skill": "perfect_cube_concept",
    },

    # ========================================
    # PERFECT CUBES — HARD (5)
    # ========================================

    {
        "id": "cb_h01",
        "chapter": "ch1_square_and_cube",
        "type": "factor",
        "difficulty": "hard",
        "question": "1323 ko kisse multiply karein ki perfect cube ban jaaye?",
        "question_en": "What number must 1323 be multiplied by to make it a perfect cube?",
        "answer": "7",
        "answer_part2": "21",
        "explanation": "1323 = 3³×7². Need one more 7. 1323×7 = 9261 = 21³.",
        "hints": [
            "1323 ke prime factors: 3 se divide karo, phir 7 se.",
            "1323 = 3×3×3×7×7. 3 ka triplet complete. 7 kitni baar hai?",
            "7 do baar hai, teen chahiye. Ek aur 7 multiply karo.",
        ],
        "sub_steps": [
            {"step": "Factorize 1323", "answer": "3³ × 7²"},
            {"step": "Which prime needs more?", "answer": "7 (has 2, needs 3)"},
            {"step": "Multiply by?", "answer": "7"},
            {"step": "Result and cube root?", "answer": "9261 = 21³"},
        ],
        "accept_patterns": ["7", "saat", "seven"],
        "common_mistakes": ["Says 49 (7²) or 63 (7×9)", "Says 3 (3 is already complete)"],
        "target_skill": "make_perfect_cube",
    },
    {
        "id": "cb_h02",
        "chapter": "ch1_square_and_cube",
        "type": "guess",
        "difficulty": "hard",
        "question": "4913 ka cube root guess karo bina factorisation ke.",
        "question_en": "Guess the cube root of 4913 without factorisation.",
        "answer": "17",
        "explanation": "Last digit 3→root ends in 7. 10³=1000, 20³=8000. Try 17: 17³=4913 ✓.",
        "hints": [
            "4913 ka last digit 3 hai. Cube table mein 3 pe end hone wala: 7³=343. Toh root 7 pe end hoga.",
            "10³=1000, 20³=8000. 4913 beech mein. Toh root teen ya saat pe end hoga between 10-20: 17!",
        ],
        "accept_patterns": ["17", "satrah", "seventeen"],
        "common_mistakes": ["Says 13 (wrong digit mapping)"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "cb_h03",
        "chapter": "ch1_square_and_cube",
        "type": "guess",
        "difficulty": "hard",
        "question": "32768 ka cube root guess karo.",
        "question_en": "Guess the cube root of 32768.",
        "answer": "32",
        "explanation": "Last digit 8→root ends in 2. 30³=27000, 40³=64000. Try 32: 32³=32768 ✓.",
        "hints": [
            "32768 ka last digit 8. Kiska cube 8 pe end hota hai? 2!",
            "30³=27000, 40³=64000. 32768 beech mein. Root 2 pe end ho — 32!",
        ],
        "accept_patterns": ["32", "battis", "thirty two"],
        "common_mistakes": ["Says 22 or 42"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "cb_h04",
        "chapter": "ch1_square_and_cube",
        "type": "compare",
        "difficulty": "hard",
        "question": "Kaunsa sabse bada hai: 67³-66³, 43³-42³, 67²-66², 43²-42²?",
        "question_en": "Which is greatest: 67³-66³, 43³-42³, 67²-66², 43²-42²?",
        "answer": "67³ - 66³",
        "explanation": (
            "n³-(n-1)³ = 3n²-3n+1. For n=67: 3(4489)-201+1 = 13266. "
            "For n=43: 3(1849)-129+1 = 5418. "
            "n²-(n-1)² = 2n-1. For n=67: 133. For n=43: 85. "
            "13266 is the largest."
        ),
        "hints": [
            "Cube differences bahut bade hote hain. Square differences chote.",
            "n³-(n-1)³ = 3n²-3n+1. n=67 ke liye calculate karo.",
        ],
        "accept_patterns": [
            "67 cube minus 66 cube", "pehla", "first", "67³-66³",
            "67 ka cube minus 66 ka cube", "a", "option a", "i",
        ],
        "common_mistakes": ["Picks 67²-66² thinking squares are bigger than cube differences"],
        "target_skill": "perfect_cube_concept",
    },
    {
        "id": "cb_h05",
        "chapter": "ch1_square_and_cube",
        "type": "taxicab",
        "difficulty": "hard",
        "question": "4104 ko do cubes ke sum se do alag tarike se likho. (Ramanujan style!)",
        "question_en": "Express 4104 as sum of two cubes in two different ways.",
        "answer": "2³+16³ and 9³+15³",
        "explanation": "4104 = 8+4096 = 2³+16³. Also 4104 = 729+3375 = 9³+15³.",
        "hints": [
            "4104 ke paas kaunsa bada cube hai? 16³ = 4096. Toh 4104-4096 = 8 = 2³!",
            "Ab doosra tarika: 15³ = 3375. 4104-3375 = 729 = 9³!",
        ],
        "accept_patterns": [
            "2 cube 16 cube 9 cube 15 cube",
            "8+4096 and 729+3375",
            "2 aur 16, 9 aur 15",
        ],
        "common_mistakes": ["Only finds one decomposition"],
        "target_skill": "taxicab_ramanujan",
    },

    # ========================================
    # CONCEPTUAL / DISCUSSION — MIXED (6)
    # ========================================

    {
        "id": "cn_01",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "easy",
        "question": "Locker puzzle mein kaunse 10 lockers khule rehte hain?",
        "question_en": "In the locker puzzle, which 10 lockers remain open?",
        "answer": "1, 4, 9, 16, 25, 36, 49, 64, 81, 100",
        "explanation": "Perfect squares 1 se 100 tak: 1², 2², 3², ..., 10².",
        "hints": [
            "Woh numbers jinke factors odd hain — perfect squares!",
            "1 se 100 tak ke perfect squares gino.",
        ],
        "accept_patterns": ["1 4 9 16 25 36 49 64 81 100", "perfect squares", "square numbers"],
        "target_skill": "perfect_square_concept",
    },
    {
        "id": "cn_02",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "medium",
        "question": "Perfect squares ke factors ki sankhya odd kyun hoti hai?",
        "question_en": "Why do perfect squares have an odd number of factors?",
        "answer": "ek factor apne aap se pair banata hai",
        "explanation": "In a perfect square n², one factor (√n²=n) pairs with itself, making total count odd.",
        "hints": [
            "9 ke factors: 1, 3, 9. Pairs: 1×9, 3×3. 3 apne aap se pair bana raha!",
        ],
        "accept_patterns": [
            "ek factor repeat", "same pair", "apne aap se",
            "one factor pairs with itself", "middle factor",
        ],
        "target_skill": "square_factor_pairs",
    },
    {
        "id": "cn_03",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "medium",
        "question": "Kya perfect square ke end mein odd number of zeros ho sakte hain?",
        "question_en": "Can a perfect square have an odd number of trailing zeros?",
        "answer": "nahi",
        "explanation": "If n has k trailing zeros, n² has 2k trailing zeros. 2k is always even.",
        "hints": [
            "10² = 100 (2 zeros). 100² = 10000 (4 zeros). Pattern?",
        ],
        "accept_patterns": ["nahi", "no", "nah", "false", "even zeros"],
        "target_skill": "square_zeros_parity",
    },
    {
        "id": "cn_04",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "medium",
        "question": "Triangular numbers aur square numbers mein kya rishta hai?",
        "question_en": "What's the relationship between triangular and square numbers?",
        "answer": "do consecutive triangular numbers ka sum = perfect square",
        "hints": [
            "1+3=4, 3+6=9, 6+10=16. Kya dikha?",
        ],
        "accept_patterns": [
            "sum square", "jodne se square", "consecutive triangular",
            "add triangular", "triangular plus next triangular",
        ],
        "target_skill": "triangular_square_relation",
    },
    {
        "id": "cn_05",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "medium",
        "question": "Kya koi perfect cube exactly do zeros pe end ho sakta hai?",
        "question_en": "Can a perfect cube end with exactly two zeros?",
        "answer": "nahi",
        "explanation": "If n has k trailing zeros, n³ has 3k zeros. 3k is always a multiple of 3, never 2.",
        "hints": [
            "10³ = 1000 (3 zeros). 100³ = 1000000 (6 zeros). Pattern?",
        ],
        "accept_patterns": ["nahi", "no", "false", "3 ke multiple"],
        "target_skill": "cube_units_digit",
    },
    {
        "id": "cn_06",
        "chapter": "ch1_square_and_cube",
        "type": "conceptual",
        "difficulty": "hard",
        "question": "Successive differences: squares mein 2 levels mein constant aata hai. Cubes mein kitne levels mein?",
        "question_en": "In successive differences, squares become constant at level 2. How many levels for cubes?",
        "answer": "3",
        "explanation": "Cubes: Level 1: 7,19,37,61... Level 2: 12,18,24... Level 3: 6,6,6. Three levels.",
        "hints": [
            "1, 8, 27, 64, 125. First differences: 7, 19, 37, 61. Second: 12, 18, 24. Third?",
        ],
        "accept_patterns": ["3", "teen", "three", "3 levels"],
        "target_skill": "successive_differences",
    },

    # ========================================
    # ADDITIONAL QUESTIONS — COVERAGE BOOST (10)
    # ========================================

    {
        "id": "sq_e07",
        "chapter": "ch1_square_and_cube",
        "type": "compute",
        "difficulty": "easy",
        "question": "25 ka square kitna hota hai?",
        "question_en": "What is 25²?",
        "answer": "625",
        "hints": ["25 × 25. Trick: 25² hamesha 625 hota hai!"],
        "accept_patterns": ["625", "chheh sau pachchees"],
        "common_mistakes": ["Says 50 (25×2)"],
        "target_skill": "squares_table_1_to_30",
    },
    {
        "id": "sq_m07",
        "chapter": "ch1_square_and_cube",
        "type": "odd_sum",
        "difficulty": "medium",
        "question": "1 + 3 + 5 + 7 + 9 + 11 + 13 ka sum kitna hai? Pattern use karo.",
        "question_en": "What is 1+3+5+7+9+11+13? Use the pattern.",
        "answer": "49",
        "explanation": "7 odd numbers ka sum = 7² = 49.",
        "hints": [
            "Kitne odd numbers hain? Gino.",
            "7 odd numbers. Pattern: pehle n odd numbers ka sum = n². 7² = ?",
        ],
        "accept_patterns": ["49", "unchaas", "forty nine", "7 ka square"],
        "common_mistakes": ["Adds manually and makes arithmetic error"],
        "target_skill": "square_odd_pattern",
    },
    {
        "id": "sq_m08",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "medium",
        "question": "Kya 2800 perfect square hai? Prime factorisation se check karo.",
        "question_en": "Is 2800 a perfect square? Check using prime factorisation.",
        "answer": "nahi",
        "explanation": "2800 = 2⁴×5²×7. 7 akela hai — not a square.",
        "hints": [
            "2800 ke prime factors: 2 se divide karte jao, phir 5, phir 7.",
            "2800 = 2×2×2×2×5×5×7. Kya sab pairs mein hain?",
        ],
        "accept_patterns": ["nahi", "no", "false", "galat"],
        "common_mistakes": ["Factorisation error"],
        "target_skill": "sqrt_prime_factorisation",
    },
    {
        "id": "sq_e08",
        "chapter": "ch1_square_and_cube",
        "type": "count",
        "difficulty": "easy",
        "question": "99 ke square aur 100 ke square ke beech mein kitne numbers hain?",
        "question_en": "How many numbers lie between 99² and 100²?",
        "answer": "198",
        "explanation": "Formula: 2n. Here n=99: 2×99 = 198.",
        "hints": [
            "99² = 9801, 100² = 10000. Beech mein: 10000-9801-1 = ?",
            "Ya seedha formula: 2 × 99 = ?",
        ],
        "accept_patterns": ["198", "ek sau anthaanavve"],
        "common_mistakes": ["Says 199 (forgets -1)"],
        "target_skill": "perfect_square_concept",
    },
    {
        "id": "sq_h06",
        "chapter": "ch1_square_and_cube",
        "type": "units_digit",
        "difficulty": "hard",
        "question": "In mein se kaunse squares ka last digit 6 hoga: 38², 34², 46², 56², 74², 82²?",
        "question_en": "Which of 38², 34², 46², 56², 74², 82² have last digit 6?",
        "answer": "34², 46², 56², 74²",
        "explanation": "Numbers ending in 4 or 6 have squares ending in 6. 34,46,56,74 end in 4 or 6.",
        "hints": [
            "Kaunse numbers 4 ya 6 pe end hote hain? Unke squares 6 pe end hote hain.",
            "38 → 8 pe end (square ends in 4). 82 → 2 pe end (square ends in 4). Baaki?",
        ],
        "accept_patterns": ["34 46 56 74", "34, 46, 56, 74"],
        "common_mistakes": ["Includes 38 or 82"],
        "target_skill": "square_units_digit",
    },
    {
        "id": "cb_e07",
        "chapter": "ch1_square_and_cube",
        "type": "compute",
        "difficulty": "easy",
        "question": "7 ka cube kitna hota hai?",
        "question_en": "What is 7³?",
        "answer": "343",
        "hints": ["7 × 7 = 49. Ab 49 × 7 = ?"],
        "accept_patterns": ["343", "teen sau taintaalees"],
        "common_mistakes": ["Says 21 (7×3)", "Says 49 (7²)"],
        "target_skill": "cubes_table_1_to_20",
    },
    {
        "id": "cb_m07",
        "chapter": "ch1_square_and_cube",
        "type": "identify",
        "difficulty": "medium",
        "question": "Kya 500 ek perfect cube hai?",
        "question_en": "Is 500 a perfect cube?",
        "answer": "nahi",
        "explanation": "500 = 2×2×5×5×5. 2 sirf 2 baar hai, triplet incomplete. Not a cube.",
        "hints": [
            "500 ke prime factors nikaliye.",
            "500 = 2²×5³. Kya sab triplets mein hain?",
        ],
        "accept_patterns": ["nahi", "no", "false", "galat"],
        "common_mistakes": ["Thinks 500 is a cube because 5³=125 divides it"],
        "target_skill": "make_perfect_cube",
    },
    {
        "id": "cb_h06",
        "chapter": "ch1_square_and_cube",
        "type": "guess",
        "difficulty": "hard",
        "question": "12167 ka cube root guess karo bina factorisation ke.",
        "question_en": "Guess the cube root of 12167 without factorisation.",
        "answer": "23",
        "explanation": "Last digit 7→root ends in 3. 20³=8000, 30³=27000. Try 23: 23³=12167 ✓.",
        "hints": [
            "12167 ka last digit 7. Cube table mein 7 pe end: 3³=27. Root 3 pe end hoga.",
            "20³=8000, 30³=27000. 12167 beech mein. Toh 23!",
        ],
        "accept_patterns": ["23", "teees", "twenty three"],
        "common_mistakes": ["Says 27 (wrong digit mapping)"],
        "target_skill": "cbrt_prime_factorisation",
    },
    {
        "id": "sq_m09",
        "chapter": "ch1_square_and_cube",
        "type": "odd_sum",
        "difficulty": "medium",
        "question": "Kya 38 perfect square hai? Consecutive odd numbers subtract karke check karo.",
        "question_en": "Is 38 a perfect square? Check by subtracting consecutive odd numbers.",
        "answer": "nahi",
        "explanation": "38-1=37, 37-3=34, 34-5=29, 29-7=22, 22-9=13, 13-11=2, 2-13=-11. Didn't reach 0.",
        "hints": [
            "38 se 1 ghatao, phir 3, phir 5... Jab tak 0 aaye ya negative ho jaaye.",
            "38→37→34→29→22→13→2→-11. Zero nahi aaya!",
        ],
        "accept_patterns": ["nahi", "no", "false", "galat", "not a square"],
        "common_mistakes": ["Arithmetic error in subtraction chain"],
        "target_skill": "square_odd_pattern",
    },
    {
        "id": "cb_m08",
        "chapter": "ch1_square_and_cube",
        "type": "cube_root",
        "difficulty": "medium",
        "question": "3375 ka cube root prime factorisation se nikalo.",
        "question_en": "Find the cube root of 3375 using prime factorisation.",
        "answer": "15",
        "explanation": "3375 = 3³×5³ = (3×5)³ = 15³. Cube root = 15.",
        "hints": [
            "3375 ÷ 3 = 1125. 1125 ÷ 3 = 375. 375 ÷ 3 = 125. 125 ÷ 5 = 25. 25 ÷ 5 = 5. 5 ÷ 5 = 1.",
            "3375 = 3×3×3×5×5×5. Teen-teen ke groups: (3×5) = 15.",
        ],
        "accept_patterns": ["15", "pandrah", "fifteen"],
        "common_mistakes": ["Groups in pairs instead of triplets"],
        "target_skill": "cbrt_prime_factorisation",
    },
]


# ============================================================
# ANSWER CHECKING RULES
# ============================================================

ANSWER_CHECKER_RULES = {
    "chapter": "ch1_square_and_cube",
    "general_rules": [
        "Accept Hindi number words: ek, do, teen, chaar, paanch, chheh, saat, aath, nau, das, gyarah, baara, etc.",
        "Accept English number words: one, two, three, etc.",
        "Accept with/without units: '21', '21 m', '21 meter'",
        "For yes/no: accept haan/nahi/ha/sahi/galat/true/false/yes/no/right/wrong",
        "For range answers: accept 'between X and Y', 'X aur Y ke beech', 'X and Y', 'X Y'",
        "Strip commas from numbers: '15,876' → '15876'",
        "For multi-part answers: accept parts separately or together",
    ],
    "tts_conversions": {
        "²": " ka square",
        "³": " ka cube",
        "√": "square root of ",
        "∛": "cube root of ",
        "×": " times ",
        "÷": " divided by ",
        "≤": " se chhota ya barabar ",
        "≥": " se bada ya barabar ",
    },
    "hindi_number_map": {
        "ek": 1, "do": 2, "teen": 3, "chaar": 4, "paanch": 5,
        "chheh": 6, "saat": 7, "aath": 8, "nau": 9, "das": 10,
        "gyarah": 11, "baara": 12, "terah": 13, "chaudah": 14,
        "pandrah": 15, "solah": 16, "satrah": 17, "athaara": 18,
        "unees": 19, "bees": 20, "ekkees": 21, "baees": 22,
        "tees": 30, "chawalees": 44, "pachaas": 50,
        "saath": 60, "sattar": 70, "assi": 80, "nabbe": 90,
        "sau": 100, "nau sau": 900, "hazaar": 1000,
    },
    "stt_math_terms": [
        "varg", "varg mool", "ghan", "ghan mool",
        "gunankhand", "abhajya", "joda", "pair",
        "perfect square", "perfect cube", "square root", "cube root",
        "prime factor", "factor", "divisible",
    ],
}


# ============================================================
# HELPER: Get questions by difficulty / skill / type
# ============================================================

def get_questions_by_difficulty(difficulty: str) -> list:
    """Return questions filtered by difficulty: 'easy', 'medium', 'hard'."""
    return [q for q in QUESTIONS if q["difficulty"] == difficulty]


def get_questions_by_skill(skill: str) -> list:
    """Return questions filtered by target_skill."""
    return [q for q in QUESTIONS if q["target_skill"] == skill]


def get_question_by_id(qid: str) -> dict | None:
    """Return a single question by its ID."""
    for q in QUESTIONS:
        if q["id"] == qid:
            return q
    return None


def get_teaching_order() -> list:
    """Return skills in recommended teaching order."""
    return CHAPTER_META["teaching_order"]


def get_skill_lesson(skill: str) -> dict | None:
    """Return the SKILL_LESSON for a given skill key."""
    return SKILL_LESSONS.get(skill)


# ============================================================
# STATS (for quick reference)
# ============================================================

def chapter_stats() -> dict:
    """Return summary stats for this chapter's question bank."""
    total = len(QUESTIONS)
    easy = len(get_questions_by_difficulty("easy"))
    medium = len(get_questions_by_difficulty("medium"))
    hard = len(get_questions_by_difficulty("hard"))
    skills = list(set(q["target_skill"] for q in QUESTIONS))
    return {
        "chapter": CHAPTER_META["id"],
        "total_questions": total,
        "easy": easy,
        "medium": medium,
        "hard": hard,
        "skills_count": len(skills),
        "skills": sorted(skills),
        "teaching_steps": len(CHAPTER_META["teaching_order"]),
    }


if __name__ == "__main__":
    stats = chapter_stats()
    print(f"Chapter: {stats['chapter']}")
    print(f"Total Questions: {stats['total_questions']}")
    print(f"  Easy: {stats['easy']}, Medium: {stats['medium']}, Hard: {stats['hard']}")
    print(f"Skills: {stats['skills_count']}")
    for s in stats['skills']:
        count = len(get_questions_by_skill(s))
        print(f"  - {s}: {count} questions")
