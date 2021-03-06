"""
Functions for scraping bricklink.com
"""
import re
import urllib

from bs4 import BeautifulSoup as BS

import color
import utils


def price_guide(item, max_cost_quantile=None):
  """Fetch pricing info for an item"""
  results = []

  if (item['ItemTypeID'] == 'P' and 'stk0' in item['ItemID']) or \
      item['ItemTypeID'] == 'S' or \
      item['ItemTypeID'] == 'M':
    # a sticker sheet, a set, or a minifigure
    color_ids = [0]
  else:
    # a normal item
    color_ids = color.similar_to(item['ColorID'])

  for c in color_ids:
    # perform HTTP request
    parameters = {
        'itemType': item['ItemTypeID'],
        'itemNo': item['ItemID'],
        'itemSeq': 1,
        'colorId': c,
        'v': 'P',
        'priceGroup': 'Y',
        'prDec': 2
    }
    url = "http://www.bricklink.com/catalogPG.asp?" + urllib.urlencode(parameters)
    html = urllib.urlopen(url).read()

    # parse page
    page = BS(html)

    if len(page.find_all(text='Currently Available')) == 0:
      # not available in this color :(
      continue
    else:

      # newly found inventory
      new = []

      for td in page.find_all('td'):
        if td.find('a', recursive=False, href=re.compile('/store.asp')) is not None:
          # find the td element with a link to a store. Its siblings contain
          # the interesting bits like price and quantity available
          store_url = td.find('a')['href']
          store_id = int(utils.get_params(store_url)['sID'])
          quantity = int(td.next_sibling.text)
          cost_per_unit = float(re.findall('[0-9.]+',
                                td.next_sibling.next_sibling.text)[0])

          new.append({
            'item_id': item['ItemID'],
            'wanted_color_id': item['ColorID'],
            'color_id': c,
            'store_id': store_id,
            'quantity_available': quantity,
            'cost_per_unit': cost_per_unit
          })

      # remove items that cost too much
      if max_cost_quantile is not None and max_cost_quantile < 1.0:
        observed_prices = [e['quantity_available'] * [e['cost_per_unit']] for e in new]
        observed_prices = list(sorted(utils.flatten(observed_prices)))
        if len(observed_prices) > 0:
          i = utils.quantile(len(observed_prices)-1, max_cost_quantile)
          max_price = observed_prices[i]
          new = filter(lambda x: x['cost_per_unit'] <= max_price, new)

      # add what's left to the considered inventory
      results.extend(new)

    if sum(e['quantity_available'] for e in results) >= item['Qty']:
      # stop early, we've got everything we need
      return results

  return results


def store_info(country=None):
  """Fetch metadata for all stores"""
  browse_page = utils.beautiful_soup('http://www.bricklink.com/browse.asp')
  country_links = (
    browse_page
    .find(text='Stores:').parent.parent.next_sibling
    .find_all('a', href=re.compile('countryID'))
  )

  result = []

  for country_link in country_links:
    country_name = country_link.text
    country_id = utils.get_params(country_link['href'])['countryID']

    # skip this country link if we're only gathering data on one country
    if country is not None and country_id != country:
      continue

    country_page = utils.beautiful_soup('http://www.bricklink.com' + country_link['href'])
    store_links = country_page.find_all('a', href=re.compile('store.asp'))

    for store_link in store_links:
      store_page = utils.beautiful_soup('http://www.bricklink.com' + '/' + store_link['href'])
      params = utils.get_params(store_page.find('frame', src=re.compile('^storeTop.asp'))['src'])

      store_name = params['storeName']
      store_id = params['uID']
      country_name = params['cn']
      country_id = params['c']
      seller_name = params['p_seller']
      feedback = params['p_feedback']

      store_splash = utils.beautiful_soup("http://www.bricklink.com/storeSplash.asp?uID=" + store_id)
      min_buy_elem = store_splash.find(text="Minimum Buy:")
      if min_buy_elem is not None:
        min_buy = min_buy_elem.parent.parent.parent.parent.next_sibling.find("font").text
        try:
          min_buy = re.search("US \$([0-9.]+)", min_buy).group(1)
          min_buy = float(min_buy)
        except AttributeError:
          # there's a minimum buy in a foreign currency :(
          continue
      else:
        min_buy = 0.0

      ships_to_elem = store_splash.find(text="Store Ships To:")
      if ships_to_elem is not None:
        ships = ships_to_elem.parent.parent.parent.parent.next_sibling.find_all(text=True)
        ships = map(lambda x: unicode(x), ships)
      else:
        ships = []


      entry = {
        'store_name': store_name,
        'store_id': int(store_id),
        'country_name': country_name,
        'country_id': country_id,
        'seller_name': seller_name,
        'feedback': int(feedback),
        'minimum_buy': min_buy,
        'ships': ships
      }
      print entry

      result.append(entry)

  return result

ALL_COUNTRIES = [
  "Argentina",
  "Australia",
  "Austria",
  "Belarus",
  "Belgium",
  "Bolivia",
  "Bosnia and Herzegovina",
  "Brazil",
  "Bulgaria",
  "Canada",
  "Chile",
  "China",
  "Croatia",
  "Czech Republic",
  "Denmark",
  "Ecuador",
  "El Salvador",
  "Estonia",
  "Finland",
  "France",
  "Germany",
  "Greece",
  "Guatemala",
  "Hong Kong",
  "Hungary",
  "Iceland",
  "India",
  "Indonesia",
  "Ireland",
  "Israel",
  "Italy",
  "Japan",
  "Jordan",
  "Latvia",
  "Lithuania",
  "Luxembourg",
  "Macau",
  "Malaysia",
  "Mexico",
  "Monaco",
  "Netherlands",
  "New Zealand",
  "Norway",
  "Pakistan",
  "Philippines",
  "Poland",
  "Portugal",
  "Romania",
  "Russia",
  "San Marino",
  "Serbia",
  "Singapore",
  "Slovakia",
  "Slovenia",
  "South Africa",
  "South Korea",
  "Spain",
  "Sweden",
  "Switzerland",
  "Syria",
  "Taiwan",
  "Thailand",
  "Trinidad and Tobago",
  "Turkey",
  "Ukraine",
  "United Kingdom",
  "USA",
  "Venezuela"
]
