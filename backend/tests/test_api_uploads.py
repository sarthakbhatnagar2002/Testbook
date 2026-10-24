from tests.test_api_roles import register

# Smallest possible valid 1x1 PNG.
TINY_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108020000009077"
    "53de000000097048597300000ec300000ec301c76fa864000000174944415478"
    "da6360606060000000050001a5f645400000000049454e44ae426082"
)


def test_teacher_can_upload_an_image(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post("/uploads", files={"file": ("diagram.png", TINY_PNG, "image/png")})
    assert r.status_code == 201, r.text
    url = r.json()["url"]
    assert url.startswith("/uploads/")

    fetched = client.get(url)
    assert fetched.status_code == 200
    assert fetched.headers["content-type"] == "image/png"


def test_student_cannot_upload(client):
    register(client, "Stu", "stu@x.com", "student")
    r = client.post("/uploads", files={"file": ("a.png", TINY_PNG, "image/png")})
    assert r.status_code == 403


def test_rejects_non_image_content_type(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    r = client.post("/uploads", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 400


def test_rejects_oversized_file(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    too_big = b"\0" * (5 * 1024 * 1024 + 1)
    r = client.post("/uploads", files={"file": ("big.png", too_big, "image/png")})
    assert r.status_code == 400


def test_uploaded_url_accepted_as_question_image(client):
    register(client, "T1", "t1@x.com", "teacher", "teacher123")
    url = client.post("/uploads", files={"file": ("a.png", TINY_PNG, "image/png")}).json()["url"]
    r = client.post(
        "/questions",
        json={
            "text": "Q",
            "image_url": url,
            "options": [
                {"text": "a", "image_url": url, "is_correct": True},
                {"text": "b"},
            ],
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["image_url"] == url
