from datetime import datetime
from typing import Optional

from fastapi import Depends, Request
from fastapi_users import BaseUserManager, IntegerIDMixin
from fastapi_users.db import BaseUserDatabase

from api.db import update_user_last_verify_request
from api.emails import send_forgot_password_email, send_verify_email
from api.users.db import FastApiUser, connect, get_user_db
from api.utils import get_secret

secret = get_secret("USER_SECRET")
if secret is None:
    raise RuntimeError("USER_SECRET secret not defined")


class UserManager(IntegerIDMixin, BaseUserManager[FastApiUser, int]):
    reset_password_token_secret = secret
    verification_token_secret = secret

    async def on_after_register(
        self, user: FastApiUser, request: Optional[Request] = None
    ):
        print(f"User {user.id} has registered.")

    async def on_after_forgot_password(
        self, user: FastApiUser, token: str, request: Optional[Request] = None
    ):
        print(f"User {user.id} has forgot their password. Reset token: {token}")
        send_forgot_password_email(user, token)

    async def on_after_request_verify(
        self, user: FastApiUser, token: str, request: Optional[Request] = None
    ):
        print(
            f"Verification requested for user {user.id}. Verification token: {token}"
        )
        request_time = datetime.now()
        if user.last_verify_request is not None:
            timedelta_since_last_request = (
                request_time - user.last_verify_request
            )
            should_send_email = timedelta_since_last_request.seconds / 60 >= 15
        else:
            should_send_email = True
        if should_send_email:
            send_verify_email(user, token)
            with connect() as conn:
                update_user_last_verify_request(conn, user.id, request_time)
        else:
            print("15 minutes not passed since last verify request")


async def get_user_manager(
    user_db: BaseUserDatabase[FastApiUser, int] = Depends(get_user_db),
):
    yield UserManager(user_db)
