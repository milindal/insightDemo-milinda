# Should I import modules elsewhere?
from urllib2 import Request, urlopen, URLError
import numpy as np 
import json 
import pandas as pd 
import matplotlib.pyplot as plt 
import gensim as gs
import nltk
from sklearn.cluster import KMeans
import pickle
import string 
import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
import sys 
import urllib
import os

alchemy_folder_path = os.environ.get('ALCHEMY_API_PATH')
data_folder_path = os.environ.get('CONV_APP_DATA_PATH')

sys.path.insert(0, alchemy_folder_path)
from alchemyapi import AlchemyAPI
alchemyapi = AlchemyAPI()

def UpdateDatabase(url_string, database_dict): 
	# Updates database_dict when url_string is not present in database_dict
	# Inputs: url_string 
	#         database_dict: dictionary to be updated with data of the url_string 
	# Output: updated_database_dict. Also pickle the updated_db_dict to the data file 

	comm_api_key = 'a635c56edacc7190b18cacc2c6c6d158:11:61744518'
	article_search_api_key = 'e66bba01217ff9552fd21988363b7e9f:11:61744518' 

	base_request_string = 'http://api.nytimes.com/svc/community/v3/user-content/url.json?url=' + url_string + '&' + 'api-key=' + comm_api_key 
	comments_list = []
	try:
		print 'getting the comments data'
		for offset in np.arange(0, 1000, 25):            
			request_str = base_request_string + '&offset=' + str(offset)
			request = Request(request_str)
			temp_data_list = json.load(urlopen(request))['results']['comments']
			if len(temp_data_list) == 0: 
				break
			comments_list += temp_data_list
	except URLError, e:
		print 'No data received. Got an error code:', e
        
	comments_df = pd.DataFrame(comments_list)
      
    # Get the article data 
	article_request_string = 'http://api.nytimes.com/svc/search/v2/articlesearch.json?&fq=web_url:("'+ url_string + '")' + '&' + 'api-key=' + article_search_api_key 
	print article_request_string
	try:
		print 'getting the artice data'
		request = Request(article_request_string)
		temp_data = json.load(urlopen(request))
		print len(temp_data)
	except URLError, e:
		print 'No data received. Got an error code:', e
      
	# Populate the database 
	database_dict[url_string] = {'comments_df': comments_df, 
								 'title': temp_data['response']['docs'][0]['headline']['main'],
								 'abstract': temp_data['response']['docs'][0]['abstract'],
								 'snippet': temp_data['response']['docs'][0]['snippet'],
 								 'pub_date': temp_data['response']['docs'][0]['pub_date'], 
								 'keyword_dict': temp_data['response']['docs'][0]['keywords'],
								 'image_part_url': temp_data['response']['docs'][0]['multimedia'][0]['url']
								 }

	senti_pos = [] 
	senti_neg = [] 
	senti_neutral = [] 
	for comment_text in database_dict[url_string]['comments_df']['commentBody']:
		filtered_comment = filter(lambda x: x in string.printable, comment_text)
		data_urlencoded = urllib.urlencode({"text": filtered_comment}) 
		u = urllib.urlopen("http://text-processing.com/api/sentiment/", data_urlencoded)
		the_page = u.read()
		senti_pos.append(json.loads(the_page)['probability']['pos'])
		senti_neg.append(json.loads(the_page)['probability']['neg'])
		senti_neutral.append(json.loads(the_page)['probability']['neutral'])
	database_dict[url_string]['comments_df']['senti_pos'] = senti_pos
	database_dict[url_string]['comments_df']['senti_neg'] = senti_neg
	database_dict[url_string]['comments_df']['senti_neutral'] = senti_neutral

	pickle.dump(database_dict, open( data_folder_path +'updated_database_dict.p', 'wb'))

	return database_dict

def getKeywords(comment_text):
	# Get a list of the top 10 keywords from the comment text using Alchemy API 
	response = alchemyapi.keywords('text', comment_text) #, {'sentiment': 1})
	kw = []
	if response['status'] == 'OK':
		#print('## Response Object ##')
		#print(json.dumps(response', indent=4))
		try:
			# if response["keywords"]:
			for keyword in response['keywords']:
				#print(keyword['text'].encode('utf-8')', keyword['relevance'])
				s = filter(lambda x: not x.isdigit(), keyword['text'].encode('utf-8').lower())
				for c in string.punctuation:
					s= s.replace(c,"")
				if s:
					kw.append(s)
				if len(kw) == 10:
					return kw
		except KeyError:
			pass
	else:
		print('Error in keyword extaction call: ', response['statusInfo'])
		if response['statusInfo'] == 'daily-transaction-limit-exceeded':
			return ['limit-exceeded']
		return ['alchemyAPI-error']

	return kw[:10]



