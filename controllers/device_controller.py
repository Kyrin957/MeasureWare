"""Synchronous wrapper around LJXAwrap for LJ-X8000 communication.

This controller is designed to run on a worker thread (not the GUI thread).
All calls are synchronous and blocking.
"""

import ctypes
import logging

import LJXAwrap

logger = logging.getLogger(__name__)


class DeviceController:
    """Thin synchronous wrapper around LJXAwrap.dll functions."""

    def __init__(self, device_id: int = 0):
        self._device_id = device_id
        self._connected = False

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    def open_connection(self, ethernet_config) -> int:
        """Open Ethernet connection. Returns LJXAwrap return code (0 = success)."""
        res = LJXAwrap.LJX8IF_EthernetOpen(self._device_id, ethernet_config)
        if res == 0:
            self._connected = True
            logger.info(f"已连接 LJ-X8000 (设备ID={self._device_id})")
        else:
            logger.error(f"连接失败: 返回码 0x{res:08X}")
        return res

    def close_connection(self) -> int:
        """Close Ethernet connection."""
        res = LJXAwrap.LJX8IF_CommunicationClose(self._device_id)
        self._connected = False
        logger.info("连接已关闭")
        return res

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Measurement control
    # ------------------------------------------------------------------

    def start_measurement(self) -> int:
        """Start measurement (continuous triggering)."""
        res = LJXAwrap.LJX8IF_StartMeasure(self._device_id)
        if res == 0:
            logger.info("测量已开始")
        else:
            logger.error(f"启动测量失败: 0x{res:08X}")
        return res

    def stop_measurement(self) -> int:
        """Stop measurement."""
        res = LJXAwrap.LJX8IF_StopMeasure(self._device_id)
        if res == 0:
            logger.info("测量已停止")
        return res

    def clear_memory(self) -> int:
        """Clear controller's internal profile memory."""
        res = LJXAwrap.LJX8IF_ClearMemory(self._device_id)
        if res == 0:
            logger.debug("控制器内存已清除")
        return res

    # ------------------------------------------------------------------
    # Profile acquisition
    # ------------------------------------------------------------------

    def get_profile(self, req, rsp, profinfo, profdata, data_size: int) -> int:
        """Get the latest profile from the controller.

        Args:
            req: LJX8IF_GET_PROFILE_REQUEST
            rsp: LJX8IF_GET_PROFILE_RESPONSE (output)
            profinfo: LJX8IF_PROFILE_INFO (output)
            profdata: ctypes array for profile data (output)
            data_size: Size of profdata buffer in bytes

        Returns:
            LJXAwrap return code (0 = success).
        """
        return LJXAwrap.LJX8IF_GetProfile(
            self._device_id, req, rsp, profinfo, profdata, data_size
        )

    @staticmethod
    def create_get_profile_request():
        """Create a default GetProfile request for latest single profile."""
        req = LJXAwrap.LJX8IF_GET_PROFILE_REQUEST()
        req.byTargetBank = 0x0       # Active bank
        req.byPositionMode = 0x0     # From current position
        req.dwGetProfileNo = 0x0     # N/A for current position mode
        req.byGetProfileCount = 1    # Single profile
        req.byErase = 0              # Do not erase
        return req

    @staticmethod
    def calculate_profile_buffer_size(xpoint_num: int, with_luminance: int,
                                      profile_count: int = 1) -> int:
        """Calculate the required buffer size for GetProfile data."""
        data_size = ctypes.sizeof(LJXAwrap.LJX8IF_PROFILE_HEADER)
        data_size += ctypes.sizeof(LJXAwrap.LJX8IF_PROFILE_FOOTER)
        data_size += ctypes.sizeof(ctypes.c_int) * xpoint_num * (1 + with_luminance)
        data_size *= profile_count
        return data_size

    def get_device_info(self) -> dict:
        """Retrieve device identification info."""
        info = {}
        try:
            headmodel = ctypes.create_string_buffer(32)
            res = LJXAwrap.LJX8IF_GetHeadModel(self._device_id, headmodel)
            if res == 0:
                info["head_model"] = headmodel.value.decode("utf-8", errors="replace")
            else:
                info["head_model"] = "N/A"

            ctrl_serial = ctypes.create_string_buffer(16)
            head_serial = ctypes.create_string_buffer(16)
            res = LJXAwrap.LJX8IF_GetSerialNumber(
                self._device_id, ctrl_serial, head_serial
            )
            if res == 0:
                info["controller_serial"] = ctrl_serial.value.decode("utf-8", errors="replace")
                info["head_serial"] = head_serial.value.decode("utf-8", errors="replace")
        except Exception as e:
            logger.warning(f"无法读取设备信息: {e}")
        return info
