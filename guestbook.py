#!/usr/bin/env python
#Author: Amit Dhamne

# [START imports]
import os
import urllib
import hashlib

from google.appengine.api import users
from google.appengine.ext import ndb

import jinja2
import webapp2
#following loads jinja2
JINJA_ENVIRONMENT = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)
# [END imports]

DEFAULT_CATEGORY_NAME = 'red' #you have to change this
DEFAULT_CART_NAME = 'default_cart' #existing cart
# We set a parent key on the 'Greetings' to ensure that they are all
# in the same entity group. Queries across the single entity group
# will be consistent. However, the write rate should be limited to
# ~1/second. -Strongly consistent

def category_key(guestbook_name=DEFAULT_CATEGORY_NAME): #Stores wines to buy per category
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('Guestbook', guestbook_name)

def cart_key(cart_name=DEFAULT_CART_NAME): #Stores wines cart per user
    return ndb.Key('Cartbook', cart_name)

def purchase_key(cart_name): #Stores wine purchases per user
    return ndb.Key('Purchasebook', cart_name)

def bid_key(category_name=DEFAULT_CATEGORY_NAME): #Database for all wines available for bidding
    return ndb.Key('Wines_to_bid_book',category_name)

def bid_cart_key(wine_id): #Registry of bids per wine
    return ndb.Key('Registered_bids_book', wine_id)

def compute_hash(wine):
    return str(hashlib.md5( wine.country.lower() + wine.region.lower() + wine.variety.lower() + wine.winery.lower() + str(wine.year) + str(wine.price)).hexdigest())
# [START wine info]
class Author(ndb.Model):
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Wine(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    wine_id = ndb.StringProperty(indexed=True) #Hash the value of country+region+variety+winery+year+
    country = ndb.StringProperty(indexed=True)
    region = ndb.StringProperty(indexed=True)
    variety = ndb.StringProperty(indexed=True)
    winery = ndb.StringProperty(indexed=True)
    year = ndb.StringProperty(indexed=True)
    price = ndb.FloatProperty(indexed=True)
    category = ndb.StringProperty(indexed=True)
    quantity_available = ndb.IntegerProperty(indexed=False)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)

class Cart(ndb.Model):
    author = ndb.StructuredProperty(Author)
    wine = ndb.StructuredProperty(Wine, indexed=True)
    quantity_to_buy = ndb.IntegerProperty(indexed=False)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)

class Bid(ndb.Model):
    wine = ndb.StructuredProperty(Wine, indexed=True)
    highest_bid = ndb.FloatProperty(indexed=True) #First Query BidCart for highest bid and if nil then make highest bid equal to price
    time_started = ndb.TimeProperty(auto_now_add=True)
    date_started = ndb.DateProperty(auto_now_add=True)
    date_end = ndb.DateProperty()
    time_end = ndb.TimeProperty()

class BidCart(ndb.Model):
    bid = ndb.StructuredProperty(Bid, indexed=True)
    bidder = ndb.StructuredProperty(Author)
    bid_price = ndb.FloatProperty(indexed=True)
    quantity_to_bid = ndb.IntegerProperty(indexed=True)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)

class MainPage(webapp2.RequestHandler): #displays main page
    def get(self):
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        template_values = {
        'user': user,
        'url':url,
        'url_linktext': url_linktext,
        }
        template = JINJA_ENVIRONMENT.get_template('main.html') #prints html
        self.response.write(template.render(template_values)) # renders output, response

