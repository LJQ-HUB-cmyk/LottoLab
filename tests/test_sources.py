from lottolab.sources import money, parse_500, parse_cwl, parse_sporttery


def test_official_ssq_parser_keeps_prizes_and_zero():
    records = parse_cwl(
        {
            "state": 0,
            "result": [
                {
                    "code": "2026105",
                    "date": "2026-09-10(四)",
                    "red": "02,04,13,14,15,30",
                    "blue": "08",
                    "sales": 0,
                    "poolmoney": "1,234",
                    "prizegrades": [{"type": 6, "typemoney": "5"}],
                }
            ],
        }
    )
    assert records[0]["main_numbers"] == [2, 4, 13, 14, 15, 30]
    assert records[0]["sales"] == "0"
    assert records[0]["prizes"] == {"6": "5"}
    assert money(None) is None


def test_secondary_source_date_and_number_mapping():
    cells = ["26105", "02", "04", "13", "14", "15", "30", "08", "", "1", "2026-09-10"]
    html = (
        '<table><tbody id="tdata"><tr>'
        + "".join(f"<td>{value}</td>" for value in cells)
        + "</tr></tbody></table>"
    )
    row = parse_500(html, "ssq")[0]
    assert row["issue"] == "2026105"
    assert row["special_numbers"] == [8]


def test_dlt_official_parser():
    payload = {
        "value": {
            "list": [
                {
                    "lotteryDrawNum": "26104",
                    "lotteryDrawTime": "2026-09-09 21:00:00",
                    "lotteryDrawResult": "01 08 15 22 35 02 12",
                    "totalSaleAmount": "1000",
                }
            ]
        }
    }
    row = parse_sporttery(payload)[0]
    assert row["issue"] == "2026104"
    assert row["main_numbers"] == [1, 8, 15, 22, 35]
    assert row["special_numbers"] == [2, 12]
