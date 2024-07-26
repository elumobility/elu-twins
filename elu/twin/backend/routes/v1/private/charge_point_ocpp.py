"""elu module"""

import logging


from elu.twin.backend.routes.v1.common.charge_point_actions import _set_charging_profile
from elu.twin.data.schemas.auth import OutputAuthV16, InputAuthV16
from elu.twin.data.schemas.charge_point import OutputChargePoint, UpdateChargePoint
from elu.twin.data.schemas.common import Index
from elu.twin.data.schemas.connector import OutputConnector, UpdateConnector
from elu.twin.data.schemas.evse import OutputEvse
from fastapi import APIRouter, Depends, HTTPException, status
from ocpp.v16.enums import ChargePointStatus, UpdateType
from sqlmodel import Session, select, delete

from elu.twin.backend.db.database import get_session
from elu.twin.data.enums import EvseStatus, ConnectorStatus, AuthMethod
from elu.twin.data.tables import (
    AssignedChargingProfile,
    ChargePoint,
    ChargingSchedulePeriod,
    Evse,
    Connector,
    OcppConfigurationV16,
    OcppAuthV16,
)
from elu.twin.data.schemas.ocpp_configuration import (
    OutputOcppConfigurationV16,
    OcppConfigurationV16Update,
)


router = APIRouter(
    prefix="/twin/charge_point",
    tags=["Charge point"],
)


@router.get("/{charge_point_id}", response_model=OutputChargePoint)
async def get_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
):
    """

    :param session:
    :param charge_point_id:
    :return:
    """
    obj = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    print("obj", obj)
    if obj:
        return obj
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Charge point not found"
    )


@router.get(
    "/{charge_point_id}/{connector_id}/{duration}", response_model=OutputChargePoint
)
async def get_composite_schedule_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    connector_id,
    duration,
):
    """

    :param session:
    :param charge_point_id:
    :return:
    """
    obj = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    if obj:
        return obj.get_composite_schedule(connector_id=connector_id, duration=duration)
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Charge point not found"
    )


@router.put("/status/{charge_point_id}/{status}", response_model=OutputChargePoint)
def update_charger_status(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    status: ChargePointStatus,
):
    """

    :param session:
    :param charge_point_id:
    :param status:
    :return:
    """
    db_charge_point = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    if not db_charge_point:
        return {"message": "Charge point not found"}
    db_charge_point.status = status
    session.add(db_charge_point)
    session.commit()
    session.refresh(db_charge_point)
    return db_charge_point


@router.patch("/{charge_point_id}", response_model=OutputChargePoint)
def update_charger(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    charge_point_update: UpdateChargePoint,
):
    """

    :param session:
    :param charge_point_id:
    :param status:
    :return:
    """
    db_charge_point = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    if not db_charge_point:
        return {"message": "Charge point not found"}
    for key, value in charge_point_update.dict().items():
        if value:
            setattr(db_charge_point, key, value)
    session.add(db_charge_point)
    session.commit()
    session.refresh(db_charge_point)
    return db_charge_point


def parse_charging_profile(data: dict) -> AssignedChargingProfile:
    charging_schedule_periods = [
        ChargingSchedulePeriod(
            start_period=period["start_period"],
            limit=period["limit"],
            number_phases=period.get("number_phases"),
        )
        for period in data.get("charging_schedule_period", [])
    ]

    charging_profile = AssignedChargingProfile(
        chargingprofileid=data["chargingprofileid"],
        connector_id=data.get("connector_id"),
        connector_0=data.get("connector_0", True),
        stack_level=data["stack_level"],
        charging_profile_purpose=data["charging_profile_purpose"],
        charging_profile_kind=(data["charging_profile_kind"]),
        charging_rate_unit=(data["charging_rate_unit"]),
        charging_schedule_period=charging_schedule_periods,
    )

    return charging_profile


