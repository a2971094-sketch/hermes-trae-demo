"""用户认证模块单元测试 — 覆盖注册/登录/刷新三个接口"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
REFRESH_URL = "/api/auth/refresh"


# ── 注册接口测试 ──────────────────────────────────────────────


class TestRegister:
    def test_register_success(self):
        """正常注册返回 user_id"""
        resp = client.post(
            REGISTER_URL, json={"username": "alice", "password": "secret123"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert "user_id" in data
        assert isinstance(data["user_id"], int)

    def test_register_duplicate_username(self):
        """重复用户名返回 409"""
        client.post(REGISTER_URL, json={"username": "dup1", "password": "secret123"})
        resp = client.post(
            REGISTER_URL, json={"username": "dup1", "password": "other456"}
        )
        assert resp.status_code == 409
        assert "已存在" in resp.json()["detail"]

    def test_register_short_username(self):
        """用户名过短返回 422"""
        resp = client.post(
            REGISTER_URL, json={"username": "ab", "password": "secret123"}
        )
        assert resp.status_code == 422

    def test_register_short_password(self):
        """密码过短返回 422"""
        resp = client.post(
            REGISTER_URL, json={"username": "valid_name", "password": "12345"}
        )
        assert resp.status_code == 422

    def test_register_invalid_username_chars(self):
        """用户名含非法字符返回 422"""
        resp = client.post(
            REGISTER_URL, json={"username": "user@name!", "password": "secret123"}
        )
        assert resp.status_code == 422


# ── 登录接口测试 ──────────────────────────────────────────────


class TestLogin:
    def test_login_success(self):
        """正常登录返回 access_token 和 refresh_token"""
        client.post(
            REGISTER_URL, json={"username": "loguser1", "password": "mypass123"}
        )
        resp = client.post(
            LOGIN_URL, json={"username": "loguser1", "password": "mypass123"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert len(data["access_token"]) > 0
        assert len(data["refresh_token"]) > 0

    def test_login_wrong_password(self):
        """密码错误返回 401"""
        client.post(
            REGISTER_URL, json={"username": "loguser2", "password": "correct123"}
        )
        resp = client.post(
            LOGIN_URL, json={"username": "loguser2", "password": "wrong000"}
        )
        assert resp.status_code == 401
        assert "错误" in resp.json()["detail"]

    def test_login_nonexistent_user(self):
        """不存在的用户返回 401"""
        resp = client.post(LOGIN_URL, json={"username": "ghost", "password": "nope123"})
        assert resp.status_code == 401


# ── 刷新 Token 接口测试 ──────────────────────────────────────


class TestRefresh:
    def test_refresh_success(self):
        """用 refresh_token 获取新的 access_token"""
        client.post(
            REGISTER_URL, json={"username": "refuser1", "password": "mypass123"}
        )
        login_resp = client.post(
            LOGIN_URL, json={"username": "refuser1", "password": "mypass123"}
        )
        refresh_token = login_resp.json()["refresh_token"]

        resp = client.post(REFRESH_URL, json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert len(data["access_token"]) > 0

    def test_refresh_with_access_token_fails(self):
        """用 access_token 调用刷新接口应失败"""
        client.post(
            REGISTER_URL, json={"username": "refuser2", "password": "mypass123"}
        )
        login_resp = client.post(
            LOGIN_URL, json={"username": "refuser2", "password": "mypass123"}
        )
        access_token = login_resp.json()["access_token"]

        resp = client.post(REFRESH_URL, json={"refresh_token": access_token})
        assert resp.status_code == 401
        assert "refresh" in resp.json()["detail"].lower()

    def test_refresh_invalid_token(self):
        """无效 token 返回 401"""
        resp = client.post(REFRESH_URL, json={"refresh_token": "invalid.token.here"})
        assert resp.status_code == 401


# ── 端到端流程测试 ────────────────────────────────────────────


class TestE2E:
    def test_full_auth_flow(self):
        """完整流程：注册 → 登录 → 刷新 → 用新 token"""
        # 注册
        reg = client.post(
            REGISTER_URL, json={"username": "e2e_user", "password": "pass123456"}
        )
        assert reg.status_code == 201
        assert "user_id" in reg.json()

        # 登录
        login = client.post(
            LOGIN_URL, json={"username": "e2e_user", "password": "pass123456"}
        )
        assert login.status_code == 200
        tokens = login.json()

        # 刷新 — 验证返回有效 access_token
        refresh = client.post(
            REFRESH_URL, json={"refresh_token": tokens["refresh_token"]}
        )
        assert refresh.status_code == 200
        new_access = refresh.json()["access_token"]
        assert len(new_access) > 0

    def test_register_then_login_different_password_fails(self):
        """注册后用不同密码登录失败"""
        client.post(
            REGISTER_URL, json={"username": "sec_user", "password": "original123"}
        )
        resp = client.post(
            LOGIN_URL, json={"username": "sec_user", "password": "different456"}
        )
        assert resp.status_code == 401
