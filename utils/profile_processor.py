"""Extract a single scalar value from a 3200-point LJ-X8000 profile."""

import ctypes
import logging

logger = logging.getLogger(__name__)

# Sentinel value for invalid/unmeasurable data points from LJ-X8000
INVALID_Z_SENTINEL = -2147483645


def extract_max_z(profdata, data_count: int, header_size_bytes: int,
                  roi_start: int, roi_end: int) -> float | None:
    """Extract the maximum Z height value within the ROI.

    Args:
        profdata: ctypes array of c_int from LJX8IF_GetProfile.
        data_count: Number of X points in the profile (typically 3200).
        header_size_bytes: Byte size of LJX8IF_PROFILE_HEADER (offset to heights).
        roi_start: Start X index of the region of interest.
        roi_end: End X index of the region of interest (inclusive).

    Returns:
        max_z_mm float, or None if all values invalid.
    """
    int_size = ctypes.sizeof(ctypes.c_int)
    offset = header_size_bytes // int_size

    roi_start = max(0, roi_start)
    roi_end = min(data_count - 1, roi_end)

    if roi_start > roi_end:
        logger.warning(f"无效的ROI: 起始={roi_start} > 结束={roi_end}")
        return None

    max_z = float('-inf')

    for i in range(roi_start, roi_end + 1):
        raw_z = profdata[offset + i]
        if raw_z <= INVALID_Z_SENTINEL:
            continue

        # Convert from 0.01 µm to mm
        z_mm = raw_z / 100.0 / 1000.0

        if z_mm > max_z:
            max_z = z_mm

    if max_z == float('-inf'):
        logger.debug("ROI内所有Z值均无效")
        return None

    return round(max_z, 6)


def extract_avg_z(profdata, data_count: int, header_size_bytes: int,
                  roi_start: int, roi_end: int) -> float | None:
    """Extract the average Z height value within the ROI.

    Returns:
        avg_z_mm float, or None if all values invalid.
    """
    int_size = ctypes.sizeof(ctypes.c_int)
    offset = header_size_bytes // int_size

    roi_start = max(0, roi_start)
    roi_end = min(data_count - 1, roi_end)

    if roi_start > roi_end:
        return None

    total = 0.0
    count = 0
    for i in range(roi_start, roi_end + 1):
        raw_z = profdata[offset + i]
        if raw_z <= INVALID_Z_SENTINEL:
            continue
        z_mm = raw_z / 100.0 / 1000.0
        total += z_mm
        count += 1

    if count == 0:
        return None

    avg_z = total / count
    return round(avg_z, 6)