@router.patch("/profile/{charge_point_id}")
def update_charger_profile(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    charging_profile_request: dict,
):
    """
    Patch an assigned charging profile to a charge point.

    :param session: Database session
    :param charge_point_id: ID of the charge point
    :param charging_profile_request: Request body with charging profile data
    :return: Updated charge point with the new charging profile
    """
    db_charge_point = session.exec(
        select(ChargePoint).where(ChargePoint.id == charge_point_id)
    ).first()
    if not db_charge_point:
        return {"message": "Charge point not found"}

    charge_profile = parse_charging_profile(charging_profile_request)
    charge_profile.charge_point_id = db_charge_point.id

    # Add charging profile and its periods to the session
    session.add(charge_profile)
    session.commit()

    # Update the charging profile ID for periods and add them to the session
    for period in charge_profile.charging_schedule_period:
        period.charging_profile_id = charge_profile.id
        session.add(period)

    session.commit()

    # Append the new charging profile to the charge point and update the session
    db_charge_point.charging_profiles.append(charge_profile)
    session.add(db_charge_point)
    session.commit()
    session.refresh(db_charge_point)

    # _set_charging_profile(session=session,)

    return db_charge_point


# @router.patch("/profile/{charge_point_id}")
# def update_charger_profile(
#     *,
#     session: Session = Depends(get_session),
#     charge_point_id: Index,
#     charging_profile_request: dict,
# ):
#     """

#     :param session:
#     :param charge_point_id:
#     :param status:
#     :return:
#     """
#     db_charge_point = session.exec(
#         select(ChargePoint).where(ChargePoint.id == charge_point_id)
#     ).first()
#     if not db_charge_point:
#         return {"message": "Charge point not found"}

#     charge_profile, charging_schedule_periods = parse_charging_profile(
#         charging_profile_request
#     )
#     charge_profile.charge_point_id = db_charge_point.id
#     charge_profile.charging_schedule_period = charging_schedule_periods
#     print("\n charge profile", charge_profile)

#     session.add(charge_profile)
#     session.commit()
#     for period in charging_schedule_periods:
#         period.charging_profile_id = charge_profile.id
#         session.add(period)
#         session.commit()

#     db_charge_point.charging_profiles.append(charge_profile)
#     session.add(db_charge_point)
#     session.commit()
#     session.refresh(db_charge_point)
#     return db_charge_point


@router.put("/evse/status/{evse_id}/{status}", response_model=OutputEvse)
def update_evse_status(
    *,
    session: Session = Depends(get_session),
    evse_id: Index,
    status: EvseStatus,
    active_connector: int | None = None,
):
    """

    :param session:
    :param evse_id:
    :param status:
    :param active_connector:
    :return:
    """
    db_evse = session.exec(select(Evse).where(Evse.id == evse_id)).first()
    if not db_evse:
        raise HTTPException(404, detail="Evse not found")
    # TODO: add logic to check if the combination of active_connector and status is valid
    db_evse.status = status
    db_evse.active_connector_id = active_connector
    session.add(db_evse)
    session.commit()
    session.refresh(db_evse)
    return db_evse


@router.put("/connector/status/{connector_id}/{status}", response_model=OutputConnector)
def update_connector_status(
    *,
    session: Session = Depends(get_session),
    connector_id: Index,
    status: ConnectorStatus,
):
    """

    :param session:
    :param connector_id:
    :param status:
    :return:
    """
    db_connector = session.exec(
        select(Connector).where(Connector.id == connector_id)
    ).first()
    if not db_connector:
        return {"message": "Connector not found"}
    # TODO: add logic to set other values based on status
    db_connector.status = status
    session.add(db_connector)
    session.commit()
    session.refresh(db_connector)
    return db_connector


@router.put("/connector/{connector_id}", response_model=OutputConnector)
def update_connector_state(
    *,
    session: Session = Depends(get_session),
    connector_id: Index,
    update_connector: UpdateConnector,
):
    """

    :param session:
    :param connector_id:
    :param update_connector:
    :return:
    """
    db_connector = session.exec(
        select(Connector).where(Connector.id == connector_id)
    ).first()
    if not db_connector:
        return {"message": "Connector not found"}
    for key, value in update_connector.dict().items():
        setattr(db_connector, key, value)
    session.add(db_connector)
    session.commit()
    session.refresh(db_connector)
    return db_connector


@router.get(
    "/configuration/{configuration_id}",
    response_model=OutputOcppConfigurationV16,
)
def get_ocpp_configuration(
    *,
    session: Session = Depends(get_session),
    configuration_id: Index,
):
    """

    :param session:
    :param configuration_id:
    :return:
    """
    db_configuration = session.exec(
        select(OcppConfigurationV16).where(OcppConfigurationV16.id == configuration_id)
    ).first()
    if not db_configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )
    return db_configuration


