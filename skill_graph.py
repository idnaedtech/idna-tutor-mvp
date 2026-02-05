"""
IDNA EdTech - Skill Graph
==========================
Maps granular skills for CBSE Class 8 Math (first 5 chapters).

Each skill has:
- skill_id: unique identifier
- display_name: human-readable name
- chapter: which chapter it belongs to
- prerequisites: skills that should be mastered first
- difficulty_band: 1=foundational, 2=procedural, 3=application

Pure data module — no runtime logic, no imports from other IDNA modules.
"""

from typing import List, TypedDict


class Skill(TypedDict):
    skill_id: str
    display_name: str
    chapter: str
    prerequisites: List[str]
    difficulty_band: int  # 1=foundational, 2=procedural, 3=application


# =============================================================================
# Chapter 1: Rational Numbers
# =============================================================================

SKILLS: dict[str, Skill] = {
    # --- Rational Numbers (Ch 1) ---
    "rn_identify": {
        "skill_id": "rn_identify",
        "display_name": "Identify rational numbers",
        "chapter": "rational_numbers",
        "prerequisites": [],
        "difficulty_band": 1,
    },
    "rn_add_same_denom": {
        "skill_id": "rn_add_same_denom",
        "display_name": "Add fractions with same denominator",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_identify"],
        "difficulty_band": 1,
    },
    "rn_add_diff_denom": {
        "skill_id": "rn_add_diff_denom",
        "display_name": "Add fractions with different denominators (LCM)",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_add_same_denom"],
        "difficulty_band": 2,
    },
    "rn_subtract": {
        "skill_id": "rn_subtract",
        "display_name": "Subtract rational numbers",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_add_diff_denom"],
        "difficulty_band": 2,
    },
    "rn_multiply": {
        "skill_id": "rn_multiply",
        "display_name": "Multiply rational numbers",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_identify"],
        "difficulty_band": 2,
    },
    "rn_divide": {
        "skill_id": "rn_divide",
        "display_name": "Divide rational numbers (reciprocal)",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_multiply"],
        "difficulty_band": 2,
    },
    "rn_additive_inverse": {
        "skill_id": "rn_additive_inverse",
        "display_name": "Find additive inverse",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_identify"],
        "difficulty_band": 1,
    },
    "rn_multiplicative_inverse": {
        "skill_id": "rn_multiplicative_inverse",
        "display_name": "Find multiplicative inverse",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_multiply"],
        "difficulty_band": 2,
    },
    "rn_simplify": {
        "skill_id": "rn_simplify",
        "display_name": "Simplify fractions to lowest terms",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_identify"],
        "difficulty_band": 1,
    },
    "rn_compare": {
        "skill_id": "rn_compare",
        "display_name": "Compare rational numbers",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_add_diff_denom"],
        "difficulty_band": 2,
    },
    "rn_between": {
        "skill_id": "rn_between",
        "display_name": "Find rational numbers between two values",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_compare"],
        "difficulty_band": 2,
    },
    "rn_word_problem": {
        "skill_id": "rn_word_problem",
        "display_name": "Solve word problems with rational numbers",
        "chapter": "rational_numbers",
        "prerequisites": ["rn_add_diff_denom", "rn_subtract"],
        "difficulty_band": 3,
    },

    # --- Linear Equations (Ch 2) ---
    "le_one_step": {
        "skill_id": "le_one_step",
        "display_name": "Solve one-step equations (x + a = b)",
        "chapter": "linear_equations",
        "prerequisites": [],
        "difficulty_band": 1,
    },
    "le_two_step": {
        "skill_id": "le_two_step",
        "display_name": "Solve two-step equations (ax + b = c)",
        "chapter": "linear_equations",
        "prerequisites": ["le_one_step"],
        "difficulty_band": 2,
    },
    "le_variables_both_sides": {
        "skill_id": "le_variables_both_sides",
        "display_name": "Solve equations with variables on both sides",
        "chapter": "linear_equations",
        "prerequisites": ["le_two_step"],
        "difficulty_band": 2,
    },
    "le_brackets": {
        "skill_id": "le_brackets",
        "display_name": "Solve equations with brackets",
        "chapter": "linear_equations",
        "prerequisites": ["le_two_step"],
        "difficulty_band": 2,
    },
    "le_fractions": {
        "skill_id": "le_fractions",
        "display_name": "Solve equations with fractions",
        "chapter": "linear_equations",
        "prerequisites": ["le_two_step"],
        "difficulty_band": 2,
    },
    "le_word_problem": {
        "skill_id": "le_word_problem",
        "display_name": "Translate word problems to equations",
        "chapter": "linear_equations",
        "prerequisites": ["le_two_step"],
        "difficulty_band": 3,
    },

    # --- Squares and Square Roots (Ch 5) ---
    "sq_perfect_squares": {
        "skill_id": "sq_perfect_squares",
        "display_name": "Identify perfect squares",
        "chapter": "squares_roots",
        "prerequisites": [],
        "difficulty_band": 1,
    },
    "sq_square_number": {
        "skill_id": "sq_square_number",
        "display_name": "Find square of a number",
        "chapter": "squares_roots",
        "prerequisites": ["sq_perfect_squares"],
        "difficulty_band": 1,
    },
    "sq_square_root": {
        "skill_id": "sq_square_root",
        "display_name": "Find square root by factorisation",
        "chapter": "squares_roots",
        "prerequisites": ["sq_perfect_squares"],
        "difficulty_band": 2,
    },
    "sq_patterns": {
        "skill_id": "sq_patterns",
        "display_name": "Use patterns in squares (units digit, odd sum)",
        "chapter": "squares_roots",
        "prerequisites": ["sq_perfect_squares"],
        "difficulty_band": 2,
    },
    "sq_estimate_root": {
        "skill_id": "sq_estimate_root",
        "display_name": "Estimate square roots of non-perfect squares",
        "chapter": "squares_roots",
        "prerequisites": ["sq_square_root"],
        "difficulty_band": 3,
    },

    # --- Algebraic Expressions (Ch 8) ---
    "ae_identify_terms": {
        "skill_id": "ae_identify_terms",
        "display_name": "Identify terms, coefficients, constants",
        "chapter": "algebraic_expressions",
        "prerequisites": [],
        "difficulty_band": 1,
    },
    "ae_add_subtract": {
        "skill_id": "ae_add_subtract",
        "display_name": "Add and subtract like terms",
        "chapter": "algebraic_expressions",
        "prerequisites": ["ae_identify_terms"],
        "difficulty_band": 1,
    },
    "ae_multiply_monomial": {
        "skill_id": "ae_multiply_monomial",
        "display_name": "Multiply monomials",
        "chapter": "algebraic_expressions",
        "prerequisites": ["ae_identify_terms"],
        "difficulty_band": 2,
    },
    "ae_multiply_polynomial": {
        "skill_id": "ae_multiply_polynomial",
        "display_name": "Multiply polynomial by monomial",
        "chapter": "algebraic_expressions",
        "prerequisites": ["ae_multiply_monomial"],
        "difficulty_band": 2,
    },
    "ae_identities": {
        "skill_id": "ae_identities",
        "display_name": "Apply algebraic identities ((a+b)^2 etc.)",
        "chapter": "algebraic_expressions",
        "prerequisites": ["ae_multiply_polynomial"],
        "difficulty_band": 3,
    },

    # --- Comparing Quantities (Ch 7) ---
    "cq_ratio": {
        "skill_id": "cq_ratio",
        "display_name": "Find and simplify ratios",
        "chapter": "comparing_quantities",
        "prerequisites": [],
        "difficulty_band": 1,
    },
    "cq_percentage": {
        "skill_id": "cq_percentage",
        "display_name": "Convert between fractions, decimals, and percentages",
        "chapter": "comparing_quantities",
        "prerequisites": ["cq_ratio"],
        "difficulty_band": 1,
    },
    "cq_profit_loss": {
        "skill_id": "cq_profit_loss",
        "display_name": "Calculate profit, loss, and percentage",
        "chapter": "comparing_quantities",
        "prerequisites": ["cq_percentage"],
        "difficulty_band": 2,
    },
    "cq_simple_interest": {
        "skill_id": "cq_simple_interest",
        "display_name": "Calculate simple interest",
        "chapter": "comparing_quantities",
        "prerequisites": ["cq_percentage"],
        "difficulty_band": 2,
    },
    "cq_compound_interest": {
        "skill_id": "cq_compound_interest",
        "display_name": "Calculate compound interest",
        "chapter": "comparing_quantities",
        "prerequisites": ["cq_simple_interest"],
        "difficulty_band": 3,
    },
    "cq_discount": {
        "skill_id": "cq_discount",
        "display_name": "Calculate discount and selling price",
        "chapter": "comparing_quantities",
        "prerequisites": ["cq_percentage"],
        "difficulty_band": 2,
    },
}


def get_skills_for_chapter(chapter: str) -> list[Skill]:
    """Get all skills belonging to a chapter."""
    return [s for s in SKILLS.values() if s["chapter"] == chapter]


def get_prerequisites(skill_id: str) -> list[str]:
    """Get prerequisite skill IDs for a given skill."""
    skill = SKILLS.get(skill_id)
    if not skill:
        return []
    return skill["prerequisites"]


def get_skill(skill_id: str) -> Skill | None:
    """Look up a skill by ID."""
    return SKILLS.get(skill_id)


# For testing
if __name__ == "__main__":
    print("=== Skill Graph Test ===\n")
    chapters = set(s["chapter"] for s in SKILLS.values())
    for ch in sorted(chapters):
        skills = get_skills_for_chapter(ch)
        print(f"{ch}: {len(skills)} skills")
        for s in skills:
            prereqs = s["prerequisites"]
            prereq_str = f" (requires: {', '.join(prereqs)})" if prereqs else ""
            print(f"  [{s['difficulty_band']}] {s['display_name']}{prereq_str}")
        print()
    print(f"Total skills: {len(SKILLS)}")
