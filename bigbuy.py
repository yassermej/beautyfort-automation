# -*- coding: utf-8 -*-
import os
import uuid
import base64
import hashlib
import string
import random
import time
from datetime import datetime
import requests

# 3rd party libraries
from peewee import *
from lxml import etree
import pandas as pd
import shopify

from env import *

import pdb


# write db file
base_dir = os.path.dirname(os.path.abspath(__file__))
db = SqliteDatabase(base_dir+'/app.db')


# define tables
class BaseModel(Model):
    class Meta:
        database = db


class BigBuyProduct(BaseModel):
    product_id = TextField()
    name = TextField()
    sku = TextField()
    ean13 = TextField()
    image = TextField()
    category = TextField()
    retail_price = TextField()
    wholesale_price = TextField()
    depth = TextField()
    description = TextField()
    tags = TextField()


def initialize_db():
    db.connect()
    db.create_tables([BigBuyProduct,], safe = True)
    db.close()

def encode_sha1(message):
    base64_bytes = base64.b64encode(message.encode('ascii'))
    return base64_bytes.decode('ascii')


def generate_random():
    letters = string.digits
    return ''.join(random.choice(letters) for i in range(6))

def extract_first(val):
    return val[0] if len(val) > 0 else ''


class BigBuy:
    def __init__(self):
        # self.api_url = 'https://api.bigbuy.eu'
        self.api_url = 'https://api.sandbox.bigbuy.eu'
        self.headers = {
            'Authorization': 'Bearer ' + BIGBUY_SANDBOX_KEY,
            # 'Authorization': 'Bearer ' + BIGBUY_API_KEY,
            'Content-Type': 'application/json'
        }

    def get_products(self):
        url = '/rest/catalog/products.json?isoCode=en'
        products = requests.get(self.api_url+url, headers=self.headers)
        return products.json()

    def get_image_by_id(self, id):
        url = '/rest/catalog/productimages/{}.json?isoCode=en'.format(id)
        image = requests.get(self.api_url+url, headers=self.headers)
        image_data = image.json()
        try:
            if len(image_data['images']) > 0:
                return image_data['images'][0]['url']
        except:
            pass
        return None

    def get_tags(self, product_id):
        url = '/rest/catalog/producttags/{}.json?isoCode=en'.format(product_id)
        res = requests.get(self.api_url+url, headers=self.headers)
        # tags = [x['name'] for x in res.json()]
        try:
            tags = res.json()
            tag_str = ''
            if len(tags) > 0:
                tag_str = ','.join(x['name'] for x in tags)
            return tag_str
        except Exception as ee:
            print(str(ee))
            return ''

    def products_by_id(self, product_id):
        url = '/rest/catalog/product/{}.json?isoCode=en'.format(product_id)
        res = requests.get(self.api_url+url, headers=self.headers)
        return res.json()

    def products_by_category(self, category):
        url = '/rest/catalog/productscategories.json?isoCode=en'
        result = []
        res = requests.get(self.api_url+url, headers=self.headers)
        try:
            products = res.json()
            # pdb.set_trace()
            for product in products:
                if product['category'] == category:
                    result.append(product['product'])
        except Exception as ee:
            print("@@@@ Product Categories API limit @@@@: ", str(ee))
            pass
        return result

    def producttag_by_id(self, product_id):
        url = '/rest/catalog/producttags/{}.json?isoCode=en'.format(product_id)
        res = requests.get(self.api_url+url, headers=self.headers)
        return ','.join(x['name'] for x in res.json())


    def product_information(self, product_id):
        url = '/rest/catalog/productinformation/{}.json?isoCode=en'.format(product_id)
        res = requests.get(self.api_url+url, headers=self.headers)
        return res.json()

    def stock_by_id(self, product_id):
        url = '/rest/catalog/productstock/{}.json?isoCode=en'.format(product_id)
        res = requests.get(self.api_url+url, headers=self.headers).json()
        if 'stocks' in res and len(res['stocks']) > 0:
            return str(res['stocks'][0]['quantity'])
        return '0'

def upload_product(api, product, variant, entry):
    # save image
    if len(product.images) == 0:
        # pull product information from BigBuy
        image_data = requests.get(entry.image).content

        image = shopify.Image({ 'product_id': product.id })
        image.attach_image(image_data, filename=entry.name.replace(' ', '_'))
        image.save()

        product.images = [image]
        variant.image = image
        product.save()

def validate_cell(val):
    return val if str(val) else ''


