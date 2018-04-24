#!/usr/bin/env python
#Author: Amit Dhamne

# [START imports]
import os
import urllib

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

def category_key(guestbook_name=DEFAULT_CATEGORY_NAME):
    """Constructs a Datastore key for a Guestbook entity.

    We use guestbook_name as the key.
    """
    return ndb.Key('Guestbook', guestbook_name)

def cart_key(cart_name=DEFAULT_CART_NAME):
    return ndb.Key('Cartbook', cart_name)

def purchase_key(cart_name):
    return ndb.Key('Purchasebook', cart_name)

def bid_key(cart_name):
    return ndb.Key('Bidbook',cart_name)

# [START wine info]
class Author(ndb.Model):
    identity = ndb.StringProperty(indexed=False)
    email = ndb.StringProperty(indexed=False)

class Wine(ndb.Model):
    """A main model for representing an individual Guestbook entry."""
    country = ndb.StringProperty(indexed=True)
    region = ndb.StringProperty(indexed=True)
    variety = ndb.StringProperty(indexed=True)
    winery = ndb.StringProperty(indexed=True)
    year = ndb.StringProperty(indexed=True)
    price = ndb.FloatProperty(indexed=True)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)

# [END wine info]
class Wine_Items(ndb.Model):
    wine = ndb.StructuredProperty(Wine)
    quantity = ndb.IntegerProperty(indexed=False)

class Cart(ndb.Model):
    author = ndb.StructuredProperty(Author)
    wine_items = ndb.StructuredProperty(Wine_Items, indexed=True)
    date = ndb.DateProperty(auto_now_add=True)
    time = ndb.TimeProperty(auto_now_add=True)
# [START main_page]

class Bid(ndb.model):
    highest_bidder = ndb.StructuredProperty(Author)
    wine_items = ndb.StructuredProperty(Wine_Items, indexed=True)
    time_started = ndb.TimeProperty(auto_now_add=True)
    date_started = ndb.DateProperty(auto_now_add=True)
    date_end = ndb.DateProperty(auto_now_add=True)
    time_end = ndb.TimeProperty(auto_now_add=True)
    bid_price = ndb.FloatProperty(auto_now_add=True)
    quantity = ndb.IntegerProperty(auto_now_add=True)
    quantity_available = ndb.IntegerProperty(auto_now_add=True)

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
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME)
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
        'cart_name': cart_name,''
        'url_linktext':url_linktext,
        'url':url,
        }
        template = JINJA_ENVIRONMENT.get_template('wine_info.html')
        self.response.write(template.render(template_values))


    def post(self):
        user = users.get_current_user()
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME)
        if user:
            cart_name = self.request.get('cart_name', user.user_id())
            cart_query = Cart.query(ancestor = cart_key(user.user_id())).order(-Cart.date)
            carts = cart_query.fetch()
            entry_exists=False
            country = self.request.get('country')
            variety = self.request.get('variety')
            region = self.request.get('region')
            winery = self.request.get('winery')
            year = self.request.get('year')
            price = float(self.request.get('price'))
            quantity = int(self.request.get('quantity'))
            for cart in carts:
                if cart.wine_items.wine.winery == winery:
                    if cart.wine_items.wine.variety == variety:
                        if cart.wine_items.wine.region == region:
                            if str(cart.wine_items.wine.price) == str(price):
                                if cart.wine_items.wine.year == year:
                                    if cart.wine_items.wine.country == country:
                                        cart_to_modify = cart.key.get()
                                        cart_to_modify.wine_items.quantity +=quantity
                                        cart_to_modify.put()
                                        entry_exists=True
            if not entry_exists:
                cart = Cart(parent=cart_key(cart_name))
                cart.author = Author(
                identity=user.user_id(),
                email=user.email()
                )
                cart.wine_items = Wine_Items()
                cart.wine_items.wine = Wine(
                country = country,
                variety = variety,
                region = region,
                winery = winery,
                year = year,
                price = price)
                cart.wine_items.quantity = quantity
                cart.put()
            query_params = {'cart_name': cart_name,
            'category_name':category_name}
            self.redirect('/display?'+urllib.urlencode(query_params))
        else:
            query_params = {'error_sign_in':True,
            'category_name':category_name}
            self.redirect('display?'+urllib.urlencode(query_params))

