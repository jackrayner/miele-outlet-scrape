# Miele Outlet UK PDF Price Scraper

[![Lint](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/lint.yml/badge.svg)](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/lint.yml)
[![Test](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/test.yml/badge.svg)](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This script extracts pricing information from PDF files published by the Miele
Outlet UK store.

## Features

- Parses the Miele Outlet pricelist to retrieve product descriptions, grades, and prices
- Filters by product name/description, grade (B1/B2/B3), and maximum price
- Optionally checks whether each product's page is still live
- Outputs data in a table or JSON format

## Requirements

- Python 3.x
- `pypdf`, `requests`, `tabulate`

## Usage

```sh
pipx run miele_outlet_scrape.py
```

Or, with [uv](https://docs.astral.sh/uv/):

```sh
uv run miele_outlet_scrape.py
```

### Options

| Flag             | Description                                                     |
|------------------|-----------------------------------------------------------------|
| `--filter TEXT`  | Match product name/description (case-insensitive, default: all) |
| `--grade`        | Restrict to grade `B1`, `B2`, or `B3` (default: all grades)     |
| `--max-price`    | Only include units at or under this price (post-discount too)   |
| `--check-status` | Check whether each product's page is still live                 |
| `--json`         | Output JSON instead of a table                                  |

## Output

```sh
python3 miele_outlet_scrape.py --filter "dishwash" --grade B1 --check-status
```

```text
+---------------------------------------+---------+-----------+---------+--------------------+-------------------------------------+-----------------+------------+----------+------------------------------------------+----------+
| description                           | grade   | rrp       | price   | discounted_price   | product_name                        | discount_rate   | updated    |       id | url                                      | status   |
+=======================================+=========+===========+=========+====================+======================================+=================+============+==========+==========================================+==========+
| G 5450 SCVi Active Plus stainless ste | B1      | £1,149.00 | £919.20 | £749.00            | Fully integrated dishwashers 60 cm  | 34.81%          | 13/07/2026 | 12656400 | https://www.miele.co.uk/product/12656400 | Error    |
+---------------------------------------+---------+-----------+---------+--------------------+-------------------------------------+-----------------+------------+----------+------------------------------------------+----------+
```

`status` is `Error` here because `--check-status` is currently blocked by Miele's
bot-detection on `www.miele.co.uk` (see Known limitations below) - the pricelist
data itself is unaffected.

## Known limitations

- `--check-status` makes a plain `requests.get()` to each product page.
  `www.miele.co.uk` runs bot-detection that returns `403` to it regardless of
  whether the product is genuinely still listed (confirmed: the same URLs return
  their real status, `200`/`404`/a redirect, to `curl`). Until that's worked
  around, `--check-status` mostly reports `Error` rather than a meaningful
  `Active`/`Inactive`.

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setting up a dev environment, running
tests, and linting.

## License

MIT - see [LICENSE](LICENSE).
