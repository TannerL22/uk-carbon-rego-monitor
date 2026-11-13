"""Offline unit tests for carbon-market fetch parsing and monthly spread logic."""

import unittest
from io import BytesIO

import pandas as pd
from openpyxl import Workbook

from tests.support import IsolatedPipelineTestCase  # noqa: F401  (adds src/ to sys.path)

import carbon_signals
import fetch_ecb_fx as ecb
import fetch_eex_eua_auctions as eex
import fetch_fmd as fmd
import fetch_tradingeconomics_reference as trading_economics
import fetch_uk_ets_ccm as ccm


EEX_HEADER = [
    None, "Date", "Time", "Auction Name", "Contract", "Status", "Auction Price €/tCO2",
    "Minimum Bid €/tCO2", "Auction Volume tCO2", "Cover Ratio",
]


def eex_workbook(sheets: dict[str, list[list[object]]]) -> bytes:
    workbook = Workbook()
    workbook.remove(workbook.active)
    for name, rows in sheets.items():
        sheet = workbook.create_sheet(name)
        sheet.append([None, None, None, "Public"])
        sheet.append(EEX_HEADER)
        for row in rows:
            sheet.append(row)
    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


def eex_row(day: str, price: float, volume: float, status: str = "successful", cover: float = 1.5) -> list[object]:
    return [None, pd.Timestamp(day).to_pydatetime(), None, "Auction", "T3PA", status, price, 60.0, volume, cover]


class EexWorkbookTests(unittest.TestCase):
    def test_reads_renamed_eu_ets1_sheet_and_ignores_ets2(self) -> None:
        payload = eex_workbook(
            {
                "EU ETS2": [eex_row("2026-11-12", 55.0, 1_000_000)],
                "EU ETS1": [
                    eex_row("2026-11-12", 90.0, 1_000_000),
                    eex_row("2026-11-13", 80.0, 3_000_000),
                    eex_row("2026-11-14", 70.0, 1_000_000, status="cancelled"),
                ],
            }
        )
        rows = eex.parse_workbook(payload, "https://example.test/2026.xlsx")
        self.assertEqual(["2026-11-12", "2026-11-13"], [row["auction_date"] for row in rows])
        self.assertNotIn(55.0, [row["clearing_price"] for row in rows])

    def test_reads_legacy_primary_market_auction_sheet(self) -> None:
        payload = eex_workbook({"Primary Market Auction": [eex_row("2025-01-07", 72.5, 2_000_000)]})
        rows = eex.parse_workbook(payload, "https://example.test/2025.xlsx")
        self.assertEqual(1, len(rows))
        self.assertEqual(72.5, rows[0]["clearing_price"])

    def test_workbook_without_auction_header_fails_clearly(self) -> None:
        workbook = Workbook()
        workbook.active.title = "Notes"
        workbook.active.append(["nothing here"])
        buffer = BytesIO()
        workbook.save(buffer)
        with self.assertRaises(eex.EexFetchError):
            eex.parse_workbook(buffer.getvalue(), "https://example.test/bad.xlsx")

    def test_candidate_sheets_prefer_known_names_and_drop_ets2(self) -> None:
        self.assertEqual(
            ["EU ETS1", "Other"],
            eex.candidate_sheet_names(["Other", "EU ETS2", "EU ETS1"]),
        )

    def test_daily_aggregation_is_volume_weighted(self) -> None:
        rows = [
            {"auction_date": "2026-11-13", "auction_volume": 1_000_000, "clearing_price": 90.0, "cover_ratio": 2.0, "country": "", "source_url": "u"},
            {"auction_date": "2026-11-13", "auction_volume": 3_000_000, "clearing_price": 80.0, "cover_ratio": 1.0, "country": "", "source_url": "u"},
        ]
        [aggregated] = eex.aggregate_daily(rows, "2026-11-13T12:00Z")
        self.assertEqual(82.5, aggregated["clearing_price"])
        self.assertEqual(1.25, aggregated["cover_ratio"])
        self.assertEqual(4_000_000, aggregated["auction_volume"])


