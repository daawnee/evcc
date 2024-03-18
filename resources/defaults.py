from models.calculate.input import (
    VehicleType,
    FuelInfo,
    FuelPrice,
    Milage,
    Amortization,
)

# https://holtankoljak.hu/
fuel = {
    VehicleType.petrol: FuelInfo(
        average=FuelPrice(price=618.8, inflation=5.0),
        highway=FuelPrice(price=708.9, inflation=5.0),
    ),
    VehicleType.diesel: FuelInfo(
        average=FuelPrice(price=642.1, inflation=5.0),
        highway=FuelPrice(price=722.9, inflation=5.0),
    ),
    VehicleType.bev: FuelInfo(
        average=FuelPrice(price=72.0, inflation=5.0),
        highway=FuelPrice(price=225.0, inflation=5.0),
    ),
}


# https://villanyautosok.hu/2021/04/18/ennyi-uzemanyagot-fustolnek-el-a-magyar-autosok-minden-evben/
milage = {
    VehicleType.petrol: Milage(commute=8000, highway=2000),
    VehicleType.diesel: Milage(commute=24000, highway=6000),
    VehicleType.bev: Milage(commute=13600, highway=3400),
}

# https://totalcar.hu/magazin/hirek/2023/05/24/hasznalt-elektromos-autok-vizsgalat-attekinthetobb-piac/
amortization = {
    VehicleType.petrol: [
        Amortization(year=3, value=66),
        Amortization(year=5, value=46),
    ],
    VehicleType.diesel: [
        Amortization(year=3, value=66),
        Amortization(year=5, value=46),
    ],
    VehicleType.bev: [
        Amortization(year=3, value=63),
        Amortization(year=5, value=37),
    ],
}
