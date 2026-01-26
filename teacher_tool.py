import csv
import asyncio
from db import init_pool, pool

UPSERT_TOPIC = """
insert into topics(topic_id, title, grade, subject)
values($1,$2,$3,$4)
on conflict (topic_id) do update set
  title=excluded.title,
  grade=excluded.grade,
  subject=excluded.subject;
"""

UPSERT_CONCEPT = """
insert into concepts(concept_id, topic_id, title, explain_text)
values($1,$2,$3,$4)
on conflict (concept_id) do update set
  topic_id=excluded.topic_id,
  title=excluded.title,
  explain_text=excluded.explain_text;
"""

UPSERT_QUESTION = """
insert into questions(question_id, topic_id, prompt, answer_key, hint1, hint2, reveal_explain)
values($1,$2,$3,$4,$5,$6,$7)
on conflict (question_id) do update set
  topic_id=excluded.topic_id,
  prompt=excluded.prompt,
  answer_key=excluded.answer_key,
  hint1=excluded.hint1,
  hint2=excluded.hint2,
  reveal_explain=excluded.reveal_explain;
"""

async def main():
    await init_pool()
    try:
        with open("content.csv", newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))

        topics_done = set()
        q_count = 0

        async with pool().acquire() as conn:
            for r in rows:
                topic_id = r["topic_id"].strip()
                if topic_id not in topics_done:
                    # Insert into topics table first (for foreign key)
                    await conn.execute(
                        UPSERT_TOPIC,
                        topic_id,
                        r["title"].strip(),
                        r["grade"].strip(),
                        r["subject"].strip(),
                    )
                    # Insert into concepts table
                    concept_id = f"concept_{topic_id}"
                    await conn.execute(
                        UPSERT_CONCEPT,
                        concept_id,
                        topic_id,
                        r["title"].strip(),
                        r["explain_text"].strip(),
                    )
                    topics_done.add(topic_id)
                    print(f"✓ Topic + Concept: {r['title']}")

                await conn.execute(
                    UPSERT_QUESTION,
                    r["question_id"].strip(),
                    topic_id,
                    r["prompt"].strip(),
                    r["answer_key"].strip(),
                    r["hint1"].strip(),
                    r["hint2"].strip(),
                    r["reveal_explain"].strip(),
                )
                q_count += 1
                print(f"  ✓ Question: {r['prompt'][:40]}...")

        print(f"\n✓ Loaded {len(topics_done)} topics/concepts")
        print(f"✓ Loaded {q_count} questions")
    finally:
        await pool().close()

if __name__ == "__main__":
    asyncio.run(main())
