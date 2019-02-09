from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
import pypyodbc
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from datetime import datetime, timezone
from dateutil.parser import parse
import requests as api_request
import json
import data # local file data.py

app = Flask(__name__, static_url_path='/static')

# Create database connection
dbconnection = pypyodbc.connect('Driver={SQL Server};'
								'Server=JM736H2;'
								'Database=myflaskapp_db;'
								'Trusted_connection=yes;')


## Article data from file data.py 
#Articles = data.Articles()

# Data from file data.py
data = data.Data()

# Headers for REST API call
headers = {
        "Content-Type": "application/json",
        "Accept": "application/hal+json",
        "x-api-key": "583C80B5796103A1812EF9D0FAD6535688AD5BE21999604F1F129E33CD60A42DB4132725367927947B2B"
        }



# Register form class
class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=4, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

# Article form class
class ArticleForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=64)])
	description = TextAreaField('Description', [validators.Length(min=4, max=256)])

# Company form class
class BuyingstatusForm(Form):
	active = StringField('Active', [validators.Length(min=1, max=50)])
	prospect = StringField('Prospect', [validators.Length(min=1, max=50)])
	excustomer = StringField('Excustomer', [validators.Length(min=1, max=50)])
	notinterested = StringField('Notinterested', [validators.Length(min=1, max=25)])
	

# Rest API call to get data
def get_api_data(headers, url):
    response = api_request.get(url=url, headers=headers, data=None, verify=False)

    # Convert the response string into json data and get embedded limeobjects
    json_data = json.loads(response.text)
    limeobjects = json_data.get("_embedded").get("limeobjects")
    
    #import pdb; pdb.set_trace()
    # Check for more data pages and get thoose too
    nextpage = json_data.get("_links").get("next")
    while nextpage is not None:
        url = nextpage["href"]
        response = api_request.get(url, headers=headers, data=None, verify=False)
        json_data = json.loads(response.text)
        limeobjects += json_data.get("_embedded").get("limeobjects")

        #import pdb; pdb.set_trace()
        nextpage = json_data.get("_links").get("next")

    return limeobjects

def get_api_limetype(header, url):
	response = api_request.get(url=url, headers=headers, data=None, verify=False)
	json_data = json.loads(response.text)
	limetype = json_data.get("options")
	
	return limetype


def put_api_data(headers, url, data):
    response = api_request.put(url=url, headers=headers, data=data, verify=False)

    return response



# Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			# import pdb; pdb.set_trace()
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap



# Index
@app.route('/')
def index():
	return render_template('home.html')

# About
@app.route('/about')
def about():
	return render_template('about.html')

# Articles
@app.route('/articles')
def articles():
	sql = "SELECT * FROM dbo.[article]"

	cursor = dbconnection.cursor().execute(sql)
	columns = [column[0] for column in cursor.description]
	
	articles = []
	for row in cursor.fetchall():
		articles.append(dict(zip(columns, row)))

	cursor.close()
	#import pdb; pdb.set_trace()

	if len(articles) > 0:
		return render_template('articles.html', articles = articles)
	else:
		msg = 'No articles found'
		return render_template('articles.html', msg = msg)


# Single article
@app.route('/article/<string:idarticle>/')
def article(idarticle):
	sql = "SELECT * FROM dbo.[article] WHERE idarticle = N'{}'".format(idarticle)

	cursor = dbconnection.cursor().execute(sql)
	columns = [column[0] for column in cursor.description]
	data = cursor.fetchone()
	article = dict(zip(columns, data))
	cursor.close()
	#import pdb; pdb.set_trace()

	return render_template('article.html', article = article)


# User register
@app.route('/register', methods=['GET', 'POST'])
def register():
	form = RegisterForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		email = form.email.data
		username = form.username.data
		password = sha256_crypt.encrypt(str(form.password.data))

		#create and execute db cursor
		sql = "INSERT INTO dbo.[user] ([name], [email], [username], [password]) VALUES (N'{}', N'{}', N'{}', N'{}')".format(name, email, username, password)
		#import pdb; pdb.set_trace()

		cursor = dbconnection.cursor()
		cursor.execute(sql)

		#commit and close
		dbconnection.commit()
		cursor.close()
		#dbconnection.close()

		flash('You are now registered and can log in', 'success')

		return redirect(url_for('index'))
	
	if request.method == 'GET':
		return render_template('register.html', form = form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		
		# Get form fields
		username = request.form['username']
		password_candidate = request.form['password']

		# Get user
		sql = "SELECT * FROM dbo.[user] WHERE [username] = N'{}'".format(username)
		cursor = dbconnection.cursor().execute(sql)
		columns = [column[0] for column in cursor.description]
		
		data = []
		for row in cursor.fetchall():
			data.append(dict(zip(columns, row)))

		cursor.close()
		#import pdb; pdb.set_trace()

		if len(data) > 0:
			app.logger.info("User found")

			# Get stored password hash
			password = data[0]["password"]
			
			# Compare password hashes
			if sha256_crypt.verify(password_candidate, password):
				# Passed
				app.logger.info("Password match")
				session['logged_in'] = True
				session['username'] = username

				# import pdb; pdb.set_trace() 
				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))

			else:
				app.logger.info("Password doesn't match")
				error = "Invalid username or password"
				return render_template('login.html', error=error)
		else:
			app.logger.info("User not found")
			error = "Invalid username or password"
			return render_template('login.html', error=error)
	
	if request.method == 'GET':
		# import pdb; pdb.set_trace()
		return render_template('login.html')

