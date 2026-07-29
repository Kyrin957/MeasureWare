"""Application settings backed by the DeviceConfig database row."""

import logging

from models.database import Session
from models.settings_model import DeviceConfig

logger = logging.getLogger(__name__)


class AppSettings:
    """Singleton accessor for DeviceConfig from the database."""

    def __init__(self):
        self._session = Session()

    def close(self):
        self._session.close()

    def _get_config(self) -> DeviceConfig:
        cfg = self._session.query(DeviceConfig).first()
        if cfg is None:
            cfg = DeviceConfig()
            self._session.add(cfg)
            self._session.commit()
            logger.info("已创建默认设备配置")
        return cfg

    # ---- IP Address ----

    @property
    def ip_octets(self) -> tuple:
        cfg = self._get_config()
        return cfg.ip_octets

    @ip_octets.setter
    def ip_octets(self, value: tuple):
        cfg = self._get_config()
        cfg.set_ip(value)
        self._session.commit()
        logger.info(f"IP地址已设置为 {cfg.ip_address}")

    @property
    def ip_address(self) -> str:
        return self._get_config().ip_address

    # ---- Ports ----

    @property
    def command_port(self) -> int:
        return self._get_config().command_port

    @command_port.setter
    def command_port(self, value: int):
        cfg = self._get_config()
        cfg.command_port = value
        self._session.commit()

    # ---- Extraction ----

    @property
    def extraction_mode(self) -> str:
        return self._get_config().extraction_mode

    @extraction_mode.setter
    def extraction_mode(self, value: str):
        cfg = self._get_config()
        cfg.extraction_mode = value
        self._session.commit()

    @property
    def extraction_roi_start(self) -> int:
        return self._get_config().extraction_roi_start

    @extraction_roi_start.setter
    def extraction_roi_start(self, value: int):
        cfg = self._get_config()
        cfg.extraction_roi_start = value
        self._session.commit()

    @property
    def extraction_roi_end(self) -> int:
        return self._get_config().extraction_roi_end

    @extraction_roi_end.setter
    def extraction_roi_end(self, value: int):
        cfg = self._get_config()
        cfg.extraction_roi_end = value
        self._session.commit()

    # ---- Build connection parameters ----

    def get_ethernet_config(self):
        """Return (ip_address, port) tuple for TCP no-protocol connection."""
        octets = self.ip_octets
        ip_address = f"{octets[0]}.{octets[1]}.{octets[2]}.{octets[3]}"
        return (ip_address, self.command_port)

    def get_extraction_config(self) -> dict:
        cfg = self._get_config()
        return {
            "mode": cfg.extraction_mode,
            "roi_start": cfg.extraction_roi_start,
            "roi_end": cfg.extraction_roi_end,
        }

    def save_all(self, ip_octets, command_port,
                 extraction_mode, roi_start, roi_end):
        cfg = self._get_config()
        cfg.set_ip(ip_octets)
        cfg.command_port = command_port
        cfg.extraction_mode = extraction_mode
        cfg.extraction_roi_start = roi_start
        cfg.extraction_roi_end = roi_end
        self._session.commit()
        logger.info("设备配置已保存")
