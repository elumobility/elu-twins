from typing import Annotated, List

from elu.twin.data.schemas.charge_point import (
    OutputChargePoint,
    InputChargePoint,
    ChargePointString,
)
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.connector import InputConnector, OutputConnector
from elu.twin.data.schemas.evse import InputEvse, OutputEvse
from fastapi import APIRouter, Depends, HTTPException, Query
from ocpp.v201.enums import ConnectorType

from elu.twin.backend.crud.user import get_current_active_user
from elu.twin.backend.db.database import get_session
from sqlmodel import select, Session
from elu.twin.backend.crud.steve_mysql import add_charge_points_to_steve

from elu.twin.data.tables import (
    User,
    ChargePoint,
    Connector,
    Evse,
    Quota,
    OcppConfigurationV16,
    Vehicle,
)

from elu.twin.data.helpers import get_token_price, get_now

router = APIRouter(
    prefix="/twin/charge-point",
    tags=["Charge point"],
)


@router.get("/", response_model=List[OutputChargePoint])
async def get_charge_points(
    *,
    session: Session = Depends(get_session),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    objs = session.exec(
        select(ChargePoint).where(ChargePoint.user_id == current_user.id)
    ).all()
    return objs


@router.get("/{charge_point_id}", response_model=OutputChargePoint)
async def get_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    obj = session.exec(
        select(ChargePoint)
        .where(ChargePoint.user_id == current_user.id)
        .where(ChargePoint.id == charge_point_id)
    ).first()
    return obj


@router.get("/evse/{evse_id}", response_model=OutputEvse)
async def get_evse(
    *,
    session: Session = Depends(get_session),
    evse_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    evse = session.exec(select(Evse).where(Evse.id == evse_id)).first()
    if not evse:
        raise HTTPException(status_code=400, detail="Evse not found")
    charge_point = evse.charge_point
    if charge_point.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Evse not found")
    return evse


@router.get("/connector/{connector_id}", response_model=OutputConnector)
async def get_connector(
    *,
    session: Session = Depends(get_session),
    connector_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    connector = session.exec(
        select(Connector).where(Connector.id == connector_id)
    ).first()
    if not connector:
        raise HTTPException(status_code=400, detail="Connector not found")
    evse = connector.evse
    charge_point = evse.charge_point
    if charge_point.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Connector not found")
    return connector


@router.put(
    "/connector/connect-vehicle/{connector_id}/{vehicle_id}",
    response_model=OutputConnector,
)
async def get_connector(
    *,
    session: Session = Depends(get_session),
    connector_id: Index,
    vehicle_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    connector = session.exec(
        select(Connector).where(Connector.id == connector_id)
    ).first()
    if not connector:
        raise HTTPException(status_code=400, detail="Connector not found")
    evse = connector.evse
    charge_point = evse.charge_point
    if charge_point.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Connector not found")
    vehicle = session.exec(select(Vehicle).where(Vehicle.id == vehicle_id)).first()
    if not vehicle:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    if vehicle.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Vehicle not found")
    connector.vehicle_id = vehicle_id
    session.add(connector)
    session.commit()
    session.refresh(connector)
    return connector


@router.put(
    "/connector/disconnect-vehicle/{connector_id}", response_model=OutputConnector
)
async def get_connector(
    *,
    session: Session = Depends(get_session),
    connector_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    connector = session.exec(
        select(Connector).where(Connector.id == connector_id)
    ).first()
    if not connector:
        raise HTTPException(status_code=400, detail="Connector not found")
    evse = connector.evse
    charge_point = evse.charge_point
    if charge_point.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Connector not found")
    if connector.vehicle_id is not None:
        raise HTTPException(status_code=400, detail="Not vehicle connected")
    connector.vehicle_id = None
    session.add(connector)
    session.commit()
    session.refresh(connector)
    return connector


def _add_charge_point(
    session: Session, charge_point: InputChargePoint, user_id: Index, quota_id: Index
):
    db_charge_point = ChargePoint(
        user_id=user_id,
        name=charge_point.name,
        cid=charge_point.cid,
        csms_url=charge_point.csms_url,
        maximum_dc_power=charge_point.maximum_dc_power,
        maximum_ac_power=charge_point.maximum_ac_power,
        quota_id=quota_id,
        token_cost_per_minute=len(charge_point.evses) * get_token_price(),
        ocpp_protocol=charge_point.ocpp_protocol,
    )
    session.add(db_charge_point)
    session.commit()
    number_connectors = 0
    for evseid, evse in enumerate(charge_point.evses):
        db_evse = Evse(charge_point_id=db_charge_point.id, evseid=evseid + 1)
        session.add(db_evse)
        session.commit()
        for connectorid, connector in enumerate(evse.connectors):
            number_connectors += 1
            db_connector = Connector(
                evse_id=db_evse.id, connectorid=number_connectors, **connector.dict()
            )
            session.add(db_connector)
            session.commit()
    ocppv16_configuration = OcppConfigurationV16(
        NumberOfConnectors=number_connectors, charge_point_id=db_charge_point.id
    )
    session.add(ocppv16_configuration)
    session.commit()
    db_charge_point.ocpp_configuration_v16_id = ocppv16_configuration.id
    session.add(db_charge_point)
    session.commit()
    session.refresh(db_charge_point)
    return db_charge_point


@router.post("/", response_model=OutputChargePoint)
def create_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point: InputChargePoint,
    add_to_internal_steve: bool = Query(
        False,
        description="Add to internal steve, use only for internal demo purpose",
        include_in_schema=False,
    ),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if not quota:
        raise HTTPException(
            status_code=400, detail="Quota not found, not able to create charge point"
        )
    if quota.current_number_of_charge_points >= quota.max_number_of_charge_points:
        raise HTTPException(
            status_code=400, detail="Quota exceeded, not able to create charge point"
        )
    quota.current_number_of_charge_points += 1
    session.add(quota)
    db_charge_point = _add_charge_point(
        session, charge_point, current_user.id, quota.id
    )
    if add_to_internal_steve:
        add_charge_points_to_steve([db_charge_point.cid])
    return db_charge_point


def get_charge_points_from_str(
    charge_point_string: ChargePointString,
) -> List[InputChargePoint]:
    """Parse a string to a list of charge points. The format of charge_point_string is:
    VENDOR:NUMBER_OF_EVSES:MAX_AC_POWER:MAX_DC_POWER:NUMBER_OF_CHARGERS
    """
    (
        vendor,
        number_of_evses,
        max_ac_power,
        max_dc_power,
        number_of_chargers,
    ) = charge_point_string.charge_point_string.split(":")

    now = get_now(as_string=False).strftime("%Y%m%d%H%M%S")

    charge_points = [
        InputChargePoint(
            name=f"{vendor}-{now}-{i}",
            maximum_dc_power=int(max_dc_power),
            maximum_ac_power=int(max_ac_power),
            password=charge_point_string.password,
            csms_url=charge_point_string.csms_url,
            evses=[
                InputEvse(
                    connectors=[InputConnector(connector_type=ConnectorType.c_ccs1)]
                )
                for _ in range(int(int(number_of_evses)))
            ],
        )
        for i in range(int(number_of_chargers))
    ]

    return charge_points


@router.post("/by-string/", response_model=List[OutputChargePoint])
def create_charge_point_by_string(
    *,
    session: Session = Depends(get_session),
    charge_point_string: ChargePointString,
    add_to_internal_steve: bool = Query(
        False,
        description="Add to internal steve, use only for internal demo purpose",
        include_in_schema=False,
    ),
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    charge_points: List[InputChargePoint] = get_charge_points_from_str(
        charge_point_string
    )
    results = []
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if not quota:
        raise HTTPException(
            status_code=400, detail="Quota not found, not able to create charge point"
        )
    if (
        quota.current_number_of_charge_points + len(charge_points)
        > quota.max_number_of_charge_points
    ):
        raise HTTPException(
            status_code=400, detail="Quota exceeded, not able to create charge point"
        )
    for charge_point in charge_points:
        db_charge_point = _add_charge_point(
            session, charge_point, current_user.id, quota.id
        )
        results.append(db_charge_point)
        if add_to_internal_steve:
            add_charge_points_to_steve([charge_point.cid])
    quota.current_number_of_charge_points += len(charge_points)
    session.add(quota)
    return results


@router.delete("/{charge_point_id}", response_model=OutputChargePoint)
async def delete_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    charge_point = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    if not charge_point:
        raise HTTPException(status_code=400, detail="Charge point not found")
    if charge_point.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="Charge point not found")
    quota = session.exec(select(Quota).where(Quota.id == current_user.quota_id)).first()
    if not quota:
        raise HTTPException(
            status_code=400, detail="Quota not found, not able to create charge point"
        )
    quota.current_number_of_charge_points -= 1
    evses = charge_point.evses
    for evse in evses:
        connectors = evse.connectors
        for connector in connectors:
            session.delete(connector)
        session.delete(evse)
    ocpp_configuration = session.exec(
        select(OcppConfigurationV16).where(
            OcppConfigurationV16.id == charge_point.ocpp_configuration_v16_id
        )
    ).first()
    session.add(quota)
    session.delete(charge_point)
    session.commit()
    session.delete(ocpp_configuration)
    session.commit()
    return charge_point