if __name__ == "__main__":
    initialize_db()

    shop_url = "https://%s:%s@%s.myshopify.com/admin" % (KITCHEN_SHOP_API_KEY, KITCHEN_SHOP_PASSWORD, 'kitchenseasyzk')
    shopify.ShopifyResource.set_site(shop_url)

    # read xlsx file from shopify
    df = pd.read_excel('./shopify.xlsx', index_col=0)
    now = datetime.now().strftime("%Y-%m-%d")

    list_to_be_updated = df['Name (IMPORT)'].tolist()

    kitchen_category = 2403

    ## create api instance
    api = BigBuy()
    products = api.products_by_category(kitchen_category)

    # products = [14975, 15188, 15302, 16581, 14191, 16607, 14437, 15682, 14506, 14527, 14564, 14580, 14596, 14606, 14622, 14632, 14649, 14665, 14681, 14691, 14701, 14718, 14734, 13684, 15185, 15202, 16578, 14194, 16604, 16620, 16696, 14434, 14503, 15740, 14509, 14533, 14577, 14593, 14603, 14619, 14629, 14646, 14662, 14678, 14698, 14715, 14731, 13238, 14981, 15181, 15199, 16529, 16575, 14186, 16601, 16693, 14431, 15696, 12501, 14574, 14590, 14600, 14616, 14626, 14643, 14659, 14675, 14695, 14711, 14728, 13225, 13266, 14976, 15196, 15309, 16598, 16614, 14421, 14428, 14444, 15693, 14571, 14587, 14613, 14640, 14656, 14672, 14688, 14708, 14725, 15193, 15306, 15398, 16595, 16611, 14425, 14441, 14534, 14568, 14584, 14610, 14637, 14653, 14669, 14685, 14692, 14705, 14722, 14982, 15190, 15303, 16530, 16582, 14189, 16608, 14438, 15683, 14529, 14565, 14581, 14607, 14633, 14650, 14666, 14682, 14702, 14719, 14735, 13226, 13296, 14977, 14987, 15186, 16579, 16605, 16621, 16697, 14435, 14504, 14510, 14513, 14562, 14578, 14594, 14604, 14620, 14630, 14647, 14663, 14679, 14699, 14716, 14732, 13252, 13260, 13267, 15182, 15200, 16576, 16592, 14187, 16602, 16618, 16694, 14432, 15697, 14535, 14575, 14591, 14601, 14617, 14627, 14644, 14660, 14676, 14696, 14712, 14729, 14983, 15179, 15197, 15223, 16573, 14190, 16599, 14199, 14202, 14422, 14429, 15694, 15742, 14530, 14572, 14588, 14598, 14614, 14624, 14641, 14657, 14673, 14689, 14693, 14709, 14726, 14978, 14988, 15194, 15307, 15399, 16596, 16612, 14426, 14442, 14569, 14585, 14611, 14638, 14654, 14670, 14686, 14706, 14723, 13250, 14953, 15191, 15224, 15304, 16609, 14205, 14423, 14439, 15684, 15743, 14536, 14566, 14582, 14608, 14635, 14651, 14667, 14683, 14703, 14720, 14984, 15187, 16580, 16606, 14436, 15681, 15691, 14505, 14511, 14531, 14563, 14579, 14595, 14605, 14621, 14631, 14648, 14664, 14680, 14700, 14717, 14733, 13245, 14979, 15184, 15201, 15225, 16577, 16603, 16619, 16695, 14433, 14502, 15744, 14576, 14592, 14602, 14618, 14628, 14645, 14661, 14677, 14690, 14697, 14714, 14730, 15180, 15198, 16574, 14188, 16600, 14203, 14430, 15695, 15738, 14537, 14573, 14589, 14599, 14615, 14625, 14642, 14658, 14674, 14694, 14710, 14727, 13246, 14985, 15195, 15308, 15400, 16597, 16613, 14420, 14427, 14443, 14532, 14570, 14586, 14612, 14639, 14655, 14671, 14687, 14707, 14724, 14939, 14990, 15115, 15192, 15305, 15397, 16594, 16610, 14424, 14440, 15685, 12476, 15739, 14567, 14583, 14609, 14636, 14652, 14668, 14684, 14704, 14721, 13287, 12634, 5987, 42, 1297, 1308, 1334, 15591, 15599, 15607, 15615, 15623, 15631, 15639, 9558, 9567, 12520, 13165, 13194, 13257, 13262, 206, 294, 5670, 15715, 16785, 16797, 15908, 15916, 15924, 15932, 13188, 13229, 5045, 13709, 15119, 1309, 15429, 15586, 15594, 15602, 15610, 15618, 15626, 15634, 15642, 14512, 1692, 15836, 1861, 6, 5342, 15357, 12518, 12803, 15911, 15919, 15927, 15935, 13259, 10146, 5405, 5588, 15354, 1302, 1310, 15589, 15597, 15605, 15613, 15621, 15629, 15637, 1578, 9559, 15741, 12628, 6728, 587, 15113, 5672, 9452, 9568, 16795, 1863, 15906, 15914, 15922, 15930, 13166, 13230, 5510, 7655, 1303, 1311, 15592, 15600, 15608, 15616, 15624, 15632, 15640, 13211, 13249, 5077, 13703, 5542, 15430, 15680, 16773, 7956, 14507, 6523, 15909, 15917, 6720, 15925, 15933, 5357, 13698, 15358, 1278, 1304, 1312, 5885, 15587, 15595, 15603, 15611, 15619, 15627, 15635, 15837, 1864, 13191, 13255, 5066, 217, 13707, 15117, 5662, 15355, 1555, 16793, 15737, 15904, 15912, 15920, 15928, 11474, 13712, 1067, 1305, 1313, 15590, 15598, 15606, 15614, 15622, 15630, 15638, 12519, 13227, 13268, 15114, 9566, 16796, 1865, 15907, 15915, 15923, 15931, 13233, 5362, 1306, 14193, 15593, 15601, 15609, 15617, 15625, 15633, 15641, 15835, 13317, 11471, 15359, 15688, 14508, 12517, 6729, 15910, 15918, 15926, 15934, 13269, 205, 15356, 1307, 15588, 15596, 15604, 15612, 15620, 15628, 15636, 12515, 15838, 1867, 13235, 5075, 5112, 15112, 1381, 15692, 16794, 15745, 6614, 1860, 15905, 15913, 15921, 15929, 13224, 143, 6027, 1814, 586, 7968, 13039, 6619, 666, 12637, 300, 5094, 13726, 13040, 13715, 9565, 2, 13727, 6461, 823, 6696, 11449, 867, 585, 13713, 12631, 5404, 5472, 5522, 1610, 1672, 12669, 13242, 2094, 11480, 10149, 547, 7850, 6525, 5300, 5321, 764, 1684, 9526, 1995, 13210, 2104, 11476, 12507, 12806, 6736, 13184, 13263, 198, 213, 11481, 5677, 9886, 13169, 13172, 11442, 13711, 788, 5545, 958, 1654, 7963, 6447, 1753, 1972, 5108, 440, 5585, 5956, 9560, 1651, 12477, 6528, 9888, 13163, 484, 679, 5538, 5999, 13203, 5322, 5402, 5408, 5520, 7650, 12629, 6737, 6622, 13185, 11447, 407, 5673, 13033, 2026, 13221, 8444, 5090, 5529, 1393, 1547, 7959, 6623, 13167, 13170, 2096, 8433, 13294, 11478, 1151, 1389, 12266, 9557, 9561, 12504, 1793, 13152, 13181, 13192, 2093, 53, 13261, 510, 5403, 13708, 668, 5521, 5971, 7845, 1629, 12508, 12630, 6554, 5323, 5340, 7362, 5663, 7651, 12500, 9544, 6613, 1991, 9887, 13153, 11475, 11479, 6735, 13183, 13186, 13228, 13265, 9524, 1736, 13168, 13171, 8487, 11491, 736, 753, 844, 1726, 1783, 1790, 875, 925, 5889, 1391, 1773, 9908, 67, 5107, 861, 5934, 5939, 1400, 6014, 6059, 6500, 6522, 6562, 8488, 738, 744, 777, 7965, 1721, 1727, 6507, 6546, 1784, 1791, 13032, 800, 877, 5808, 5984, 6757, 754, 767, 863, 5523, 1153, 5942, 6496, 8490, 8501, 8506, 740, 779, 1392, 1572, 1722, 1729, 6552, 1769, 1774, 5058, 802, 872, 5546, 1397, 7867, 6492, 6558, 745, 755, 769, 864, 921, 5806, 5943, 5952, 5991, 7862, 1636, 7982, 6488, 9531, 6497, 6503, 6508, 1792, 8491, 8509, 662, 741, 798, 1573, 1724, 1730, 1775, 8485, 11489, 807, 873, 1398, 6483, 6493, 1788, 520, 5396, 5490, 1660, 6504, 6520, 6548, 1799, 618, 5868, 5995, 6069, 6498, 1731, 1772, 1776, 8486, 11490, 10145, 734, 750, 809, 874, 930, 5543, 1394, 6484, 1789, 12933, 11469, 743, 772, 791, 799, 5886, 6506, 6537, 6550, 2086, 5283, 5676, 5869, 5932, 6494, 6499, 6521, 6560, 12802, 1819, 1955, 5360, 5709, 6207, 7948, 12983, 13161, 439, 1138, 1159, 895, 1627, 5390, 12608, 1815, 1982, 5541, 1406, 6005, 8483, 11473, 6501, 5710, 1785, 12984, 732, 841, 5527, 1662, 5102, 183, 1106, 1501, 1738, 202, 677, 6445, 1816, 9906, 11468, 5471, 5814, 1691, 11448, 1321, 1828, 1537, 7868, 94, 6006, 6485, 13253, 118, 8500, 792, 868, 1665, 6551, 5116, 787, 8809, 1335, 6467, 6495, 1779, 606, 1280, 1499, 12971, 793, 6490, 5117, 5372, 5994, 6297, 12938, 1551, 1749, 1755, 6547, 6594, 5867, 1639, 1666, 9878, 5339, 790, 9884, 8502, 5391, 782, 13264, 438, 1674, 6524, 5375, 865, 6020, 9879, 8492, 5413, 783, 858, 1337, 5864, 1725, 6595, 195, 5410, 1399, 8503, 5148, 410, 1105, 1186, 6545, 1794, 1981, 9885, 5341, 5416, 5456, 785, 859, 939, 5719, 1607, 1635, 12479, 1664, 12970, 7741, 13251, 43, 5636, 5876, 6590, 1931, 12516, 1355, 8514, 6553, 826, 6448, 6559, 6591, 771, 6609, 5644, 5875, 5716, 6592, 9880, 5389, 846, 6487, 5411, 5046, 847, 5149, 5415, 849, 5627, 5074, 5988, 6003, 13704, 6489, 5115, 5993, 7363, 7957, 6557, 5679, 6132, 13057, 5414, 11470, 5067, 6296]

    count = 0
    for product_id in products:
        big_product = api.products_by_id(product_id)
        product_quantity = api.stock_by_id(product_id)
        try:
            entry = BigBuyProduct.get(BigBuyProduct.product_id==product_id)
            entry.retail_price=big_product['retailPrice']
            entry.wholesale_price=big_product['wholesalePrice']
            entry.save()
        except:
            product_detail = api.product_information(product_id)
            product_image = api.get_image_by_id(product_id)
            tags = api.producttag_by_id(product_id)

            entry = BigBuyProduct(product_id=big_product['id'],
                                name=product_detail['name'],
                                sku=big_product['sku'],
                                ean13=big_product['ean13'],
                                image=product_image,
                                category='kitchen',
                                retail_price=big_product['retailPrice'],
                                wholesale_price=big_product['wholesalePrice'],
                                depth=big_product['depth'],
                                description=product_detail['description'],
                                tags=tags)
            entry.save()

        # try:
        res = shopify.Product().find(title=entry.name)

        if len(res) > 0:
            product = res[0]
            variants = product.variants
            if len(variants) == 1:
                variant = variants[0]

                variant.compare_at_price = validate_cell(entry.retail_price)
                variant.sku = entry.sku
                variant.save()


                inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
                inventory_item.cost = validate_cell(entry.wholesale_price)
                inventory_item.country_code_of_origin = 'GB'
                inventory_item.sku = entry.sku
                inventory_item.tracked = True
                inventory_item.save()

                time.sleep(1)

                inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
                if len(inventory_levels) > 0:
                    inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
                                        available=str(product_quantity),
                                        location_id=str(inventory_levels[0].location_id))

            product.product_type = entry.category
            product.body_html = entry.description
            product.tags = entry.tags.split(',')
            product.vendor = 'BigBuy'
            product.save()

            # save image 
            upload_product(api, product, variant, entry)

            print("Product is updated successfully. Id is {}!  ".format(product.id))
        else:
            # Create product
            product = shopify.Product()
            product.title = entry.name
            product.body_html = entry.description
            product.tags = entry.tags.split(',')
            product.vendor = 'BigBuy'
            product.product_type = entry.category

            variant = shopify.Variant()
            product.variants =[variant]
            product.save()

            variant.product_id = product.id
            # variant.price = selected_row[7]
            variant.compare_at_price = validate_cell(entry.retail_price)
            variant.sku = entry.sku
            variant.fulfillment_service = 'manual'
            variant.inventory_management = 'shopify'
            product.variants =[variant]
            product.save()

            time.sleep(1)


            variant = product.variants[0]
            inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
            inventory_item.cost = validate_cell(entry.wholesale_price)
            inventory_item.country_code_of_origin = 'GB'
            inventory_item.sku = entry.sku
            inventory_item.tracked = True
            inventory_item.save()

            inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
            if len(inventory_levels) > 0:
                inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
                                    available=str(product_quantity),
                                    location_id=str(inventory_levels[0].location_id))

            # save image 
            upload_product(api, product, variant, entry)
            print("Product is saved successfully. Id is {}!  ".format(product.id))

        # except Exception as ee:
        #     print("######## Error {} #######: {}".format(entry.name, str(ee)))
        #     pdb.set_trace()

        time.sleep(5)
