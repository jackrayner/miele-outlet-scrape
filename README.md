# Miele Outlet UK PDF Price Scraper

[![Lint](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/lint.yml/badge.svg)](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/lint.yml)
[![Test](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/test.yml/badge.svg)](https://github.com/jackrayner/miele-outlet-scrape/actions/workflows/test.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

This script extracts pricing information from PDF files published by the Miele
Outlet UK store.

## Features

- Parses the Miele Outlet pricelist to retrieve product names and prices
- Outputs data in a table or json format

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

## Output

```text
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
|       ID | Description                   | Grade   | RRP       | Price     | Discounted Price   | Discount Rate   | Link                                     | Status   |
+==========+===============================+=========+===========+===========+====================+=================+==========================================+==========+
| 11871890 | TCR780WP Eco &Steam &9kg      | B2      | £2,349.00 | £1,644.30 | £0.00              | 30.0%           | https://www.miele.co.uk/product/11871890 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 11871740 | TED265WP 8kg                  | B2      | £1,049.00 | £734.30   | £0.00              | 30.0%           | https://www.miele.co.uk/product/11871740 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 11871820 | TEF765WP EcoSpeed &8kg        | B2      | £1,249.00 | £874.30   | £0.00              | 30.0%           | https://www.miele.co.uk/product/11871820 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 11871830 | TEH785WP EcoSpeed &9kg        | B2      | £1,199.00 | £839.30   | £0.00              | 30.0%           | https://www.miele.co.uk/product/11871830 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 12719130 | TSA523WP 8kg Active           | B2      | £899.00   | £629.30   | £0.00              | 30.0%           | https://www.miele.co.uk/product/12719130 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 12719160 | TEC645WP EcoSpeed &8kg        | B3      | £949.00   | £569.40   | £0.00              | 40.0%           | https://www.miele.co.uk/product/12719160 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
| 11871900 | TEL785WP EcoSpeed &Steam &9kg | B3      | £1,649.00 | £989.40   | £0.00              | 40.0%           | https://www.miele.co.uk/product/11871900 | Active   |
+----------+-------------------------------+---------+-----------+-----------+--------------------+-----------------+------------------------------------------+----------+
```

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for setting up a dev environment, running
tests, and linting.

## License

MIT - see [LICENSE](LICENSE).
