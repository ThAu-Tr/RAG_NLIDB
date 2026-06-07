"""
classDiagram
direction LR
class dim_area_h{
 *INTEGER area_id
   TEXT city
   REAL latitude
   REAL longitude
   TEXT state
   TEXT tso_region
   INTEGER zipcode
}
class dim_asset{
 *INTEGER asset_id
   INTEGER area_id
   TEXT asset_name
   INTEGER commissioning_date_id
   INTEGER company_id
   INTEGER energy_source_id
   REAL generation_capacity_mw
}
class dim_company_h{
 *INTEGER company_id
   TEXT company_level
   TEXT company_name
   TEXT parent_company
}
class dim_energy_source_h{
 *INTEGER energy_source_id
   TEXT energy_source_group
   TEXT energy_source_name
}
class dim_date{
 *INTEGER date_id
   TEXT date
   INTEGER day_of_year
   INTEGER is_holiday
   INTEGER is_weekend
   INTEGER is_workday
   INTEGER month
   TEXT month_name
   TEXT quarter
   TEXT season
   TEXT week_iso
   TEXT weekday
   INTEGER weekday_num
   INTEGER year
   INTEGER year_iso
}
class fact_generation_daily{
 INTEGER asset_id
   INTEGER date_id
   REAL generation_mwh
}
class fact_weather_daily{
 INTEGER area_id
   REAL avg_temperature_c
   REAL avg_wind_power_density_w_per_m2
   INTEGER date_id
   REAL total_solar_irradiation_kwh_per_m2
}
dim_energy_source_h "0..1" -- "0..n" dim_asset
dim_date "0..1" -- "0..n" dim_asset
dim_area_h "0..1" -- "0..n" dim_asset
dim_company_h "0..1" -- "0..n" dim_asset
dim_asset "0..1" -- "0..n" fact_generation_daily
dim_date "0..1" -- "0..n" fact_generation_daily
dim_area_h "0..1" -- "0..n" fact_weather_daily
dim_date "0..1" -- "0..n" fact_weather_daily
"""