import pdb
import re
import json
from time import sleep, strftime
from selenium import webdriver
# from selenium.webdriver.chrome.options import Options
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By

# TODO: nutritional table sometimes changes

PAGE_LIMIT = None  # Either a number, None or False
COOKIE_WAIT_TIME = 5  # First time when cookies load
DEFAULT_WAIT_TIME = 1  # Each time a button is clicked
G_PER_EGG = 50
OUTPUT_FILE_NAME = 'data.json'
URLS = [
    "https://www.willys.se/sortiment/kott-chark-och-fagel/fagel"
]
# URLS = [
#     "https://www.willys.se/sortiment/mejeri-ost-och-agg",
#     "https://www.willys.se/sortiment/kott-chark-och-fagel",
#     "https://www.willys.se/sortiment/skafferi",
#     "https://www.willys.se/sortiment/brod-och-kakor",
#     "https://www.willys.se/sortiment/fryst",
#     "https://www.willys.se/sortiment/fisk-och-skaldjur",
#     "https://www.willys.se/sortiment/vegetariskt",
#     "https://www.willys.se/sortiment/glass-godis-och-snacks",
#     "https://www.willys.se/sortiment/fardigmat"
# ]

def log(msg, indent):
    print(f"[{strftime('%X')}]: {'    ' * indent}{msg}")

def do_until_possible(f):
    # Execute function f until it does not fail
    working = False
    while not working:
        try:
            val = f()
        except:
            sleep(DEFAULT_WAIT_TIME)
        else:
            working = True
    return val

def extract_data_from_food_img(driver, data, food_img):
    food_img.click()
    sleep(DEFAULT_WAIT_TIME)
    # This looks really bad...
    def temp_f():
        name = driver.find_element(By.CSS_SELECTOR, ".Headingstyles__StyledH2-sc-r7tfy8-1.cJhDBd").text
        return name
    name = do_until_possible(temp_f)
    log(f"Gathering data for \"{name}\"", 0)
    brand = driver.find_element(By.CSS_SELECTOR, "a.Linkstyles__StyledLink-sc-blur7a-0.epxKYt.ProductDetailsstyles__StyledProductDetailsManufacturerLink-sc-1gianr0-21.fpLVjo").text

    # Process subname, exit if unit does not match
    subname = driver.find_element(By.CSS_SELECTOR, "span.ProductDetailsstyles__StyledProductDetailsManufacturerVolume-sc-1gianr0-22.jlvnMx").text
    match = re.search(r'([,\d]+)(g|kg|p|ml|dl|l)', subname)
    if match:
        num_str, unit_str = match.groups()
    else:
        log(f"Unexpected unit in subname {subname}", 1)
        driver.back()
        return data
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
        qty = float(num_str)
    # For liquids, assume 1g per ml
    elif unit_str == 'ml':
        volume_in_ml = float(num_str)
        weight_in_g = volume_in_ml
    elif unit_str == 'dl':
        volume_in_ml = float(num_str) * 100
        weight_in_g = volume_in_ml * 100
    elif unit_str == 'l':
        volume_in_ml = float(num_str) * 1000
        weight_in_g = volume_in_ml * 1000
    else:
        log(f"Could not get weight, quantity or volume from {subname}", 1)

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
        log(f"Price unit was neither weight or quantity in {price_text}", 1)

    # Try to get macros
    try:
        # pdb.set_trace()
        show_more_button = driver.find_element(By.CSS_SELECTOR, "button.Buttonstyles__StyledButton-sc-1g4oxwr-0.hVCRFK.ExpandableContainerstyles__StyledExandableContainerButton-sc-1ywlidl-1.jyNfOr")
        show_more_button.click()
        sleep(DEFAULT_WAIT_TIME)
        nutrition_table_header_text = driver.find_element(By.CSS_SELECTOR, "thead").text
        # Units given in the table always seem to be in g,
        # this is just a sanity check
        if not (('milliliter' in nutrition_table_header_text) or ('gram' in nutrition_table_header_text)):
            raise Exception("Nutritional units are neither in ml or g.")
        nutrition_table_body = driver.find_element(By.CSS_SELECTOR, "tbody")
        match = re.findall(r'\n(fett|kolhydrat|protein)[\s<]*([.\d]+)', nutrition_table_body.text)
        # Turn match into a dictionary
        d = {}
        for item in match:
            d[item[0]] = float(item[1].replace(',', '.')) / 100
        macros_per_g = d
        log('Found nutritional value.', 1)
    except Exception as e:
        log(f'Error while parsing nutrition: {e}', 1)
        macros_per_g = None

    data[f"{name} - {subname}"] = {
        'price_per_g': price_per_g,
        'price_per_qty': price_per_qty,
        'price_per_ml': price_per_ml,
        'brand': brand,
        'weight_in_g': weight_in_g,
        'volume_in_ml': volume_in_ml,
        'qty': qty,
        'macros_per_g': macros_per_g
    }
    driver.back()
    return data

