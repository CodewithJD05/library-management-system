
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.borrowing import Borrowing
from app.models.fine import Fine
from app.models.staff_user import StaffUser
from app.routers.auth import get_current_staff_user
from app.schemas.fine import FineResponse


router = APIRouter(prefix="/fines", tags=["Fines"])

CurrentStaff = Annotated[
    StaffUser,
    Depends(get_current_staff_user),
]

DatabaseSession = Annotated[
    Session,
    Depends(get_db),
]


@router.get("/", response_model=list[FineResponse])
def get_fines(
    db: DatabaseSession,
    current_user: CurrentStaff,
    unpaid_only: bool = Query(default=False),
    member_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    statement = select(Fine)

    if unpaid_only:
        statement = statement.where(Fine.status == "unpaid")

    if member_id is not None:
        statement = (
            statement
            .join(Borrowing, Fine.borrowing_id == Borrowing.id)
            .where(Borrowing.member_id == member_id)
        )

    statement = (
        statement
        .order_by(Fine.id.desc())
        .offset(skip)
        .limit(limit)
    )

    return db.scalars(statement).all()


@router.put("/{fine_id}/pay", response_model=FineResponse)
def pay_fine(
    fine_id: int,
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    try:
        fine = db.scalar(
            select(Fine)
            .where(Fine.id == fine_id)
            .with_for_update()
        )

        if fine is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Fine record not found",
            )

        if fine.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This fine has already been paid",
            )

        fine.status = "paid"
        fine.paid_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(fine)

        return fine

    except Exception:
        db.rollback()
        raise


@router.get("/summary")
def get_fine_summary(
    db: DatabaseSession,
    current_user: CurrentStaff,
):
    statement = select(
        func.count(Fine.id).label("total_fines"),
        func.coalesce(
            func.sum(case((Fine.status == "unpaid", 1), else_=0)),
            0,
        ).label("unpaid_fines"),
        func.coalesce(
            func.sum(case((Fine.status == "paid", 1), else_=0)),
            0,
        ).label("paid_fines"),
        func.coalesce(
            func.sum(Fine.amount),
            0,
        ).label("total_amount"),
        func.coalesce(
            func.sum(
                case(
                    (Fine.status == "unpaid", Fine.amount),
                    else_=0,
                )
            ),
            0,
        ).label("unpaid_amount"),
        func.coalesce(
            func.sum(
                case(
                    (Fine.status == "paid", Fine.amount),
                    else_=0,
                )
            ),
            0,
        ).label("paid_amount"),
    )

    result = db.execute(statement).one()

    return {
        "total_fines": result.total_fines,
        "unpaid_fines": result.unpaid_fines,
        "paid_fines": result.paid_fines,
        "total_amount": float(result.total_amount),
        "unpaid_amount": float(result.unpaid_amount),
        "paid_amount": float(result.paid_amount),
    }
