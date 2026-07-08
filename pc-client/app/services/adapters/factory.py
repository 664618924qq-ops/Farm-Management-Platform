from app.models.device import Device
from app.services.adapters.base import DeviceAdapter
from app.services.adapters.mock_adapter import MockDeviceAdapter


def build_adapter(device: Device) -> DeviceAdapter:
    protocol = (device.protocol_type or "").lower()
    # Real protocol drivers can be registered here later by protocol/model.
    if protocol in {"modbus_rtu", "modbus_tcp", "mock", "custom"}:
        return MockDeviceAdapter(device_code=device.device_code)
    return MockDeviceAdapter(device_code=device.device_code)