class SearchAddPage(webapp2.RequestHandler):

    def post(self):
        user = users.get_current_user()
        category_name = self.request.get('category_name',DEFAULT_CATEGORY_NAME)
        if user:
            cart_name = user.user_id()
            cart_query = Cart.query(ancestor = cart_key(cart_name)).order(-Cart.date)
            carts = cart_query.fetch()
            entry_exists = False
            country = self.request.get('country')
            variety = self.request.get('variety')
            region = self.request.get('region')
            winery = self.request.get('winery')
            year = self.request.get('year')
            price = float(self.request.get('price'))
            quantity = int(self.request.get('quantity'))
            for cart in carts:
                if cart.wine_items.wine.winery == winery:
                    if cart.wine_items.wine.variety == variety:
                        if cart.wine_items.wine.region == region:
                            if str(cart.wine_items.wine.price) == str(price):
                                if cart.wine_items.wine.year == year:
                                    if cart.wine_items.wine.country == country:
                                        cart_to_modify = cart.key.get()
                                        cart_to_modify.wine_items.quantity +=quantity
                                        cart_to_modify.put()
                                        entry_exists=True
            if not entry_exists:
                cart = Cart(parent=cart_key(cart_name))
                cart.author = Author(
                identity = user.user_id(),
                email = user.email()
                )
                cart.wine_items = Wine_Items()
                cart.wine_items.wine = Wine(
                country = country,
                variety = variety,
                region = region,
                winery = winery,
                year = year,
                price = price)
                cart.wine_items.quantity = quantity
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
        wine.price = float(self.request.get('price'))

        if wine.country and wine.year and wine.region and wine.variety and wine.winery and wine.price:
            wine.put()
            query_params = {'category_name': category_name}
            self.redirect('/?'+ urllib.urlencode(query_params))
        else :
            self.get(True)

class SearchPage(webapp2.RequestHandler): #displays search and search page
    def get(self, error_empty_fields=False, error_no_result=False):
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME)
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
        category_name = self.request.get('category_name', DEFAULT_CATEGORY_NAME)
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

        wines_query = Wine.query(ancestor = category_key(category_name.lower()))
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
            if cart.wine_items.quantity:
                total_cost+=(cart.wine_items.wine.price*cart.wine_items.quantity)
            else:
                total_cost+=cart.wine_items.wine.price
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
            if str(cart.wine_items.quantity) == str(self.request.get('quantity')):
                if cart.wine_items.wine.winery == self.request.get('winery'):
                    if cart.wine_items.wine.variety == self.request.get('variety'):
                        if str(cart.wine_items.wine.price) == str(self.request.get('price')):
                            if cart.wine_items.wine.region == self.request.get('region'):
                                if cart.wine_items.wine.year == self.request.get('year'):
                                    if cart.wine_items.wine.country == self.request.get('country'):
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
            if cart.wine_items.quantity:
                total_cost+=(cart.wine_items.wine.price*cart.wine_items.quantity)
            else:
                total_cost+=cart.wine_items.wine.price
        for cart in carts:
            cart_purchased = Cart(parent=purchase_key(cart_name))
            cart_purchased.author = Author(identity=user.user_id(),email=user.email())
            cart_purchased.wine_items=Wine_Items(wine=Wine( country=cart.wine_items.wine.country,
            region= cart.wine_items.wine.region,
            winery= cart.wine_items.wine.winery,
            variety= cart.wine_items.wine.variety,
            price= cart.wine_items.wine.price,
            year= cart.wine_items.wine.year),
            quantity=cart.wine_items.quantity)
            cart_purchased.put()
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
    ('/confirmation',ConfirmPage)
], debug=True)
# [END app]
