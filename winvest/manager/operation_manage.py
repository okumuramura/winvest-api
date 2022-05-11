from typing import List

from sqlalchemy.orm import Session, joinedload

from winvest.manager import orm_function
from winvest.models import db, response_model


@orm_function
def get_by_user(
    user_id: int, offset: int = 0, limit: int = 30, session: Session = None
) -> response_model.OperationList:
    base_request = session.query(db.Operation).filter(
        db.Operation.user_id == user_id
    )

    total = base_request.count()
    operations: List[db.Operation] = (
        base_request.options(joinedload(db.Operation.subject))
        .offset(offset)
        .limit(limit)
        .all()
    )

    operation_list = []
    for operation in operations:
        operation_model = response_model.Operation(
            id=operation.id,
            type=operation.type,
            user=response_model.User(
                id=operation.user.id,
                login=operation.user.login,
                registered=operation.user.registered,
            ),
            subject=None
            if operation.subject is None
            else response_model.StockTiny(
                id=operation.subject.id, shortname=operation.subject.shortname
            ),
            args=operation.args,
        )
        operation_list.append(operation_model)

    return response_model.OperationList(
        operations=operation_list, total=total, offset=offset
    )
