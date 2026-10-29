from tests.helpers import register


def test_register_logs_them_in(client):
    r = client.post(
        "/auth/register", json={"name": "Stu", "email": "stu@x.com", "password": "password123"}
    )
    assert r.status_code == 200
    assert r.json()["email"] == "stu@x.com"
    assert "role" not in r.json()
    assert "session" in r.cookies

    me = client.get("/auth/me")
    assert me.json()["email"] == "stu@x.com"


def test_duplicate_email_rejected(client):
    body = {"name": "A", "email": "dup@x.com", "password": "password123"}
    assert client.post("/auth/register", json=body).status_code == 200
    assert client.post("/auth/register", json=body).status_code == 400


def test_login_wrong_password(client):
    register(client, "A", "a@x.com")
    r = client.post("/auth/login", json={"email": "a@x.com", "password": "wrong"})
    assert r.status_code == 401


def test_me_is_null_when_signed_out(client):
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json() is None


def test_logout_clears_session(client):
    register(client, "A", "a@x.com")
    client.post("/auth/logout")
    assert client.get("/auth/me").json() is None


def test_protected_routes_require_login(client):
    assert client.get("/subjects").status_code == 401
    assert client.get("/profile").status_code == 401
