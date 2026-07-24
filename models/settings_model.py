"""DeviceConfig ORM model — singleton row holding communication & extraction settings."""

from sqlalchemy import Column, Integer, String
from models.database import Base


class DeviceConfig(Base):
    """Singleton configuration row for device communication and data extraction."""

    __tablename__ = "device_config"

    id = Column(Integer, primary_key=True, default=1)

    # IP address octets
    ip_octet1 = Column(Integer, default=192)
    ip_octet2 = Column(Integer, default=168)
    ip_octet3 = Column(Integer, default=0)
    ip_octet4 = Column(Integer, default=1)

    # Port numbers
    command_port = Column(Integer, default=24691)
    high_speed_port = Column(Integer, default=24692)

    # Extraction settings
    extraction_mode = Column(String(32), default="max")  # "max", "avg", "index"
    extraction_roi_start = Column(Integer, default=0)     # X index 0-3199
    extraction_roi_end = Column(Integer, default=3199)    # X index 0-3199

    @property
    def ip_address(self) -> str:
        return f"{self.ip_octet1}.{self.ip_octet2}.{self.ip_octet3}.{self.ip_octet4}"

    @property
    def ip_octets(self) -> tuple:
        return (self.ip_octet1, self.ip_octet2, self.ip_octet3, self.ip_octet4)

    def set_ip(self, octets: tuple):
        self.ip_octet1, self.ip_octet2, self.ip_octet3, self.ip_octet4 = octets