# User logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

# Deals
@app.route('/deals')
# @is_logged_in
def deals():
	# API call to get deals
	url = "https://localhost/lime_core_v6_1_2/api/v1/limeobject/deal/"
	deals = get_api_data(headers, url)

	if len(deals) > 0:
		# Create a list of dictionaries for each month of last year
		today = datetime.today()
		lastyear = today.year - 1
		ly_monthlist = []

		for month in range(12):
			date = datetime(lastyear, month+1, 1)
			# import pdb; pdb.set_trace()
			monthdict = {
				'id': date.strftime('%Y%m'),
				'name': date.strftime('%b-%y'),
				'year': lastyear,
				'month': month+1,
				'deals': 0,
				'value' : 0
			}
			ly_monthlist.append(monthdict)


		# Loop though deals and update ly_monthlist with values
		today = datetime.today()
		lastyear = today.year - 1
		
		for deal in deals:
			try:
				# Trying to parse 'None' will throw TypeError
				closeddate = parse(deal['closeddate']) # using dateutil.parser.parse()
				if closeddate.year == lastyear:
					
					for month in ly_monthlist:
						#import pdb; pdb.set_trace()
						if month['id'] == closeddate.strftime('%Y%m'):
							month['deals'] += 1
							month['value'] += deal['value']

			except TypeError:
				pass

		# import pdb; pdb.set_trace()


		# Collect all kpi's in this list
		kpis = []

		# Declare time variables used below
		today = datetime.today()
		lastyear = today.year - 1

		# Calculate number of won deals per month the last year.
		nbrtext = "This was the number of won deals per month the last year."
		lastyear_values = []

		for month in ly_monthlist:
			lastyear_values.append(month['deals'])
		
		ly_numberavg = round( sum(lastyear_values) / len(lastyear_values), 2)
		kpis.append(
			{
				'header': 'DEALS/MONTH',
				'text': nbrtext,
				'value': ly_numberavg
			}
		)



		# Calculate average value of a won deal last year.
		avgtext = "This was the average value of a won deal last year."
		lastyear_values = []

		for deal in deals:	
			try:
				closeddate = parse(deal['closeddate']) # using dateutil.parser.parse()
				if closeddate.year == lastyear:
					lastyear_values.append(deal['value'])
			except TypeError:
				pass
		
		ly_valueavg = round( sum(lastyear_values) / len(lastyear_values), 2)
		kpis.append(
			{
				'header': 'SEK',
				'text': avgtext,
				'value': ly_valueavg
			}
		)

		# import pdb; pdb.set_trace()
		
		# Calculate average value for won deals per customer the last year.
		totaltext = "This was the average value of won deals per customer the last year."
		companydeals = {}
		lastyear_values = []

		for deal in deals:
			try:
				closeddate = parse(deal['closeddate'])
				if closeddate.year == lastyear:
					try:
						companydeals[deal['company']]['deals'] += 1
						companydeals[deal['company']]['value'] += deal['value']
						if parse(companydeals[deal['company']]['latestdeal']) < parse(deal['closeddate']):
							companydeals[deal['company']]['latestdeal'] = deal['closeddate']
						
					except KeyError:
						companydeals[deal['company']] = {
								'latestdeal': deal['closeddate'],
								'deals': 1,
								'value': deal['value']
							}
			except TypeError:
				pass

		for company in companydeals.keys():
			lastyear_values.append(companydeals[company]['value'])

		ly_custtotal = round( sum(lastyear_values) / len(lastyear_values), 2 ) 
		kpis.append(
			{
				'header': 'SEK/CUSTOMER',
				'text': totaltext,
				'value': ly_custtotal
			}
		)		
		#import pdb; pdb.set_trace()

		return render_template('deals.html', months = ly_monthlist , kpis = kpis) #deals = deals
	else:
		msg = 'No deals found'
		return render_template('deals.html', msg = msg)

