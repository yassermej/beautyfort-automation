# -*- coding: utf-8 -*-
import os
import uuid
import base64
import hashlib
import string
import random
from datetime import datetime
import requests

# 3rd party libraries
from peewee import *
from lxml import etree

import pandas as pd
import shopify

from env import *

USERNAME = USERNAME
SECRET_KEY = SECRET_KEY
SHOP_NAME = SHOP_NAME
SHOPIFY_API_KEY = SHOPIFY_API_KEY
SHOPIFY_PASSWORD = SHOPIFY_PASSWORD

# write db file
base_dir = os.path.dirname(os.path.abspath(__file__))
db = SqliteDatabase(base_dir+'/app.db')


# define tables
class BaseModel(Model):
    class Meta:
        database = db


class Category(BaseModel):
    uid = TextField()
    name = TextField()


class Brand(BaseModel):
    uid = TextField()
    name = TextField()


class ProductType(BaseModel):
    uid = TextField()
    name = TextField()

def initialize_db():
    db.connect()
    db.create_tables([Category, Brand, ProductType], safe = True)
    db.close()

def encode_sha1(message):
    base64_bytes = base64.b64encode(message.encode('ascii'))
    return base64_bytes.decode('ascii')


def generate_random():
    letters = string.digits
    return ''.join(random.choice(letters) for i in range(6))

def extract_first(val):
    return val[0] if len(val) > 0 else ''


