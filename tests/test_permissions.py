"""权限与用户管理测试 — 覆盖角色权限中间件和管理员接口"""

from fastapi.testclient import TestClient

from app.main import app
from app.database import SessionLocal
from app.models import User
from app.auth import hash_password

client = TestClient(app)

REGISTER_URL = "/api/auth/register"
LOGIN_URL = "/api/auth/login"
ME_URL = "/api/users/me"
ADMIN_USERS_URL = "/api/admin/users"


def _register(username: str, password: str = "secret123", role: str | None = None):
    params = {}
    if role:
        params["role"] = role
    return client.post(
        REGISTER_URL, json={"username": username, "password": password}, params=params
    )


def _login(username: str, password: str = "secret123"):
    resp = client.post(LOGIN_URL, json={"username": username, "password": password})
    return resp.json()["access_token"]


def _create_user_direct(
    username: str, password: str = "secret123", role: str = "user"
) -> int:
    """直接通过数据库创建用户，绕过注册逻辑"""
    db = SessionLocal()
    try:
        user = User(
            username=username,
            password_hash=hash_password(password),
            role=role,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user.id
    finally:
        db.close()


# ── 用户资料接口测试 ──────────────────────────────────────────


class TestUserProfile:
    def test_get_me_success(self):
        """认证用户可获取自身信息"""
        _register("me_user1")
        token = _login("me_user1")

        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["username"] == "me_user1"
        assert data["role"] == "user"
        assert "id" in data
        assert "created_at" in data

    def test_get_me_no_auth(self):
        """未认证访问返回 401"""
        resp = client.get(ME_URL)
        assert resp.status_code == 401

    def test_get_me_invalid_token(self):
        """无效 token 返回 401"""
        resp = client.get(ME_URL, headers={"Authorization": "Bearer invalid.token"})
        assert resp.status_code == 401

    def test_get_me_wrong_scheme(self):
        """非 Bearer scheme 返回 401"""
        _register("me_user2")
        token = _login("me_user2")
        resp = client.get(ME_URL, headers={"Authorization": f"Basic {token}"})
        assert resp.status_code == 401

    def test_get_me_token_without_sub(self):
        """token 缺少 sub 返回 401"""
        from app.auth import create_access_token

        token = create_access_token({"username": "ghost"})
        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "用户标识" in resp.json()["detail"]

    def test_get_me_user_not_found(self):
        """token 有效但用户已被删除返回 401"""
        from app.auth import create_access_token

        # 使用不存在的用户 id
        token = create_access_token(
            {"sub": "99999", "username": "ghost", "role": "user"}
        )
        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "不存在" in resp.json()["detail"]


# ── 管理员接口测试 ────────────────────────────────────────────


class TestAdminUsers:
    def test_list_users_as_admin(self):
        """管理员可获取所有用户列表"""
        _create_user_direct("admin1", role="admin")
        token = _login("admin1")

        resp = client.get(ADMIN_USERS_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert isinstance(data["users"], list)
        # 至少包含 admin1 自己
        usernames = [u["username"] for u in data["users"]]
        assert "admin1" in usernames

    def test_list_users_as_normal_user(self):
        """普通用户访问管理员接口返回 403"""
        _register("norm_user1")
        token = _login("norm_user1")

        resp = client.get(ADMIN_USERS_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 403

    def test_list_users_no_auth(self):
        """未认证访问管理员接口返回 401"""
        resp = client.get(ADMIN_USERS_URL)
        assert resp.status_code == 401

    def test_delete_user_as_admin(self):
        """管理员可删除其他用户"""
        _create_user_direct("admin2", role="admin")
        admin_token = _login("admin2")

        _register("del_target1")
        # 获取用户列表找到 id
        list_resp = client.get(
            ADMIN_USERS_URL, headers={"Authorization": f"Bearer {admin_token}"}
        )
        target = next(
            u for u in list_resp.json()["users"] if u["username"] == "del_target1"
        )

        resp = client.delete(
            f"{ADMIN_USERS_URL}/{target['id']}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )
        assert resp.status_code == 204

        # 验证已删除
        list_resp2 = client.get(
            ADMIN_USERS_URL, headers={"Authorization": f"Bearer {admin_token}"}
        )
        usernames = [u["username"] for u in list_resp2.json()["users"]]
        assert "del_target1" not in usernames

    def test_delete_user_as_normal_user(self):
        """普通用户删除用户返回 403"""
        _register("norm_user2")
        token = _login("norm_user2")

        resp = client.delete(
            f"{ADMIN_USERS_URL}/1", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 403

    def test_delete_nonexistent_user(self):
        """删除不存在的用户返回 404"""
        _create_user_direct("admin3", role="admin")
        token = _login("admin3")

        resp = client.delete(
            f"{ADMIN_USERS_URL}/99999", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 404


# ── 注册 role 参数测试 ───────────────────────────────────────


class TestRegisterRole:
    def test_register_admin_after_first_user_ignored(self):
        """非首次注册时 role=admin 被忽略，创建普通用户"""
        # 确保数据库中已有用户
        _register("existing_for_role")
        _register("late_admin", role="admin")
        token = _login("late_admin")

        resp = client.get(ME_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.json()["role"] == "user"

    def test_first_admin_can_access_admin_api(self):
        """直接创建的 admin 可正常访问管理员接口"""
        _create_user_direct("first_admin_chk", role="admin")
        token = _login("first_admin_chk")

        resp = client.get(ADMIN_USERS_URL, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
