from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from app.models import User
from app.schemas import ICreateUserController, IUpdateUserController
import re
from app.utils.error_handler import ErrorHandler
from app.utils.password_operator import verify_password
from datetime import datetime


class UserController:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, id: int):
        user = (await self.db.execute(select(User).where(User.id == id))).scalar_one_or_none()
        return user

    async def get_by_username(self, username: str):
        user = (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        # if not user:
        # raise ErrorHandler.not_found("User")
        return user

    async def get_by_email(self, email: str):
        user = (await self.db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        return user

    async def create(self, user_items: ICreateUserController):
        async with self.db as async_session:
            new_user = User(
                username=user_items["username"],
                fullname=user_items["fullname"],
                email=user_items["email"],
                hashedPassword=user_items["hashedPassword"],
                dob=user_items["dob"],
                gender=user_items["gender"]
            )
            async_session.add(new_user)
            await async_session.commit()
            await async_session.refresh(new_user)
            return new_user

    async def update_by_id(self, id: int, user_items: IUpdateUserController):
        user = await self.get_by_id(id=id)

        if user:
            for key, value in user_items.items():
                setattr(user, key, value)
            await self.db.commit()
        return user

    async def delete_by_id(self, id: int):
        user = await self.get_by_id(id=id)

        if user:
            await self.db.execute(delete(User).where(User.id == id))
            await self.db.commit()
        return

    # validations

    def validate_password_characters(self, password: str):
        errors = []

        # Check length
        if len(password) < 8:
            errors.append("Password length must be at least 8 characters.")

        # Check for uppercase letters
        if not any(char.isupper() for char in password):
            errors.append(
                "Password must contain at least one uppercase letter.")

        # Check for lowercase letters
        if not any(char.islower() for char in password):
            errors.append(
                "Password must contain at least one lowercase letter.")

        # Check for digits
        if not any(char.isdigit() for char in password):
            errors.append("Password must contain at least one digit.")

        # Check for special characters
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append(
                "Password must contain at least one special character.")

        if errors:
            raise ErrorHandler.bad_request(errors)

    def validate_username_characters(self, username: str):
        errors = []

        # Check length
        if len(username) < 4:
            errors.append("username length must be at least 4 characters.")

        # Check for uppercase letters
        if any(char.isupper() for char in username):
            errors.append(
                "username must not contain any uppercase letter.")

        # Check for space
        if " " in username:
            errors.append(
                "username must not contain space characters.")

        # Check for -
        if "-" in username:
            errors.append(
                "username must not contain - characters.")

        # Check for special characters
        if re.search(r'[!#$%^&*(),.?":{}|<>]', username):
            errors.append(
                "username must not contain special characters.")

        if errors:
            raise ErrorHandler.bad_request(errors)

    async def check_username_exists(self, username: str):
        user = (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if not user:
            raise ErrorHandler.bad_request(
                "User with this username does not exist.")

    async def check_username_not_exists(self, username: str):
        user = (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user:
            raise ErrorHandler.bad_request(
                "User with this username does exist.")

    async def check_email_not_exists(self, email: str):
        user = await self.get_by_email(email=email)
        if user:
            raise ErrorHandler.bad_request("User with this email does exist.")

    async def verify_password(self, username: str, password: str):
        user = await self.get_by_username(username=username)
        is_valid_password = verify_password(password, user.hashedPassword)

        if not is_valid_password:
            raise ErrorHandler.bad_request("Password is incorrect")

    # def validate_scope(self, scope, operation):
    #     if (scope == "user" and operation not in USER_SCOPES) or (scope == "admin" and operation not in ADMIN_SCOPES):
    #         raise ErrorHandler.access_denied(operation)

    async def check_username_not_repeat(self, user_id, username):
        existing_username = (await self.db.execute(select(User).where(User.username == username))).scalar_one_or_none()

        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

        if existing_username and existing_username.id != user.id:
            raise ErrorHandler.bad_request(
                custom_message="username is repeated.")

    async def check_email_not_repeat(self, user_id, email):
        existing_email = (await self.db.execute(select(User).where(User.email == email))).scalar_one_or_none()

        user = (await self.db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()

        if existing_email and existing_email.id != user.id:
            raise ErrorHandler.bad_request(custom_message="Email is repeated.")

    async def validate_dob(self, dob: str):  # should be in this format: 01-04-1987
        valid, dob_date = await User.validate_dob(dob)
        if not valid:
            raise ErrorHandler.bad_request(custom_message=dob_date)
        dob_date = datetime.combine(dob_date, datetime.min.time())
        return dob_date
