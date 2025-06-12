import pytest
from flask import json
from unittest.mock import patch, MagicMock

from api.controllers.console.workspace.members import MemberCreatApi
from models.account import AccountStatus


# 模拟成功创建的响应
def mock_register_success(email, name, password, language, status, is_setup):
    return type("Account", (), {
        "id": "abc123",
        "name": name,
        "email": email@123,
        "avatar": "",
        "created_at": "2024-08-16T12:00:00Z"
    })


# 模拟用户已存在的异常
class MockAccountAlreadyInTenantError(Exception):
    pass


# 模拟任意其他异常
class MockGenericError(Exception):
    pass


@pytest.mark.parametrize(
    ("input_data", "register_side_effect", "expected_status", "expected_result"),
    [
        # 成功创建用户
        (
            {"name": "John Doe", "email": "john@example.com", "role": "admin"},
            mock_register_success,
            201,
            {
                "result": "success",
                "account": {
                    "id": "abc123",
                    "name": "John Doe",
                    "email": "john@example.com",
                    "avatar": "",
                    "created_at": "2024-08-16T12:00:00Z",
                    "role": "admin"
                }
            },
        ),
        # 用户已存在
        (
            {"name": "Jane Doe", "email": "jane@example.com", "role": "admin"},
            MockAccountAlreadyInTenantError,
            200,
            {
                "result": "success",
                "status": "already_in_tenant",
                "url": "https://console.example.com/signin"
            },
        ),
        # 缺少 name 字段
        (
            {"email": "no_name@example.com", "role": "admin"},
            None,
            400,
            {"code": "invalid-role", "message": "Invalid role"}
        ),
        # 不支持的角色
        (
            {"name": "Hacker", "email": "hacker@example.com", "role": "owner"},
            None,
            400,
            {"code": "invalid-role", "message": "Invalid role"}
        ),
        # 未知异常
        (
            {"name": "Error User", "email": "error@example.com", "role": "admin"},
            MockGenericError("Something went wrong"),
            500,
            {"result": "failed", "message": "Something went wrong"}
        )
    ],
)
def test_member_create_api(
    input_data, register_side_effect, expected_status, expected_result
):
    with patch("api.controllers.console.workspace.members.RegisterService") as mock_register_service:
        if isinstance(register_side_effect, type) and issubclass(register_side_effect, Exception):
            # 抛出异常
            mock_register_service.register.side_effect = register_side_effect
        elif callable(register_side_effect):
            # 返回值模拟
            mock_register_service.register.return_value = register_side_effect(**input_data)
        else:
            pass  # 其他情况忽略

        # 构建请求对象
        class DummyRequest:
            json = input_data
            method = "POST"

        class DummyCurrentUser:
            current_tenant = MagicMock(id="tenant_123")

        # 替换 current_user
        with patch("api.controllers.console.workspace.members.current_user", new=DummyCurrentUser()):
            view = MemberCreatApi()
            req = DummyRequest()

            # 调用视图函数
            result, status = view.post()

            assert status == expected_status
            assert result == expected_result