class DisplayPage(webapp2.RequestHandler): #displays individual category page
    def get(self):
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME).lower()
        wine_query = Wine.query(ancestor = category_key(category_name)).order(-Wine.date)
        error_sign_in = self.request.get('error_sign_in',False)
        wines = wine_query.fetch()
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            default_cart_name = users.get_current_user().user_id()

        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
            default_cart_name = DEFAULT_CART_NAME
        cart_name = self.request.get('cart_name', default_cart_name)
        template_values = {
        'user': user,
        'error_sign_in':error_sign_in,
        'category_name': category_name,
        'wines': wines,
        'cart_name': cart_name,
        'url_linktext':url_linktext,
        'url':url,
        }
        template = JINJA_ENVIRONMENT.get_template('wine_info.html')
        self.response.write(template.render(template_values))


    def post(self):
        user = users.get_current_user()
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME).lower()
        if user:
            cart_name = self.request.get('cart_name', user.user_id())
            cart_query = Cart.query(ancestor = cart_key(user.user_id())).order(-Cart.date)
            carts = cart_query.fetch()
            entry_exists=False
            wine = Wine()
            wine.country = self.request.get('country')
            wine.variety = self.request.get('variety')
            wine.region = self.request.get('region')
            wine.winery = self.request.get('winery')
            wine.year = self.request.get('year')
            wine.price = float(self.request.get('price'))
            quantity = int(self.request.get('quantity'))
            wine.wine_id = self.request.get('wine_id')
            wine.category = category_name

            wines_query = Wine.query(ancestor=category_key(category_name)).filter(ndb.GenericProperty("wine_id")==wine.wine_id) #Pull out the latest quantity available
            wines = wines_query.fetch()
            print "************* PRINTING WINE IDS ************"
            for item in wines:
                print item.wine_id
            for cart in carts:
                if cart.wine.winery == wine.winery:
                    if cart.wine.variety == wine.variety:
                        if cart.wine.region == wine.region:
                            if str(cart.wine.price) == str(wine.price):
                                if cart.wine.year == wine.year:
                                    if cart.wine.country == wine.country:
                                        cart_to_modify = cart.key.get()
                                        if (cart_to_modify.quantity_to_buy + quantity) >= wines[0].quantity_available : #if quantity available is less than the cart quantity
                                            cart_to_modify.quantity_to_buy =wines[0].quantity_available
                                        else:
                                            cart_to_modify.quantity_to_buy +=quantity
                                        cart_to_modify.put()
                                        entry_exists=True
            if not entry_exists:
                cart = Cart(parent=cart_key(cart_name))
                cart.author = Author(
                    identity=user.user_id(),
                    email=user.email()
                    )
                cart.wine = wine
                cart.quantity_to_buy = quantity
                cart.put()
            query_params = {'cart_name': cart_name,
            'category_name':category_name}
            self.redirect('/display?'+urllib.urlencode(query_params))
        else:
            query_params = {'error_sign_in':True,
            'category_name':category_name}
            self.redirect('/display?'+urllib.urlencode(query_params))

class BidPage(webapp2.RequestHandler):

    def get(self):
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME).lower()
        wines_to_bid_query = Bid.query(ancestor = bid_key(category_name)).order(-Bid.date_started).order(-Bid.time_started)
        error_sign_in = self.request.get('error_sign_in',False)
        wines_to_bid = wines_to_bid_query.fetch()
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
            default_cart = users.get_current_user().user_id()
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        #Add Bidding Cart
        template_values = {
        'user': user,
        'error_sign_in': error_sign_in,
        'category_name': category_name,
        'bids': wines_to_bid,
        'url_linktext':url_linktext,
        'error_sign_in':error_sign_in,
        'url':url,
        }
        template = JINJA_ENVIRONMENT.get_template('bidding_page.html')
        self.response.write(template.render(template_values))

    def post(self):
        user = users.get_current_user()
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME).lower()
        if user:
            wine = Wine()
            wine.country = self.request.get('country')
            wine.variety = self.request.get('variety')
            wine.region = self.request.get('region')
            wine.winery = self.request.get('winery')
            wine.year = self.request.get('year')
            wine.price = float(self.request.get('price'))
            wine.wine_id = self.request.get('wine_id')
            wine.category = category_name
            quantity_to_bid = int(self.request.get('quantity'))
            bid_price = float(self.request.get('bid_price'))
            highest_bid = float(self.request.get('highest_bid'))
            bid_cart = BidCart(parent=bid_cart_key(wine_id))
            if highest_bid < bid_price:
                highest_bid = bid_price
                bid_query = Bid.query(ancestor = category_key(category_name.lower()))
                items = bid_query.fetch()
                for item in items:
                    if wine.wine_id == item.wine.wine_id:
                        item_to_modify = item.key.get()
                        item_to_modify.highest_bid = bid_price
                        item_to_modify.put()
                        break
            bid = Bid(wine=wine,
                highest_bid=highest_bid)
            bid_cart.bid =  bid
            bid.bidder = Author(identity=user.user_id(),email=user.email())
            bid.bid_price = bid_price
            bid.quantity_to_bid = quantity_to_bid
            bid.put()
        else:
            query_params ={'error_sign_in':True,
            'category_name':category_name}
            self.redirect('/bidding?'+ urllib.urlencode(query_params))

