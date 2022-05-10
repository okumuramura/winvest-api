from typing import Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from winvest.manager import create_operation, logger, orm_function
from winvest.models import db


@orm_function
def register(
    login: str, password: str, session: Session = None
) -> Optional[int]:
    new_user = db.User(login, password)
    session.add(new_user)

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return None
    create_operation(new_user.id, 'REGISTER', session=session)
    logger.info('new user registered: %s', new_user.login)
    return new_user.id


@orm_function
def sign_in(
    login: str, password: str, session: Session = None
) -> Optional[db.Token]:
    user: db.User = (
        session.query(db.User).filter(db.User.login == login).first()
    )

    if user is None or not user.check_password(password):
        return None

    new_token = db.Token(user)
    session.add(new_token)

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        return None

    token_json = {'token': new_token.token}
    create_operation(user.id, 'SIGN_IN', args=str(token_json), session=session)
    logger.info('user sign in: %s', user.login)
    return new_token


@orm_function
def get_by_id(user_id: int, session: Session = None) -> Optional[db.User]:
    return session.query(db.User).filter(db.User.id == id).first()


@orm_function
def get_by_token(token: str, session: Session = None) -> Optional[db.User]:
    return (
        session.query(db.User)
        .join(db.Token)
        .filter(db.Token.token == token)
        .first()
    )
