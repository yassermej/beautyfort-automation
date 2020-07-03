# -*- coding: utf-8 -*-
import os
import uuid
import base64
import hashlib
import string
import random
import time
import csv
from datetime import datetime
import requests

import pandas as pd
import shopify

from env import *

import pdb


def validate_cell(val):
    if str(val) == 'nan':
        return ''
    return val

def validate_stock(val):
    if not val or str(val) == 'nan':
        return 0
    return val

def extract_first(val):
    return val[0] if len(val) > 0 else ''

def get_product_image(image_url):
    return requests.get(image_url).content

def upload_product(product, variant, image_url):
    # save image
    if len(product.images) == 0:
        image_data = get_product_image(image_url)

        image = shopify.Image({ 'product_id': product.id })
        image.attach_image(image_data, filename=product.title.replace(' ', '_'))
        image.save()

        product.images = [image]
        variant.image = image
        product.save()


if __name__ == "__main__":
    shop_url = "https://%s:%s@%s.myshopify.com/admin" % (SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOP_NAME)
    shopify.ShopifyResource.set_site(shop_url)

    # read xlsx file from shopify
    df = pd.read_csv('./bts_products.csv', sep=';')
    template = pd.read_csv('./template.csv', sep=',')
    shopify_columns =  template.columns.tolist()

    inventory_template = pd.read_csv('./inventory_template.csv', sep=',')
    inventory_columns = inventory_template.columns.tolist()

    now = datetime.now().strftime("%Y-%m-%d")

    with open("./bts_outputs_{}.csv".format(now), 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=shopify_columns)
        writer.writeheader()

        with open("./inventory_bts_outputs_{}.csv".format(now), 'w') as invent_csv:
            inventory_writer = csv.DictWriter(invent_csv, fieldnames=inventory_columns)
            inventory_writer.writeheader()

            idx = 0
            for index, selected_row in df.iterrows():
                if idx > 0:
                    break
                product_name = validate_cell(selected_row['name'])

                # image_data = get_product_image(selected_row['image'])
                # image = shopify.Image({})
                # image.attach_image(image_data, filename=product_name.replace(' ', '_'))
                # image.save()

                # pdb.set_trace()

                product = dict()
                product['Handle'] = product_name.replace(' ', '-')
                product['Title'] = product_name
                product['Vendor'] = 'btswholesaler'
                product['Body (HTML)'] = validate_cell(selected_row['description'])
                product['Option1 Name'] = 'Title'
                product['Option1 Value'] = 'Default Title'
                product['Variant Price'] = 0
                product['Variant SKU'] = product_name.replace(' ', '-')
                product['Variant Compare At Price'] = validate_cell(selected_row['price'])
                product['Variant Fulfillment Service'] = 'manual'
                product['Variant Inventory Tracker'] = 'shopify'
                product['Cost per item'] = validate_cell(selected_row['price'])
                product['Variant Inventory Policy'] = 'deny'
                product['Image Src'] = validate_cell(selected_row['image'])
                writer.writerow(product)

                inventory = dict()
                inventory['Handle'] = product_name.replace(' ', '-')
                inventory['Title'] = product_name
                inventory['Option1 Name'] = 'Title'
                inventory['Option1 Value'] = 'Default Title'
                inventory['SKU'] = product_name.replace(' ', '-')
                inventory['Beauty Fort UK'] = validate_stock(selected_row['stock'])
                inventory_writer.writerow(inventory)
                idx = idx + 1
            invent_csv.close()

        csvfile.close()

    print("Done !")


    # testIdx = 11
    # idx = 0
    # for index, selected_row in df.iterrows():   
    #     product_name = validate_cell(selected_row['name'])

    #     # Create or update product
    #     try:
    #         res = shopify.Product().find(title=product_name)
    #         if len(res) > 0:
    #             product = res[0]
    #             variants = product.variants
    #             if len(variants) == 1:
    #                 variant = variants[0]

    #                 variant.compare_at_price = validate_cell(selected_row['recommended_price'])
    #                 variant.sku = product_name.replace(' ', '-')
    #                 variant.save()


    #                 inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
    #                 inventory_item.cost = validate_cell(selected_row['price'])
    #                 inventory_item.country_code_of_origin = 'GB'
    #                 inventory_item.sku = variant.sku
    #                 inventory_item.tracked = True
    #                 inventory_item.save()

    #                 time.sleep(1)

    #                 inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
    #                 if len(inventory_levels) > 0:
    #                     inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
    #                                         available=str(validate_cell(selected_row['stock'])),
    #                                         location_id=str(inventory_levels[0].location_id))

    #             # product.product_type = product_type
    #             # product.vendor = selected_row[0]
    #             product.save()

    #             # save image 
    #             upload_product(product, variant, selected_row['image'])

    #             print("Product is updated successfully. Id is {}!  ".format(product.id))
    #         else:
    #             # Create product
    #             product = shopify.Product()
    #             product.title = product_name
    #             # product.vendor = validate_cell(selected_row[0])
    #             # product.product_type = product_type

    #             variant = shopify.Variant()
    #             product.variants =[variant]
    #             product.save()

    #             variant = product.variants[0]
    #             variant.product_id = product.id
    #             # variant.price = selected_row[7]
    #             variant.compare_at_price = validate_cell(selected_row['recommended_price'])
    #             variant.sku = product_name.replace(' ', '-')
    #             variant.fulfillment_service = 'manual'
    #             variant.inventory_management = 'shopify'
    #             variant.save()

    #             time.sleep(1)

    #             inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
    #             inventory_item.cost = validate_cell(selected_row['price'])
    #             inventory_item.country_code_of_origin = 'GB'
    #             inventory_item.sku = variant.sku
    #             inventory_item.tracked = True
    #             inventory_item.save()

    #             inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
    #             if len(inventory_levels) > 0:
    #                 inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
    #                                     available=str(validate_cell(selected_row['stock'])),
    #                                     location_id=str(inventory_levels[0].location_id))

    #             # save image 
    #             upload_product(product, variant, selected_row['image'])
    #             print("Product is saved successfully. Id is {}!  ".format(product.id))

    #     except Exception as ee:
    #         print("######## Error #######: ", str(ee))
    #         pdb.set_trace()
    #     idx = idx + 1