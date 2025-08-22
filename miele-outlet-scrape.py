#!/usr/bin/env python3

# /// script
# dependencies = [
#   "pypdf",
#   "requests",
#   "tabulate",
# ]
# ///

from pypdf import PdfReader

import re
import requests
import locale
from tabulate import tabulate
from io import BytesIO
import argparse
import json

locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

def load_pdf():
    """
    Loads the Miele Outlet Pricelist PDF from the specified URL.
    Returns the content of the PDF as a BytesIO object.
    """
    response = requests.get("https://application.miele.co.uk/resources/pdf/MieleOutletPricelist.pdf")
    response.raise_for_status()
    return PdfReader(BytesIO(response.content))

def check_product_status(url):
    """
    Checks the status of a product URL.
    Returns 'Active' if the product is available, 'Inactive' if it returns a 404 status code.
    """
    try:
        response = requests.get(url)
        if response.status_code == 404:
            return "Inactive"
        else:
            return "Active"
    except requests.RequestException:
        return "Error"

def parse_pdf(check_status):
    """
    Parses the Miele Outlet Pricelist PDF and extracts product information.
    Returns a list of matches containing product details.
    """

    pattern = r"""
    ^(?P<id>\d+)\s+
    (?P<description>.+?)\s+
    (?P<grade>Outlet\ [A-Z0-9]+\ Stock)\s+
    £(?P<rrp>[\d,]+\.\d{2})\s+
    £(?P<price>[\d,]+\.\d{2})
    (?:\s+£(?P<discounted_price>[\d,]+\.\d{2}))?
    $
    """

    reader = load_pdf()

    matches = []

    for page in reader.pages:
        text = page.extract_text()
        for line in text.splitlines():
            match = re.match(pattern, line, re.X)
            if match:
                match_dict = match.groupdict()
                # Reformat the description to remove unwanted parts
                split_description = [item.strip() for item in re.split(r"(GB|EU1)\b", match_dict['description'])]

                # Set the description to the first part of the split
                match_dict['description'] = split_description[0]

                # Try and set the product name from the GB/EU1 split, e.g. if
                # the description is "Duoflex HX1 Terra Red GB Duoflex", we want
                # to set the product name to "Duoflex"
                # If the split doesn't yield enough parts, we just set it to an
                # empty string
                match_dict['product_name'] = split_description[2] if len(split_description) > 1 else ""

                # Reformat the grade column
                match_dict['grade'] = match_dict['grade'].split()[1]
                # Convert prices to float and format them
                match_dict['rrp'] = float(match_dict['rrp'].replace(",", ""))
                match_dict['price'] = float(match_dict['price'].replace(",", ""))
                match_dict['url'] = "https://www.miele.co.uk/product/" + match_dict['id']
                # If a discounted price exists, convert it to float
                if match_dict['discounted_price']:
                    match_dict['discounted_price'] = float(match_dict['discounted_price'].replace(",", ""))
                    match_dict['discount_rate'] = round((match_dict['rrp'] - match_dict['discounted_price']) / match_dict['rrp'] * 100, 2)
                else:
                    match_dict['discounted_price'] = 0
                    match_dict['discount_rate'] = round((match_dict['rrp'] - match_dict['price']) / match_dict['rrp'] * 100, 2)

                if check_status:
                    match_dict['status'] = check_product_status(match_dict['url'])
                else:
                    match_dict['status'] = "Unknown"

                matches.append(match_dict)

    return matches

def filter_products(products, filter, grade, max_price):
    """
    Filters the list of products based on the provided filter string.
    Returns a list of filtered products.
    """

    filter_pattern = fr".*({filter}).*"
    filtered_products = []

    for product in products:
        if product['grade'] == grade or grade == "":
            if re.match(filter_pattern, product['product_name'], re.IGNORECASE) or re.match(filter_pattern, product['description'], re.IGNORECASE):
                if max_price is not None and product['price'] <= max_price:
                    filtered_products.append(product)
                elif max_price is not None and product['discounted_price'] != 0 and product['discounted_price'] <= max_price:
                    filtered_products.append(product)
                elif max_price is None:
                    filtered_products.append(product)

    return filtered_products

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrape Miele Outlet Pricelist PDF for heat pump products.")
    parser.add_argument("--filter", type=str, default="", help="Filter string for product search (default: empty string).")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format.")
    parser.add_argument("--check-status", action="store_true", help="Check the status of each product link.")
    parser.add_argument(
        "--grade",
        type=str,
        choices=["B1", "B2", "B3"],
        default="",
        help="Filter by product grade (must be one of: B1, B2, B3)."
    )
    parser.add_argument("--max-price", type=float, default=None, help="Maximum price to filter products (default: None).")
    args = parser.parse_args()

    products = parse_pdf(args.check_status)

    matches = filter_products(products, args.filter, args.grade, args.max_price)

    if args.json:
        import json
        print(json.dumps(matches))
    else:
        print(tabulate(matches, headers="keys", tablefmt="grid"))