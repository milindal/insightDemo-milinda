from comments_nlp import GetRepresentativeComments, getKeywords, UpdateDatabase
from flask import render_template, request
from ConvApp import app
import pickle 
import os 

import datetime
import StringIO
import random
import urllib
import matplotlib as mpl
import numpy as np

from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.dates import DateFormatter

from wordcloud import WordCloud

mpl.rcParams['font.size'] = 20
data_folder_path = os.environ.get('CONV_APP_DATA_PATH')

@app.route('/')
@app.route('/index')
def index():
   user = '' # fake user
   return render_template("index.html",
       title = 'Home',
       user = user)

@app.route('/slides')
def slides(): 
  return render_template("slides.html", title = 'Slides')

@app.route('/output')
def output():
  # # Load the dictionary
  # database_dict = pickle.load(open( '/Users/milindal/Dropbox/Insight/insightDemo-milinda/data/updated_database_dict.p', 'rb'))
  database_dict = pickle.load(open( data_folder_path + 'updated_database_dict.p', 'rb'))

  # #pull 'ID' from input field and store it
  url_string = request.args.get('ID')
  # pull the number of clusters from the user form
  if request.args.get('Nclusters'): 
    Nclusters = int(request.args.get('Nclusters'))
  else: 
    Nclusters = 3
  
  if len(url_string) < 5: 
    url_string = 'http://www.nytimes.com/2015/09/20/opinion/sunday/a-toxic-work-world.html'

  if url_string not in database_dict.keys(): 
    database_dict = UpdateDatabase(url_string, database_dict)

  print 'Nclusters: ', Nclusters
  
  headline = database_dict[url_string]['title']
  abstract = database_dict[url_string]['abstract']
  article_summary = dict(headline = headline, abstract = abstract)

  # Generate a wordcloud plot for the article 
  Nkeywords = len(database_dict[url_string]['keyword_dict'])
  word_freq_list = [(entry['value'], Nkeywords - float(entry['rank'])) for entry in database_dict[url_string]['keyword_dict']]     
  title_wordcloud = WordCloud().generate_from_frequencies(word_freq_list)
  fig = Figure() 
  fig.set_facecolor('None')
  ax = fig.add_subplot(111)
  ax.imshow(title_wordcloud)
  ax.set_axis_off()
  canvas=FigureCanvas(fig)
  title_cloud_png_output = StringIO.StringIO()
  canvas.print_png(title_cloud_png_output)
  title_cloud_png_output = title_cloud_png_output.getvalue().encode("base64")



  # Get the three representative comments
  rep_comments = GetRepresentativeComments(database_dict[url_string]['comments_df'], Nclusters) 
  senti_pos = database_dict[url_string]['comments_df']['senti_pos'] 
 
 # Get the pie chart 
  fig = Figure() 
  fig.set_facecolor('None')
  ax = fig.add_subplot(111)

  color_repo = ['#4D4D4D', '#5DA5DA', '#FAA43A', '#60BD68', '#F17CB0', '#B2912F', '#B276B2', '#DECF3F', '#F15854']

  
  sizes = [rep_comments[i]['count'] for i in range(Nclusters)]
  colors = [color_repo[i] for i in range(Nclusters)]
  sorted_sizes_args = np.argsort(sizes)[::-1]
  labels = ['Cluster ' + str(i+1) for i in range(Nclusters)]
  sorted_sizes = sorted(sizes)[::-1]

  ax.pie(sorted_sizes, labels=labels, colors=colors,
          autopct='%1.1f%%', shadow=True, startangle=90)
  ax.set_axis_off()
  canvas=FigureCanvas(fig)
  pie_png_output = StringIO.StringIO()
  canvas.print_png(pie_png_output)
  pie_png_output = pie_png_output.getvalue().encode("base64")


  # Sentiment plot
  fig=Figure()
  fig.set_facecolor('None')
  ax=fig.add_subplot(111)

  ax.hist(senti_pos, bins = 20)
  ax.set_xlim(0,1)
  ax.set_xlabel('Sentiment Scale')
  ax.set_ylabel('Number of Comments')
  ax.set_xticks(np.linspace(0, 1, 5))
  senti_labels = [item.get_text() for item in ax.get_xticklabels()]
  senti_labels[0] = 'Neg'
  senti_labels[2] = '0'
  senti_labels[-1] = 'Pos'
  ax.set_xticklabels(senti_labels)
  canvas=FigureCanvas(fig)
  png_output = StringIO.StringIO()
  canvas.print_png(png_output)
  png_output = png_output.getvalue().encode("base64")

  # Return word clouds for different comments 
  word_cloud_comments = {} # key: cluster_label, val: 
  for lab in range(Nclusters):
    comment_keywords = getKeywords(rep_comments[lab]['comment'])
    # comment_keywords = rep_comments[lab]['cluster_keywords']
    keyword_wordfreq_list = [ (word, len(comment_keywords) - i) for i,word in enumerate(comment_keywords)]
    wordcloud = WordCloud().generate_from_frequencies(keyword_wordfreq_list)
    fig = Figure() 
    fig.set_facecolor('None')
    ax = fig.add_subplot(111)
    ax.imshow(wordcloud)
    ax.set_axis_off()
    canvas=FigureCanvas(fig)
    comment_cloud_png_output = StringIO.StringIO()
    canvas.print_png(comment_cloud_png_output)
    comment_cloud_png_output = comment_cloud_png_output.getvalue().encode("base64")
    word_cloud_comments[lab] = urllib.quote(comment_cloud_png_output.rstrip('\n'))

  print word_cloud_comments[0].__class__.__name__
  comment_div_str = '' 
  for i in range(Nclusters): 
    temp_str = '<div class="row"> <div class="col-md-12" > <h4> Cluster ' + str(i+1) + 'count: ' + str(sizes[sorted_sizes_args[i]]) + '</h4>  <div class="col-md-5" > <img src="data:image/png;base64,' + word_cloud_comments[sorted_sizes_args[i]] + '" width="400" height="300"/> </div>' + '<div class="col-md-7" > <p class="lead"> ' + rep_comments[sorted_sizes_args[i]]['comment'] + '</p> </div>' + '</div> </div> '
    comment_div_str += temp_str


  return render_template("output.html", title_png = urllib.quote(title_cloud_png_output.rstrip('\n')), 
    article_summary = article_summary,  RepComment = rep_comments, comment_coulds = word_cloud_comments, 
    pie_png = urllib.quote(pie_png_output.rstrip('\n')), img_data=urllib.quote(png_output.rstrip('\n')),
    Nclusters = Nclusters, comment_div_str=comment_div_str)

