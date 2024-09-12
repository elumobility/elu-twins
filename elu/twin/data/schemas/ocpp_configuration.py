from typing import Tuple

from ocpp.v16.datatypes import KeyValue
from ocpp.v16.enums import Measurand
from sqlmodel import Field, SQLModel

from elu.twin.data.schemas.common import TableBase, Index

read_only = [
    "AuthorizeRemoteTxRequests",
    "GetConfigurationMaxKeys",
    "MeterValuesAlignedDataMaxLength",
    "MeterValuesSampledDataMaxLength",
    "NumberOfConnectors",
    "ConnectorPhaseRotationMaxLength",
    "StopTxnAlignedDataMaxLength",
    "StopTxnSampledDataMaxLength",
    "SupportedFeatureProfilesMaxLength",
    "LocalAuthListMaxLength",
    "SendLocalListMaxLength",
    "ReserveConnectorZeroSupported",
    "ChargeProfileMaxStackLevel",
    "ChargingScheduleAllowedChargingRateUnit",
    "ChargingScheduleMaxPeriods",
    "ConnectorSwitch3to1PhaseSupported",
    "MaxChargingProfilesInstalled",
]

ocpp_configuration_types = {
    "bool": [
        "AllowOfflineTxForUnknownId",
        "AuthorizationCacheEnabled",
        "AuthorizeRemoteTxRequests",
        "LocalAuthorizeOffline",
        "LocalPreAuthorize",
        "StopTransactionOnEVSideDisconnect",
        "StopTransactionOnInvalidId",
        "UnlockConnectorOnEVSideDisconnect",
        "LocalAuthListEnabled",
        "ReserveConnectorZeroSupported",
        "ConnectorSwitch3to1PhaseSupported",
    ],
    "int": [
        "BlinkRepeat",
        "ClockAlignedDataInterval",
        "ConnectionTimeOut",
        "GetConfigurationMaxKeys",
        "HeartbeatInterval",
        "LightIntensity",
        "MaxEnergyOnInvalidId",
        "MeterValuesAlignedDataMaxLength",
        "MeterValuesSampledDataMaxLength",
        "MeterValueSampleInterval",
        "MinimumStatusDuration",
        "NumberOfConnectors",
        "ResetRetries",
        "ConnectorPhaseRotationMaxLength",
        "StopTxnAlignedDataMaxLength",
        "StopTxnSampledDataMaxLength",
        "SupportedFeatureProfilesMaxLength",
        "TransactionMessageAttempts",
        "TransactionMessageRetryInterval",
        "WebSocketPingInterval",
        "LocalAuthListMaxLength",
        "SendLocalListMaxLength",
        "ChargeProfileMaxStackLevel",
        "ChargingScheduleMaxPeriods",
        "MaxChargingProfilesInstalled",
    ],
    "list": [
        "MeterValuesAlignedData",
        "MeterValuesSampledData",
        "StopTxnAlignedData",
        "StopTxnSampledData",
        "SupportedFeatureProfiles",
    ],
}

ocpp_key = (
    ocpp_configuration_types["int"]
    + ocpp_configuration_types["bool"]
    + ocpp_configuration_types["list"]
)
ocpp_key.sort()


def is_read_only(key: str) -> bool:
    """Evaluate if a key can be updated

    :param key: name of charge_point key configuration
    :return: true if is a read only key or false if not
    """

    return key in read_only


def cast_to_key_value(key: str, value: str | bool | int | list | None) -> str | None:
    """

    :param key:
    :param value:
    """
    if value is None:
        return None
    if key in ocpp_configuration_types.get("list"):
        return ",".join(value)
    return str(value)


def cast_from_key_value(
    key_value: KeyValue,
) -> Tuple[str, str | int | bool | list | None]:
    """

    :param key_value:
    """
    key = key_value.key
    if key_value.value is None:
        return key, None
    if key_value.key in ocpp_configuration_types.get("list"):
        return key, key_value.value.split(",")
    if key_value.key in ocpp_configuration_types.get("bool"):
        return key, bool(key_value.value)
    if key_value.key in ocpp_configuration_types.get("int"):
        return key, int(key_value.value)
    return key, key_value.value