def extract_data_from_page(driver, data, url):
    log(f"Entering {url}...", 0)
    driver.get(url)
    # Get number of items
    n_items = int(re.search(r"\d+", driver.find_element(By.CSS_SELECTOR, "p.Textstyles__StyledText-sc-3u2veo-0.iEVqfZ").text).group())
    counter = 1
    # Load all items
    try:
        load_button = driver.find_element(By.CSS_SELECTOR, ".Buttonstyles__StyledButton-sc-1g4oxwr-0.bXXAMk.LoadMore__LoadMoreBtn-sc-16fjaj7-3.bnbvpm")
    except:
        loading_items = False
    else:
        loading_items = True
        page = 0
    while loading_items:
        log("Loading more items...", 0)
        load_button.click()
        sleep(DEFAULT_WAIT_TIME)
        page += 1
        try:
            # pdb.set_trace()
            items_loaded_text = driver.find_element(By.CSS_SELECTOR, "p.Textstyles__StyledText-sc-3u2veo-0.jWLQxR.LoadMore__Info-sc-16fjaj7-2.hnbkdF").text
            match = re.search(r"Visar ([\d]+) av ([\d]+)", items_loaded_text)
            num1, num2 = map(int, match.groups())
            log(f"Loaded {num1} out of {num2} items...", 1)
            load_button = driver.find_element(By.CSS_SELECTOR, ".Buttonstyles__StyledButton-sc-1g4oxwr-0.bXXAMk.LoadMore__LoadMoreBtn-sc-16fjaj7-3.bnbvpm")
        except:
            loading_items = False
        if PAGE_LIMIT and page >= PAGE_LIMIT:
            loading_items = False

    log("Loaded all items!", 0)

    food_imgs = driver.find_elements(By.CSS_SELECTOR,".Product__ImageWrapper-sc-e8fauy-0.OJXsI")
    # pdb.set_trace()
    for food_img in food_imgs:
        log(f"---{counter}/{n_items}---", 0)
        data = extract_data_from_food_img(driver, data, food_img)
        counter += 1
    log(f"Exiting {url}...", 0)
    return data


c = Options()
# c.add_argument("--headless")
# driver = webdriver.Chrome(options = c)
driver = webdriver.Firefox(options = c)
driver.get("https://www.willys.se")
log("Waiting for cookies prompt...", 0)
sleep(COOKIE_WAIT_TIME)
cookies_button = driver.find_element(By.CSS_SELECTOR, "#onetrust-reject-all-handler")
cookies_button.click()
sleep(5)

data = {}
for url in URLS:
    data = extract_data_from_page(driver, data, url)
driver.close()

log("Converting data to json...", 0)
final = json.dumps(data, indent=2)

log(f"Writing data to {OUTPUT_FILE_NAME}...", 0)
f = open(OUTPUT_FILE_NAME, "w")
f.write(final)
f.close()
log("Finished!", 0)