class SearchAddPage(webapp2.RequestHandler):

    def post(self):
        user = users.get_current_user()
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME).lower()

        if user:
            cart_name = user.user_id()
            cart_query = Cart.query(ancestor = cart_key(cart_name)).order(-Cart.date)
            carts = cart_query.fetch()
            entry_exists = False
            wine = Wine()
            wine.country = self.request.get('country')
            wine.variety = self.request.get('variety')
            wine.region = self.request.get('region')
            wine.winery = self.request.get('winery')
            wine.year = self.request.get('year')
            wine.price = float(self.request.get('price'))
            quantity = int(self.request.get('quantity'))
            wine.wine_id = self.request.get('wine_id')
            wine.category=category_name

            wines_query = Wine.query(ancestor=category_key(category_name)).filter(ndb.GenericProperty("wine_id")==wine.wine_id) #Pull out the latest quantity available
            wines = wines_query.fetch()

            for cart in carts:
                if cart.wine.winery == wine.winery:
                    if cart.wine.variety == wine.variety:
                        if cart.wine.region == wine.region:
                            if str(cart.wine.price) == str(wine.price):
                                if cart.wine.year == wine.year:
                                    if cart.wine.country == wine.country:
                                        cart_to_modify = cart.key.get()
                                        if (cart_to_modify.quantity_to_buy + quantity) >= wines[0].quantity_available : #if quantity available is less than the cart quantity
                                            cart_to_modify.quantity_to_buy =wines[0].quantity_available
                                        else:
                                            cart_to_modify.quantity_to_buy +=quantity
                                        cart_to_modify.put()
                                        entry_exists=True
            if not entry_exists:
                cart = Cart(parent=cart_key(cart_name))
                cart.author = Author(
                    identity = user.user_id(),
                    email = user.email()
                    )
                cart.wine = wine
                cart.quantity_to_buy = quantity
                cart.put()
            query_params = {'cart_name': cart_name,
            'category_name':category_name}
            self.redirect('/search?'+urllib.urlencode(query_params))

        else:
            error_sign_in = True
            query_params = {'error_sign_in':error_sign_in,
            'category_name':category_name}
            self.redirect('/search?'+urllib.urlencode(query_params))

class InfoPage(webapp2.RequestHandler): # adds info
    def get(self, error=False):
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME)
        template_values = {
        'category_name': category_name,
        'error': error,
        }
        template = JINJA_ENVIRONMENT.get_template('index.html') #prints html
        self.response.write(template.render(template_values)) # renders output, response

    def post(self):
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME)
        wine = Wine(parent = category_key(category_name.lower()))

        wine.country = self.request.get('country')
        wine.variety = self.request.get('variety')
        wine.region = self.request.get('region')
        wine.winery = self.request.get('winery')
        wine.year = self.request.get('year')
        wine.category = category_name
        wine.price = float(self.request.get('price'))
        wine.quantity_available = int(self.request.get('quantity_available'))
        wine.wine_id = compute_hash(wine)
        print "***** WINE ID: "+wine.wine_id
        if wine.country and wine.year and wine.region and wine.variety and wine.winery and wine.price and wine.quantity_available:
            wine.put()
            query_params = {'category_name': category_name}
            self.redirect('/?'+ urllib.urlencode(query_params))

        else :
            self.get(True)

