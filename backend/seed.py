"""Demo data: two accounts and one published test with two timed sections.

Run with: python seed.py   (safe to run once on a fresh database)
"""

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.security import hash_password

SECTIONS = [
    {
        "title": "Math",
        "duration_mins": 5,
        "questions": [
            {
                "rating": "easy",
                "text": "What is the value of x if 2x + 6 = 14?",
                "opts": ["4", "5", "8", "10"],
                "correct": 0,
                "explanation": "2x = 8, so x = 4.",
            },
            {
                "rating": "medium",
                "text": "If x² - 5x + 6 = 0, which are the roots?",
                "opts": ["1 and 6", "2 and 3", "-2 and -3", "5 and 1"],
                "correct": 1,
                "explanation": "Factorise: (x - 2)(x - 3) = 0.",
            },
            {
                "rating": "easy",
                "text": "How many degrees are in the interior angles of a triangle, summed?",
                "opts": ["90", "180", "270", "360"],
                "correct": 1,
                "explanation": "The angles of any triangle add up to 180 degrees.",
            },
        ],
    },
    {
        "title": "Science",
        "duration_mins": 5,
        "questions": [
            {
                "rating": "medium",
                "text": "Which quantity is a vector?",
                "opts": ["Speed", "Mass", "Velocity", "Time"],
                "correct": 2,
                "explanation": "Velocity has both magnitude and direction.",
            },
            {
                "rating": "hard",
                "text": "What is the chemical symbol for sodium?",
                "opts": ["So", "Sd", "Na", "S"],
                "correct": 2,
                "explanation": "Na comes from the Latin natrium.",
            },
        ],
    },
]


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.execute(
            select(models.User).where(models.User.email == "teacher@example.com")
        ).scalar_one_or_none()
        if existing:
            print("Seed data already present, skipping.")
            return

        password_hash = hash_password("password123")
        teacher = models.User(
            name="Demo Teacher", email="teacher@example.com", password_hash=password_hash, role="teacher"
        )
        student = models.User(
            name="Demo Student", email="student@example.com", password_hash=password_hash, role="student"
        )
        db.add_all([teacher, student])
        db.commit()
        db.refresh(teacher)

        test = models.Test(teacher_id=teacher.id, title="Starter quiz", room_key="DEMO01", published=True)
        db.add(test)
        db.commit()
        db.refresh(test)

        for section_position, section in enumerate(SECTIONS):
            ts = models.TestSection(
                test_id=test.id,
                title=section["title"],
                position=section_position,
                duration_mins=section["duration_mins"],
            )
            db.add(ts)
            db.commit()
            db.refresh(ts)

            for q_position, item in enumerate(section["questions"]):
                question = models.Question(
                    teacher_id=teacher.id,
                    text=item["text"],
                    teacher_rating=item["rating"],
                    explanation=item["explanation"],
                )
                question.options = [
                    models.Option(text=text, position=position, is_correct=position == item["correct"])
                    for position, text in enumerate(item["opts"])
                ]
                db.add(question)
                db.commit()
                db.refresh(question)
                db.add(models.TestQuestion(section_id=ts.id, question_id=question.id, position=q_position))
            db.commit()

        # Pre-join the demo student so the starter quiz shows up immediately;
        # try the join flow yourself with the same room key.
        db.add(models.TestAccess(user_id=student.id, test_id=test.id))
        db.commit()

        print("Seeded. Log in as teacher@example.com or student@example.com (password: password123).")
        print(f"Starter quiz room key: {test.room_key}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
