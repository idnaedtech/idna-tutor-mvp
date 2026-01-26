"""
IDNA EdTech - CBSE Class 8 Mathematics Question Bank
Based on NCERT Syllabus

Chapters:
1. Rational Numbers (परिमेय संख्याएँ)
2. Linear Equations in One Variable (एक चर वाले रैखिक समीकरण)
3. Understanding Quadrilaterals (चतुर्भुजों को समझना)
4. Data Handling (आँकड़ों का प्रबंधन)
5. Squares and Square Roots (वर्ग और वर्गमूल)
6. Cubes and Cube Roots (घन और घनमूल)
7. Comparing Quantities (राशियों की तुलना)
8. Algebraic Expressions (बीजीय व्यंजक और सर्वसमिकाएँ)
9. Mensuration (क्षेत्रमिति)
10. Exponents and Powers (घातांक और घात)
"""

# Chapter names (English + Hindi)
CHAPTER_NAMES = {
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
}

# Question bank
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
            "difficulty": 1
        },
        {
            "id": "rn_002",
            "text": "Find the additive inverse of 5/8",
            "answer": "-5/8",
            "hint": "Additive inverse means change the sign",
            "difficulty": 1
        },
        {
            "id": "rn_003",
            "text": "What is 2/3 × (-3/4)?",
            "answer": "-1/2",
            "hint": "Multiply numerators and denominators: (2×-3)/(3×4) = -6/12 = -1/2",
            "difficulty": 2
        },
        {
            "id": "rn_004",
            "text": "Find the multiplicative inverse of -7/9",
            "answer": "-9/7",
            "hint": "Flip the fraction, keep the sign",
            "difficulty": 2
        },
        {
            "id": "rn_005",
            "text": "Is 0 a rational number? Answer yes or no",
            "answer": "yes",
            "hint": "0 can be written as 0/1",
            "difficulty": 1
        },
        {
            "id": "rn_006",
            "text": "What is -5/6 ÷ 2/3?",
            "answer": "-5/4",
            "hint": "Divide = multiply by reciprocal: -5/6 × 3/2 = -15/12 = -5/4",
            "difficulty": 2
        },
        {
            "id": "rn_007",
            "text": "Find a rational number between 1/4 and 1/2",
            "answer": "3/8",
            "hint": "Average: (1/4 + 1/2)/2 = (1/4 + 2/4)/2 = (3/4)/2 = 3/8",
            "difficulty": 2
        },
        {
            "id": "rn_008",
            "text": "What is the value of (-1/2) + (-1/3)?",
            "answer": "-5/6",
            "hint": "LCM of 2 and 3 is 6: -3/6 + -2/6 = -5/6",
            "difficulty": 2
        },
        {
            "id": "rn_009",
            "text": "Simplify: 12/18 to lowest terms",
            "answer": "2/3",
            "hint": "GCD of 12 and 18 is 6. Divide both by 6",
            "difficulty": 1
        },
        {
            "id": "rn_010",
            "text": "What property does a + (-a) = 0 represent?",
            "answer": "additive inverse",
            "hint": "When sum is zero, they are inverses",
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
            "difficulty": 1
        },
        {
            "id": "le_002",
            "text": "Solve: 3x = 21",
            "answer": "7",
            "hint": "x = 21 ÷ 3",
            "difficulty": 1
        },
        {
            "id": "le_003",
            "text": "Solve: 2x - 7 = 13",
            "answer": "10",
            "hint": "2x = 13 + 7 = 20, so x = 10",
            "difficulty": 2
        },
        {
            "id": "le_004",
            "text": "Solve: 5x + 3 = 2x + 15",
            "answer": "4",
            "hint": "5x - 2x = 15 - 3, so 3x = 12, x = 4",
            "difficulty": 2
        },
        {
            "id": "le_005",
            "text": "Solve: (x + 4)/3 = 5",
            "answer": "11",
            "hint": "x + 4 = 15, so x = 11",
            "difficulty": 2
        },
        {
            "id": "le_006",
            "text": "Solve: 4(x - 2) = 20",
            "answer": "7",
            "hint": "x - 2 = 5, so x = 7",
            "difficulty": 2
        },
        {
            "id": "le_007",
            "text": "If 7x - 3 = 25, find x",
            "answer": "4",
            "hint": "7x = 28, x = 4",
            "difficulty": 2
        },
        {
            "id": "le_008",
            "text": "Solve: x/4 + 3 = 8",
            "answer": "20",
            "hint": "x/4 = 5, so x = 20",
            "difficulty": 2
        },
        {
            "id": "le_009",
            "text": "The sum of a number and 7 is 15. Find the number.",
            "answer": "8",
            "hint": "Let number = x, then x + 7 = 15",
            "difficulty": 1
        },
        {
            "id": "le_010",
            "text": "Three times a number minus 4 equals 11. Find the number.",
            "answer": "5",
            "hint": "3x - 4 = 11, so 3x = 15, x = 5",
            "difficulty": 2
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
            "difficulty": 1
        },
        {
            "id": "qu_002",
            "text": "How many sides does a hexagon have?",
            "answer": "6",
            "hint": "Hex = 6",
            "difficulty": 1
        },
        {
            "id": "qu_003",
            "text": "Each angle of a rectangle is how many degrees?",
            "answer": "90",
            "hint": "All angles in a rectangle are right angles",
            "difficulty": 1
        },
        {
            "id": "qu_004",
            "text": "In a parallelogram, opposite angles are ___? (equal/unequal)",
            "answer": "equal",
            "hint": "Property of parallelogram",
            "difficulty": 1
        },
        {
            "id": "qu_005",
            "text": "A quadrilateral with all sides equal and all angles 90° is called?",
            "answer": "square",
            "hint": "Equal sides + right angles = ?",
            "difficulty": 1
        },
        {
            "id": "qu_006",
            "text": "Three angles of a quadrilateral are 80°, 90°, 100°. Find the fourth.",
            "answer": "90",
            "hint": "Sum = 360, so fourth = 360 - 80 - 90 - 100",
            "difficulty": 2
        },
        {
            "id": "qu_007",
            "text": "How many diagonals does a quadrilateral have?",
            "answer": "2",
            "hint": "Connect opposite corners",
            "difficulty": 1
        },
        {
            "id": "qu_008",
            "text": "In a rhombus, diagonals bisect each other at what angle?",
            "answer": "90",
            "hint": "Diagonals of rhombus are perpendicular",
            "difficulty": 2
        },
        {
            "id": "qu_009",
            "text": "A trapezium has how many pairs of parallel sides?",
            "answer": "1",
            "hint": "Only one pair of opposite sides is parallel",
            "difficulty": 1
        },
        {
            "id": "qu_010",
            "text": "Sum of adjacent angles in a parallelogram is?",
            "answer": "180",
            "hint": "Adjacent angles are supplementary",
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
            "difficulty": 1
        },
        {
            "id": "dh_002",
            "text": "Find the median of 3, 7, 2, 9, 5",
            "answer": "5",
            "hint": "Arrange: 2,3,5,7,9. Middle value = 5",
            "difficulty": 2
        },
        {
            "id": "dh_003",
            "text": "Find the mode of 4, 6, 4, 8, 4, 9",
            "answer": "4",
            "hint": "Mode = most frequent value",
            "difficulty": 1
        },
        {
            "id": "dh_004",
            "text": "Range of data 12, 5, 18, 3, 9 is?",
            "answer": "15",
            "hint": "Range = Max - Min = 18 - 3",
            "difficulty": 1
        },
        {
            "id": "dh_005",
            "text": "Probability of getting head in a coin toss is?",
            "answer": "0.5",
            "hint": "1 head out of 2 outcomes = 1/2",
            "difficulty": 1
        },
        {
            "id": "dh_006",
            "text": "A die is thrown. Probability of getting 6 is?",
            "answer": "1/6",
            "hint": "1 favorable out of 6 possible",
            "difficulty": 2
        },
        {
            "id": "dh_007",
            "text": "Mean of first 5 natural numbers is?",
            "answer": "3",
            "hint": "(1+2+3+4+5)/5 = 15/5 = 3",
            "difficulty": 1
        },
        {
            "id": "dh_008",
            "text": "If mean of 5 numbers is 12, their sum is?",
            "answer": "60",
            "hint": "Sum = Mean × Count = 12 × 5",
            "difficulty": 2
        },
        {
            "id": "dh_009",
            "text": "Median of 2, 4, 6, 8 is?",
            "answer": "5",
            "hint": "Even count: average of middle two = (4+6)/2",
            "difficulty": 2
        },
        {
            "id": "dh_010",
            "text": "In a pie chart, total angle is how many degrees?",
            "answer": "360",
            "hint": "Full circle = 360°",
            "difficulty": 1
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
            "difficulty": 1
        },
        {
            "id": "sr_002",
            "text": "What is √81?",
            "answer": "9",
            "hint": "9 × 9 = 81",
            "difficulty": 1
        },
        {
            "id": "sr_003",
            "text": "What is 15²?",
            "answer": "225",
            "hint": "15 × 15 = 225",
            "difficulty": 1
        },
        {
            "id": "sr_004",
            "text": "What is √169?",
            "answer": "13",
            "hint": "13 × 13 = 169",
            "difficulty": 2
        },
        {
            "id": "sr_005",
            "text": "Is 50 a perfect square? (yes/no)",
            "answer": "no",
            "hint": "7² = 49, 8² = 64. 50 is between them.",
            "difficulty": 2
        },
        {
            "id": "sr_006",
            "text": "What is √(36/49)?",
            "answer": "6/7",
            "hint": "√36/√49 = 6/7",
            "difficulty": 2
        },
        {
            "id": "sr_007",
            "text": "Find the square of 25",
            "answer": "625",
            "hint": "25 × 25 = 625",
            "difficulty": 1
        },
        {
            "id": "sr_008",
            "text": "What is √196?",
            "answer": "14",
            "hint": "14 × 14 = 196",
            "difficulty": 2
        },
        {
            "id": "sr_009",
            "text": "Between which two numbers does √50 lie?",
            "answer": "7",
            "hint": "7² = 49, 8² = 64. √50 is closer to 7",
            "difficulty": 2
        },
        {
            "id": "sr_010",
            "text": "What is 11²?",
            "answer": "121",
            "hint": "11 × 11 = 121",
            "difficulty": 1
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
            "difficulty": 1
        },
        {
            "id": "cr_002",
            "text": "What is ∛27?",
            "answer": "3",
            "hint": "3 × 3 × 3 = 27",
            "difficulty": 1
        },
        {
            "id": "cr_003",
            "text": "What is 5³?",
            "answer": "125",
            "hint": "5 × 5 × 5 = 125",
            "difficulty": 1
        },
        {
            "id": "cr_004",
            "text": "What is ∛125?",
            "answer": "5",
            "hint": "5 × 5 × 5 = 125",
            "difficulty": 1
        },
        {
            "id": "cr_005",
            "text": "What is 3³?",
            "answer": "27",
            "hint": "3 × 3 × 3 = 27",
            "difficulty": 1
        },
        {
            "id": "cr_006",
            "text": "What is ∛64?",
            "answer": "4",
            "hint": "4 × 4 × 4 = 64",
            "difficulty": 1
        },
        {
            "id": "cr_007",
            "text": "What is 6³?",
            "answer": "216",
            "hint": "6 × 6 × 6 = 216",
            "difficulty": 2
        },
        {
            "id": "cr_008",
            "text": "What is ∛216?",
            "answer": "6",
            "hint": "6 × 6 × 6 = 216",
            "difficulty": 2
        },
        {
            "id": "cr_009",
            "text": "Is 100 a perfect cube? (yes/no)",
            "answer": "no",
            "hint": "4³=64, 5³=125. 100 is not a perfect cube.",
            "difficulty": 2
        },
        {
            "id": "cr_010",
            "text": "What is 10³?",
            "answer": "1000",
            "hint": "10 × 10 × 10 = 1000",
            "difficulty": 1
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
            "difficulty": 1
        },
        {
            "id": "cq_002",
            "text": "Convert 3/4 to percentage",
            "answer": "75",
            "hint": "3/4 × 100 = 75%",
            "difficulty": 1
        },
        {
            "id": "cq_003",
            "text": "A shirt costs ₹500. After 10% discount, price is?",
            "answer": "450",
            "hint": "Discount = 50, Price = 500 - 50 = 450",
            "difficulty": 2
        },
        {
            "id": "cq_004",
            "text": "Simple Interest on ₹1000 at 5% for 2 years is?",
            "answer": "100",
            "hint": "SI = P×R×T/100 = 1000×5×2/100 = 100",
            "difficulty": 2
        },
        {
            "id": "cq_005",
            "text": "If CP = ₹80 and SP = ₹100, profit is?",
            "answer": "20",
            "hint": "Profit = SP - CP = 100 - 80",
            "difficulty": 1
        },
        {
            "id": "cq_006",
            "text": "Profit% when CP=₹50 and Profit=₹10 is?",
            "answer": "20",
            "hint": "Profit% = (Profit/CP)×100 = (10/50)×100 = 20%",
            "difficulty": 2
        },
        {
            "id": "cq_007",
            "text": "What is 15% of 400?",
            "answer": "60",
            "hint": "15% of 400 = (15/100)×400 = 60",
            "difficulty": 1
        },
        {
            "id": "cq_008",
            "text": "A book's MRP is ₹200. After 15% discount, price is?",
            "answer": "170",
            "hint": "Discount = 30, Price = 200 - 30 = 170",
            "difficulty": 2
        },
        {
            "id": "cq_009",
            "text": "If SP = ₹90 and Loss = ₹10, find CP",
            "answer": "100",
            "hint": "CP = SP + Loss = 90 + 10",
            "difficulty": 2
        },
        {
            "id": "cq_010",
            "text": "Express 0.45 as percentage",
            "answer": "45",
            "hint": "0.45 × 100 = 45%",
            "difficulty": 1
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
            "difficulty": 1
        },
        {
            "id": "ae_002",
            "text": "Find value of 2x + 3 when x = 4",
            "answer": "11",
            "hint": "2(4) + 3 = 8 + 3 = 11",
            "difficulty": 1
        },
        {
            "id": "ae_003",
            "text": "Multiply: 2x × 3x",
            "answer": "6x²",
            "hint": "2×3=6, x×x=x²",
            "difficulty": 2
        },
        {
            "id": "ae_004",
            "text": "Expand: (x + 2)²",
            "answer": "x² + 4x + 4",
            "hint": "(a+b)² = a² + 2ab + b²",
            "difficulty": 2
        },
        {
            "id": "ae_005",
            "text": "Simplify: 7y - 3y + 2y",
            "answer": "6y",
            "hint": "7 - 3 + 2 = 6",
            "difficulty": 1
        },
        {
            "id": "ae_006",
            "text": "What is (a + b)(a - b)?",
            "answer": "a² - b²",
            "hint": "Difference of squares identity",
            "difficulty": 2
        },
        {
            "id": "ae_007",
            "text": "Find: x² when x = 5",
            "answer": "25",
            "hint": "5² = 25",
            "difficulty": 1
        },
        {
            "id": "ae_008",
            "text": "Simplify: 4x² + 2x²",
            "answer": "6x²",
            "hint": "4 + 2 = 6",
            "difficulty": 1
        },
        {
            "id": "ae_009",
            "text": "Expand: (x - 3)²",
            "answer": "x² - 6x + 9",
            "hint": "(a-b)² = a² - 2ab + b²",
            "difficulty": 2
        },
        {
            "id": "ae_010",
            "text": "Factorize: x² - 9",
            "answer": "(x+3)(x-3)",
            "hint": "a² - b² = (a+b)(a-b)",
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
            "difficulty": 1
        },
        {
            "id": "me_002",
            "text": "Perimeter of square with side 7 cm?",
            "answer": "28",
            "hint": "Perimeter = 4 × side = 4 × 7",
            "difficulty": 1
        },
        {
            "id": "me_003",
            "text": "Area of triangle with base 10 cm and height 6 cm?",
            "answer": "30",
            "hint": "Area = (1/2) × b × h = (1/2) × 10 × 6",
            "difficulty": 1
        },
        {
            "id": "me_004",
            "text": "Volume of cube with side 4 cm?",
            "answer": "64",
            "hint": "Volume = side³ = 4³",
            "difficulty": 2
        },
        {
            "id": "me_005",
            "text": "Area of square with side 9 cm?",
            "answer": "81",
            "hint": "Area = side² = 9²",
            "difficulty": 1
        },
        {
            "id": "me_006",
            "text": "Volume of cuboid 5×4×3 cm?",
            "answer": "60",
            "hint": "Volume = l × b × h = 5 × 4 × 3",
            "difficulty": 2
        },
        {
            "id": "me_007",
            "text": "Perimeter of rectangle 12 cm × 8 cm?",
            "answer": "40",
            "hint": "Perimeter = 2(l + b) = 2(12 + 8)",
            "difficulty": 1
        },
        {
            "id": "me_008",
            "text": "Surface area of cube with side 3 cm?",
            "answer": "54",
            "hint": "SA = 6 × side² = 6 × 9",
            "difficulty": 2
        },
        {
            "id": "me_009",
            "text": "Area of trapezium with parallel sides 8,6 cm and height 5 cm?",
            "answer": "35",
            "hint": "Area = (1/2)(a+b)×h = (1/2)(14)×5",
            "difficulty": 2
        },
        {
            "id": "me_010",
            "text": "Circumference of circle with radius 7 cm? (Use π=22/7)",
            "answer": "44",
            "hint": "C = 2πr = 2 × 22/7 × 7 = 44",
            "difficulty": 2
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
            "difficulty": 1
        },
        {
            "id": "ex_002",
            "text": "What is 10⁰?",
            "answer": "1",
            "hint": "Any number to power 0 is 1",
            "difficulty": 1
        },
        {
            "id": "ex_003",
            "text": "Simplify: 2³ × 2²",
            "answer": "32",
            "hint": "2³⁺² = 2⁵ = 32",
            "difficulty": 2
        },
        {
            "id": "ex_004",
            "text": "What is 3⁴?",
            "answer": "81",
            "hint": "3×3×3×3 = 81",
            "difficulty": 1
        },
        {
            "id": "ex_005",
            "text": "Simplify: 5⁶ ÷ 5⁴",
            "answer": "25",
            "hint": "5⁶⁻⁴ = 5² = 25",
            "difficulty": 2
        },
        {
            "id": "ex_006",
            "text": "What is (-2)³?",
            "answer": "-8",
            "hint": "(-2)×(-2)×(-2) = -8",
            "difficulty": 2
        },
        {
            "id": "ex_007",
            "text": "Express 1000000 as power of 10",
            "answer": "10⁶",
            "hint": "Count the zeros: 6 zeros",
            "difficulty": 1
        },
        {
            "id": "ex_008",
            "text": "What is (2³)²?",
            "answer": "64",
            "hint": "(2³)² = 2⁶ = 64",
            "difficulty": 2
        },
        {
            "id": "ex_009",
            "text": "What is 7¹?",
            "answer": "7",
            "hint": "Any number to power 1 is itself",
            "difficulty": 1
        },
        {
            "id": "ex_010",
            "text": "Simplify: (3²)³",
            "answer": "729",
            "hint": "(3²)³ = 3⁶ = 729",
            "difficulty": 3
        },
    ],
}


def check_answer(correct, student):
    """Basic answer check - for robust checking use evaluator.py"""
    try:
        # Clean up answers
        correct_clean = str(correct).lower().strip()
        student_clean = str(student).lower().strip()
        
        # Direct match
        if correct_clean == student_clean:
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
        except:
            pass
        
        return False
    except:
        return False