class OcppConfigurationBase(SQLModel):
    """Basic method useful for a charge_point configuration"""

    def get_key_value(self, key: str) -> KeyValue | None:
        """Return the value of the corresponding with in KeyValue format

        :param key: key to get value
        :return: KeyValue from OCPP protocol
        """
        if hasattr(self, key):
            return KeyValue(
                key,
                readonly=is_read_only(key),
                value=cast_to_key_value(key, getattr(self, key)),
            )
        return None

    def set_value(self, key, value):
        """

        :param key:
        :param value:
        """
        key_value = KeyValue(key=key, value=value, readonly=False)
        _key, _value = cast_from_key_value(key_value)
        self.__setattr__(_key, _value)

    def get_list_of_keys(
        self, key: list[str] | None
    ) -> Tuple[list[KeyValue], list[str]]:
        """

        :param key:
        :return:
        """
        list_keys = key if key else ocpp_key
        configuration_key = [self.get_key_value(k) for k in list_keys if k in ocpp_key]
        unknown_key = None if key is None else [k for k in key if k not in ocpp_key]
        return configuration_key, unknown_key


class OcppConfigurationV16Params(OcppConfigurationBase):
    AllowOfflineTxForUnknownId: bool = Field(
        default=True, description="Allow offline transactions for unknown id"
    )
    AuthorizationCacheEnabled: bool | None = Field(
        default=False, description="Enable authorization cache"
    )
    AuthorizeRemoteTxRequests: bool = Field(
        default=True, description="Authorize remote transaction requests"
    )
    BlinkRepeat: int | None = Field(default=None, description="Blink repeat")
    ClockAlignedDataInterval: int = Field(
        default=900, description="Clock aligned data interval"
    )
    ConnectionTimeOut: int = Field(default=60, description="Connection timeout")
    GetConfigurationMaxKeys: int = Field(
        default=50, description="Get configuration max keys"
    )
    HeartbeatInterval: int = Field(default=30, description="Heartbeat interval")
    LightIntensity: int | None = Field(default=None, description="Light intensity")
    LocalAuthorizeOffline: bool = Field(
        default=True, description="Local authorize offline"
    )
    LocalPreAuthorize: bool = Field(default=True, description="Local pre authorize")
    MaxEnergyOnInvalidId: int | None = Field(
        default=None, description="Max energy on invalid id"
    )
    MeterValuesAlignedData: str = Field(
        default="", description="Meter values aligned data"
    )
    MeterValuesAlignedDataMaxLength: int = Field(
        default=30, description="Meter values aligned data max length"
    )
    MeterValuesSampledData: str = ",".join(
        [
            f"{Measurand.soc.value}",
            f"{Measurand.energy_active_import_register.value}",
            f"{Measurand.power_active_import.value}",
            f"{Measurand.voltage.value}",
            f"{Measurand.current_import.value}",
        ]
    )
    MeterValuesSampledDataMaxLength: int = Field(
        default=30, description="Meter values sampled data max length"
    )
    MeterValueSampleInterval: int = Field(
        default=30, description="Meter value sample interval"
    )
    MinimumStatusDuration: int | None = Field(
        default=None, description="Minimum status duration"
    )
    NumberOfConnectors: int = Field(default=1, description="Number of connectors")
    ResetRetries: int = Field(default=3, description="Reset retries")
    ConnectorPhaseRotation: str = Field(
        default="", description="Connector phase rotation"
    )
    ConnectorPhaseRotationMaxLength: int | None = Field(
        default=None, description="Connector phase rotation max length"
    )
    StopTransactionOnEVSideDisconnect: bool = Field(
        default=True, description="Stop transaction on EV side disconnect"
    )
    StopTransactionOnInvalidId: bool = Field(
        default=True, description="Stop transaction on invalid id"
    )
    StopTxnAlignedData: str = Field(
        default="", description="Stop transaction aligned data"
    )
    StopTxnAlignedDataMaxLength: int | None = Field(
        default=None, description="Stop transaction aligned data max length"
    )
    StopTxnSampledData: str = Field(
        default="", description="Stop transaction sampled data"
    )
    StopTxnSampledDataMaxLength: int | None = Field(
        default=None, description="Stop transaction sampled data max length"
    )
    SupportedFeatureProfiles: str = Field(
        default="", description="Supported feature profiles"
    )
    SupportedFeatureProfilesMaxLength: int = Field(
        default=100, description="Supported feature profiles max length"
    )
    TransactionMessageAttempts: int = Field(
        default=3, description="Transaction message attempts"
    )
    TransactionMessageRetryInterval: int = Field(
        default=30, description="Transaction message retry interval"
    )
    UnlockConnectorOnEVSideDisconnect: bool = Field(
        default=True, description="Unlock connector on EV side disconnect"
    )
    WebSocketPingInterval: int | None = Field(
        default=None, description="Web socket ping interval"
    )
    LocalAuthListEnabled: bool = Field(
        default=True, description="Local authorization list enabled"
    )
    LocalAuthListMaxLength: int = Field(
        default=100, description="Local authorization list max length"
    )
    SendLocalListMaxLength: int = Field(
        default=100, description="Send local list max length"
    )
    ReserveConnectorZeroSupported: bool = Field(
        default=False, description="Reserve connector zero supported"
    )
    ChargeProfileMaxStackLevel: int = Field(
        default=10, description="Charge profile max stack level"
    )
    ChargingScheduleAllowedChargingRateUnit: str = Field(
        default="", description="Charging schedule allowed charging rate unit"
    )
    ChargingScheduleMaxPeriods: int = Field(
        default=10, description="Charging schedule max periods"
    )
    ConnectorSwitch3to1PhaseSupported: bool = Field(
        default=False, description="Connector switch 3 to 1 phase supported"
    )
    MaxChargingProfilesInstalled: int = Field(
        default=10, description="Max charging profiles installed"
    )