# Deal graph
@app.route('/dealgraph')
# @is_logged_in
def dealgraph():
	# API call to get deals
	url = "https://localhost/lime_core_v6_1_2/api/v1/limeobject/deal/"
	deals = get_api_data(headers, url)

	if len(deals) > 0:
		# Create a list of dictionaries for each month of last year
		today = datetime.today()
		lastyear = today.year - 1
		ly_monthlist = []

		for month in range(12):
			date = datetime(lastyear, month+1, 1)
			# import pdb; pdb.set_trace()
			monthdict = {
				'id': date.strftime('%Y%m'),
				'name': date.strftime('%b-%y'),
				'year': lastyear,
				'month': month+1,
				'deals': 0,
				'value' : 0
			}
			ly_monthlist.append(monthdict)


		# Loop though deals and update ly_monthlist with values
		today = datetime.today()
		lastyear = today.year - 1
		
		for deal in deals:
			try:
				# Trying to parse 'None' will throw TypeError
				closeddate = parse(deal['closeddate']) # using dateutil.parser.parse()
				if closeddate.year == lastyear:
					
					for month in ly_monthlist:
						#import pdb; pdb.set_trace()
						if month['id'] == closeddate.strftime('%Y%m'):
							month['deals'] += 1
							month['value'] += deal['value']

			except TypeError:
				pass
				
		labels = []
		values = []

		for month in ly_monthlist:
			# import pdb; pdb.set_trace()		
			labels.append(month['name'])
			values.append(month['value'])
						

		return render_template('dealgraph.html', months = ly_monthlist, labels = labels, values = values)
	else:
		msg = 'No deals found'
		return render_template('dealgraph.html', msg = msg)

# Companies
@app.route('/companies', methods=['GET', 'POST'])
# @is_logged_in
def companies():
	form = BuyingstatusForm(request.form)
	if request.method == 'POST' and form.validate():
		active = form.active.data
		prospect = form.prospect.data
		excustomer = form.excustomer.data
		notinterested = form.notinterested.data


	# API call to get available buying statuses
	url_buyingstatus = "https://localhost/lime_core_v6_1_2/api/v1/limetype/company/buyingstatus/"
	buyingstatuses = get_api_limetype(headers, url_buyingstatus)


	# API call to get deals
	url_deals = "https://localhost/lime_core_v6_1_2/api/v1/limeobject/deal/"
	deals = get_api_data(headers, url_deals)

	if len(deals) > 0:
		# Create a dictionary of the companies with won deals
		companydeals = {}

		for deal in deals:
			if deal['dealstatus']['key'] == 'agreement':
				try:
					companydeals[deal['company']]['deals'] += 1
					companydeals[deal['company']]['value'] += deal['value']
					if parse(companydeals[deal['company']]['latestdeal']) < parse(deal['closeddate']):
						companydeals[deal['company']]['latestdeal'] = deal['closeddate']
					
				except KeyError:
					companydeals[deal['company']] = {
							'latestdeal': deal['closeddate'],
							'deals': 1,
							'value': deal['value']
						}
		#import pdb; pdb.set_trace()


	# API call to get companies
	url_companies = "https://localhost/lime_core_v6_1_2/api/v1/limeobject/company/"
	companies = get_api_data(headers, url_companies)


	if len(companies) > 0:

		# Go through all companies and create payload if buyingstatus needs update
		update_companies = {}

		for company in companies:
			current_buyingstatus = company['buyingstatus']
			#import pdb; pdb.set_trace()

			try:
				# This first line will throw a KeyError is the company is not in companydeals
				value = companydeals[company['_id']]['value']
				latestdeal = parse(companydeals[company['_id']]['latestdeal'])
				today = datetime.now(timezone.utc)
				oneyear_ago = today.replace(year=(today.year - 1))
				#import pdb; pdb.set_trace()

				# Active customer
				if value > 0 and latestdeal > oneyear_ago :
					if current_buyingstatus['key'] != 'active': 
						update_companies[company['_id']] = {
																'buyingstatus': 
																	{
																		'key': 'active'
																	}
															}	

				#Excustomer
				elif value > 0 and latestdeal < oneyear_ago :
					if current_buyingstatus['key'] != 'excustomer':
						update_companies[company['_id']] = {
																'buyingstatus': 
																	{
																		'key': 'excustomer'
																	}
															}	

			except KeyError:
				#Prospect
				if current_buyingstatus['key'] not in ('notinterested', 'prospect'):
					update_companies[company['_id']] = {
															'buyingstatus': 
																{
																	'key': 'prospect'
																}
														}


		# API call to send payload and update companies
		# for key in update_companies.keys():		
		# 	url_put_company = "https://localhost/lime_core_v6_1_2/api/v1/limeobject/company/" + str(key) + "/"
			
		# 	data = json.dumps(update_companies[key])
		# 	put_response = put_api_data(headers=headers, url=url_put_company, data=data)
			
		# 	if put_response.status_code == "200":
		# 		logstring = put_response.reason + " - company " + str(company['id'] + " successfully updated")
		# 		app.logger.info(logstring)

		# import pdb; pdb.set_trace()

		return render_template('companies.html', companies = companies, buyingstatuses = buyingstatuses)
	else:
		msg = 'No companies found'
		return render_template('companies.html', msg = msg)


