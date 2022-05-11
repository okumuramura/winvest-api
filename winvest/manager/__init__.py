import logging
from functools import wraps
from typing import Any, Callable, Coroutine, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from winvest import Session as SessionCreator
from winvest.models import db

logger = logging.Logger(__name__)


def orm_function(func: Callable[..., Any]):  # type: ignore
    @wraps(func)
    def wrapper(*args, **kwargs):  # type: ignore
        if kwargs.get('session') is None:
            with SessionCreator() as session:
                return func(*args, session=session, **kwargs)
        else:
            return func(*args, **kwargs)

    return wrapper


def async_orm_function(func: Callable[..., Coroutine[Any, Any, Any]]):  # type: ignore
    @wraps(func)
    async def wrapper(*args, **kwargs):  # type: ignore
        if kwargs.get('session') is None:
            with SessionCreator() as session:
                return await func(*args, session=session, **kwargs)
        else:
            return await func(*args, **kwargs)

    return wrapper


@orm_function
def create_operation(
    user_id: int,
    _type: str,
    subject_id: Optional[int] = None,
    args: Optional[str] = None,
    session: Session = None,
) -> Optional[db.Operation]:
    operation = db.Operation(user_id, _type, subject_id, args)
    session.add(operation)

    try:
        session.commit()
    except SQLAlchemyError:
        session.rollback()
        logger.warning('can not create operation %s', operation)
        return None
    return operation
