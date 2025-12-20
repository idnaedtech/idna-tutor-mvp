#!/usr/bin/env python3
"""
Teacher Tool - Manage educational content for the tutoring service.
Load CSV content into the database, validate structure, and manage topics/questions.
"""
import csv
import asyncio
import sys
from db import init_pool, add_topic, add_question

async def load_csv(filename):
    """Load content from CSV file"""
    rows = []
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
        print(f"✓ Loaded {len(rows)} rows from {filename}")
        return rows
    except FileNotFoundError:
        print(f"✗ File not found: {filename}")
        return []

async def validate_row(row):
    """Validate a single content row"""
    required = ['topic_id', 'title', 'explain_text', 'question_id', 'prompt', 'answer_key']
    for field in required:
        if not row.get(field):
            return False, f"Missing {field}"
    return True, "OK"

async def load_content_to_db(rows):
    """Load validated content into database"""
    await init_pool()
    
    loaded_topics = set()
    loaded_questions = 0
    
    for row in rows:
        valid, msg = await validate_row(row)
        if not valid:
            print(f"  ✗ Invalid row: {msg}")
            continue
        
        # Add topic (deduplicated)
        topic_id = row['topic_id']
        if topic_id not in loaded_topics:
            try:
                await add_topic(
                    topic_id=topic_id,
                    title=row['title'],
                    explain_text=row['explain_text']
                )
                loaded_topics.add(topic_id)
                print(f"  ✓ Topic: {row['title']}")
            except Exception as e:
                print(f"  ! Topic already exists: {topic_id}")
        
        # Add question
        try:
            await add_question(
                question_id=row['question_id'],
                topic_id=topic_id,
                prompt=row['prompt'],
                answer_key=row['answer_key'],
                hint1=row.get('hint1', ''),
                hint2=row.get('hint2', ''),
                reveal_explain=row.get('reveal_explain', '')
            )
            loaded_questions += 1
            print(f"    ✓ Question: {row['prompt'][:40]}...")
        except Exception as e:
            print(f"    ! Question already exists: {row['question_id']}")
    
    print(f"\n✓ Loaded {loaded_questions} questions from {len(loaded_topics)} topics")

async def main():
    if len(sys.argv) < 2:
        print("Usage: python teacher_tool.py <csv_file>")
        print("Example: python teacher_tool.py content.csv")
        sys.exit(1)
    
    csv_file = sys.argv[1]
    rows = await load_csv(csv_file)
    
    if rows:
        await load_content_to_db(rows)

if __name__ == "__main__":
    asyncio.run(main())
