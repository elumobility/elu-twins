from elu.twin.data.schemas.common import Index
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlmodel import Session, select

from elu.twin.backend.db.database import get_session
from elu.twin.data.enums import PowerType, VehicleStatus
from elu.twin.data.tables import Vehicle
from elu.twin.data.schemas.vehicle import OutputVehicle, UpdateVehicle

router = APIRouter(prefix="/twin/vehicle", tags=["Vehicle"])


@router.get("/{vehicle_id}", response_model=OutputVehicle)
def get_vehicle(
    *,
    session: Session = Depends(get_session),
    vehicle_id: Index,
):
    """
    Get vehicle
    """
    obj = session.exec(select(Vehicle).where(Vehicle.id == vehicle_id)).first()
    if not obj:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    return obj


@router.put("/soc/{vid}", response_model=OutputVehicle)
def update_vehicle_soc(
    *, session: Session = Depends(get_session), vid: str, vehicle: UpdateVehicle
):
    """
    Update vehicle state of charge
    """
    if vehicle.soc is None:
        raise HTTPException(status_code=400, detail="Soc not provided")
    db_vehicle = session.exec(select(Vehicle).where(Vehicle.id == vid)).first()
    if not vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    db_vehicle.soc = vehicle.soc
    session.add(db_vehicle)
    session.commit()
    session.refresh(db_vehicle)
    return db_vehicle


@router.put("/charging-rate/{vid}/{power_type}/{soc}")
def get_power_from_soc(
    *,
    session: Session = Depends(get_session),
    vid: str,
    power_type: PowerType,
    soc: float,
    charging_type,
):
    """
    Update vehicle state of charge
    """
    db_vehicle = session.exec(select(Vehicle).where(Vehicle.id == vid)).first()
    if not db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    power = (
        db_vehicle.maximum_dc_charging_rate
        if power_type == PowerType.dc
        else db_vehicle.maximum_ac_charging_rate
    )
    response = {"power": power}
    return response


@router.put("/status/{vid}/{status}", response_model=OutputVehicle)
def get_power_from_soc(
    *,
    session: Session = Depends(get_session),
    vid: str,
    status: VehicleStatus,
):
    """
    Update vehicle state of charge
    """
    db_vehicle = session.exec(select(Vehicle).where(Vehicle.id == vid)).first()
    if not db_vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    db_vehicle.status = status
    session.add(db_vehicle)
    session.commit()
    session.refresh(db_vehicle)
    return db_vehicle