class OcppConfigurationV16Update(SQLModel):
    """Define the OCPP v1.6 configuration for a charge point"""

    AllowOfflineTxForUnknownId: bool | None = None
    AuthorizationCacheEnabled: bool | None = None
    AuthorizeRemoteTxRequests: bool | None = None
    BlinkRepeat: int | None = None
    ClockAlignedDataInterval: int | None = None
    ConnectionTimeOut: int | None = None
    GetConfigurationMaxKeys: int | None = None
    HeartbeatInterval: int | None = None
    LightIntensity: int | None = None
    LocalAuthorizeOffline: bool | None = None
    LocalPreAuthorize: bool | None = None
    MaxEnergyOnInvalidId: int | None = None
    MeterValuesAlignedData: str | None = None
    MeterValuesAlignedDataMaxLength: int | None = None
    MeterValuesSampledData: str | None = None
    MeterValuesSampledDataMaxLength: int | None = None
    MeterValueSampleInterval: int | None = None
    MinimumStatusDuration: int | None = None
    NumberOfConnectors: int | None = None
    ResetRetries: int | None = None
    ConnectorPhaseRotation: str | None = None
    ConnectorPhaseRotationMaxLength: int | None = None
    StopTransactionOnEVSideDisconnect: bool | None = None
    StopTransactionOnInvalidId: bool | None = None
    StopTxnAlignedData: str | None = None
    StopTxnAlignedDataMaxLength: int | None = None
    StopTxnSampledData: str | None = None
    StopTxnSampledDataMaxLength: int | None = None
    SupportedFeatureProfiles: str | None = None
    SupportedFeatureProfilesMaxLength: int | None = None
    TransactionMessageAttempts: int | None = None
    TransactionMessageRetryInterval: int | None = None
    UnlockConnectorOnEVSideDisconnect: bool | None = None
    WebSocketPingInterval: int | None = None
    LocalAuthListEnabled: bool | None = None
    LocalAuthListMaxLength: int | None = None
    SendLocalListMaxLength: int | None = None
    ReserveConnectorZeroSupported: bool | None = None
    ChargeProfileMaxStackLevel: int | None = None
    ChargingScheduleAllowedChargingRateUnit: str | None = None
    ChargingScheduleMaxPeriods: int | None = None
    ConnectorSwitch3to1PhaseSupported: bool | None = None
    MaxChargingProfilesInstalled: int | None = None


class OcppConfigurationV16Base(OcppConfigurationV16Params):
    """Define the OCPP v1.6 configuration for a charge point"""

    pass


class OutputOcppConfigurationV16(OcppConfigurationV16Params):
    """Define the OCPP v1.6 configuration for a charge point"""

    id: Index
