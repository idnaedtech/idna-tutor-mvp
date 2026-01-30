"""
IDNA EdTech - CBSE Class 8 Question Bank
Based on NCERT Syllabus (2024-25)

IMPORTANT: Questions should match NCERT textbook exactly!
- Use same terminology as textbook (e.g., "additive inverse" not "opposite")
- Follow chapter order from NCERT
- Include exercise numbers where possible
- Word problems should use Indian context (rupees, km, etc.)

NCERT Class 8 Math Chapters:
1. Rational Numbers (परिमेय संख्याएँ)
2. Linear Equations in One Variable (एक चर वाले रैखिक समीकरण)
3. Understanding Quadrilaterals (चतुर्भुजों को समझना)
4. Data Handling (आँकड़ों का प्रबंधन) - Added for CBSE 2024-25
5. Squares and Square Roots (वर्ग और वर्गमूल)
6. Cubes and Cube Roots (घन और घनमूल)
7. Comparing Quantities (राशियों की तुलना)
8. Algebraic Expressions and Identities (बीजीय व्यंजक और सर्वसमिकाएँ)
9. Mensuration (क्षेत्रमिति)
10. Exponents and Powers (घातांक और घात)
11. Direct and Inverse Proportions (प्रत्यक्ष और प्रतिलोम समानुपात)
12. Factorisation (गुणनखंडन)
13. Introduction to Graphs (ग्राफ का परिचय)

Subjects:
- Mathematics (10 chapters, 150 questions)
- Science (5 chapters, 50 questions)

Question Types:
- text: Open-ended numeric/text answers
- mcq: Multiple choice (A/B/C/D)

Difficulty Levels:
- 1: Easy (basic concepts from NCERT examples)
- 2: Medium (NCERT exercise questions)
- 3: Hard (NCERT "Think and Discuss" / word problems)

TODO: Add NCERT exercise references (e.g., "Ex 1.1 Q3")
"""

# ============================================================
# CHAPTER NAMES
# ============================================================

CHAPTER_NAMES = {
    # Math chapters
    "rational_numbers": "Ch 1: Rational Numbers (परिमेय संख्याएँ)",
    "linear_equations": "Ch 2: Linear Equations (रैखिक समीकरण)",
    "quadrilaterals": "Ch 3: Quadrilaterals (चतुर्भुज)",
    "data_handling": "Ch 4: Data Handling (आँकड़ों का प्रबंधन)",
    "squares_roots": "Ch 5: Squares & Square Roots (वर्ग और वर्गमूल)",
    "cubes_roots": "Ch 6: Cubes & Cube Roots (घन और घनमूल)",
    "comparing_quantities": "Ch 7: Comparing Quantities (राशियों की तुलना)",
    "algebraic_expressions": "Ch 8: Algebraic Expressions (बीजीय व्यंजक)",
    "mensuration": "Ch 9: Mensuration (क्षेत्रमिति)",
    "exponents": "Ch 10: Exponents & Powers (घातांक और घात)",
    # Science chapters
    "science_matter": "Science: Materials & Matter (पदार्थ)",
    "science_life": "Science: Life Processes (जीवन प्रक्रियाएं)",
    "science_force": "Science: Force & Motion (बल और गति)",
    "science_light": "Science: Light & Sound (प्रकाश और ध्वनि)",
    "science_nature": "Science: Natural Resources (प्राकृतिक संसाधन)",
}

# ============================================================
# MATHEMATICS QUESTION BANK
# ============================================================

