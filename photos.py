"""
Shows basic usage of the Photos v1 API.
Creates a Photos v1 API service and prints the names and ids of the last 10 albums
the user has access to.
"""
from __future__ import print_function
import os 
import pickle
import json
import time

import requests
from peewee import *
import pandas as pd
import shopify
import google_auth_httplib2  # This gotta be installed for build() to work
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

from env import *

import pdb


base_dir = os.path.dirname(os.path.abspath(__file__))
db = SqliteDatabase(base_dir+'/app.db')

# define tables
class BaseModel(Model):
    class Meta:
        database = db


class ProductImage(BaseModel):
    product_id = TextField(default='')
    name = TextField()
    image = TextField(default='')
    description = TextField()


def initialize_db():
    db.connect()
    db.drop_tables([ProductImage,], safe = True)
    db.create_tables([ProductImage,], safe = True)
    db.close()


# Setup the Photo v1 API
SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']


def getMediaItems(service, pageToken=None):
    if pageToken != None:
        results = service.mediaItems().list(
            pageSize=100, pageToken=pageToken).execute()
    else:
        results = service.mediaItems().list(pageSize=100).execute()

    media_items = results.get('mediaItems', [])
    for media in media_items:
        filename = media['filename'][:-4] if len(media['filename']) > 4 else 'no_data*'
        mime_type = media['mimeType']
        image_url = media['baseUrl']

        if 'image' in mime_type:
            try:
                entry = ProductImage.get(ProductImage.name==filename)
                entry.image = image_url
                entry.save()
                print(filename, "   @@@ \n")
            except:
                pass

    if 'nextPageToken' not in results or not results['nextPageToken'] or results['nextPageToken'] == '':
        return
    else:
        getMediaItems(service, results['nextPageToken'])

def upload_product(product, variant, entry):
    # save image
    if len(product.images) == 0 and entry.image != '' and entry.image != None:
        try:
            image_data = requests.get(entry.image).content

            image = shopify.Image({ 'product_id': product.id })
            image.attach_image(image_data, filename=entry.name.replace(' ', '_'))
            image.save()

            product.images = [image]
            variant.image = image
            product.save()
        except:
            print("image upload issue: {}, product_image: {}".format(product.id, entry.image))
        time.sleep(1)


if __name__ == "__main__":
    initialize_db()

    shop_url = "https://%s:%s@%s.myshopify.com/admin" % (SHOPIFY_API_KEY, SHOPIFY_PASSWORD, SHOP_NAME)
    shopify.ShopifyResource.set_site(shop_url)

    # read xlsx file from shopify
    df = pd.read_excel('./Liporia_Master.xlsx', index_col=0)

    idx = 0
    for index, selected_row in df.iterrows():
        product_name = index.strip()
        if product_name[-1] == ',':
            product_name = product_name[:-1]

        try:
            entry = ProductImage.get(ProductImage.name==product_name)
        except:
            entry = ProductImage(name=product_name)

        try:
            if 'lh3.googleusercontent.com' in selected_row['Image source']:
                entry.image = selected_row['Image source']
        except:
            pass
        entry.save()


    creds = None
    if(os.path.exists("token.pickle")):
        with open("token.pickle", "rb") as tokenFile:
            creds = pickle.load(tokenFile)
    if not creds or not creds.valid:
        if (creds and creds.expired and creds.refresh_token):
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
            creds = flow.run_local_server(port = 0)
        with open("token.pickle", "wb") as tokenFile:
            pickle.dump(creds, tokenFile)
    service = build('photoslibrary', 'v1', credentials = creds)

    getMediaItems(service)

    print("~~~~~~~~~~~~~~~~~~ Download Done ~~~~~~~")

    dbrows = ProductImage.select()
    idx = 0

    with open('photo_uploads_error.txt', 'w') as f:
        for entry in dbrows:
            print("index: {}".format(idx))
            try:
                if entry.image != None and entry.image != '':
                    res = shopify.Product().find(title=entry.name)
                    if len(res) > 0:
                        product = res[0]
                        variants = product.variants
                        if len(variants) > 0:
                            variant = variants[0]
                            time.sleep(1)
                            try:
                                upload_product(product, variant, entry)
                            except:
                                upload_product(product, variant, entry)
                            print("Product {} is successfully updated".format(product.id))
                else:
                    f.write('{}{}'.format(entry.name, ','))
                    f.write('\n')
            except Exception as ee:
                print(str(ee))
            idx = idx + 1
        f.close()


