"""Demo data: one account and a few subject banks with sample questions.

Run with: python seed.py   (safe to run once on a fresh database)
"""

from sqlalchemy import select

from app import models
from app.database import SessionLocal
from app.security import hash_password

BANKS = {
    "Physics": [
        {
            "text": "What is the SI unit of force?",
            "opts": ["Joule", "Newton", "Watt", "Pascal"],
            "correct": 1,
            "explanation": "Force = mass x acceleration, measured in newtons (N) in SI units.",
        },
        {
            "text": "Which of these is a vector quantity?",
            "opts": ["Speed", "Mass", "Velocity", "Energy"],
            "correct": 2,
            "explanation": "Velocity has both magnitude and direction, which makes it a vector; the others are scalars.",
        },
        {
            "text": "A body moving with constant velocity has acceleration equal to",
            "opts": ["Infinity", "Zero", "Equal to velocity", "Equal to gravity"],
            "correct": 1,
            "explanation": "Constant velocity means no change in speed or direction, so acceleration is zero.",
        },
    ],
    "Chemistry": [
        {
            "text": "What is the chemical symbol for sodium?",
            "opts": ["So", "Sd", "Na", "S"],
            "correct": 2,
            "explanation": "Na comes from the Latin name for sodium, natrium.",
        },
        {
            "text": "Which gas is most abundant in Earth's atmosphere?",
            "opts": ["Oxygen", "Carbon dioxide", "Nitrogen", "Argon"],
            "correct": 2,
            "explanation": "Nitrogen makes up about 78% of the atmosphere by volume.",
        },
    ],
    "Mathematics": [
        {
            "text": "What is the value of x if 2x + 6 = 14?",
            "opts": ["4", "5", "8", "10"],
            "correct": 0,
            "explanation": "2x = 8, so x = 4.",
        },
        {
            "text": "If x² - 5x + 6 = 0, which are the roots?",
            "opts": ["1 and 6", "2 and 3", "-2 and -3", "5 and 1"],
            "correct": 1,
            "explanation": "Factorise: (x - 2)(x - 3) = 0, so x = 2 or x = 3.",
        },
        {
            "text": "How many degrees are in the interior angles of a triangle, summed?",
            "opts": ["90", "180", "270", "360"],
            "correct": 1,
            "explanation": "The interior angles of any triangle always sum to 180 degrees.",
        },
    ],
}


def main() -> None:
    db = SessionLocal()
    try:
        existing = db.execute(
            select(models.User).where(models.User.email == "demo@example.com")
        ).scalar_one_or_none()
        if existing:
            print("Seed data already present, skipping.")
            return

        user = models.User(
            name="Demo User", email="demo@example.com", password_hash=hash_password("password123")
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        for subject_name, questions in BANKS.items():
            subject = models.Subject(name=subject_name, created_by=user.id)
            db.add(subject)
            db.commit()
            db.refresh(subject)

            for item in questions:
                question = models.Question(
                    subject_id=subject.id,
                    created_by=user.id,
                    text=item["text"],
                    explanation=item["explanation"],
                )
                question.options = [
                    models.Option(text=text, position=position, is_correct=position == item["correct"])
                    for position, text in enumerate(item["opts"])
                ]
                db.add(question)
            db.commit()

        print("Seeded. Log in as demo@example.com (password: password123).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