ALL_CHAPTERS = {
    # ============================================================
    # Chapter 1: Rational Numbers (परिमेय संख्याएँ)
    # ============================================================
    "rational_numbers": [
        {
            "id": "rn_001",
            "text": "What is -3/7 + 2/7?",
            "answer": "-1/7",
            "hint": "Same denominator, just add numerators: -3 + 2 = -1",
            "solution": "Since both fractions have the same denominator 7, we just add the numerators: -3 + 2 = -1. So the answer is -1/7.",
            "difficulty": 1
        },
        {
            "id": "rn_002",
            "text": "Find the additive inverse of 5/8",
            "answer": "-5/8",
            "hint": "Additive inverse means change the sign",
            "solution": "The additive inverse of a number is what you add to get zero. For 5/8, we change the sign to get -5/8. Check: 5/8 + (-5/8) = 0.",
            "difficulty": 1
        },
        {
            "id": "rn_003",
            "text": "What is 2/3 × (-3/4)?",
            "answer": "-1/2",
            "hint": "Multiply numerators and denominators: (2×-3)/(3×4) = -6/12 = -1/2",
            "solution": "Multiply the numerators: 2 × (-3) = -6. Multiply the denominators: 3 × 4 = 12. So we get -6/12. Simplify by dividing both by 6: -1/2.",
            "difficulty": 2
        },
        {
            "id": "rn_004",
            "text": "Find the multiplicative inverse of -7/9",
            "answer": "-9/7",
            "hint": "Flip the fraction, keep the sign",
            "solution": "The multiplicative inverse is what you multiply to get 1. Flip the fraction: -7/9 becomes -9/7. The sign stays negative. Check: (-7/9) × (-9/7) = 63/63 = 1.",
            "difficulty": 2
        },
        {
            "id": "rn_005",
            "text": "Is 0 a rational number? Answer yes or no",
            "answer": "yes",
            "hint": "0 can be written as 0/1",
            "solution": "Yes! A rational number is any number that can be written as p/q where q is not zero. Zero can be written as 0/1, 0/2, or 0/any-number. So 0 is rational.",
            "difficulty": 1
        },
        {
            "id": "rn_006",
            "text": "What is -5/6 ÷ 2/3?",
            "answer": "-5/4",
            "hint": "Divide = multiply by reciprocal: -5/6 × 3/2 = -15/12 = -5/4",
            "solution": "To divide fractions, multiply by the reciprocal. So -5/6 ÷ 2/3 becomes -5/6 × 3/2. Multiply: (-5 × 3)/(6 × 2) = -15/12. Simplify by dividing by 3: -5/4.",
            "difficulty": 2
        },
        {
            "id": "rn_007",
            "text": "Find a rational number between 1/4 and 1/2",
            "answer": "3/8",
            "hint": "Average: (1/4 + 1/2)/2 = (1/4 + 2/4)/2 = (3/4)/2 = 3/8",
            "solution": "Take the average of the two numbers. First, make denominators same: 1/4 and 2/4. Add them: 1/4 + 2/4 = 3/4. Divide by 2: (3/4)/2 = 3/8. So 3/8 is between 1/4 and 1/2.",
            "difficulty": 2
        },
        {
            "id": "rn_008",
            "text": "What is the value of (-1/2) + (-1/3)?",
            "answer": "-5/6",
            "hint": "LCM of 2 and 3 is 6: -3/6 + -2/6 = -5/6",
            "solution": "Find LCM of 2 and 3, which is 6. Convert: -1/2 = -3/6 and -1/3 = -2/6. Now add: -3/6 + (-2/6) = -5/6.",
            "difficulty": 2
        },
        {
            "id": "rn_009",
            "text": "Simplify: 12/18 to lowest terms",
            "answer": "2/3",
            "hint": "GCD of 12 and 18 is 6. Divide both by 6",
            "solution": "Find the GCD of 12 and 18. Factors of 12: 1,2,3,4,6,12. Factors of 18: 1,2,3,6,9,18. GCD is 6. Divide both by 6: 12÷6 = 2, 18÷6 = 3. Answer: 2/3.",
            "difficulty": 1
        },
        {
            "id": "rn_010",
            "text": "What property does a + (-a) = 0 represent?",
            "answer": "additive inverse",
            "hint": "When sum is zero, they are inverses",
            "solution": "When you add a number and its opposite and get zero, that's the additive inverse property. For example: 5 + (-5) = 0. The -a is called the additive inverse of a.",
            "difficulty": 1
        },
        # NEW QUESTIONS
        {
            "id": "rn_011",
            "text": "What is 3/4 - 5/6?",
            "answer": "-1/12",
            "hint": "LCM of 4 and 6 is 12. Convert: 9/12 - 10/12",
            "solution": "Find LCM of 4 and 6, which is 12. Convert: 3/4 = 9/12 and 5/6 = 10/12. Subtract: 9/12 - 10/12 = -1/12.",
            "difficulty": 2
        },
        {
            "id": "rn_012",
            "text": "Ram has 3/4 kg of rice. He uses 1/3 kg. How much is left?",
            "answer": "5/12",
            "hint": "Find 3/4 - 1/3 using LCM of 4 and 3",
            "solution": "We need 3/4 - 1/3. LCM of 4 and 3 is 12. Convert: 3/4 = 9/12, 1/3 = 4/12. Subtract: 9/12 - 4/12 = 5/12 kg left.",
            "difficulty": 3
        },
        {
            "id": "rn_013",
            "text": "What is (-2/5) × (-5/8)?",
            "answer": "1/4",
            "hint": "Negative × Negative = Positive. Multiply: (2×5)/(5×8)",
            "solution": "Negative times negative is positive. Multiply numerators: 2 × 5 = 10. Multiply denominators: 5 × 8 = 40. Result: 10/40 = 1/4.",
            "difficulty": 2
        },
        {
            "id": "rn_014",
            "text": "Which is greater: -3/4 or -5/6?",
            "answer": "-3/4",
            "hint": "Convert to same denominator and compare. Less negative = greater",
            "solution": "LCM of 4 and 6 is 12. -3/4 = -9/12, -5/6 = -10/12. Since -9 > -10, we have -9/12 > -10/12. So -3/4 is greater.",
            "difficulty": 2
        },
        {
            "id": "rn_015",
            "text": "Find three rational numbers between 0 and 1. Give the middle one.",
            "answer": "1/2",
            "hint": "Divide 0 to 1 into 4 parts: 1/4, 2/4, 3/4",
            "solution": "Three rational numbers between 0 and 1: 1/4, 1/2, 3/4. The middle one is 1/2 (or 2/4).",
            "difficulty": 1
        },
    ],

    # ============================================================
    # Chapter 2: Linear Equations in One Variable (रैखिक समीकरण)
    # ============================================================
    "linear_equations": [
        {
            "id": "le_001",
            "text": "Solve: x + 5 = 12",
            "answer": "7",
            "hint": "x = 12 - 5",
            "solution": "We need to find x. Subtract 5 from both sides: x + 5 - 5 = 12 - 5. This gives us x = 7.",
            "difficulty": 1
        },
        {
            "id": "le_002",
            "text": "Solve: 3x = 21",
            "answer": "7",
            "hint": "x = 21 ÷ 3",
            "solution": "We have 3 times x equals 21. Divide both sides by 3: 3x ÷ 3 = 21 ÷ 3. So x = 7.",
            "difficulty": 1
        },
        {
            "id": "le_003",
            "text": "Solve: 2x - 7 = 13",
            "answer": "10",
            "hint": "2x = 13 + 7 = 20, so x = 10",
            "solution": "First, add 7 to both sides: 2x - 7 + 7 = 13 + 7. This gives 2x = 20. Now divide by 2: x = 10.",
            "difficulty": 2
        },
        {
            "id": "le_004",
            "text": "Solve: 5x + 3 = 2x + 15",
            "answer": "4",
            "hint": "5x - 2x = 15 - 3, so 3x = 12, x = 4",
            "solution": "Move x terms to one side: 5x - 2x = 15 - 3. Simplify: 3x = 12. Divide by 3: x = 4.",
            "difficulty": 2
        },
        {
            "id": "le_005",
            "text": "Solve: (x + 4)/3 = 5",
            "answer": "11",
            "hint": "x + 4 = 15, so x = 11",
            "solution": "Multiply both sides by 3: x + 4 = 15. Subtract 4 from both sides: x = 11.",
            "difficulty": 2
        },
        {
            "id": "le_006",
            "text": "Solve: 4(x - 2) = 20",
            "answer": "7",
            "hint": "x - 2 = 5, so x = 7",
            "solution": "Divide both sides by 4: x - 2 = 5. Add 2 to both sides: x = 7.",
            "difficulty": 2
        },
        {
            "id": "le_007",
            "text": "If 7x - 3 = 25, find x",
            "answer": "4",
            "hint": "7x = 28, x = 4",
            "solution": "Add 3 to both sides: 7x = 25 + 3 = 28. Divide by 7: x = 4.",
            "difficulty": 2
        },
        {
            "id": "le_008",
            "text": "Solve: x/4 + 3 = 8",
            "answer": "20",
            "hint": "x/4 = 5, so x = 20",
            "solution": "Subtract 3 from both sides: x/4 = 5. Multiply both sides by 4: x = 20.",
            "difficulty": 2
        },
        {
            "id": "le_009",
            "text": "The sum of a number and 7 is 15. Find the number.",
            "answer": "8",
            "hint": "Let number = x, then x + 7 = 15",
            "solution": "Let the number be x. The equation is x + 7 = 15. Subtract 7: x = 15 - 7 = 8.",
            "difficulty": 1
        },
        {
            "id": "le_010",
            "text": "Three times a number minus 4 equals 11. Find the number.",
            "answer": "5",
            "hint": "3x - 4 = 11, so 3x = 15, x = 5",
            "solution": "Let the number be x. Equation: 3x - 4 = 11. Add 4: 3x = 15. Divide by 3: x = 5.",
            "difficulty": 2
        },
        # NEW QUESTIONS
        {
            "id": "le_011",
            "text": "Solve: 2(x + 3) = x + 10",
            "answer": "4",
            "hint": "Expand: 2x + 6 = x + 10, then solve",
            "solution": "Expand: 2x + 6 = x + 10. Subtract x from both sides: x + 6 = 10. Subtract 6: x = 4.",
            "difficulty": 2
        },
        {
            "id": "le_012",
            "text": "A number is doubled and 5 is added. The result is 17. Find the number.",
            "answer": "6",
            "hint": "Let number = x. Equation: 2x + 5 = 17",
            "solution": "Let the number be x. Equation: 2x + 5 = 17. Subtract 5: 2x = 12. Divide by 2: x = 6.",
            "difficulty": 2
        },
        {
            "id": "le_013",
            "text": "Solve: (3x - 2)/4 = 7",
            "answer": "10",
            "hint": "Multiply by 4: 3x - 2 = 28",
            "solution": "Multiply both sides by 4: 3x - 2 = 28. Add 2: 3x = 30. Divide by 3: x = 10.",
            "difficulty": 3
        },
        {
            "id": "le_014",
            "text": "The perimeter of a rectangle is 30 cm. Length is twice the width. Find the width.",
            "answer": "5",
            "hint": "Let width = w, length = 2w. Perimeter = 2(l+w) = 30",
            "solution": "Let width = w, length = 2w. Perimeter = 2(2w + w) = 2(3w) = 6w = 30. So w = 5 cm.",
            "difficulty": 3
        },
        {
            "id": "le_015",
            "text": "Solve: 5(x - 1) = 3(x + 3)",
            "answer": "7",
            "hint": "Expand both sides: 5x - 5 = 3x + 9",
            "solution": "Expand: 5x - 5 = 3x + 9. Subtract 3x: 2x - 5 = 9. Add 5: 2x = 14. Divide by 2: x = 7.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 3: Understanding Quadrilaterals (चतुर्भुज)
    # ============================================================
    "quadrilaterals": [
        {
            "id": "qu_001",
            "text": "What is the sum of all angles in a quadrilateral?",
            "answer": "360",
            "hint": "Sum of angles = (n-2) × 180 = 2 × 180 = 360",
            "solution": "A quadrilateral has 4 sides. The formula is (n-2) × 180, where n is number of sides. So (4-2) × 180 = 2 × 180 = 360 degrees.",
            "difficulty": 1
        },
        {
            "id": "qu_002",
            "text": "How many sides does a hexagon have?",
            "answer": "6",
            "hint": "Hex = 6",
            "solution": "The prefix 'hex' means 6. So a hexagon has 6 sides. Think of it like: tri=3, quad=4, penta=5, hex=6.",
            "difficulty": 1
        },
        {
            "id": "qu_003",
            "text": "Each angle of a rectangle is how many degrees?",
            "answer": "90",
            "hint": "All angles in a rectangle are right angles",
            "solution": "A rectangle has four right angles. A right angle is exactly 90 degrees. So each angle is 90°.",
            "difficulty": 1
        },
        {
            "id": "qu_004",
            "text": "In a parallelogram, opposite angles are ___? (equal/unequal)",
            "answer": "equal",
            "hint": "Property of parallelogram",
            "solution": "In a parallelogram, opposite angles are always equal. If one angle is 60°, the opposite one is also 60°. The adjacent angles add up to 180°.",
            "difficulty": 1
        },
        {
            "id": "qu_005",
            "text": "A quadrilateral with all sides equal and all angles 90° is called?",
            "answer": "square",
            "hint": "Equal sides + right angles = ?",
            "solution": "When all four sides are equal AND all four angles are 90°, it's a square. A rhombus has equal sides but not 90° angles. A rectangle has 90° angles but not equal sides.",
            "difficulty": 1
        },
        {
            "id": "qu_006",
            "text": "Three angles of a quadrilateral are 80°, 90°, 100°. Find the fourth.",
            "answer": "90",
            "hint": "Sum = 360, so fourth = 360 - 80 - 90 - 100",
            "solution": "Sum of all angles = 360°. Add the three known angles: 80 + 90 + 100 = 270. Fourth angle = 360 - 270 = 90°.",
            "difficulty": 2
        },
        {
            "id": "qu_007",
            "text": "How many diagonals does a quadrilateral have?",
            "answer": "2",
            "hint": "Connect opposite corners",
            "solution": "A diagonal connects two non-adjacent corners. In a quadrilateral, you can draw one diagonal from corner A to C, and another from B to D. Total: 2 diagonals.",
            "difficulty": 1
        },
        {
            "id": "qu_008",
            "text": "In a rhombus, diagonals bisect each other at what angle?",
            "answer": "90",
            "hint": "Diagonals of rhombus are perpendicular",
            "solution": "In a rhombus, the diagonals are perpendicular bisectors of each other. Perpendicular means they meet at 90 degrees.",
            "difficulty": 2
        },
        {
            "id": "qu_009",
            "text": "A trapezium has how many pairs of parallel sides?",
            "answer": "1",
            "hint": "Only one pair of opposite sides is parallel",
            "solution": "A trapezium (or trapezoid) has exactly one pair of parallel sides. These parallel sides are called the bases. The other two sides are not parallel.",
            "difficulty": 1
        },
        {
            "id": "qu_010",
            "text": "Sum of adjacent angles in a parallelogram is?",
            "answer": "180",
            "hint": "Adjacent angles are supplementary",
            "solution": "In a parallelogram, adjacent angles (angles next to each other) are supplementary, meaning they add up to 180°. This is because the sides are parallel.",
            "difficulty": 2
        },
        # NEW QUESTIONS
        {
            "id": "qu_011",
            "text": "What is the sum of interior angles of a pentagon?",
            "answer": "540",
            "hint": "(n-2) × 180 = (5-2) × 180",
            "solution": "Formula: (n-2) × 180 where n = number of sides. For pentagon: (5-2) × 180 = 3 × 180 = 540°.",
            "difficulty": 2
        },
        {
            "id": "qu_012",
            "text": "Each interior angle of a regular hexagon is how many degrees?",
            "answer": "120",
            "hint": "Total = (6-2)×180 = 720. Each = 720/6",
            "solution": "Total sum = (6-2) × 180 = 720°. In a regular hexagon, all angles are equal. Each angle = 720 ÷ 6 = 120°.",
            "difficulty": 3
        },
        {
            "id": "qu_013",
            "text": "A parallelogram has one angle 70°. What are the other three angles?",
            "answer": "110",
            "hint": "Opposite angles equal, adjacent angles sum to 180",
            "solution": "Opposite angle is also 70°. Adjacent angles = 180 - 70 = 110°. So angles are: 70°, 110°, 70°, 110°. The adjacent angle is 110°.",
            "difficulty": 2
        },
        {
            "id": "qu_014",
            "text": "How many diagonals does a hexagon have?",
            "answer": "9",
            "hint": "Formula: n(n-3)/2 where n=6",
            "solution": "Number of diagonals = n(n-3)/2 = 6(6-3)/2 = 6×3/2 = 9 diagonals.",
            "difficulty": 3
        },
        {
            "id": "qu_015",
            "text": "A kite has two pairs of equal adjacent sides. How many axes of symmetry does it have?",
            "answer": "1",
            "hint": "Think about folding the kite",
            "solution": "A kite has exactly 1 axis of symmetry - the diagonal that connects the vertices where unequal sides meet.",
            "difficulty": 2
        },
    ],

    # ============================================================
    # Chapter 4: Data Handling (आँकड़ों का प्रबंधन)
    # ============================================================
    "data_handling": [
        {
            "id": "dh_001",
            "text": "Find the mean of 5, 10, 15, 20, 25",
            "answer": "15",
            "hint": "Mean = Sum/Count = 75/5 = 15",
            "solution": "Mean is the average. Add all numbers: 5+10+15+20+25 = 75. Count of numbers: 5. Mean = 75 ÷ 5 = 15.",
            "difficulty": 1
        },
        {
            "id": "dh_002",
            "text": "Find the median of 3, 7, 2, 9, 5",
            "answer": "5",
            "hint": "Arrange: 2,3,5,7,9. Middle value = 5",
            "solution": "First arrange in order: 2, 3, 5, 7, 9. There are 5 numbers (odd count). The middle one is the 3rd number, which is 5.",
            "difficulty": 2
        },
        {
            "id": "dh_003",
            "text": "Find the mode of 4, 6, 4, 8, 4, 9",
            "answer": "4",
            "hint": "Mode = most frequent value",
            "solution": "Mode is the number that appears most often. Count: 4 appears 3 times, 6 once, 8 once, 9 once. So mode = 4.",
            "difficulty": 1
        },
        {
            "id": "dh_004",
            "text": "Range of data 12, 5, 18, 3, 9 is?",
            "answer": "15",
            "hint": "Range = Max - Min = 18 - 3",
            "solution": "Range = Maximum value - Minimum value. Maximum is 18, minimum is 3. Range = 18 - 3 = 15.",
            "difficulty": 1
        },
        {
            "id": "dh_005",
            "text": "Probability of getting head in a coin toss is?",
            "answer": "0.5",
            "hint": "1 head out of 2 outcomes = 1/2",
            "solution": "A coin has 2 outcomes: head or tail. Only 1 is head. Probability = favorable outcomes / total outcomes = 1/2 = 0.5.",
            "difficulty": 1
        },
        {
            "id": "dh_006",
            "text": "A die is thrown. Probability of getting 6 is?",
            "answer": "1/6",
            "hint": "1 favorable out of 6 possible",
            "solution": "A die has 6 faces: 1,2,3,4,5,6. Only one face shows 6. Probability = 1/6.",
            "difficulty": 2
        },
        {
            "id": "dh_007",
            "text": "Mean of first 5 natural numbers is?",
            "answer": "3",
            "hint": "(1+2+3+4+5)/5 = 15/5 = 3",
            "solution": "First 5 natural numbers: 1,2,3,4,5. Sum = 1+2+3+4+5 = 15. Mean = 15/5 = 3.",
            "difficulty": 1
        },
        {
            "id": "dh_008",
            "text": "If mean of 5 numbers is 12, their sum is?",
            "answer": "60",
            "hint": "Sum = Mean × Count = 12 × 5",
            "solution": "Mean = Sum / Count. So Sum = Mean × Count. Sum = 12 × 5 = 60.",
            "difficulty": 2
        },
        {
            "id": "dh_009",
            "text": "Median of 2, 4, 6, 8 is?",
            "answer": "5",
            "hint": "Even count: average of middle two = (4+6)/2",
            "solution": "With 4 numbers (even count), median is average of the two middle values. Middle values are 4 and 6. Median = (4+6)/2 = 5.",
            "difficulty": 2
        },
        {
            "id": "dh_010",
            "text": "In a pie chart, total angle is how many degrees?",
            "answer": "360",
            "hint": "Full circle = 360°",
            "solution": "A pie chart is a full circle. A complete circle has 360 degrees. So total angle in a pie chart is always 360°.",
            "difficulty": 1
        },
        # NEW QUESTIONS
        {
            "id": "dh_011",
            "text": "A die is thrown. Probability of getting an even number is?",
            "answer": "1/2",
            "hint": "Even numbers on die: 2, 4, 6 (3 outcomes)",
            "solution": "Even numbers: 2, 4, 6 = 3 outcomes. Total outcomes = 6. Probability = 3/6 = 1/2.",
            "difficulty": 2
        },
        {
            "id": "dh_012",
            "text": "Find the mean of 12, 15, 18, 21, 24",
            "answer": "18",
            "hint": "Sum = 90, Count = 5",
            "solution": "Sum = 12+15+18+21+24 = 90. Count = 5. Mean = 90/5 = 18.",
            "difficulty": 1
        },
        {
            "id": "dh_013",
            "text": "Data: 3, 5, 7, 5, 9, 5, 11. What is the mode?",
            "answer": "5",
            "hint": "Which number appears most often?",
            "solution": "Count each: 3(once), 5(three times), 7(once), 9(once), 11(once). Mode = 5 (appears 3 times).",
            "difficulty": 1
        },
        {
            "id": "dh_014",
            "text": "A bag has 3 red and 7 blue balls. Probability of picking red?",
            "answer": "3/10",
            "hint": "P = favorable/total = 3/(3+7)",
            "solution": "Total balls = 3 + 7 = 10. Red balls = 3. Probability = 3/10.",
            "difficulty": 2
        },
        {
            "id": "dh_015",
            "text": "Mean of 4 numbers is 20. Three numbers are 15, 18, 25. Find the fourth.",
            "answer": "22",
            "hint": "Sum = 20×4 = 80. Fourth = 80 - (15+18+25)",
            "solution": "Sum of 4 numbers = 20 × 4 = 80. Sum of three = 15+18+25 = 58. Fourth = 80 - 58 = 22.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 5: Squares and Square Roots (वर्ग और वर्गमूल)
    # ============================================================
    "squares_roots": [
        {
            "id": "sr_001",
            "text": "What is 12²?",
            "answer": "144",
            "hint": "12 × 12 = 144",
            "solution": "12 squared means 12 times 12. Calculate: 12 × 12 = 144.",
            "difficulty": 1
        },
        {
            "id": "sr_002",
            "text": "What is √81?",
            "answer": "9",
            "hint": "9 × 9 = 81",
            "solution": "We need a number that when multiplied by itself gives 81. Try 9: 9 × 9 = 81. So √81 = 9.",
            "difficulty": 1
        },
        {
            "id": "sr_003",
            "text": "What is 15²?",
            "answer": "225",
            "hint": "15 × 15 = 225",
            "solution": "15 squared = 15 × 15. Calculate: 15 × 15 = 225.",
            "difficulty": 1
        },
        {
            "id": "sr_004",
            "text": "What is √169?",
            "answer": "13",
            "hint": "13 × 13 = 169",
            "solution": "We need to find what number times itself equals 169. Try 13: 13 × 13 = 169. So √169 = 13.",
            "difficulty": 2
        },
        {
            "id": "sr_005",
            "text": "Is 50 a perfect square? (yes/no)",
            "answer": "no",
            "hint": "7² = 49, 8² = 64. 50 is between them.",
            "solution": "Check: 7² = 49 and 8² = 64. Since 50 is between 49 and 64, there's no whole number whose square is 50. So no, 50 is not a perfect square.",
            "difficulty": 2
        },
        {
            "id": "sr_006",
            "text": "What is √(36/49)?",
            "answer": "6/7",
            "hint": "√36/√49 = 6/7",
            "solution": "For a fraction under square root, take square root of numerator and denominator separately. √36 = 6, √49 = 7. So √(36/49) = 6/7.",
            "difficulty": 2
        },
        {
            "id": "sr_007",
            "text": "Find the square of 25",
            "answer": "625",
            "hint": "25 × 25 = 625",
            "solution": "Square of 25 = 25 × 25 = 625. Tip: For numbers ending in 5, the answer ends in 25 and starts with n×(n+1) where n is the digit before 5.",
            "difficulty": 1
        },
        {
            "id": "sr_008",
            "text": "What is √196?",
            "answer": "14",
            "hint": "14 × 14 = 196",
            "solution": "Find what number squared gives 196. Try 14: 14 × 14 = 196. So √196 = 14.",
            "difficulty": 2
        },
        {
            "id": "sr_009",
            "text": "Between which two numbers does √50 lie?",
            "answer": "7",
            "hint": "7² = 49, 8² = 64. √50 is closer to 7",
            "solution": "We know 7² = 49 and 8² = 64. Since 50 is between 49 and 64, √50 is between 7 and 8. It's closer to 7 since 50 is closer to 49.",
            "difficulty": 2
        },
        {
            "id": "sr_010",
            "text": "What is 11²?",
            "answer": "121",
            "hint": "11 × 11 = 121",
            "solution": "11 squared = 11 × 11 = 121. Quick trick: For 11², it's always 121!",
            "difficulty": 1
        },
        # NEW QUESTIONS
        {
            "id": "sr_011",
            "text": "What is √256?",
            "answer": "16",
            "hint": "16 × 16 = 256",
            "solution": "We need √256. Try 16: 16 × 16 = 256. So √256 = 16.",
            "difficulty": 2
        },
        {
            "id": "sr_012",
            "text": "What is 19²?",
            "answer": "361",
            "hint": "19 × 19 = 361 (or use 20² - 2×20 + 1)",
            "solution": "19² = 19 × 19 = 361. Shortcut: (20-1)² = 400 - 40 + 1 = 361.",
            "difficulty": 2
        },
        {
            "id": "sr_013",
            "text": "Find the smallest number by which 72 must be multiplied to get a perfect square.",
            "answer": "2",
            "hint": "72 = 2³ × 3². Need one more 2 to make 2⁴",
            "solution": "72 = 8 × 9 = 2³ × 3². For perfect square, all powers must be even. 3² is fine. 2³ needs one more 2. Multiply by 2 to get 144 = 12².",
            "difficulty": 3
        },
        {
            "id": "sr_014",
            "text": "A square has area 289 cm². What is its side?",
            "answer": "17",
            "hint": "Side = √Area = √289",
            "solution": "Area of square = side². So side = √289 = 17 cm.",
            "difficulty": 2
        },
        {
            "id": "sr_015",
            "text": "What is √(0.04)?",
            "answer": "0.2",
            "hint": "0.04 = 4/100 = (2/10)²",
            "solution": "0.04 = 4/100. √(4/100) = √4/√100 = 2/10 = 0.2.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 6: Cubes and Cube Roots (घन और घनमूल)
    # ============================================================
    "cubes_roots": [
        {
            "id": "cr_001",
            "text": "What is 4³?",
            "answer": "64",
            "hint": "4 × 4 × 4 = 64",
            "solution": "4 cubed means 4 × 4 × 4. First: 4 × 4 = 16. Then: 16 × 4 = 64.",
            "difficulty": 1
        },
        {
            "id": "cr_002",
            "text": "What is ∛27?",
            "answer": "3",
            "hint": "3 × 3 × 3 = 27",
            "solution": "Cube root of 27 is the number that when multiplied by itself 3 times gives 27. That's 3, because 3 × 3 × 3 = 27.",
            "difficulty": 1
        },
        {
            "id": "cr_003",
            "text": "What is 5³?",
            "answer": "125",
            "hint": "5 × 5 × 5 = 125",
            "solution": "5 cubed = 5 × 5 × 5. First: 5 × 5 = 25. Then: 25 × 5 = 125.",
            "difficulty": 1
        },
        {
            "id": "cr_004",
            "text": "What is ∛125?",
            "answer": "5",
            "hint": "5 × 5 × 5 = 125",
            "solution": "We need a number that cubed gives 125. Try 5: 5 × 5 × 5 = 125. So ∛125 = 5.",
            "difficulty": 1
        },
        {
            "id": "cr_005",
            "text": "What is 3³?",
            "answer": "27",
            "hint": "3 × 3 × 3 = 27",
            "solution": "3 cubed = 3 × 3 × 3 = 9 × 3 = 27.",
            "difficulty": 1
        },
        {
            "id": "cr_006",
            "text": "What is ∛64?",
            "answer": "4",
            "hint": "4 × 4 × 4 = 64",
            "solution": "Cube root of 64: what number times itself three times equals 64? It's 4, because 4 × 4 × 4 = 64.",
            "difficulty": 1
        },
        {
            "id": "cr_007",
            "text": "What is 6³?",
            "answer": "216",
            "hint": "6 × 6 × 6 = 216",
            "solution": "6 cubed = 6 × 6 × 6. First: 6 × 6 = 36. Then: 36 × 6 = 216.",
            "difficulty": 2
        },
        {
            "id": "cr_008",
            "text": "What is ∛216?",
            "answer": "6",
            "hint": "6 × 6 × 6 = 216",
            "solution": "We need a number whose cube is 216. Try 6: 6 × 6 × 6 = 216. So ∛216 = 6.",
            "difficulty": 2
        },
        {
            "id": "cr_009",
            "text": "Is 100 a perfect cube? (yes/no)",
            "answer": "no",
            "hint": "4³=64, 5³=125. 100 is not a perfect cube.",
            "solution": "Check: 4³ = 64 and 5³ = 125. Since 100 is between 64 and 125 but not equal to any cube, 100 is not a perfect cube.",
            "difficulty": 2
        },
        {
            "id": "cr_010",
            "text": "What is 10³?",
            "answer": "1000",
            "hint": "10 × 10 × 10 = 1000",
            "solution": "10 cubed = 10 × 10 × 10 = 100 × 10 = 1000. Easy to remember: 10³ has 3 zeros!",
            "difficulty": 1
        },
        # NEW QUESTIONS
        {
            "id": "cr_011",
            "text": "What is ∛343?",
            "answer": "7",
            "hint": "7 × 7 × 7 = 343",
            "solution": "Try 7: 7 × 7 = 49, 49 × 7 = 343. So ∛343 = 7.",
            "difficulty": 2
        },
        {
            "id": "cr_012",
            "text": "What is 8³?",
            "answer": "512",
            "hint": "8 × 8 × 8 = 512",
            "solution": "8³ = 8 × 8 × 8 = 64 × 8 = 512.",
            "difficulty": 2
        },
        {
            "id": "cr_013",
            "text": "A cube has volume 729 cm³. What is its side?",
            "answer": "9",
            "hint": "Side = ∛Volume = ∛729",
            "solution": "Volume of cube = side³. So side = ∛729 = 9 cm (since 9×9×9 = 729).",
            "difficulty": 2
        },
        {
            "id": "cr_014",
            "text": "What is (-3)³?",
            "answer": "-27",
            "hint": "(-3) × (-3) × (-3) = 9 × (-3) = -27",
            "solution": "(-3)³ = (-3) × (-3) × (-3) = 9 × (-3) = -27. Odd power of negative = negative.",
            "difficulty": 2
        },
        {
            "id": "cr_015",
            "text": "What is ∛(-8)?",
            "answer": "-2",
            "hint": "(-2) × (-2) × (-2) = -8",
            "solution": "We need a number whose cube is -8. Try -2: (-2)³ = -8. So ∛(-8) = -2.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 7: Comparing Quantities (राशियों की तुलना)
    # ============================================================
    "comparing_quantities": [
        {
            "id": "cq_001",
            "text": "What is 25% of 200?",
            "answer": "50",
            "hint": "25% = 1/4, so 200/4 = 50",
            "solution": "25% means 25/100 = 1/4. So 25% of 200 = 200 ÷ 4 = 50. Or: (25/100) × 200 = 50.",
            "difficulty": 1
        },
        {
            "id": "cq_002",
            "text": "Convert 3/4 to percentage",
            "answer": "75",
            "hint": "3/4 × 100 = 75%",
            "solution": "To convert fraction to percentage, multiply by 100. So 3/4 × 100 = 300/4 = 75%.",
            "difficulty": 1
        },
        {
            "id": "cq_003",
            "text": "A shirt costs ₹500. After 10% discount, price is?",
            "answer": "450",
            "hint": "Discount = 50, Price = 500 - 50 = 450",
            "solution": "10% of 500 = 50 (the discount amount). New price = 500 - 50 = ₹450.",
            "difficulty": 2
        },
        {
            "id": "cq_004",
            "text": "Simple Interest on ₹1000 at 5% for 2 years is?",
            "answer": "100",
            "hint": "SI = P×R×T/100 = 1000×5×2/100 = 100",
            "solution": "Simple Interest formula: SI = (P × R × T)/100. Here P=1000, R=5, T=2. SI = (1000 × 5 × 2)/100 = 10000/100 = ₹100.",
            "difficulty": 2
        },
        {
            "id": "cq_005",
            "text": "If CP = ₹80 and SP = ₹100, profit is?",
            "answer": "20",
            "hint": "Profit = SP - CP = 100 - 80",
            "solution": "Profit = Selling Price - Cost Price = 100 - 80 = ₹20.",
            "difficulty": 1
        },
        {
            "id": "cq_006",
            "text": "Profit% when CP=₹50 and Profit=₹10 is?",
            "answer": "20",
            "hint": "Profit% = (Profit/CP)×100 = (10/50)×100 = 20%",
            "solution": "Profit percentage = (Profit/Cost Price) × 100 = (10/50) × 100 = 0.2 × 100 = 20%.",
            "difficulty": 2
        },
        {
            "id": "cq_007",
            "text": "What is 15% of 400?",
            "answer": "60",
            "hint": "15% of 400 = (15/100)×400 = 60",
            "solution": "15% of 400 = (15/100) × 400 = 15 × 4 = 60.",
            "difficulty": 1
        },
        {
            "id": "cq_008",
            "text": "A book's MRP is ₹200. After 15% discount, price is?",
            "answer": "170",
            "hint": "Discount = 30, Price = 200 - 30 = 170",
            "solution": "15% of 200 = 30 (discount). Sale price = 200 - 30 = ₹170.",
            "difficulty": 2
        },
        {
            "id": "cq_009",
            "text": "If SP = ₹90 and Loss = ₹10, find CP",
            "answer": "100",
            "hint": "CP = SP + Loss = 90 + 10",
            "solution": "When there's a loss: Cost Price = Selling Price + Loss. CP = 90 + 10 = ₹100.",
            "difficulty": 2
        },
        {
            "id": "cq_010",
            "text": "Express 0.45 as percentage",
            "answer": "45",
            "hint": "0.45 × 100 = 45%",
            "solution": "To convert decimal to percentage, multiply by 100. 0.45 × 100 = 45%.",
            "difficulty": 1
        },
        # NEW QUESTIONS
        {
            "id": "cq_011",
            "text": "A price increased from ₹80 to ₹100. Find % increase.",
            "answer": "25",
            "hint": "Increase = 20. % = (20/80)×100",
            "solution": "Increase = 100 - 80 = 20. % increase = (20/80) × 100 = 25%.",
            "difficulty": 2
        },
        {
            "id": "cq_012",
            "text": "Compound Interest on ₹1000 at 10% for 2 years is?",
            "answer": "210",
            "hint": "A = P(1+R/100)² = 1000(1.1)² = 1210. CI = A-P",
            "solution": "A = 1000 × (1.1)² = 1000 × 1.21 = 1210. CI = 1210 - 1000 = ₹210.",
            "difficulty": 3
        },
        {
            "id": "cq_013",
            "text": "A shopkeeper sold an item for ₹480 at 20% profit. Find CP.",
            "answer": "400",
            "hint": "SP = CP + 20% of CP = 1.2 × CP",
            "solution": "SP = CP × 1.2. So CP = 480/1.2 = ₹400.",
            "difficulty": 3
        },
        {
            "id": "cq_014",
            "text": "What is 12.5% as a fraction in lowest terms?",
            "answer": "1/8",
            "hint": "12.5/100 = 125/1000 = 1/8",
            "solution": "12.5% = 12.5/100 = 125/1000 = 1/8.",
            "difficulty": 2
        },
        {
            "id": "cq_015",
            "text": "Population grew from 10000 to 12100 in 2 years. Find annual growth rate %.",
            "answer": "10",
            "hint": "12100/10000 = 1.21 = (1+r)². So r = 0.1",
            "solution": "12100/10000 = 1.21 = (1+r)². Taking root: 1+r = 1.1. So r = 0.1 = 10%.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 8: Algebraic Expressions (बीजीय व्यंजक)
    # ============================================================
    "algebraic_expressions": [
        {
            "id": "ae_001",
            "text": "Simplify: 3x + 5x",
            "answer": "8x",
            "hint": "Add coefficients: 3 + 5 = 8",
            "solution": "These are like terms (both have x). Add the coefficients: 3 + 5 = 8. So 3x + 5x = 8x.",
            "difficulty": 1
        },
        {
            "id": "ae_002",
            "text": "Find value of 2x + 3 when x = 4",
            "answer": "11",
            "hint": "2(4) + 3 = 8 + 3 = 11",
            "solution": "Substitute x = 4: 2(4) + 3 = 8 + 3 = 11.",
            "difficulty": 1
        },
        {
            "id": "ae_003",
            "text": "Multiply: 2x × 3x",
            "answer": "6x²",
            "hint": "2×3=6, x×x=x²",
            "solution": "Multiply coefficients: 2 × 3 = 6. Multiply variables: x × x = x². Result: 6x².",
            "difficulty": 2
        },
        {
            "id": "ae_004",
            "text": "Expand: (x + 2)²",
            "answer": "x² + 4x + 4",
            "hint": "(a+b)² = a² + 2ab + b²",
            "solution": "Use identity (a+b)² = a² + 2ab + b². Here a=x, b=2. So: x² + 2(x)(2) + 2² = x² + 4x + 4.",
            "difficulty": 2
        },
        {
            "id": "ae_005",
            "text": "Simplify: 7y - 3y + 2y",
            "answer": "6y",
            "hint": "7 - 3 + 2 = 6",
            "solution": "All terms have y, so add/subtract coefficients: 7 - 3 + 2 = 6. Answer: 6y.",
            "difficulty": 1
        },
        {
            "id": "ae_006",
            "text": "What is (a + b)(a - b)?",
            "answer": "a² - b²",
            "hint": "Difference of squares identity",
            "solution": "This is the difference of squares identity. (a + b)(a - b) = a² - b². The middle terms cancel out!",
            "difficulty": 2
        },
        {
            "id": "ae_007",
            "text": "Find: x² when x = 5",
            "answer": "25",
            "hint": "5² = 25",
            "solution": "Substitute x = 5: x² = 5² = 5 × 5 = 25.",
            "difficulty": 1
        },
        {
            "id": "ae_008",
            "text": "Simplify: 4x² + 2x²",
            "answer": "6x²",
            "hint": "4 + 2 = 6",
            "solution": "Both terms are like terms (both have x²). Add coefficients: 4 + 2 = 6. Answer: 6x².",
            "difficulty": 1
        },
        {
            "id": "ae_009",
            "text": "Expand: (x - 3)²",
            "answer": "x² - 6x + 9",
            "hint": "(a-b)² = a² - 2ab + b²",
            "solution": "Use identity (a-b)² = a² - 2ab + b². Here a=x, b=3. So: x² - 2(x)(3) + 3² = x² - 6x + 9.",
            "difficulty": 2
        },
        {
            "id": "ae_010",
            "text": "Factorize: x² - 9",
            "answer": "(x+3)(x-3)",
            "hint": "a² - b² = (a+b)(a-b)",
            "solution": "This is difference of squares. x² - 9 = x² - 3². Using a² - b² = (a+b)(a-b), we get (x+3)(x-3).",
            "difficulty": 3
        },
        # NEW QUESTIONS
        {
            "id": "ae_011",
            "text": "Expand: (2x + 3)(x - 1)",
            "answer": "2x² + x - 3",
            "hint": "Use FOIL: First, Outer, Inner, Last",
            "solution": "FOIL: 2x×x + 2x×(-1) + 3×x + 3×(-1) = 2x² - 2x + 3x - 3 = 2x² + x - 3.",
            "difficulty": 2
        },
        {
            "id": "ae_012",
            "text": "Find value of x² - 2x + 1 when x = 3",
            "answer": "4",
            "hint": "Substitute x=3: 9 - 6 + 1",
            "solution": "x² - 2x + 1 = 3² - 2(3) + 1 = 9 - 6 + 1 = 4. (Or recognize (x-1)² = 2² = 4)",
            "difficulty": 2
        },
        {
            "id": "ae_013",
            "text": "Factorize: x² + 5x + 6",
            "answer": "(x+2)(x+3)",
            "hint": "Find two numbers that multiply to 6 and add to 5",
            "solution": "We need numbers that multiply to 6 and add to 5: 2 and 3. So x² + 5x + 6 = (x+2)(x+3).",
            "difficulty": 3
        },
        {
            "id": "ae_014",
            "text": "Simplify: (3x²y)(2xy²)",
            "answer": "6x³y³",
            "hint": "Multiply: 3×2=6, x²×x=x³, y×y²=y³",
            "solution": "Coefficients: 3×2 = 6. For x: x²×x = x³. For y: y×y² = y³. Answer: 6x³y³.",
            "difficulty": 3
        },
        {
            "id": "ae_015",
            "text": "What is (x + y + z)² expanded? Give the number of terms.",
            "answer": "6",
            "hint": "x² + y² + z² + 2xy + 2yz + 2zx has 6 terms",
            "solution": "(x+y+z)² = x² + y² + z² + 2xy + 2yz + 2zx. Count: 6 terms.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 9: Mensuration (क्षेत्रमिति)
    # ============================================================
    "mensuration": [
        {
            "id": "me_001",
            "text": "Area of rectangle with length 8 cm and breadth 5 cm?",
            "answer": "40",
            "hint": "Area = l × b = 8 × 5",
            "solution": "Area of rectangle = length × breadth = 8 × 5 = 40 sq cm.",
            "difficulty": 1
        },
        {
            "id": "me_002",
            "text": "Perimeter of square with side 7 cm?",
            "answer": "28",
            "hint": "Perimeter = 4 × side = 4 × 7",
            "solution": "Perimeter of square = 4 × side = 4 × 7 = 28 cm.",
            "difficulty": 1
        },
        {
            "id": "me_003",
            "text": "Area of triangle with base 10 cm and height 6 cm?",
            "answer": "30",
            "hint": "Area = (1/2) × b × h = (1/2) × 10 × 6",
            "solution": "Area of triangle = (1/2) × base × height = (1/2) × 10 × 6 = 30 sq cm.",
            "difficulty": 1
        },
        {
            "id": "me_004",
            "text": "Volume of cube with side 4 cm?",
            "answer": "64",
            "hint": "Volume = side³ = 4³",
            "solution": "Volume of cube = side³ = 4³ = 4 × 4 × 4 = 64 cubic cm.",
            "difficulty": 2
        },
        {
            "id": "me_005",
            "text": "Area of square with side 9 cm?",
            "answer": "81",
            "hint": "Area = side² = 9²",
            "solution": "Area of square = side² = 9² = 81 sq cm.",
            "difficulty": 1
        },
        {
            "id": "me_006",
            "text": "Volume of cuboid 5×4×3 cm?",
            "answer": "60",
            "hint": "Volume = l × b × h = 5 × 4 × 3",
            "solution": "Volume of cuboid = length × breadth × height = 5 × 4 × 3 = 60 cubic cm.",
            "difficulty": 2
        },
        {
            "id": "me_007",
            "text": "Perimeter of rectangle 12 cm × 8 cm?",
            "answer": "40",
            "hint": "Perimeter = 2(l + b) = 2(12 + 8)",
            "solution": "Perimeter of rectangle = 2(length + breadth) = 2(12 + 8) = 2 × 20 = 40 cm.",
            "difficulty": 1
        },
        {
            "id": "me_008",
            "text": "Surface area of cube with side 3 cm?",
            "answer": "54",
            "hint": "SA = 6 × side² = 6 × 9",
            "solution": "Surface area of cube = 6 × side² = 6 × 3² = 6 × 9 = 54 sq cm.",
            "difficulty": 2
        },
        {
            "id": "me_009",
            "text": "Area of trapezium with parallel sides 8,6 cm and height 5 cm?",
            "answer": "35",
            "hint": "Area = (1/2)(a+b)×h = (1/2)(14)×5",
            "solution": "Area of trapezium = (1/2) × (sum of parallel sides) × height = (1/2) × (8+6) × 5 = (1/2) × 14 × 5 = 35 sq cm.",
            "difficulty": 2
        },
        {
            "id": "me_010",
            "text": "Circumference of circle with radius 7 cm? (Use π=22/7)",
            "answer": "44",
            "hint": "C = 2πr = 2 × 22/7 × 7 = 44",
            "solution": "Circumference = 2πr = 2 × (22/7) × 7 = 2 × 22 = 44 cm.",
            "difficulty": 2
        },
        # NEW QUESTIONS
        {
            "id": "me_011",
            "text": "Area of circle with radius 7 cm? (Use π=22/7)",
            "answer": "154",
            "hint": "A = πr² = (22/7) × 49",
            "solution": "Area = πr² = (22/7) × 7² = (22/7) × 49 = 22 × 7 = 154 sq cm.",
            "difficulty": 2
        },
        {
            "id": "me_012",
            "text": "Volume of cylinder with radius 7 cm and height 10 cm? (π=22/7)",
            "answer": "1540",
            "hint": "V = πr²h = (22/7) × 49 × 10",
            "solution": "Volume = πr²h = (22/7) × 7² × 10 = 22 × 7 × 10 = 1540 cubic cm.",
            "difficulty": 3
        },
        {
            "id": "me_013",
            "text": "A room is 6m × 4m × 3m. Find volume in cubic meters.",
            "answer": "72",
            "hint": "Volume = l × b × h",
            "solution": "Volume = 6 × 4 × 3 = 72 cubic meters.",
            "difficulty": 2
        },
        {
            "id": "me_014",
            "text": "Curved surface area of cylinder with radius 7 cm, height 10 cm? (π=22/7)",
            "answer": "440",
            "hint": "CSA = 2πrh",
            "solution": "CSA = 2πrh = 2 × (22/7) × 7 × 10 = 2 × 22 × 10 = 440 sq cm.",
            "difficulty": 3
        },
        {
            "id": "me_015",
            "text": "A rectangular field is 80m × 60m. Find its area in hectares. (1 hectare = 10000 m²)",
            "answer": "0.48",
            "hint": "Area = 4800 m². Convert to hectares.",
            "solution": "Area = 80 × 60 = 4800 m². In hectares: 4800/10000 = 0.48 hectares.",
            "difficulty": 3
        },
    ],

    # ============================================================
    # Chapter 10: Exponents and Powers (घातांक और घात)
    # ============================================================
    "exponents": [
        {
            "id": "ex_001",
            "text": "What is 2⁵?",
            "answer": "32",
            "hint": "2×2×2×2×2 = 32",
            "solution": "2⁵ means 2 multiplied 5 times: 2×2×2×2×2 = 4×4×2 = 32.",
            "difficulty": 1
        },
        {
            "id": "ex_002",
            "text": "What is 10⁰?",
            "answer": "1",
            "hint": "Any number to power 0 is 1",
            "solution": "Any non-zero number raised to the power 0 equals 1. So 10⁰ = 1. This is a rule of exponents!",
            "difficulty": 1
        },
        {
            "id": "ex_003",
            "text": "Simplify: 2³ × 2²",
            "answer": "32",
            "hint": "2³⁺² = 2⁵ = 32",
            "solution": "When multiplying same bases, add exponents: 2³ × 2² = 2³⁺² = 2⁵ = 32.",
            "difficulty": 2
        },
        {
            "id": "ex_004",
            "text": "What is 3⁴?",
            "answer": "81",
            "hint": "3×3×3×3 = 81",
            "solution": "3⁴ = 3×3×3×3 = 9×9 = 81.",
            "difficulty": 1
        },
        {
            "id": "ex_005",
            "text": "Simplify: 5⁶ ÷ 5⁴",
            "answer": "25",
            "hint": "5⁶⁻⁴ = 5² = 25",
            "solution": "When dividing same bases, subtract exponents: 5⁶ ÷ 5⁴ = 5⁶⁻⁴ = 5² = 25.",
            "difficulty": 2
        },
        {
            "id": "ex_006",
            "text": "What is (-2)³?",
            "answer": "-8",
            "hint": "(-2)×(-2)×(-2) = -8",
            "solution": "(-2)³ = (-2)×(-2)×(-2). First: (-2)×(-2) = 4. Then: 4×(-2) = -8. Odd power of negative = negative.",
            "difficulty": 2
        },
        {
            "id": "ex_007",
            "text": "Express 1000000 as power of 10",
            "answer": "10⁶",
            "hint": "Count the zeros: 6 zeros",
            "solution": "Count the zeros in 1000000: there are 6 zeros. So 1000000 = 10⁶.",
            "difficulty": 1
        },
        {
            "id": "ex_008",
            "text": "What is (2³)²?",
            "answer": "64",
            "hint": "(2³)² = 2⁶ = 64",
            "solution": "Power of a power: multiply exponents. (2³)² = 2³ˣ² = 2⁶ = 64.",
            "difficulty": 2
        },
        {
            "id": "ex_009",
            "text": "What is 7¹?",
            "answer": "7",
            "hint": "Any number to power 1 is itself",
            "solution": "Any number raised to power 1 equals itself. So 7¹ = 7.",
            "difficulty": 1
        },
        {
            "id": "ex_010",
            "text": "Simplify: (3²)³",
            "answer": "729",
            "hint": "(3²)³ = 3⁶ = 729",
            "solution": "Power of a power: multiply exponents. (3²)³ = 3²ˣ³ = 3⁶. Calculate: 3⁶ = 729.",
            "difficulty": 3
        },
        # NEW QUESTIONS
        {
            "id": "ex_011",
            "text": "Simplify: (2⁴ × 2³) ÷ 2⁵",
            "answer": "4",
            "hint": "2⁴⁺³⁻⁵ = 2² = 4",
            "solution": "Add exponents for multiply, subtract for divide: 2⁴⁺³⁻⁵ = 2² = 4.",
            "difficulty": 2
        },
        {
            "id": "ex_012",
            "text": "What is 2⁻³?",
            "answer": "1/8",
            "hint": "2⁻³ = 1/2³ = 1/8",
            "solution": "Negative exponent means reciprocal: 2⁻³ = 1/2³ = 1/8.",
            "difficulty": 2
        },
        {
            "id": "ex_013",
            "text": "Express 0.001 as a power of 10",
            "answer": "10⁻³",
            "hint": "0.001 = 1/1000 = 1/10³",
            "solution": "0.001 = 1/1000 = 1/10³ = 10⁻³.",
            "difficulty": 2
        },
        {
            "id": "ex_014",
            "text": "Simplify: (5/3)² × (3/5)²",
            "answer": "1",
            "hint": "These are reciprocals, so product = 1",
            "solution": "(5/3)² × (3/5)² = (5/3 × 3/5)² = 1² = 1. Or: 25/9 × 9/25 = 1.",
            "difficulty": 3
        },
        {
            "id": "ex_015",
            "text": "If 2ⁿ = 128, what is n?",
            "answer": "7",
            "hint": "128 = 2 × 64 = 2 × 2⁶ = 2⁷",
            "solution": "128 = 2⁷ (since 2,4,8,16,32,64,128). So n = 7.",
            "difficulty": 2
        },
    ],

    # ============================================================
    # SCIENCE CHAPTERS (MCQ + Short Answer)
    # ============================================================

    # ============================================================
    # Science: Materials & Matter (पदार्थ)
    # ============================================================
    "science_matter": [
        {
            "id": "sm_001",
            "text": "What are the three states of matter?",
            "answer": "solid liquid gas",
            "type": "text",
            "hint": "Think about ice, water, and steam",
            "solution": "The three states of matter are: Solid (fixed shape, fixed volume), Liquid (no fixed shape, fixed volume), Gas (no fixed shape, no fixed volume).",
            "difficulty": 1
        },
        {
            "id": "sm_002",
            "text": "Which state of matter has definite shape and volume?",
            "answer": "solid",
            "type": "mcq",
            "options": ["A. Solid", "B. Liquid", "C. Gas", "D. Plasma"],
            "hint": "Think about a rock or ice cube",
            "solution": "Solids have definite (fixed) shape and volume because particles are tightly packed.",
            "difficulty": 1
        },
        {
            "id": "sm_003",
            "text": "What is the process of liquid turning into gas called?",
            "answer": "evaporation",
            "type": "text",
            "hint": "Think about water disappearing from a wet floor",
            "solution": "Evaporation is when liquid turns to gas at its surface. It happens at any temperature below boiling point.",
            "difficulty": 1
        },
        {
            "id": "sm_004",
            "text": "At what temperature does water boil (in Celsius)?",
            "answer": "100",
            "type": "text",
            "hint": "Standard boiling point at sea level",
            "solution": "Water boils at 100°C (212°F) at standard atmospheric pressure (sea level).",
            "difficulty": 1
        },
        {
            "id": "sm_005",
            "text": "What is the process of gas turning directly into solid called?",
            "answer": "deposition",
            "type": "mcq",
            "options": ["A. Condensation", "B. Sublimation", "C. Deposition", "D. Freezing"],
            "hint": "Opposite of sublimation",
            "solution": "Deposition is gas → solid directly. Example: frost forming on cold surfaces.",
            "difficulty": 2
        },
        {
            "id": "sm_006",
            "text": "Which metal is liquid at room temperature?",
            "answer": "mercury",
            "type": "text",
            "hint": "Used in old thermometers",
            "solution": "Mercury (Hg) is the only metal that is liquid at room temperature. Its melting point is -39°C.",
            "difficulty": 2
        },
        {
            "id": "sm_007",
            "text": "What is the chemical formula of water?",
            "answer": "H2O",
            "type": "text",
            "hint": "2 hydrogen atoms, 1 oxygen atom",
            "solution": "Water is H₂O - two hydrogen atoms bonded to one oxygen atom.",
            "difficulty": 1
        },
        {
            "id": "sm_008",
            "text": "Which of these is a compound?",
            "answer": "C",
            "type": "mcq",
            "options": ["A. Oxygen", "B. Gold", "C. Water", "D. Iron"],
            "hint": "A compound has two or more different elements",
            "solution": "Water (H₂O) is a compound - made of hydrogen and oxygen. The others are elements.",
            "difficulty": 2
        },
        {
            "id": "sm_009",
            "text": "What happens to particles when a solid is heated?",
            "answer": "vibrate faster",
            "type": "text",
            "hint": "Particles gain energy",
            "solution": "When heated, particles gain kinetic energy and vibrate faster. This can lead to melting.",
            "difficulty": 2
        },
        {
            "id": "sm_010",
            "text": "What is sublimation?",
            "answer": "solid to gas",
            "type": "text",
            "hint": "Dry ice does this",
            "solution": "Sublimation is when a solid turns directly into gas without becoming liquid. Example: dry ice (solid CO₂).",
            "difficulty": 2
        },
    ],

    # ============================================================
    # Science: Life Processes (जीवन प्रक्रियाएं)
    # ============================================================
    "science_life": [
        {
            "id": "sl_001",
            "text": "What is the process by which plants make food called?",
            "answer": "photosynthesis",
            "type": "text",
            "hint": "Uses sunlight, water, and carbon dioxide",
            "solution": "Photosynthesis: Plants use sunlight + CO₂ + water → glucose + oxygen. Happens in chloroplasts.",
            "difficulty": 1
        },
        {
            "id": "sl_002",
            "text": "Which gas do plants release during photosynthesis?",
            "answer": "oxygen",
            "type": "mcq",
            "options": ["A. Carbon dioxide", "B. Nitrogen", "C. Oxygen", "D. Hydrogen"],
            "hint": "The gas we breathe",
            "solution": "Plants release oxygen (O₂) as a byproduct of photosynthesis.",
            "difficulty": 1
        },
        {
            "id": "sl_003",
            "text": "What is the powerhouse of the cell?",
            "answer": "mitochondria",
            "type": "text",
            "hint": "Produces ATP (energy)",
            "solution": "Mitochondria are called the powerhouse because they produce ATP through cellular respiration.",
            "difficulty": 2
        },
        {
            "id": "sl_004",
            "text": "What carries oxygen in blood?",
            "answer": "hemoglobin",
            "type": "text",
            "hint": "Red colored protein in RBCs",
            "solution": "Hemoglobin is a protein in red blood cells that binds to oxygen and carries it around the body.",
            "difficulty": 2
        },
        {
            "id": "sl_005",
            "text": "Which organ pumps blood in the human body?",
            "answer": "heart",
            "type": "mcq",
            "options": ["A. Brain", "B. Lungs", "C. Heart", "D. Kidney"],
            "hint": "Located in your chest",
            "solution": "The heart is a muscular organ that pumps blood throughout the body via blood vessels.",
            "difficulty": 1
        },
        {
            "id": "sl_006",
            "text": "How many chambers does the human heart have?",
            "answer": "4",
            "type": "text",
            "hint": "Two atria and two ventricles",
            "solution": "Human heart has 4 chambers: Right atrium, Right ventricle, Left atrium, Left ventricle.",
            "difficulty": 1
        },
        {
            "id": "sl_007",
            "text": "What is the basic unit of life?",
            "answer": "cell",
            "type": "text",
            "hint": "All living things are made of these",
            "solution": "The cell is the basic structural and functional unit of all living organisms.",
            "difficulty": 1
        },
        {
            "id": "sl_008",
            "text": "Where does digestion of food begin?",
            "answer": "mouth",
            "type": "mcq",
            "options": ["A. Stomach", "B. Mouth", "C. Small intestine", "D. Large intestine"],
            "hint": "Teeth and saliva start the process",
            "solution": "Digestion begins in the mouth with mechanical (chewing) and chemical (saliva/amylase) breakdown.",
            "difficulty": 1
        },
        {
            "id": "sl_009",
            "text": "What is the green pigment in plants called?",
            "answer": "chlorophyll",
            "type": "text",
            "hint": "Absorbs sunlight for photosynthesis",
            "solution": "Chlorophyll is the green pigment in chloroplasts that absorbs light energy for photosynthesis.",
            "difficulty": 2
        },
        {
            "id": "sl_010",
            "text": "Which blood vessels carry blood away from the heart?",
            "answer": "arteries",
            "type": "text",
            "hint": "Start with 'A' - Away from heart",
            "solution": "Arteries carry blood away from the heart. Veins carry blood towards the heart.",
            "difficulty": 2
        },
    ],

    # ============================================================
    # Science: Force & Motion (बल और गति)
    # ============================================================
    "science_force": [
        {
            "id": "sf_001",
            "text": "What is the SI unit of force?",
            "answer": "newton",
            "type": "text",
            "hint": "Named after a famous scientist",
            "solution": "The SI unit of force is Newton (N), named after Sir Isaac Newton.",
            "difficulty": 1
        },
        {
            "id": "sf_002",
            "text": "What force pulls objects towards Earth?",
            "answer": "gravity",
            "type": "mcq",
            "options": ["A. Friction", "B. Gravity", "C. Magnetism", "D. Tension"],
            "hint": "Why things fall down",
            "solution": "Gravity is the force of attraction between objects with mass. Earth's gravity pulls things downward.",
            "difficulty": 1
        },
        {
            "id": "sf_003",
            "text": "What is the formula for speed?",
            "answer": "distance/time",
            "type": "text",
            "hint": "Speed = ?/?",
            "solution": "Speed = Distance ÷ Time. Units: m/s or km/h.",
            "difficulty": 1
        },
        {
            "id": "sf_004",
            "text": "A car travels 100 km in 2 hours. What is its speed in km/h?",
            "answer": "50",
            "type": "text",
            "hint": "Speed = 100/2",
            "solution": "Speed = Distance/Time = 100 km / 2 hours = 50 km/h.",
            "difficulty": 1
        },
        {
            "id": "sf_005",
            "text": "Which force opposes motion between surfaces?",
            "answer": "friction",
            "type": "text",
            "hint": "Makes it hard to push heavy objects",
            "solution": "Friction is the force that opposes motion when two surfaces are in contact.",
            "difficulty": 1
        },
        {
            "id": "sf_006",
            "text": "What is Newton's First Law also called?",
            "answer": "inertia",
            "type": "mcq",
            "options": ["A. Law of Gravity", "B. Law of Inertia", "C. Law of Action", "D. Law of Energy"],
            "hint": "Objects at rest stay at rest",
            "solution": "Newton's First Law is the Law of Inertia: Objects maintain their state of motion unless acted upon by a force.",
            "difficulty": 2
        },
        {
            "id": "sf_007",
            "text": "What is the acceleration due to gravity on Earth (m/s²)?",
            "answer": "9.8",
            "type": "text",
            "hint": "Approximately 10 m/s²",
            "solution": "Acceleration due to gravity (g) on Earth is approximately 9.8 m/s² (often rounded to 10 m/s²).",
            "difficulty": 2
        },
        {
            "id": "sf_008",
            "text": "What is the unit of work and energy?",
            "answer": "joule",
            "type": "text",
            "hint": "Named after James Joule",
            "solution": "The SI unit of work and energy is Joule (J). 1 Joule = 1 Newton × 1 meter.",
            "difficulty": 2
        },
        {
            "id": "sf_009",
            "text": "What type of friction is the strongest?",
            "answer": "static",
            "type": "mcq",
            "options": ["A. Sliding friction", "B. Rolling friction", "C. Static friction", "D. Fluid friction"],
            "hint": "The friction before an object starts moving",
            "solution": "Static friction (before movement starts) is strongest. Rolling friction is weakest.",
            "difficulty": 2
        },
        {
            "id": "sf_010",
            "text": "Force = Mass × ?",
            "answer": "acceleration",
            "type": "text",
            "hint": "F = m × a (Newton's Second Law)",
            "solution": "Newton's Second Law: Force = Mass × Acceleration (F = ma).",
            "difficulty": 2
        },
    ],

    # ============================================================
    # Science: Light & Sound (प्रकाश और ध्वनि)
    # ============================================================
    "science_light": [
        {
            "id": "sli_001",
            "text": "What is the speed of light in vacuum (km/s)?",
            "answer": "300000",
            "type": "text",
            "hint": "About 3 × 10⁸ m/s",
            "solution": "Speed of light in vacuum is approximately 3 × 10⁸ m/s = 300,000 km/s.",
            "difficulty": 2
        },
        {
            "id": "sli_002",
            "text": "Which color of light has the longest wavelength?",
            "answer": "red",
            "type": "mcq",
            "options": ["A. Violet", "B. Blue", "C. Green", "D. Red"],
            "hint": "VIBGYOR - which is at one end?",
            "solution": "Red light has the longest wavelength. Violet has the shortest. Remember: VIBGYOR.",
            "difficulty": 2
        },
        {
            "id": "sli_003",
            "text": "What is the bouncing back of light called?",
            "answer": "reflection",
            "type": "text",
            "hint": "What mirrors do to light",
            "solution": "Reflection is when light bounces back from a surface. Mirrors reflect light.",
            "difficulty": 1
        },
        {
            "id": "sli_004",
            "text": "What is the bending of light when it passes from one medium to another?",
            "answer": "refraction",
            "type": "text",
            "hint": "Why a pencil looks bent in water",
            "solution": "Refraction is the bending of light when it passes between media of different densities.",
            "difficulty": 2
        },
        {
            "id": "sli_005",
            "text": "Sound cannot travel through:",
            "answer": "vacuum",
            "type": "mcq",
            "options": ["A. Air", "B. Water", "C. Steel", "D. Vacuum"],
            "hint": "Sound needs a medium",
            "solution": "Sound needs a medium (solid, liquid, or gas) to travel. It cannot travel through vacuum (empty space).",
            "difficulty": 1
        },
        {
            "id": "sli_006",
            "text": "What is the unit of frequency?",
            "answer": "hertz",
            "type": "text",
            "hint": "Abbreviated as Hz",
            "solution": "Frequency is measured in Hertz (Hz). 1 Hz = 1 vibration per second.",
            "difficulty": 1
        },
        {
            "id": "sli_007",
            "text": "What type of lens is used to correct short-sightedness?",
            "answer": "concave",
            "type": "mcq",
            "options": ["A. Convex lens", "B. Concave lens", "C. Plane mirror", "D. Convex mirror"],
            "hint": "Diverging lens",
            "solution": "Concave (diverging) lens is used for myopia (short-sightedness). Convex lens for hypermetropia.",
            "difficulty": 2
        },
        {
            "id": "sli_008",
            "text": "What is the range of human hearing (in Hz)?",
            "answer": "20 to 20000",
            "type": "text",
            "hint": "20 Hz to 20 kHz",
            "solution": "Humans can hear sounds from 20 Hz to 20,000 Hz (20 kHz). Below is infrasound, above is ultrasound.",
            "difficulty": 2
        },
        {
            "id": "sli_009",
            "text": "What splits white light into seven colors?",
            "answer": "prism",
            "type": "text",
            "hint": "A triangular glass object",
            "solution": "A prism disperses white light into its seven component colors (VIBGYOR) due to refraction.",
            "difficulty": 1
        },
        {
            "id": "sli_010",
            "text": "The angle of incidence equals the angle of:",
            "answer": "reflection",
            "type": "text",
            "hint": "Law of reflection",
            "solution": "Law of Reflection: Angle of incidence = Angle of reflection.",
            "difficulty": 1
        },
    ],

    # ============================================================
    # Science: Natural Resources (प्राकृतिक संसाधन)
    # ============================================================
    "science_nature": [
        {
            "id": "sn_001",
            "text": "What percentage of Earth is covered by water?",
            "answer": "71",
            "type": "text",
            "hint": "About 70%",
            "solution": "About 71% of Earth's surface is covered by water, mostly in oceans.",
            "difficulty": 1
        },
        {
            "id": "sn_002",
            "text": "Which gas is most abundant in Earth's atmosphere?",
            "answer": "nitrogen",
            "type": "mcq",
            "options": ["A. Oxygen", "B. Carbon dioxide", "C. Nitrogen", "D. Argon"],
            "hint": "About 78% of atmosphere",
            "solution": "Nitrogen makes up about 78% of Earth's atmosphere. Oxygen is about 21%.",
            "difficulty": 1
        },
        {
            "id": "sn_003",
            "text": "What is the main cause of global warming?",
            "answer": "greenhouse gases",
            "type": "text",
            "hint": "CO₂ and methane trap heat",
            "solution": "Greenhouse gases (CO₂, methane, etc.) trap heat in the atmosphere, causing global warming.",
            "difficulty": 2
        },
        {
            "id": "sn_004",
            "text": "Which layer of atmosphere protects us from UV rays?",
            "answer": "ozone",
            "type": "text",
            "hint": "O₃ layer in stratosphere",
            "solution": "The ozone layer (O₃) in the stratosphere absorbs harmful ultraviolet radiation from the Sun.",
            "difficulty": 2
        },
        {
            "id": "sn_005",
            "text": "Coal, petroleum, and natural gas are examples of:",
            "answer": "fossil fuels",
            "type": "text",
            "hint": "Formed from ancient dead organisms",
            "solution": "Fossil fuels are formed from remains of ancient plants and animals over millions of years.",
            "difficulty": 1
        },
        {
            "id": "sn_006",
            "text": "Which of these is a renewable energy source?",
            "answer": "D",
            "type": "mcq",
            "options": ["A. Coal", "B. Petroleum", "C. Natural gas", "D. Solar energy"],
            "hint": "Can be replenished naturally",
            "solution": "Solar energy is renewable - it won't run out. Fossil fuels (coal, petroleum, gas) are non-renewable.",
            "difficulty": 1
        },
        {
            "id": "sn_007",
            "text": "What is the water cycle also called?",
            "answer": "hydrological cycle",
            "type": "text",
            "hint": "Hydro means water",
            "solution": "The water cycle (hydrological cycle) describes how water evaporates, condenses, and precipitates.",
            "difficulty": 2
        },
        {
            "id": "sn_008",
            "text": "What is the main component of natural gas?",
            "answer": "methane",
            "type": "text",
            "hint": "CH₄",
            "solution": "Natural gas is mainly methane (CH₄), along with small amounts of other hydrocarbons.",
            "difficulty": 2
        },
        {
            "id": "sn_009",
            "text": "Deforestation leads to:",
            "answer": "soil erosion",
            "type": "mcq",
            "options": ["A. More rainfall", "B. Soil erosion", "C. Cooler climate", "D. More oxygen"],
            "hint": "Tree roots hold soil together",
            "solution": "Without trees, soil is not held together and gets washed away - this is soil erosion.",
            "difficulty": 2
        },
        {
            "id": "sn_010",
            "text": "What is the process of maintaining ecological balance called?",
            "answer": "conservation",
            "type": "text",
            "hint": "Protecting natural resources",
            "solution": "Conservation is the careful management and protection of natural resources and the environment.",
            "difficulty": 1
        },
    ],
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def check_answer(correct: str, student: str) -> bool:
    """
    Basic answer check - for robust checking use evaluator.py

    Handles:
    - Case-insensitive comparison
    - Numeric comparison
    - Fraction comparison
    - MCQ letter answers (A, B, C, D)
    """
    try:
        # Clean up answers
        correct_clean = str(correct).lower().strip()
        student_clean = str(student).lower().strip()

        # Direct match
        if correct_clean == student_clean:
            return True

        # MCQ: Accept just the letter or full option
        if correct_clean in ['a', 'b', 'c', 'd']:
            if student_clean.startswith(correct_clean):
                return True

        # Multi-word answers: check if all words are present
        if ' ' in correct_clean:
            correct_words = set(correct_clean.split())
            student_words = set(student_clean.split())
            if correct_words.issubset(student_words) or student_words.issubset(correct_words):
                return True

        # Try numeric comparison
        try:
            # Handle fractions like "6/7"
            if '/' in correct_clean:
                parts = correct_clean.split('/')
                correct_num = float(parts[0]) / float(parts[1])
            else:
                correct_num = float(correct_clean)

            if '/' in student_clean:
                parts = student_clean.split('/')
                student_num = float(parts[0]) / float(parts[1])
            else:
                student_num = float(student_clean)

            return abs(correct_num - student_num) < 0.01
        except Exception:
            pass

        return False
    except Exception:
        return False


def get_subject_chapters(subject: str = "math") -> list:
    """Get list of chapters for a subject"""
    if subject == "math":
        return [k for k in ALL_CHAPTERS.keys() if not k.startswith("science_")]
    elif subject == "science":
        return [k for k in ALL_CHAPTERS.keys() if k.startswith("science_")]
    return list(ALL_CHAPTERS.keys())


def get_questions_by_difficulty(chapter: str, difficulty: int) -> list:
    """Get questions filtered by difficulty level"""
    questions = ALL_CHAPTERS.get(chapter, [])
    return [q for q in questions if q.get("difficulty", 1) == difficulty]


def get_mcq_questions(chapter: str) -> list:
    """Get only MCQ questions from a chapter"""
    questions = ALL_CHAPTERS.get(chapter, [])
    return [q for q in questions if q.get("type") == "mcq"]