# Dashboard
@app.route('/dashboard')
# @is_logged_in
def dashboard():

	#Get articles
	sql = "SELECT * FROM dbo.[article]"
	cursor = dbconnection.cursor().execute(sql)
	columns = [column[0] for column in cursor.description]
	
	articles = []
	for row in cursor.fetchall():
		articles.append(dict(zip(columns, row)))

	cursor.close()
	#import pdb; pdb.set_trace()

	if len(articles) > 0:
		return render_template('dashboard.html', articles = articles)
	else:
		msg = 'No articles found'
		return render_template('dashboard.html', msg = msg)

# Add article
@app.route('/addarticle', methods=['GET', 'POST'])
@is_logged_in
def addarticle():
	form = ArticleForm(request.form)
	if request.method == 'POST' and form.validate():
		name = form.name.data
		description = form.description.data

		# Get user
		sqlselect = "SELECT iduser FROM dbo.[user] WHERE [username] = N'{}'".format(session['username'])
		cursor = dbconnection.cursor().execute(sqlselect)
		data = cursor.fetchone()
		iduser = data[0]
		cursor.close()
		#import pdb; pdb.set_trace()

		# Insert article
		sqlinsert = "INSERT INTO dbo.[article] ([name], [description], createduser) VALUES (N'{}', N'{}', N'{}')".format(name, description, iduser)
		#import pdb; pdb.set_trace()
		cursor = dbconnection.cursor().execute(sqlinsert)
		dbconnection.commit()
		cursor.close()
		#dbconnection.close()

		flash('Article added', 'success')

		return redirect(url_for('dashboard'))
	return render_template('addarticle.html', form = form)

# Edit article
@app.route('/editarticle/<string:idarticle>', methods=['GET', 'POST'])
@is_logged_in
def editarticle(idarticle):
	
	#Get article
	sqlselect = "SELECT * FROM dbo.[article] WHERE [idarticle] = N'{}'".format(idarticle)
	cursor = dbconnection.cursor().execute(sqlselect)
	columns = [column[0] for column in cursor.description]
	data = cursor.fetchone()
	article = dict(zip(columns, data))
	#cursor.close()
	#import pdb; pdb.set_trace()

	# Populate article form fields
	form = ArticleForm(request.form)
	form.name.data = article['name']
	form.description.data = article['description']

	# When changes are saved
	if request.method == 'POST' and form.validate():
		name = request.form['name']
		description = request.form['description']

		# Get user
		sqlselect = "SELECT iduser FROM dbo.[user] WHERE [username] = N'{}'".format(session['username'])
		cursor = dbconnection.cursor().execute(sqlselect)
		data = cursor.fetchone()
		iduser = data[0]
		#cursor.close()
		#import pdb; pdb.set_trace()

		# Update article
		sqlupdate = "UPDATE dbo.[article] SET [name] = N'{}', [description] = N'{}', updateduser = {} WHERE idarticle = {}".format(name, description, iduser, idarticle)
		#import pdb; pdb.set_trace()
		cursor = dbconnection.cursor()
		cursor.execute(sqlupdate)
		dbconnection.commit()
		cursor.close()
		#dbconnection.close()

		flash('Article updated', 'success')

		return redirect(url_for('dashboard'))
	return render_template('editarticle.html', form = form)

# Delete article
@app.route('/deletearticle/<string:idarticle>', methods=['POST'])
@is_logged_in
def deletearticle(idarticle):

	sqldelete = "DELETE FROM dbo.[article] WHERE idarticle = {}".format(idarticle)
	#import pdb; pdb.set_trace()
	cursor = dbconnection.cursor().execute(sqldelete)
	dbconnection.commit()
	cursor.close()

	flash('Article deleted', 'success')

	return redirect(url_for('dashboard')) 

if __name__ == '__main__':
	app.secret_key = 'somethingsecret'
	app.run(debug=True)