class SearchPage(webapp2.RequestHandler): #displays search and search page
    def get(self, error_empty_fields=False, error_no_result=False):
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME).lower()
        user = users.get_current_user()
        error_sign_in = self.request.get('error_sign_in')
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        template_values = {
        'user':user,
        'error_sign_in':error_sign_in,
        'category_name': category_name,
        'error_empty_fields': error_empty_fields,
        'error_no_result': error_no_result,
        'url_linktext':url_linktext,
        'url':url,
        }
        template = JINJA_ENVIRONMENT.get_template('search.html')
        self.response.write(template.render(template_values))

    def post(self):
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME).lower()
        user = users.get_current_user()
        if user:
            url = users.create_logout_url(self.request.uri)
            url_linktext = 'Logout'
        else:
            url = users.create_login_url(self.request.uri)
            url_linktext = 'Login'
        country = self.request.get('country').lower()
        variety = self.request.get('variety').lower()
        region = self.request.get('region').lower()
        winery = self.request.get('winery').lower()
        price = self.request.get('price')

        wines_query = Wine.query(ancestor = category_key(category_name))
        wines_all = wines_query.fetch()
        wines = []
        if not (country or variety or region or winery):
            self.get(True,False)
        else:
            for wine in wines_all:
                if country in wine.country.lower():
                    flag_country = True
                else:
                    flag_country = False
                if variety in wine.variety.lower():
                    flag_variety = True
                else:
                    flag_variety =  False
                if region in wine.region.lower():
                    flag_region = True
                else:
                    flag_region = False
                if winery in wine.winery.lower():
                    flag_winery = True
                else:
                    flag_winery = False
                if flag_winery and flag_country and flag_variety and flag_region:
                    wines.append(wine)
            if len(wines)==0:
                self.get(False,True)
            else:
                template_values = {
                    'wines': wines,
                    'category_name': category_name,
                    'user':user,
                    'url_linktext':url_linktext,
                    'url':url,
                }
                template = JINJA_ENVIRONMENT.get_template('search.html')
                self.response.write(template.render(template_values))


class CheckoutPage(webapp2.RequestHandler):
    def get(self, min_purchase=False):
        user = users.get_current_user()
        cart_name = self.request.get('cart_name', user.user_id())
        cart_query = Cart.query(ancestor= cart_key(cart_name)).order(-Cart.date)
        carts = cart_query.fetch()
        total_cost=0
        for cart in carts:
            if cart.quantity_to_buy:
                total_cost+=(cart.wine.price*cart.quantity_to_buy)
            else:
                total_cost+=cart.wine.price
        template_values = {
        'min_purchase': min_purchase,
        'user': user,
        'carts': carts,
        'total_cost': total_cost,
        'cart_name': cart_name,
        }
        template = JINJA_ENVIRONMENT.get_template('checkout.html')
        self.response.write(template.render(template_values))

    def post(self):
        user = users.get_current_user()
        cart_name = self.request.get('cart_name', user.user_id())
        cart_query = Cart.query(ancestor=cart_key(cart_name)).order(-Cart.date)
        carts = cart_query.fetch()
        if len(carts)==0:
            self.get(True)
        else:
            query_params = {'cart_name':cart_name}
            self.redirect('/confirmation?'+urllib.urlencode(query_params))
        """cart_purchased_query = Cart.query(ancestor=purchase_key(cart_name)).order(-Cart.date)#debugging Debug
           purchased_carts = cart_purchased_query.fetch()
           for cart in purchased_carts:
           print "Email: "+ cart.author.email+ " Price: " + str(cart.wine_items.wine.price) +" Winery: " +str(cart.wine_items.wine.winery) + " Date: " +str(cart.date) + " Time: " +str(cart.time)"""

