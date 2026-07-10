"""用户资料接口单元测试 — 覆盖更新资料接口"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
UPDATE_ME_URL = "/api/users/me"


def _get_auth_token(username: str, password: str) -> str:
    """辅助函数：注册用户并获取 access_token"""
    client.post(REGISTER_URL, json={"username": username, "password": password})
    resp = client.post(LOGIN_URL, json={"username": username, "password": password})
    return resp.json()["access_token"]


class TestUpdateProfile:
    def test_update_profile_success(self):
        """正常更新用户资料"""
        token = _get_auth_token("profile_user1", "mypass123")
        resp = client.put(
            UPDATE_ME_URL,
            json={"nickname": "Alice", "avatar_url": "https://example.com/avatar.png"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "profile_user1"
        assert data["nickname"] == "Alice"
        assert data["avatar_url"] == "https://example.com/avatar.png"
        assert data["role"] == "user"
        assert "id" in data

    def test_update_profile_partial(self):
        """只更新昵称"""
        token = _get_auth_token("profile_user2", "mypass123")
        resp = client.put(
            UPDATE_ME_URL,
            json={"nickname": "Bob"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["nickname"] == "Bob"
        assert data["avatar_url"] is None

    def test_update_profile_no_auth(self):
        """未认证返回 401"""
        resp = client.put(
            UPDATE_ME_URL,
            json={"nickname": "Hacker"},
        )
        assert resp.status_code == 401

    def test_update_profile_invalid_token(self):
        """无效 token 返回 401"""
        resp = client.put(
            UPDATE_ME_URL,
            json={"nickname": "Hacker"},
            headers={"Authorization": "Bearer invalid.token.here"},
        )
        assert resp.status_code == 401

    def test_update_profile_with_refresh_token(self):
        """用 refresh_token 访问返回 401"""
        client.post(
            REGISTER_URL, json={"username": "profile_user3", "password": "mypass123"}
        )
        login_resp = client.post(
            LOGIN_URL, json={"username": "profile_user3", "password": "mypass123"}
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.put(
            UPDATE_ME_URL,
            json={"nickname": "Hacker"},
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert resp.status_code == 401

    def test_update_profile_empty_body(self):
        """空 body 不修改资料"""
        token = _get_auth_token("profile_user4", "mypass123")
        resp = client.put(
            UPDATE_ME_URL,
            json={},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "profile_user4"
        assert data["nickname"] is None
        assert data["avatar_url"] is None
