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


@app.route('/output')
def output():
  # # Load the dictionary
  # database_dict = pickle.load(open( '/Users/milindal/Dropbox/Insight/insightDemo-milinda/data/updated_database_dict.p', 'rb'))
  database_dict = pickle.load(open( data_folder_path + 'updated_database_dict.p', 'rb'))

  # #pull 'ID' from input field and store it
  url_string = request.args.get('ID')
  if len(url_string) < 5: 
    url_string = 'http://www.nytimes.com/2015/09/20/opinion/sunday/a-toxic-work-world.html'

  if url_string not in database_dict.keys(): 
    database_dict = UpdateDatabase(url_string, database_dict)
  
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
  rep_comments = GetRepresentativeComments(database_dict[url_string]['comments_df']) 
  senti_pos = database_dict[url_string]['comments_df']['senti_pos'] 
 
 # Get the pie chart 
  fig = Figure() 
  fig.set_facecolor('None')
  ax = fig.add_subplot(111)

  labels = ['Cluster 1', 'Cluster 2', 'Cluster 3']
  sizes = [rep_comments[0]['count'], rep_comments[1]['count'], rep_comments[2]['count']]
  colors = ['yellowgreen', 'gold', 'lightskyblue'] #, 'lightcoral']

  ax.pie(sizes, labels=labels, colors=colors,
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
  canvas=FigureCanvas(fig)
  png_output = StringIO.StringIO()
  canvas.print_png(png_output)
  png_output = png_output.getvalue().encode("base64")

  # Return word clouds for different comments 
  word_cloud_comments = {} # key: cluster_label, val: 
  for lab in range(3):
    comment_keywords = getKeywords(rep_comments[lab]['comment'])
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

  # return render_template("output.html", article_summary = article_summary, the_result = the_result, RepComment = rep_comments)

  return render_template("output.html", title_png = urllib.quote(title_cloud_png_output.rstrip('\n')), 
    article_summary = article_summary,  RepComment = rep_comments, comment_coulds = word_cloud_comments, 
    pie_png = urllib.quote(pie_png_output.rstrip('\n')), img_data=urllib.quote(png_output.rstrip('\n')))