class CcmTableTests(unittest.TestCase):
    HTML = """
    <p>Updated 12 October 2026</p>
    <table>
      <tr><th>Month</th><th>2-year reference period</th><th>Trigger price</th><th>3-month monitoring period</th>
          <th>Month 1 average price</th><th>Month 2 average price</th><th>Month 3 average price</th><th>CCM triggered? Yes or No</th></tr>
      <tr><td>Jan-26</td><td>ref</td><td>£120.00</td><td>Oct, Nov, Dec</td><td>£50.00</td><td>£51.00</td><td>£52.50</td><td>No</td></tr>
      <tr><td>Feb-26</td><td>ref</td><td>£121.00</td><td>Nov, Dec, Jan</td><td>£51.00</td><td>£52.50</td><td>TBD</td><td>TBD</td></tr>
    </table>
    """

    def test_previous_month_handles_year_boundary(self) -> None:
        self.assertEqual("2025-12", ccm.previous_month("2026-01"))
        self.assertEqual("2026-09", ccm.previous_month("2026-10"))

    def test_rows_carry_price_month_for_final_average(self) -> None:
        rows = ccm.parse_tables(self.HTML, "2026-10-13T00:00Z", ccm.parse_published_at(self.HTML))
        january, february = rows
        self.assertEqual(("2026-01", "2025-12", 52.5), (january["month"], january["price_month"], january["monthly_average_price"]))
        self.assertEqual("", february["monthly_average_price"])
        self.assertEqual("2026-10-12", january["published_at"])


class MonthlySpreadTests(unittest.TestCase):
    def ccm_frame(self, prices: dict[str, float]) -> pd.DataFrame:
        return pd.DataFrame(
            {"price_month": list(prices), "monthly_average_price": list(prices.values())}
        )

    def test_eua_monthly_average_is_volume_weighted(self) -> None:
        auctions = pd.DataFrame(
            {
                "market": ["EUA", "EUA", "EUA", "UKA"],
                "auction_date": pd.to_datetime(["2026-09-01", "2026-09-02", "2026-10-01", "2026-09-01"]),
                "clearing_price": [80.0, 90.0, 85.0, 1.0],
                "auction_volume": [3.0, 1.0, 2.0, 5.0],
            }
        )
        monthly = carbon_signals.monthly_eua_prices(auctions).set_index("price_month")
        self.assertAlmostEqual(82.5, monthly.loc["2026-09", "EUA"])
        self.assertEqual(2, monthly.loc["2026-09", "eua_auction_count"])

    def test_spread_uses_only_months_with_both_legs_and_prior_trailing_window(self) -> None:
        ccm_frame = self.ccm_frame({f"2026-0{m}": 60.0 + m for m in range(1, 7)})
        eua = pd.DataFrame({"price_month": [f"2026-0{m}" for m in range(2, 8)], "EUA": [80.0] * 6, "eua_auction_count": [10] * 6})
        spread = carbon_signals.build_monthly_spread(ccm_frame, eua, fallback_rate=0.9)
        self.assertEqual([f"2026-0{m}" for m in range(2, 7)], spread["price_month"].tolist())
        latest = spread.iloc[-1]
        self.assertAlmostEqual(66.0 - 72.0, latest["spread_gbp"])
        # Trailing average covers Feb-May only (months before June).
        self.assertAlmostEqual((-10 - 9 - 8 - 7) / 4, latest["trailing_average_spread_gbp"])

    def test_monthly_ecb_rates_are_used_with_static_fallback(self) -> None:
        ccm_frame = self.ccm_frame({"2026-09": 60.0, "2026-10": 64.0})
        eua = pd.DataFrame({"price_month": ["2026-09", "2026-10"], "EUA": [80.0, 80.0], "eua_auction_count": [10, 10]})
        rates = pd.Series({"2026-09": 0.85})
        spread = carbon_signals.build_monthly_spread(ccm_frame, eua, fallback_rate=0.9, fx_rates=rates).set_index("price_month")
        self.assertAlmostEqual(68.0, spread.loc["2026-09", "EUA_GBP"])
        self.assertEqual("ECB monthly average", spread.loc["2026-09", "fx_basis"])
        self.assertAlmostEqual(72.0, spread.loc["2026-10", "EUA_GBP"])
        self.assertEqual("static fallback", spread.loc["2026-10", "fx_basis"])

    def test_regime_wording_respects_spread_sign(self) -> None:
        self.assertEqual("UKA discount narrower than recent average", carbon_signals.classify_spread(1.5, -5.0))
        self.assertEqual("UKA discount wider than recent average", carbon_signals.classify_spread(-1.5, -5.0))
        self.assertEqual("UKA premium wider than recent average", carbon_signals.classify_spread(1.5, 5.0))
        self.assertEqual("UKA premium broadly stable", carbon_signals.classify_spread(0.2, 5.0))


