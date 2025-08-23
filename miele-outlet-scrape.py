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
from datetime import datetime

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

def parse_pdf():
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

    update_pattern = r"Miele\ Outlet\ (?P<grade>[A-Z0-9]+)\ Grade\ Pricelist\ -\ Updated\ (?P<date>\d{2}\/\d{2}\/\d{4})"

    reader = load_pdf()

    matches = {}
    update_info = {}

    for page in reader.pages:
        text = page.extract_text()
        for line in text.splitlines():
            match = re.match(pattern, line, re.X)
            update_match = re.match(update_pattern, line, re.X)
            if update_match:
                update_match_info = update_match.groupdict()
                update_info[update_match_info['grade']] = update_match_info['date']
            elif match:
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

                product_id = match_dict['id']

                if product_id not in matches:
                    matches[product_id] = {
                        "url": match_dict['url'],
                        "status": "Unknown",
                        "available_units": []
                    }

                match_dict.pop('id')
                match_dict.pop('url')
                
                matches[product_id]['available_units'].append(match_dict)

    return matches, update_info

def filter_products(products, update_info, filter, grade, max_price, check_status):
    """
    Filters the list of products based on the provided filter string.
    Returns a list of filtered products.
    """

    filter_pattern = fr".*({filter}).*"
    filtered_products = {}

    for id, details in products.items():
        available_units = details['available_units']
        details.pop('available_units')
        details['available_units'] = []
        filtered_products[id] = details
        for available_unit in available_units:
            available_unit['updated'] = update_info.get(available_unit['grade'])
            if available_unit['grade'] == grade or grade == "":
                if re.match(filter_pattern, available_unit['product_name'], re.IGNORECASE) or re.match(filter_pattern, available_unit['description'], re.IGNORECASE):
                    if max_price is not None and available_unit['price'] <= max_price:
                        filtered_products[id]['available_units'].append(available_unit)
                    elif max_price is not None and available_unit['discounted_price'] != 0 and available_unit['discounted_price'] <= max_price:
                        filtered_products[id]['available_units'].append(available_unit)
                    elif max_price is None:
                        filtered_products[id]['available_units'].append(available_unit)
        if len(filtered_products[id]['available_units']) == 0:
            filtered_products.pop(id)
        elif check_status:
            filtered_products[id]['status'] = check_product_status(filtered_products[id]['url'])

    return filtered_products

if __name__ == "__main__":
    start_time = datetime.now()

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

    products, update_info = parse_pdf()

    matches = filter_products(products, update_info, args.filter, args.grade, args.max_price, args.check_status)

    results_dict = {
        "time": start_time.isoformat(),
        "products": matches
    }

    if args.json:
        print(json.dumps(results_dict))
    else:
        table_data = []
        for product_id, product_info in results_dict['products'].items():
            metadata = product_info.copy()
            metadata.pop('available_units')
            for available_unit in product_info['available_units']:
                newdict = available_unit | { 'id' : product_id } | metadata
                newdict['rrp'] = locale.currency(newdict['rrp'], grouping=True)
                newdict['price'] = locale.currency(newdict['price'], grouping=True)
                newdict['discounted_price'] = locale.currency(newdict['discounted_price'], grouping=True) if newdict['discounted_price'] != 0 else "N/A"
                newdict['discount_rate'] = f"{newdict['discount_rate']}%"
                table_data.append(newdict)

        print(tabulate(table_data, headers="keys", tablefmt="grid"))