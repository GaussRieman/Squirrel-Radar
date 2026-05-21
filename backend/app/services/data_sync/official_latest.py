from app.services.data_sync.models import RawIndicatorRow


def load_official_latest_rows() -> list[RawIndicatorRow]:
    """Latest verified public macro snapshot available as of 2026-05-20.

    Most monthly China macro indicators publish with a one-month lag. The latest
    complete dashboard month is therefore 2026-04; quarterly household income and
    industrial profit keep their latest official quarter/month-period readings.
    """

    source_ref = "official-public-snapshot:2026-04"
    return [
        RawIndicatorRow("m2_yoy", "2026-04", 8.6, 8.6, -0.23, 8.7, 80, "strong", source_ref),
        RawIndicatorRow("tsf_stock_yoy", "2026-04", 7.8, 7.8, None, 7.9, 30, "weak", source_ref),
        RawIndicatorRow("new_rmb_loan", "2026-04", -100, -103.57, -100.33, 12933, 5, "weak", source_ref),
        RawIndicatorRow("household_mid_long_loan", "2026-04", -3408, -176.8, None, 466, 10, "weak", source_ref),
        RawIndicatorRow("enterprise_mid_long_loan", "2026-04", -4100, -183.0, None, 16700, 10, "weak", source_ref),
        RawIndicatorRow("core_cpi", "2026-04", 1.2, 1.2, None, 1.17, 75, "strong", source_ref),
        RawIndicatorRow("ppi", "2026-04", 2.8, 2.8, 1.7, 0.8, 100, "strong", source_ref),
        RawIndicatorRow("secondhand_home_price_mom_70c", "2026-04", -0.19, None, -0.19, -0.21, 70, "neutral", source_ref),
        RawIndicatorRow("commodity_house_sales_area", "2026-04", -10.2, -10.2, None, -10.5, 20, "weak", source_ref),
        RawIndicatorRow("wage_income", "2026-04", 4.9, 4.9, None, 4.9, 45, "neutral", source_ref),
        RawIndicatorRow("private_investment", "2026-04", -5.2, -5.2, None, -4.2, 10, "weak", source_ref),
        RawIndicatorRow("industrial_profit", "2026-04", 15.5, 15.5, None, 10.4, 85, "strong", source_ref),
    ]