class EcbRatesTests(unittest.TestCase):
    PAYLOAD = (
        "KEY,FREQ,CURRENCY,CURRENCY_DENOM,EXR_TYPE,EXR_SUFFIX,TIME_PERIOD,OBS_VALUE\n"
        "EXR.M.GBP.EUR.SP00.A,M,GBP,EUR,SP00,A,2026-10,0.8428213636\n"
        "EXR.M.GBP.EUR.SP00.A,M,GBP,EUR,SP00,A,2026-09,0.858125\n"
        "EXR.M.USD.EUR.SP00.A,M,USD,EUR,SP00,A,2026-10,1.09\n"
    )

    def test_parses_gbp_per_eur_monthly_rates_sorted(self) -> None:
        self.assertEqual([("2026-09", 0.858125), ("2026-10", 0.8428213636)], ecb.parse_rates(self.PAYLOAD))

    def test_rejects_implausible_rates(self) -> None:
        with self.assertRaises(ecb.EcbFetchError):
            ecb.parse_rates(self.PAYLOAD.replace("0.858125", "8.58125"))


class FmdTableTests(unittest.TestCase):
    HTML = """
    <p>The data are for the disclosure period 1 April 2025 to 31 March 2026.</p><p>Updated 3 August 2026</p>
    <table><tr><th>Energy Source</th><th>%</th></tr>
      <tr><td>Coal</td><td>11.4</td></tr><tr><td>Natural Gas</td><td>65.3</td></tr><tr><td>Nuclear</td><td>7.1</td></tr>
      <tr><td>Renewables</td><td>10.8</td></tr><tr><td>Other Fuels</td><td>5.4</td></tr></table>
    <table><tr><th>Energy Source</th><th>g/kWh (2025)</th><th>g/kWh (2024)</th></tr>
      <tr><td>Coal (see note 3)</td><td>-</td><td>921</td></tr><tr><td>Natural Gas</td><td>365</td><td></td></tr>
      <tr><td>Nuclear</td><td>0</td><td></td></tr><tr><td>Renewables</td><td>0</td><td></td></tr>
      <tr><td>Other</td><td>969</td><td></td></tr><tr><td>Overall average</td><td>147</td><td></td></tr></table>
    <p>High-level radioactive waste</p><p>0.006 g/kWh</p>
    <table><tr><th>Energy Source</th><th>%</th></tr>
      <tr><td>Coal</td><td>4.7</td></tr><tr><td>Natural Gas</td><td>31.4</td></tr><tr><td>Nuclear</td><td>13.7</td></tr>
      <tr><td>Renewables</td><td>48.0</td></tr><tr><td>Other</td><td>2.2</td></tr></table>
    """

    def test_parses_period_mixes_and_factors(self) -> None:
        table = fmd.parse_fmd(self.HTML)
        self.assertEqual(("2025-26", "2025-04-01", "2026-03-31"), (table["disclosure_period"], table["period_start"], table["period_end"]))
        self.assertEqual(65.3, table["residual"]["Natural Gas"])
        self.assertEqual(48.0, table["uk_mix"]["Renewables"])
        self.assertEqual(5.4, table["residual"]["Other"])
        self.assertEqual(147.0, table["overall_average"])
        self.assertEqual(0.006, table["radioactive_waste"])
        self.assertEqual("2026-08-03", table["published_at"])

    def test_uses_prior_year_factor_when_latest_is_dash(self) -> None:
        self.assertEqual(921.0, fmd.parse_fmd(self.HTML)["factors"]["Coal"])

    def test_rejects_mix_that_does_not_sum_to_100(self) -> None:
        with self.assertRaises(fmd.FmdFetchError):
            fmd.parse_fmd(self.HTML.replace("<td>65.3</td>", "<td>95.3</td>"))


class SourceIdTests(unittest.TestCase):
    def test_trading_economics_does_not_reuse_customer_contract_source_id(self) -> None:
        self.assertNotEqual("SRC-008", trading_economics.SOURCE_ID)

    def test_fetchers_use_distinct_source_ids(self) -> None:
        ids = [trading_economics.SOURCE_ID, ecb.SOURCE_ID, fmd.SOURCE_ID, eex.SOURCE_ID, ccm.SOURCE_ID]
        self.assertEqual(len(ids), len(set(ids)))


if __name__ == "__main__":
    unittest.main()
