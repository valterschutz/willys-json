import pdb
import re
import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

PAGE_LIMIT = 1
G_PER_EGG = 50
OUTPUT_FILE_NAME = 'data.json'
URLS = [
    "https://www.willys.se/sortiment/mejeri-ost-och-agg",
    "https://www.willys.se/sortiment/kott-chark-och-fagel",
    "https://www.willys.se/sortiment/skafferi",
    "https://www.willys.se/sortiment/brod-och-kakor",
    "https://www.willys.se/sortiment/fryst",
    "https://www.willys.se/sortiment/fisk-och-skaldjur",
    "https://www.willys.se/sortiment/vegetariskt",
    # "https://www.willys.se/sortiment/glass-godis-och-snacks",
    "https://www.willys.se/sortiment/fardigmat"
]

# TODO: egg weight, water weight -> convert to kr/g
# Average egg = 50 g

def extract_data_from_page(driver, data, url):
    print(f"Entering {url}...")
    driver.get(url)
    # Load all items
    load_button = driver.find_element(By.CSS_SELECTOR, ".Buttonstyles__StyledButton-sc-1g4oxwr-0.bXXAMk.LoadMore__LoadMoreBtn-sc-16fjaj7-3.bnbvpm")
    loading_items = True
    page = 0
    while loading_items:
        print("Loading more items...")
        load_button.click()
        page += 1
        sleep(0)
        try:
            load_button = driver.find_element(By.CSS_SELECTOR, ".Buttonstyles__StyledButton-sc-1g4oxwr-0.bXXAMk.LoadMore__LoadMoreBtn-sc-16fjaj7-3.bnbvpm")
        except:
            loading_items = False
        if page >= PAGE_LIMIT:
            loading_items = False

    print("Loaded all items!")

    food_imgs = driver.find_elements(By.CSS_SELECTOR,".Product__ImageWrapper-sc-e8fauy-0.OJXsI")
    # pdb.set_trace()
    for food_img in food_imgs:
        food_img.click()
        sleep(1)
        name = driver.find_element(By.CSS_SELECTOR, ".Headingstyles__StyledH2-sc-r7tfy8-1.cJhDBd").text
        print(f"Gathering data for \"{name}\"")
        brand = driver.find_element(By.CSS_SELECTOR, "a.Linkstyles__StyledLink-sc-blur7a-0.epxKYt.ProductDetailsstyles__StyledProductDetailsManufacturerLink-sc-1gianr0-21.fpLVjo").text

        # Process subname
        subname = driver.find_element(By.CSS_SELECTOR, "span.ProductDetailsstyles__StyledProductDetailsManufacturerVolume-sc-1gianr0-22.jlvnMx").text
        num_str, unit_str = re.search(r'([,\d]+)(g|kg|p|ml|dl|l)', subname).groups()
        weight_in_g = None
        qty = None
        volume_in_ml = None
        # For some products we can calculate kr/g even though the unit is qty
        if unit_str == 'g':
            weight_in_g = float(num_str.replace(',', '.'))
        elif unit_str == 'kg':
            weight_in_g = float(num_str.replace(',', '.')) * 1000
        elif unit_str == 'p':
            if "ägg" in name.lower():
                weight_in_g = float(num_str) * G_PER_EGG
            qty = int(num_str)
        elif unit_str == 'ml':
            volume_in_ml = int(num_str)
        elif unit_str == 'dl':
            volume_in_ml = int(num_str) * 100
        elif unit_str == 'l':
            volume_in_ml = int(num_str) * 1000
            # For liquids, assume 1g per ml
            weight_in_g = volume_in_ml
        else:
            raise Exception("Could not get weight, quantity or volume from subname")

        # Process price
        price_text = driver.find_element(By.CSS_SELECTOR, ".Textstyles__StyledText-sc-3u2veo-0.kIqpfh").text
        num_str, unit_str = re.search(f'Jmf-pris ([,\d]*) (kr/kg|kr/st|kr/l)', price_text).groups()
        price_per_g= None
        price_per_qty = None
        price_per_ml = None
        if unit_str == 'kr/kg':
            price_per_g = float(num_str.replace(',', '.')) / 1000
        elif unit_str == 'kr/st':
            if "ägg" in name.lower():
                price_per_g = float(num_str.replace(',', '.')) / G_PER_EGG
            price_per_qty = float(num_str.replace(',', '.'))
        elif unit_str == 'kr/l':
            price_per_ml = float(num_str.replace(',', '.')) / 1000
            price_per_g = price_per_ml
        else:
            raise Exception("Price unit was neither weight or quantity")

        pdb.set_trace()

        
        # Try to get nutritional value
        try:
            # pdb.set_trace()
            show_more_button = driver.find_element(By.CSS_SELECTOR, "button.Buttonstyles__StyledButton-sc-1g4oxwr-0.hVCRFK.ExpandableContainerstyles__StyledExandableContainerButton-sc-1ywlidl-1.jyNfOr")
            show_more_button.click()
            nutrition_table_header_text = driver.find_element(By.CSS_SELECTOR, "thead").text
            # Units given in the table always seem to be in g,
            # this is just a sanity check
            if not ('milliliter' in nutrition_table_header_text or 'gram' in nutrition_table_header_text):
                raise Exception("Nutritional units are neither in ml or g.")
            nutrition_table_body = driver.find_element(By.CSS_SELECTOR, "tbody")
            fat_text = nutrition_table_body.find_element(By.CSS_SELECTOR, "tbody>tr:nth-child(3)").text
            fat = float(re.search(r'[.\d]+', fat_text).group())
            carb_text = nutrition_table_body.find_element(By.CSS_SELECTOR, "tbody>tr:nth-child(5)").text
            carb = float(re.search(r'[.\d]+', carb_text).group())
            protein_text = nutrition_table_body.find_element(By.CSS_SELECTOR, "tbody>tr:nth-child(7)").text
            protein = float(re.search(r'[.\d]+', protein_text).group())
            nutritional_value = {
                'fat': fat,
                'carb': carb,
                'protein': protein
            }
            print('  Found nutritional value.')
        except:
            print('  Did not find nutritional value.')
            nutritional_value = None

        pdb.set_trace()

        data[f"{name} - {subname}"] = {
            # 'name': name,
            'price_per_g': price_per_g,
            'price_per_qty': price_per_qty,
            'price_per_ml': price_per_ml,
            'brand': brand,
            'weight_in_g': weight_in_g,
            'volume_in_ml': volume_in_ml,
            'qty': qty,
            'nutritional_value': nutritional_value
        }
        driver.back()
    print(f"Exiting {url}...")
    return data

driver = webdriver.Firefox()
driver.get("https://www.willys.se")
sleep(5)
cookies_button = driver.find_element(By.CSS_SELECTOR, "#onetrust-reject-all-handler")
cookies_button.click()
sleep(5)

data = {}
for url in URLS:
    data = extract_data_from_page(driver, data, url)

print("Converting data to json...")
final = json.dumps(data, indent=2)

print(f"Writing data to {OUTPUT_FILE_NAME}...")
f = open(OUTPUT_FILE_NAME, "w")
f.write(final)
f.close()
print("Finished!")
