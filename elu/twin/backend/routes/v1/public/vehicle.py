from datetime import datetime
from typing import Annotated

from elu.twin.data.schemas.common import Index
from fastapi import APIRouter, Depends, HTTPException, Query

from elu.twin.backend.crud.user import get_current_active_user
from elu.twin.backend.db.database import engine, get_session
from sqlmodel import select, Session

from elu.twin.data.tables import Vehicle, User, Quota
from elu.twin.data.schemas.vehicle import OutputVehicle, InputVehicle
from elu.twin.backend.crud.steve_mysql import add_ocpp_tags_to_steve

from fastapi import status


router = APIRouter(
    prefix="/twin/vehicle",
    tags=["Vehicle"],
)


@router.get("/", response_model=list[OutputVehicle])
async def get_vehicles(
    *,
    session: Session = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    objs = session.exec(select(Vehicle).where(Vehicle.user_id == current_user.id)).all()
    return objs


@router.get("/{vehicle_id}", response_model=OutputVehicle)
async def get_vehicle(
    vehicle_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    with Session(engine) as session:
        obj = session.exec(
            select(Vehicle)
            .where(Vehicle.user_id == current_user.id)
            .where(Vehicle.id == vehicle_id)
        ).first()
        return obj


@router.post("/", response_model=OutputVehicle)
def create_vehicle(
    *,
    session: Session = Depends(get_session),
    vehicle: InputVehicle,
    add_to_internal_steve: bool = Query(
        False,
        description="Add to internal steve, use only for internal demo purpose",
        include_in_schema=False,
    ),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if quota is None:
        raise Exception("User quota not found")
    if quota.current_number_of_vehicles >= quota.max_number_of_vehicles:
        raise Exception("User quota exceeded")
    quota.current_number_of_vehicles += 1
    session.add(quota)
    db_vehicle = Vehicle(
        user_id=current_user.id,
        **vehicle.dict(),
    )
    session.add(db_vehicle)
    session.commit()
    session.refresh(db_vehicle)
    if add_to_internal_steve:
        add_ocpp_tags_to_steve([db_vehicle.id_tag_suffix])
    return db_vehicle


def get_vehicles_from_str(vehicle_str: str) -> list[InputVehicle]:
    "format VENDOR:MODEL:MAX_AC_POWER:MAX_DC_POWER:BATTERY_CAPACITY:NUM_VEHICLES"

    (
        vendor,
        model,
        max_ac_power,
        max_dc_power,
        battery_capacity,
        num_vehicles,
    ) = vehicle_str.split(":")

    now = datetime.utcnow().strftime("%Y%m%d%H%M%S")

    vehicles = [
        InputVehicle(
            name=f"{vendor}-{model}-{now}-{i}",
            maximum_ac_charging_rate=int(max_ac_power),
            maximum_dc_charging_rate=int(max_dc_power),
            battery_capacity=int(battery_capacity),
            created_at=now,
            updated_at=now,
        )
        for i in range(int(num_vehicles))
    ]

    return vehicles


@router.post("/{vehicle_str}", response_model=list[OutputVehicle])
def create_vehicle_from_string(
    *,
    session: Session = Depends(get_session),
    vehicle_str: str,
    add_to_internal_steve: bool = Query(
        False,
        description="Add to internal steve, use only for internal demo purpose",
        include_in_schema=False,
    ),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if quota is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User quota not found"
        )

    vehicles = get_vehicles_from_str(vehicle_str)
    if quota.current_number_of_vehicles + len(vehicles) >= quota.max_number_of_vehicles:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="User quota exceeded"
        )
    quota.current_number_of_vehicles += len(vehicles)
    result = []
    for vehicle in vehicles:
        db_vehicle = Vehicle(
            user_id=current_user.id,
            **vehicle.dict(),
        )
        session.add(db_vehicle)
        session.commit()
        result.append(db_vehicle)
        if add_to_internal_steve:
            add_ocpp_tags_to_steve([db_vehicle.id_tag_suffix])
    session.add(quota)
    session.commit()
    return result


@router.delete("/{vehicle_id}", response_model=OutputVehicle)
async def delete_vehicle(
    *,
    session: Session = Depends(get_session),
    vehicle_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    vehicle = session.exec(
        select(Vehicle)
        .where(Vehicle.user_id == current_user.id)
        .where(Vehicle.id == vehicle_id)
    ).first()
    if not vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if not quota:
        raise HTTPException(
            status_code=400, detail="Quota not found, not able to delete vehicle"
        )
    quota.current_number_of_vehicles -= 1
    session.add(quota)
    session.delete(vehicle)
    session.commit()
    return vehicle
