def test_register_student_logs_them_in(client):
    r = client.post(
        "/auth/register", json={"name": "Stu", "email": "stu@x.com", "password": "password123", "role": "student"}
    )
    assert r.status_code == 200
    assert r.json()["role"] == "student"
    assert "session" in r.cookies

    me = client.get("/auth/me")
    assert me.json()["email"] == "stu@x.com"


def test_register_teacher_needs_invite_code(client):
    r = client.post(
        "/auth/register",
        json={"name": "T", "email": "t@x.com", "password": "password123", "role": "teacher"},
    )
    assert r.status_code == 400

    r = client.post(
        "/auth/register",
        json={
            "name": "T",
            "email": "t@x.com",
            "password": "password123",
            "role": "teacher",
            "invite_code": "teacher123",
        },
    )
    assert r.status_code == 200
    assert r.json()["role"] == "teacher"


def test_duplicate_email_rejected(client):
    body = {"name": "A", "email": "dup@x.com", "password": "password123", "role": "student"}
    assert client.post("/auth/register", json=body).status_code == 200
    assert client.post("/auth/register", json=body).status_code == 400


def test_login_wrong_password(client):
    client.post(
        "/auth/register", json={"name": "A", "email": "a@x.com", "password": "password123", "role": "student"}
    )
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_is_null_when_signed_out(client):
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json() is None


def test_logout_clears_session(client):
    client.post(
        "/auth/register", json={"name": "A", "email": "a@x.com", "password": "password123", "role": "student"}
    )
    client.post("/auth/logout")
    assert client.get("/auth/me").json() is None
