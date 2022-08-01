import json
import sys
import re
import requests
from time import strftime
from os.path import exists

OUTPUT_FILENAME = "data.json"

# Data will only be generated for the following categories:
URLS = [
    "https://www.willys.se/c/kott-chark-och-fagel?size=9999",
    "https://www.willys.se/c/mejeri-ost-och-agg?size=9999",
    "https://www.willys.se/c/skafferi?size=9999",
    "https://www.willys.se/c/brod-och-kakor?size=9999",
    "https://www.willys.se/c/fryst?size=9999",
    "https://www.willys.se/c/fisk-och-skaldjur?size=9999",
    "https://www.willys.se/c/vegetariskt?size=9999",
    "https://www.willys.se/c/glass-godis-och-snacks?size=9999",
    "https://www.willys.se/c/dryck?size=9999",
    "https://www.willys.se/c/fardigmat?size=9999",
]

# A helper function
def log(msg, indent=0):
    print(f"[{strftime('%X')}]: {'    ' * indent}{msg}")

# This parses the json data for each product, only keeping values
# of interest and doing type conversions
# Note that it only keeps items that have defined comparison prices
def parse_product_json(json_data):
    d = {}
    try:
        d["name"] = json_data["name"]
        d["comparePrice"] = float(re.search(r"[\d, ]+", "".join(json_data["comparePrice"].split()), re.IGNORECASE).group().replace(',', '.'))
        d["comparePriceUnit"] = json_data["comparePriceUnit"]
        d["displayVolume"] = json_data["displayVolume"]
        for nutritionFact in json_data["nutritionsFactList"]:
            if nutritionFact["typeCode"] == "fett":
                d["fats"] = float(nutritionFact["value"])
            elif nutritionFact["typeCode"] == "kolhydrat":
                d["carbs"] = float(nutritionFact["value"])
            elif nutritionFact["typeCode"] == "protein":
                d["protein"] = float(nutritionFact["value"])
        return d
    except Exception as e:
        log(e, 1)
        return {}

if __name__ == "__main__":
    all_products = []
    for category_url in URLS:
        log(f"Getting products from url {category_url}...")
        category_request = requests.get(category_url)
        category_products_json = category_request.json()
        n_products = len(category_products_json["results"])
        for i, result in enumerate(category_products_json["results"]):
            log(f"Processing request #{i+1}/#{n_products}...", 1)
            code = result["code"]
            url = "https://www.willys.se/axfood/rest/p/" + str(code)
            request = requests.get(url)
            try:
                json_data = request.json()
                parsed_json = parse_product_json(json_data)
                all_products.append(parsed_json)
            except Exception as e:
                log(e)

    json_str = json.dumps(all_products)
    f = open(OUTPUT_FILENAME, "w")
    f.write(json_str)
    f.close()
