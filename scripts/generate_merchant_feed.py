#!/usr/bin/env python3
import html
import os
import re
from html.parser import HTMLParser
from xml.etree.ElementTree import Element, SubElement, ElementTree, register_namespace

import requests

SHOP = os.environ.get('SHOPIFY_SHOP', 'carokazmada-store.myshopify.com')
TOKEN = os.environ.get('SHOPIFY_ADMIN_TOKEN', '')
API_VERSION = os.environ.get('SHOPIFY_API_VERSION', '2025-07')
OUT = os.environ.get('MERCHANT_FEED_OUTPUT', 'feeds/carokaz-merchant-mg.xml')
BASE = 'https://carokazmada.com'

QUERY = '''query {
  products(first: 50, query: "status:ACTIVE") {
    nodes {
      title handle descriptionHtml onlineStoreUrl vendor productType
      featuredImage { url altText }
      variants(first: 1) { nodes { price } }
    }
  }
}'''

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
    def handle_data(self, data):
        self.parts.append(data)

def plain_text(value):
    parser = TextParser()
    parser.feed(value or '')
    return re.sub(r'\s+', ' ', html.unescape(' '.join(parser.parts))).strip()

def brand_for(title, vendor):
    if vendor and vendor.strip():
        return vendor.strip()
    names = [('CITROËN', 'Citroën'), ('TOYOTA', 'Toyota'), ('VOLKSWAGEN', 'Volkswagen'),
             ('PORSCHE', 'Porsche'), ('MAZDA', 'Mazda'), ('MITSUBISHI', 'Mitsubishi'),
             ('FORD', 'Ford'), ('HYUNDAI', 'Hyundai'), ('BMW', 'BMW')]
    upper = (title or '').upper()
    for prefix, label in names:
        if upper.startswith(prefix):
            return label
    return ''

if not TOKEN:
    raise SystemExit('SHOPIFY_ADMIN_TOKEN absent; feed refresh deferred')

response = requests.post(
    f'https://{SHOP}/admin/api/{API_VERSION}/graphql.json',
    headers={'X-Shopify-Access-Token': TOKEN, 'Content-Type': 'application/json'},
    json={'query': QUERY}, timeout=60)
response.raise_for_status()
payload = response.json()
if payload.get('errors'):
    raise SystemExit(str(payload['errors']))
products = payload.get('data', {}).get('products', {}).get('nodes', [])

G = 'http://base.google.com/ns/1.0'
register_namespace('g', G)
root = Element('rss', {'version': '2.0'})
channel = SubElement(root, 'channel')
SubElement(channel, 'title').text = 'Carokaz Mada — Véhicules d’occasion à Madagascar'
SubElement(channel, 'link').text = BASE + '/collections/vehicules-disponibles'
SubElement(channel, 'description').text = 'Véhicules d’occasion disponibles à Antananarivo et Madagascar.'
count = 0
for product in products:
    title = (product.get('title') or '').strip()
    handle = product.get('handle') or ''
    image = product.get('featuredImage') or {}
    variants = (product.get('variants') or {}).get('nodes') or []
    price = variants[0].get('price') if variants else None
    if not title or not handle or not image.get('url') or price is None:
        continue
    description = plain_text(product.get('descriptionHtml'))
    description = (description + ' Voiture d’occasion à Antananarivo, Madagascar. Contact Carokaz Mada : +261 38 84 241 38.')[:4990]
    item = SubElement(channel, 'item')
    fields = {
        'id': 'carokaz-' + handle,
        'title': title[:150],
        'description': description,
        'link': product.get('onlineStoreUrl') or f'{BASE}/products/{handle}',
        'image_link': image['url'],
        'availability': 'in_stock',
        'condition': 'used',
        'price': f'{float(price):.2f} MGA',
        'identifier_exists': 'no',
        'custom_label_0': product.get('productType') or 'Véhicule d’occasion',
    }
    for key, value in fields.items():
        SubElement(item, f'{{{G}}}{key}').text = value
    brand = brand_for(title, product.get('vendor'))
    if brand:
        SubElement(item, f'{{{G}}}brand').text = brand
    count += 1

os.makedirs(os.path.dirname(OUT) or '.', exist_ok=True)
ElementTree(root).write(OUT, encoding='utf-8', xml_declaration=True)
print(f'Generated {OUT} with {count} products')