class BeautyFort:
    def __init__(self, secret):
        nounce = generate_random()
        created_at = datetime.now().strftime("%Y-%m-%dT%H:%M:%S-05:00")
       
        sha1 = hashlib.sha1('{}{}{}'.format(nounce, created_at, secret).encode('ascii'))    
        password = encode_sha1(sha1.hexdigest())

        self.nounce = nounce
        self.created_at = created_at
        self.secret = secret
        self.password = password
        self.url = 'http://www.beautyfort.com/api/soap/v2'

        shop_url = "https://%s:%s@%s.myshopify.com/admin" % (SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOP_NAME)
        shopify.ShopifyResource.set_site(shop_url)

    def encode_sha1(message):
        base64_bytes = base64.b64encode(message.encode('ascii'))
        return base64_bytes.decode('ascii')

    def parse_res_to_xml(self, res):
        tree = etree.HTML(res.split('<SOAP-ENV:Body>')[1].split('</SOAP-ENV:Body>')[0])
        return tree

    def search_products(self, product_type_name, brand_name, stock_code):
        brand = Brand.select().where(Brand.name==brand_name).execute()
        product_type = ProductType.select().where(ProductType.name==product_type_name).execute()

        category_id = ''
        brand_id = ''
        product_type_id = ''

        # for entry in category:
        #     category_id = entry.uid

        for entry in brand:
            brand_id = entry.uid
        for entry in product_type:
            product_type_id = entry.uid

        xml = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bf="http://www.beautyfort.com/api/"><soap:Header>
                <bf:AuthHeader>
                    <bf:Username>%s</bf:Username>
                    <bf:Nonce>%s</bf:Nonce>
                    <bf:Created>%s</bf:Created>
                    <bf:Password>%s</bf:Password>
                </bf:AuthHeader>
            </soap:Header>
            <soap:Body>
                <bf:ProductSearchRequest>
                    <bf:TestMode>true</bf:TestMode>
                    <bf:StockCodes> ArrayOfStockCode
                        <bf:StockCode>%s</bf:StockCode>
                    </bf:StockCodes>
                    <bf:Brands> ArrayOfBrand
                        <bf:Brand> Brand
                            <bf:ID>%s</bf:ID>
                        </bf:Brand>
                    </bf:Brands>
                    <bf:ProductTypes> ArrayOfProductType
                        <bf:ProductType>
                            <bf:ID>%s</bf:ID>
                        </bf:ProductType>
                    </bf:ProductTypes>
                </bf:ProductSearchRequest>
            </soap:Body></soap:Envelope>
        """ % (USERNAME, self.nounce, self.created_at, self.password, \
               stock_code, brand_id, product_type_id)

        headers = {'Content-Type': 'application/xml'}
        res = requests.post(self.url, data=xml, headers=headers).text
        return res

    def get_account(self):
        xml = """<?xml version="1.0" encoding="utf-8"?>
            <soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:bf="http://www.beautyfort.com/api/"><soap:Header>
                <bf:AuthHeader>
                    <bf:Username>%s</bf:Username>
                    <bf:Nonce>%s</bf:Nonce>
                    <bf:Created>%s</bf:Created>
                    <bf:Password>%s</bf:Password>
                </bf:AuthHeader>
            </soap:Header>
            <soap:Body>
                <bf:GetAccountInformationRequest> GetAccountInformationRequestType
                    <bf:TestMode>true</bf:TestMode>
                    <AccountInformationTypes>
                        <AccountInformationType>Brands</AccountInformationType>
                        <AccountInformationType>ProductTypes</AccountInformationType>
                        <AccountInformationType>Categories</AccountInformationType>
                        <AccountInformationType>Genders</AccountInformationType>
                    </AccountInformationTypes>
                </bf:GetAccountInformationRequest>
            </soap:Body></soap:Envelope>
        """ % (USERNAME, self.nounce, self.created_at, self.password)

        headers = {'Content-Type': 'application/xml'}
        res = requests.post(self.url, data=xml, headers=headers).text
        
        with open('account.xml', 'w') as f:
            f.write(res)

    def import_metadata(self):
        xmlstr = ''
        with open('account.xml', 'r', encoding="utf-8") as f:
            xmlstr = f.read()

        tree = etree.HTML(xmlstr.split('<SOAP-ENV:Body>')[1].split('</SOAP-ENV:Body>')[0])
        # save categories
        categories = tree.xpath("//categories//category")
        for category in categories[:1]:
            cid = category.xpath(".//id/text()")[0]
            name = category.xpath(".//name/text()")[0]
            entry = Category(uid=cid, name=name)
            entry.save()
        t = Category.select().execute()

        brands = tree.xpath("//brands//brand")
        for brand in brands:
            cid = brand.xpath(".//id/text()")[0]
            name = brand.xpath(".//name/text()")[0]
            entry = Brand(uid=cid, name=name)
            entry.save()

        producttypes = tree.xpath("//producttypes//producttype")
        for producttype in producttypes:
            cid = producttype.xpath(".//id/text()")[0]
            name = producttype.xpath(".//name/text()")[0]
            entry = ProductType(uid=cid, name=name)
            entry.save()


def get_product_image(product_xml):
    tree = api.parse_res_to_xml(product_xml)
    products = tree.xpath("//items//item")
    product_image = ''
    product_thumbnail = ''
    for product in products:
        name = extract_first(product.xpath(".//name//text()"))
        if name == product_name:
            price = extract_first(product.xpath(".//amount//text()"))
            product_thumbnail = extract_first(product.xpath(".//thumbnailimageurl//text()"))
            product_image = extract_first(product.xpath(".//highresimageurl//text()"))

    return requests.get(product_thumbnail).content

def upload_product(api, product, variant):
    # save image
    if len(product.images) == 0:
        # pull product information from beautyfort
        product_xml = api.search_products(product_type, brand_name, stock_code)
        image_data = get_product_image(product_xml)

        image = shopify.Image({ 'product_id': product.id })
        image.attach_image(image_data, filename=product.name.replace(' ', '_'))
        image.save()

        product.images = [image]
        variant.image = image
        product.save()


if __name__ == "__main__":
    # Initialize db
    initialize_db()

    ## create api instance
    api = BeautyFort(SECRET_KEY)

    # read xlsx file from shopify
    df = pd.read_excel('./shopify.xlsx', index_col=0)

    idx = 0
    for index, selected_row in df.iterrows():
        product_type = selected_row[1]
        brand_name = selected_row[2]
        product_name = selected_row[3]
        stock_code = selected_row[4]

        # Create or update product
        res = shopify.Product().find(title=product_name)
        if len(res) > 0:
            product = res[0]
            variants = product.variants
            if len(variants) == 1:
                variant = variants[0]
                variant.compare_at_price = selected_row[5]
                variant.inventory_quantity = selected_row[6]
                variant.sku = product_name.replace(' ', '-')
                variant.save()
                product.variants = [variant]
                inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
                inventory_item.cost = selected_row[7]
                inventory_item.country_code_of_origin = 'GB'
                inventory_item.sku = stock_code
                inventory_item.tracked = True
                inventory_item.save()

                inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
                if len(inventory_levels) > 0:
                    inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
                                        available=str(selected_row[6]),
                                        location_id=str(inventory_levels[0].location_id))

            product.product_type = product_type
            product.vendor = selected_row[0]
            product.save()

            # save image
            # if len(product.images) == 0:
            #     # pull product information from beautyfort
            #     product_xml = api.search_products(product_type, brand_name, stock_code)
            #     image_data = get_product_image(product_xml)

            #     image = shopify.Image({ 'product_id': product.id })
            #     image.attach_image(image_data, filename=product_name.replace(' ', '_'))
            #     image.save()

            #     product.images = [image]
            #     variant.image = image
            #     product.variants = [variant]
            #     product.save()
            print("Product is updated successfully. Id is {}!  ".format(product.id))
        else:
            # Create product
            product = shopify.Product()
            product.title = product_name
            product.vendor = selected_row[0]
            product.product_type = product_type

            variant = shopify.Variant()
            product.variants =[variant]
            variant.product_id = product.id
            # variant.price = selected_row[7]
            variant.compare_at_price = selected_row[5]
            variant.inventory_quantity = selected_row[6]
            variant.sku = product_name.replace(' ', '-')
            variant.fulfillment_service = 'manual'
            variant.inventory_management = 'shopify'
            product.save()
            # variant.save()


            variant = product.variants[0]
            inventory_item = shopify.InventoryItem().find(variant.inventory_item_id)
            inventory_item.cost = selected_row[7]
            inventory_item.country_code_of_origin = 'GB'
            inventory_item.sku = stock_code
            inventory_item.tracked = True
            inventory_item.save()

            inventory_levels = shopify.InventoryLevel().find(inventory_item_ids=variant.inventory_item_id)
            if len(inventory_levels) > 0:
                inventory_levels[0].set(inventory_item_id=variant.inventory_item_id,
                                    available=str(selected_row[6]),
                                    location_id=str(inventory_levels[0].location_id))

            # save image
            # if len(product.images) == 0:
            #     # pull product information from beautyfort
            #     product_xml = api.search_products(product_type, brand_name, stock_code)
            #     image_data = get_product_image(product_xml)

            #     image = shopify.Image({ 'product_id': product.id })
            #     image.attach_image(image_data, filename=product_name.replace(' ', '_'))
            #     image.save()

            #     product.images = [image]
            #     variant.image = image
            #     product.variants = [variant]
            #     product.save()
            print("Product is saved successfully. Id is {}!  ".format(product.id))