@router.put(
    "/configuration/{configuration_id}",
    response_model=OutputOcppConfigurationV16,
)
def update_ocpp_configuration(
    *,
    session: Session = Depends(get_session),
    configuration_id: Index,
    configuration_update: OcppConfigurationV16Update,
):
    """

    :param session:
    :param configuration_id:
    :param configuration_update:
    :return:
    """
    db_configuration = session.exec(
        select(OcppConfigurationV16).where(OcppConfigurationV16.id == configuration_id)
    ).first()
    if not db_configuration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Configuration not found"
        )
    for key, value in configuration_update.dict().items():
        if value:
            setattr(db_configuration, key, value)
    session.add(db_configuration)
    session.commit()
    session.refresh(db_configuration)
    return db_configuration


@router.get("/charge-point/auth/{charge_point_id}", response_model=list[OutputAuthV16])
def get_list_of_auth_objects_for_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    auth_method: AuthMethod | None = None,
):
    """

    :param session:
    :param charge_point_id:
    :param auth_method:
    :return:
    """
    query = select(OcppAuthV16).where(OcppAuthV16.charge_point_id == charge_point_id)
    if auth_method:
        query = query.where(OutputAuthV16.auth_method == auth_method)
    db_auth_objects = session.exec(query).all()
    return db_auth_objects


@router.post(
    "/charge-point/auth/{charge_point_id}/cache", response_model=list[OutputAuthV16]
)
def create_auth_objects_for_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    auth: InputAuthV16,
):
    """

    :param session:
    :param charge_point_id:
    :param auth:
    :return:
    """
    db_auth = session.exec(
        select(OcppAuthV16).where(OcppAuthV16.id_tag == auth.id_tag)
    ).first()
    if db_auth:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Auth object already exists"
        )
    db_auth = OcppAuthV16(**auth.dict(), charge_point_id=charge_point_id)
    session.add(db_auth)
    session.commit()
    session.refresh(db_auth)
    return db_auth


@router.post(
    "/charge-point/auth/{charge_point_id}/list/{update_list_mode}",
    response_model=list[OutputAuthV16],
)
def create_auth_objects_for_charge_point(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
    auth: list[InputAuthV16],
    update_list: UpdateType,
):
    """

    :param session:
    :param charge_point_id:
    :param auth:
    :return:
    """
    db_auth_objects = []
    if update_list == UpdateType.differential:
        db_auth = session.exec(
            select(OcppAuthV16).where(OcppAuthV16.charge_point_id == charge_point_id)
        ).all()
        for auth_object in auth:
            db_auth_object = session.exec(
                select(OcppAuthV16).where(OcppAuthV16.id_tag == auth_object.id_tag)
            ).first()
            if db_auth_object:
                for key, value in auth_object.dict().items():
                    setattr(db_auth_object, key, value)
                session.add(db_auth_object)
            else:
                db_auth_object = OcppAuthV16(
                    **auth_object.dict(), charge_point_id=charge_point_id
                )
                session.add(db_auth_object)
            db_auth_objects.append(db_auth_object)
        session.commit()
    else:
        for auth_object in auth:
            db_auth_object = session.exec(
                select(OcppAuthV16).where(OcppAuthV16.id_tag == auth_object.id_tag)
            ).first()
            if db_auth_object:
                for key, value in auth_object.dict().items():
                    setattr(db_auth_object, key, value)
                session.add(db_auth_object)
            else:
                db_auth_object = OcppAuthV16(
                    **auth_object.dict(), charge_point_id=charge_point_id
                )
                session.add(db_auth_object)
            db_auth_objects.append(db_auth_object)
        session.commit()
    return db_auth_objects


@router.delete("/charge-point/auth/{charge_point_id}/cache")
def delete_auth_cache(
    *,
    session: Session = Depends(get_session),
    charge_point_id: Index,
):
    """

    :return:
    """
    _ = session.exec(
        delete(OcppAuthV16)
        .where(OcppAuthV16.charge_point_id == charge_point_id)
        .where(OcppAuthV16.auth_method == AuthMethod.cache)
    )
    logging.warning("Deleting auth cache")
    return {"message": "Auth cache deleted"}
