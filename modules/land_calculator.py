def convert_land_to_sqwah(rai: float, ngan: float, wah: float) -> float:
    return rai * 400 + ngan * 100 + wah


def sqwah_to_sqm(sqwah: float) -> float:
    return sqwah * 4
