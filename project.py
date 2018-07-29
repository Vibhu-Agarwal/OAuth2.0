from flask import Flask, render_template, request, redirect,jsonify, url_for, flash, make_response
from flask import session as login_session
app = Flask(__name__)

from sqlalchemy import create_engine, asc
from sqlalchemy.orm import sessionmaker
from database_setup import Base, Restaurant, MenuItem

from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

import random, string

json_file = json.loads(open('client_secrets.json', 'r').read())
CLIENT_ID = json_file['web']['client_id']

#Connect to Database and create database session
engine = create_engine('sqlite:///restaurantmenu.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()


#JSON APIs to view Restaurant Information
@app.route('/restaurant/<int:restaurant_id>/menu/JSON')
def restaurantMenuJSON(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).all()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return jsonify(MenuItems=[i.serialize for i in items])


@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/JSON')
def menuItemJSON(restaurant_id, menu_id):
    Menu_Item = session.query(MenuItem).filter_by(id = menu_id).all()
    return jsonify(Menu_Item = Menu_Item[0].serialize)

@app.route('/restaurant/JSON')
def restaurantsJSON():
    restaurants = session.query(Restaurant).all()
    return jsonify(restaurants= [r.serialize for r in restaurants])


#Show all restaurants
@app.route('/')
@app.route('/restaurant/')
def showRestaurants():
  restaurants = session.query(Restaurant).order_by(asc(Restaurant.name))
  return render_template('restaurants.html', restaurants = restaurants)

#Create a new restaurant
@app.route('/restaurant/new/', methods=['GET','POST'])
def newRestaurant():
  if request.method == 'POST':
      newRestaurant = Restaurant(name = request.form['name'])
      session.add(newRestaurant)
      flash('New Restaurant %s Successfully Created' % newRestaurant.name)
      session.commit()
      return redirect(url_for('showRestaurants'))
  else:
      return render_template('newRestaurant.html')

#Edit a restaurant
@app.route('/restaurant/<int:restaurant_id>/edit/', methods = ['GET', 'POST'])
def editRestaurant(restaurant_id):
  editedRestaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if request.method == 'POST':
      if request.form['name']:
        editedRestaurant.name = request.form['name']
        flash('Restaurant Successfully Edited %s' % editedRestaurant.name)
        return redirect(url_for('showRestaurants'))
  else:
    return render_template('editRestaurant.html', restaurant = editedRestaurant)


#Delete a restaurant
@app.route('/restaurant/<int:restaurant_id>/delete/', methods = ['GET','POST'])
def deleteRestaurant(restaurant_id):
  restaurantToDelete = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if request.method == 'POST':
    session.delete(restaurantToDelete)
    flash('%s Successfully Deleted' % restaurantToDelete.name)
    session.commit()
    return redirect(url_for('showRestaurants', restaurant_id = restaurant_id))
  else:
    return render_template('deleteRestaurant.html',restaurant = restaurantToDelete)

#Show a restaurant menu
@app.route('/restaurant/<int:restaurant_id>/')
@app.route('/restaurant/<int:restaurant_id>/menu/')
def showMenu(restaurant_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).all()
    items = session.query(MenuItem).filter_by(restaurant_id = restaurant_id).all()
    return render_template('menu.html', items = items, restaurant = restaurant[0])
     


#Create a new menu item
@app.route('/restaurant/<int:restaurant_id>/menu/new/',methods=['GET','POST'])
def newMenuItem(restaurant_id):
  restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
  if request.method == 'POST':
      newItem = MenuItem(name = request.form['name'], description = request.form['description'], price = request.form['price'], course = request.form['course'], restaurant_id = restaurant_id)
      session.add(newItem)
      session.commit()
      flash('New Menu %s Item Successfully Created' % (newItem.name))
      return redirect(url_for('showMenu', restaurant_id = restaurant_id))
  else:
      return render_template('newmenuitem.html', restaurant_id = restaurant_id)

#Edit a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/edit', methods=['GET','POST'])
def editMenuItem(restaurant_id, menu_id):

    editedItem = session.query(MenuItem).filter_by(id = menu_id).one()
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    if request.method == 'POST':
        if request.form['name']:
            editedItem.name = request.form['name']
        if request.form['description']:
            editedItem.description = request.form['description']
        if request.form['price']:
            editedItem.price = request.form['price']
        if request.form['course']:
            editedItem.course = request.form['course']
        session.add(editedItem)
        session.commit() 
        flash('Menu Item Successfully Edited')
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('editmenuitem.html', restaurant_id = restaurant_id, menu_id = menu_id, item = editedItem)


#Delete a menu item
@app.route('/restaurant/<int:restaurant_id>/menu/<int:menu_id>/delete', methods = ['GET','POST'])
def deleteMenuItem(restaurant_id,menu_id):
    restaurant = session.query(Restaurant).filter_by(id = restaurant_id).one()
    itemToDelete = session.query(MenuItem).filter_by(id = menu_id).one() 
    if request.method == 'POST':
        session.delete(itemToDelete)
        session.commit()
        flash('Menu Item Successfully Deleted')
        return redirect(url_for('showMenu', restaurant_id = restaurant_id))
    else:
        return render_template('deleteMenuItem.html', item = itemToDelete)

#Create a state token to prevent request forgery
#Store it in a session for later validation
@app.route('/login')
def showLogin():
	state = ''.join(random.choice(string.ascii_uppercase + string.digits)
		for x in range(32))
	login_session['state'] = state
	return render_template('login.html', STATE = state)

@app.route('/gconnect', methods = ['POST'])
def gconnect():
	print('gconnect function called in python')
	#Checking for data forgery
	if request.args.get('state') != login_session['state']:
		response = make_response(json.dumps('Invalid State'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		#The code which the google gave to the client
		code = request.data
		try:
			oauth_flow = flow_from_clientsecrets('client_secrets.json', scope = '')
			oauth_flow.redirect_uri = 'postmessage'
			#Google will give a credentials object in exchange of this 'code'
			credentials = oauth_flow.step2_exchange(code)
		except:
			response = make_response(json.dumps('Failed to upgrade authorization code'), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

		#Now checking if there is a valid access token
		access_token = credentials.access_token
		url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token={}'.format(access_token))
		h = httplib2.Http()
		print('-------> url:', url)
		result = json.loads(h.request(url, 'GET')[1])
		print('-------> result', result)
		if result.get('error') is not None:
			response = make_response(json.dumps(result.get('error')), 500)
			response.headers['Content-Type'] = 'application/json'
			return response
		else:
			#Now checking if we have the right access token: verify that the access token is for the intended user
			gplus_id = credentials.id_token['sub']
			if result['user_id'] != gplus_id:
				response = make_response(json.dumps("Token's user id doesn't match the given user id"), 401)
				response.headers['Content-Type'] = 'application/json'
				return response
			else:
				# Verify that the access token is valid for this app.
				if result['issued_to'] != CLIENT_ID:
					response = make_response(json.dumps("Token's client ID does not match app's."), 401)
					print("Token's client ID does not match app's.")
					response.headers['Content-Type'] = 'application/json'
					return response

				#Now checking if this user is already logged in
				stored_access_token = login_session.get('access_token')
				stored_gplus_id = login_session.get('gplus_id')
				if stored_access_token is not None and gplus_id == stored_gplus_id:
					response = make_response(json.dumps('Current user is already logged in'), 200)
					response.headers['Content-Type'] = 'application/json'
					return response
				else:
					#User is not already signed in
					#Storing the access token in session for later use
					login_session['access_token'] = credentials.access_token
					login_session['gplus_id'] = gplus_id

					#Getting user info here
					user_info_url = "https://www.googleapis.com/oauth2/v1/userinfo"
					params = {'access_token': credentials.access_token, 'alt': 'json'}
					answer = requests.get(user_info_url, params = params)

					data = answer.json()
					print('-------> data', data)

					login_session['username'] = data['name']
					login_session['picture'] = data['picture']
					login_session['email'] = data['email']

					output = ''
					output += "<h1>Welcome, '{username}'!</h1>"
					output += '''<img src = "'{img_url}'" style = "width: 300px; height: 300px;border-radius: 150px;-webkit-border-radius: 150px;-moz-border-radius: 150px;">'''

					flash("You are now logged in as {username}".format(username = login_session['username']))

					print('Done Loggin in!')
					return output.format(username = login_session['username'], img_url = login_session['picture'])

def resetLoginSession():
	login_session['access_token'] = None
	login_session['gplus_id'] = None
	login_session['username'] = None
	login_session['picture'] = None
	login_session['email'] = None

#DISCONNECT - Revoke the current user's token and reset their_login session
@app.route('/gdisconnect')
def gdisconnect():
	access_token = login_session['access_token']
	if access_token is None:
		response = make_response(json.dumps('Curent user not connected'), 401)
		response.headers['Content-Type'] = 'application/json'
		return response
	else:
		#Execute HTTP GET request to revoke current token
		url = 'https://accounts.google.com/o/oauth2/revoke?token={}'.format(access_token)
		h = httplib2.Http()
		req = h.request(url, 'GET')
		result = req[0]
		print('-------> req', req)
		print('-------> result', result)
		if result['status'] == '200':
			resetLoginSession()
			response = make_response(json.dumps('Successfully disconnected'), 200)
			response.headers['Content-Type'] = 'application/json'
			return response
		else:
			response = make_response(json.dumps('Failed to revoke token for the given user'), 400)
			response.headers['Content-Type'] = 'application/json'
			return response


if __name__ == '__main__':
  app.secret_key = 'super_secret_key'
  app.debug = True
  app.run(host = '0.0.0.0', port = 5000)