class DeleteCart(webapp2.RequestHandler):
    def post(self):
        user = users.get_current_user()
        cart_name = self.request.get('cart_name',user.user_id())
        cart_query = Cart.query(ancestor=cart_key(cart_name)).order(-Cart.date)
        carts = cart_query.fetch()
        for cart in carts:
            if str(cart.quantity_to_buy) == str(self.request.get('quantity')):
                if cart.wine.winery == self.request.get('winery'):
                    if cart.wine.variety == self.request.get('variety'):
                        if str(cart.wine.price) == str(self.request.get('price')):
                            if cart.wine.region == self.request.get('region'):
                                if cart.wine.year == self.request.get('year'):
                                    if cart.wine.country == self.request.get('country'):
                                        cart.key.delete()
                                        break
        query_params = {'cart_name':cart_name}
        self.redirect('/checkout?'+urllib.urlencode(query_params))

class ConfirmPage(webapp2.RequestHandler):
    def get(self):
        user = users.get_current_user()
        cart_name = self.request.get('cart_name',user.user_id())
        cart_query = Cart.query(ancestor=cart_key(cart_name)).order(-Cart.date)
        carts = cart_query.fetch()
        total_cost=0

        for cart in carts:
            if cart.quantity_to_buy:
                total_cost+=(cart.wine.price*cart.quantity_to_buy)
            else:
                total_cost+=cart.wine.price

        for cart in carts:
            cart_purchased = Cart(parent=purchase_key(cart_name))
            cart_purchased.author = Author(identity=user.user_id(),email=user.email())

            cart_purchased.wine = Wine( country=cart.wine.country,
            region= cart.wine.region,
            winery= cart.wine.winery,
            variety= cart.wine.variety,
            price= cart.wine.price,
            year= cart.wine.year,
            category=cart.wine.category,
            wine_id = cart.wine.wine_id)

            cart_purchased.quantity_to_buy=cart.quantity_to_buy
            cart_purchased.put() #Confirmed Purchase

            wine_query = Wine.query(ancestor=category_key(cart.wine.category)).filter(ndb.GenericProperty("wine_id")==cart.wine.wine_id)
            wines = wine_query.fetch()
            wine_entry_to_modify = wines[0].key.get()

            wine_entry_to_modify.quantity_available -= cart.quantity_to_buy #Deduct from the total available quantity

            if wine_entry_to_modify.quantity_available==0: #Quantity becomes 0 then remove item from db
                wines[0].key.delete()

            elif wine_entry_to_modify.quantity_available <= (0.25*wine_entry_to_modify.price): #Calculate the threshold and add to the bid
                bid = Bid(parent = bid_key(cart.wine.category))
                bid.wine = Wine(country=cart.wine.country,
                region= cart.wine.region,
                winery= cart.wine.winery,
                variety= cart.wine.variety,
                price= cart.wine.price,
                year= cart.wine.year,
                category=cart.wine.category,
                quantity_available=wine_entry_to_modify.quantity_available,
                wine_id = cart.wine.wine_id)
                bid.highest_bid = cart.wine.price
                #add datetime (ends)
                bid.put()
                wines[0].key.delete()

            else:
                wine_entry_to_modify.put()

        template_values = {
        'user':user,
        'carts':carts,
        'total_cost':total_cost,
        'cart_name':cart_name,
        'time':cart.time,
        'date':cart.date
        }
        template = JINJA_ENVIRONMENT.get_template('thank.html')
        self.response.write(template.render(template_values))
        for cart in carts:
            cart.key.delete()


# [START app]
app = webapp2.WSGIApplication([
    ('/', MainPage),
    ('/display', DisplayPage),
    ('/enter', InfoPage),
    ('/search', SearchPage),
    ('/checkout', CheckoutPage),
    ('/search_add_cart',SearchAddPage),
    ('/delete_cart',DeleteCart),
    ('/confirmation',ConfirmPage),
    ('/bidding',BidPage),
], debug=True)
# [END app]
