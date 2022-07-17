import re
import requests
from time import strftime
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
# url = "https://www.willys.se/axfood/rest/p/101336170_ST"

def log(msg, indent=0):
    print(f"[{strftime('%X')}]: {'    ' * indent}{msg}")

def parse_product_json(json_data):
    d = {}
    try:
        d["name"] = json_data["name"]
        d["comparePrice"] = float(re.search(r"[\d,]+", json_data["comparePrice"], re.IGNORECASE).group().replace(',', '.'))
        d["comparePriceUnit"] = json_data["comparePriceUnit"]
        d["displayVolume"] = json_data["displayVolume"]
        for nutritionFact in json_data["nutritionsFactList"]:
            if nutritionFact["typeCode"] == "fett":
                d["fats"] = nutritionFact["value"]
            elif nutritionFact["typeCode"] == "kolhydrat":
                d["carbs"] = nutritionFact["value"]
            elif nutritionFact["typeCode"] == "protein":
                d["protein"] = nutritionFact["value"]
        return d
    except Exception as e:
        log(e, 1)
        return {}

all_products = []
for category_url in URLS:
    log(f"Getting products from url {category_url}...")
    category_request = requests.get(category_url)
    category_products_json = category_request.json()
    n_products = len(category_products_json["results"])
    for i, result in enumerate(category_products_json["results"]):
        log(f"Processing request #{i+1}/#{n_products}...", 1)
        code = result["code"]
        url = "https://www.willys.se/axfood/rest/p/X".replace("X", code)
        request = requests.get(url)
        json_data = request.json()
        parsed_json = parse_product_json(json_data)
        all_products.append(parsed_json)

json_str = json.dumps(all_products)
f = open(sys.argv[1], "w")
f.write(json_str)
f.close()
# print(products)