def StripHtml(data):
	p = re.compile(r'<.*?>')
	return p.sub('', data)


def GetRepresentativeComments(comments_df): 
	# Input: comments_df - Dataframe with the information of the comments
	# Output: closest_trusted - Dictionary with key: cluster_id, val: { 'comment': closest trusted comment, 'count': Ncomments}
	#        If there is no trusted comment in the cluster, we choose the closest comment to 
	#        the centroid
	SOME_FIXED_SEED = 70
	np.random.seed(SOME_FIXED_SEED)

	comment_bodies = comments_df['commentBody']

	ps = PorterStemmer()
	stop_words = set(stopwords.words('english')).union(set(['``', "''", '.', ',', '!', ':', '[', ']', '...', "\'\'" , '']))

    # round 1: tokenizing, stemming, removing html tags and stop words
	comment_texts = [[ps.stem(filter(lambda x: x in string.printable, word).lower()) for word in nltk.word_tokenize(StripHtml(comment)) 
                	if word not in stop_words] for comment in comment_bodies]
#     print len(comment_texts)

    # round 2: filtering, remove words from comments that are too short or which are not alphabets
	comment_texts = [[word for word in comment if (len(word) > 2 and not word.isdigit())] for comment in comment_texts]
#     print comment_texts[0:5]

    # create a dictionary for the words that appear in the comments 
	dictionary = gs.corpora.Dictionary(comment_texts)

    # Bag of words representation for the comments 
	comment_corpus = [dictionary.doc2bow(text) for text in comment_texts]

    # Train tf-idf model on the comment_corpus
	tfidf = gs.models.TfidfModel(comment_corpus)
	corpus_tfidf = tfidf[comment_corpus]

    # initialize an LSI transformation
	lsi = gs.models.LsiModel(corpus_tfidf, id2word=dictionary, num_topics=5) 
	corpus_lsi = lsi[corpus_tfidf] # create a double wrapper over the original corpus: bow->tfidf->fold-in-lsi
#     lsi.print_topics(5)

    # Create the coordinates for the corpus to send into the Kmeans clustering algorithm
	comments_coords_lsi_ND = [] 
	N_dimensions = 10
	for item in corpus_lsi: 
		coord_temp = [0]*N_dimensions
		for val_tuple in item:
			if val_tuple[0] < N_dimensions: 
				coord_temp[val_tuple[0]] = val_tuple[1]
		comments_coords_lsi_ND.append(coord_temp)

	## Clustering 
	k_fixed = 3
	kmeans = KMeans(k_fixed).fit(np.array(comments_coords_lsi_ND)[:, 0:10])

	# Calculate the distances 
	dist_from_centroid = [ np.sqrt(np.sum((np.array(comments_coords_lsi_ND)[i,0:10] - kmeans.cluster_centers_[lab])**2)) for i, lab in 
	   enumerate(kmeans.labels_) ]

    # Get the three closest comments 
	closest_trusted = {}
	for lab in range(3):
		closest_trusted[lab] = {} 
#         print 'cluster: ', lab
		indices = [i for i, x in enumerate(kmeans.labels_) if x == lab]

		# Get the comment that is closest to the centroid
		min_dist = 1000 
		closest_idx = -1
		for i in indices: 
			if dist_from_centroid[i] < min_dist: 
				min_dist = dist_from_centroid[i]
				closest_idx = i

		# Get the trusted comment that is closest to the centroid
		closest_trusted_idx = -2
		min_dist= 1000
		for i in indices: 
			if comments_df.loc[i, 'trusted'] == 1: 
				if dist_from_centroid[i] < min_dist: 
					min_dist = dist_from_centroid[i]
					closest_trusted_idx = i
		            
		# closest trusted or closest 
		if closest_trusted_idx != -2: 
			closest_trusted[lab]['comment'] = StripHtml(comments_df.loc[closest_trusted_idx, 'commentBody'])
		else: 
			closest_trusted[lab]['comment'] = StripHtml(comments_df.loc[closest_idx, 'commentBody'])

		closest_trusted[lab]['count'] = sum(kmeans.labels_ == lab)
        
	return closest_trusted