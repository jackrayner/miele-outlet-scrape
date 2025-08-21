from pypdf import PdfReader

import re
import requests
import locale
from tabulate import tabulate
from io import BytesIO

locale.setlocale(locale.LC_ALL, 'en_GB.UTF-8')

response = requests.get("https://application.miele.co.uk/resources/pdf/MieleOutletPricelist.pdf")
response.raise_for_status()
pdf_file = BytesIO(response.content)

pattern = r"""
^(?P<id>\d+)\s+
(?P<descriptipn>.+?)\s+
(?P<grade>Outlet\ [A-Z0-9]+\ Stock)\s+
£(?P<rrp>[\d,]+\.\d{2})\s+
£(?P<price>[\d,]+\.\d{2})
(?:\s+£(?P<discount_price_2>[\d,]+\.\d{2}))? 
$
"""

filter_pattern = r".*(Heat-pump).*"

reader = PdfReader(pdf_file)
number_of_pages = len(reader.pages)
page = reader.pages[1]
text = page.extract_text()

matches = []

for page in reader.pages:
    text = page.extract_text()
    for line in text.splitlines():
        match = re.match(pattern, line, re.X)
        if match:
            match2 = re.match(filter_pattern, line)
            if match2:
                matches.append(list(match.groups()))

# Post processing
for idx, match in enumerate(matches):
    # Process the description to remove unwanted parts
    match[1] = re.split(r"\b(GB|EU1)\b", match[1])[0].strip()
    # Reformat the grade column
    match[2] = match[2].split()[1]
    # Convert prices to float and format them
    match[3] = float(match[3].replace(",", ""))
    match[4] = float(match[4].replace(",", ""))
    # If a discounted price exists, convert it to float
    if match[5]:
        match[5] = float(match[5].replace(",", ""))
    else:
        match[5] = 0

    # Calculate the discount rate
    if match[5] == 0:
        match.append(round((match[3] - match[4]) / match[3] * 100, 2))
    else:
        match.append(round((match[3] - match[5]) / match[3] * 100, 2))
        
    match[3] = locale.currency(match[3], grouping=True)
    match[4] = locale.currency(match[4], grouping=True)
    match[5] = locale.currency(match[5], grouping=True)
    match[6] = str(match[6]) + "%"

    link = "https://www.miele.co.uk/product/" + match[0]
    match.append(link)
    response_code = requests.get(link).status_code
    if response_code == 404:
        match.append("Inactive")
    else:
        match.append("Active")
    matches[idx] = match
            
print(tabulate(matches, headers=["ID", "Description", "Grade", "RRP", "Price", "Discounted Price", "Discount Rate", "Link", "Status"], tablefmt="grid"))