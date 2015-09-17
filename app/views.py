from a_model import ModelIt
from flask import render_template, request
from app import app

@app.route('/')
@app.route('/index')
def index():
   user = { 'nickname': 'Miguel' } # fake user
   return render_template("index.html",
       title = 'Home',
       user = user)

@app.route('/input')
def cities_input():
  return render_template("input.html")

@app.route('/output')
def cities_output():
  #pull 'ID' from input field and store it
  city = request.args.get('ID')
  cities = [ dict(name = 'Boston', country = 'USA', population = 10000)]
  

  # cities = []
  # for result in query_results:
  #   cities.append(dict(name=result[0], country=result[1], population=result[2]))
  #call a function from a_Model package. note we are only pulling one result in the query
  pop_input = cities[0]['population']
  the_result = ModelIt(city, pop_input)
  return render_template("output.html", cities = cities, the_result = the_result)