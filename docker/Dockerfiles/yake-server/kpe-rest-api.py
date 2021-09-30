"""
Credits @arianpasquali
https://gist.githubusercontent.com/arianpasquali/16b2b0ab2095ee35dbede4dd2f4f8520/raw/ba4ea7da0d958fc4b1b2e694f45f17cc71d8238d/yake_rest_api.py

The simple example serving YAKE as a rest api.

instructions:

 pip install flasgger
 pip install git+https://github.com/LIAAD/yake

 python yake_rest_api.py

open http://127.0.0.1:5000/apidocs/
"""
import sys
from flask import Flask, jsonify, request

from flasgger import Swagger
import pandas as pd
import traceback
import logging
import urllib

logging.basicConfig()
logger = logging.getLogger('server')
try:
    import simplejson as json
except ImportError:
    import json
try:
    from http import HTTPStatus
except ImportError:
    import httplib as HTTPStatus

import yake
import spacy
zh_nlp = spacy.load("zh_core_web_lg")

app = Flask(__name__)
app.config['SWAGGER'] = {
    'title': 'Yake API Explorer',
    'uiversion': 3
}
swagger = Swagger(app)

extractors={}
AdditionalKeyphrases_file='AdditionalKeyphrases.csv'
try:
    g_additionalKeyphrases_df=pd.read_csv(AdditionalKeyphrases_file)
except:
    g_additionalKeyphrases_df=pd.DataFrame({'DomainCode':[],'Language':[],'Keyphrase':[],'Score':[]})


@swagger.validate('content')
@app.route('/extract_keyphrases/',methods=['POST'])
def extract_keyphrases():
    """Example endpoint return a list of keywords using YAKE
    ---
    consumes:
      - application/json
    produces:
      - application/json
    parameters:
        - name: content
          in: body
          description: content object
          required: true
          schema:
            $ref: '#/definitions/content'

    requestBody:
        description: Optional description in *Markdown*
        required: true
        content:
          application/json:
            schema:
              id: content
              type: object


    responses:
      200:
        description: Extract keywords from input text
        schema:
            $ref: '#/definitions/result'

    definitions:
      content:
        description: content object
        properties:
          text:
            type: string
          language:
            type: string
          max_ngram_size:
            type: integer
            minimum: 1
          number_of_keywords:
            type: integer
            minimum: 1
        required:
          - text
          - language
          - max_ngram_size
          - number_of_keywords
        example:   # Sample object
            text: Sources tell us that Google is acquiring Kaggle, a platform that hosts data science and machine learning   competitions. Details about the transaction remain somewhat vague , but given that Google is hosting   its Cloud Next conference in San Francisco this week, the official announcement could come as early   as tomorrow.  Reached by phone, Kaggle co-founder CEO Anthony Goldbloom declined to deny that the   acquisition is happening. Google itself declined 'to comment on rumors'.   Kaggle, which has about half a million data scientists on its platform, was founded by Goldbloom   and Ben Hamner in 2010. The service got an early start and even though it has a few competitors   like DrivenData, TopCoder and HackerRank, it has managed to stay well ahead of them by focusing on its   specific niche. The service is basically the de facto home for running data science  and machine learning   competitions.  With Kaggle, Google is buying one of the largest and most active communities for   data scientists - and with that, it will get increased mindshare in this community, too   (though it already has plenty of that thanks to Tensorflow and other projects).   Kaggle has a bit of a history with Google, too, but that's pretty recent. Earlier this month,   Google and Kaggle teamed up to host a $100,000 machine learning competition around classifying   YouTube videos. That competition had some deep integrations with the Google Cloud Platform, too.   Our understanding is that Google will keep the service running - likely under its current name.   While the acquisition is probably more about Kaggle's community than technology, Kaggle did build   some interesting tools for hosting its competition and 'kernels', too. On Kaggle, kernels are   basically the source code for analyzing data sets and developers can share this code on the   platform (the company previously called them 'scripts').  Like similar competition centric sites,   Kaggle also runs a job board, too. It's unclear what Google will do with that part of the service.   According to Crunchbase, Kaggle raised $12.5 million (though PitchBook says it's $12.75) since its   launch in 2010. Investors in Kaggle include Index Ventures, SV Angel, Max Levchin, Naval Ravikant,   Google chief economist Hal Varian, Khosla Ventures and Yuri Milner
            language: en
            max_ngram_size: 3
            number_of_keywords: 10
      result:
        type: array
        items:
          minItems: 0
          type: object
          required:
            - name
            - value
          properties:
            ngram:
              type: string
            score:
              type: number
    """
    try:
        #read params
        params = request.json
        if params is None:
            params=request.form
        print (params.get("language","language"))
        if params.get("text",None) is None:
            return jsonify("Invalid text"), HTTPStatus.BAD_REQUEST
        if len(params["language"]) != 2:
            return jsonify("Invalid language (should be 2 characters)"), HTTPStatus.BAD_REQUEST
        

        text = params["text"]
        language = params["language"]
        max_ngram_size = int(params.get("max_ngram_size",3))
        number_of_keywords = int(params.get("number_of_keywords",20))
        dedupFunc = params.get("dedupFunc","sqem")
        dedupLim =  float(params.get("dedupLim",0.9))
        windowsSize =  int(params.get("windowsSize",1))
        domainCode =  params.get("domainCode","NONE")
        
        #Preprocess text if needed
        text=preprocess_text(text,language)

        #get extractor from the cache
        key ='_'.join([language,str(max_ngram_size),str(number_of_keywords),str(dedupFunc),str(dedupLim),str(windowsSize)])
        extractor=extractors.get(key,None)
        #build extractor if not found in cache
        if (extractor is None) or (params.get("useExisting","True")=="False"):
            extractor = yake.KeywordExtractor(lan=language,
                                        n=max_ngram_size,
                                        top=number_of_keywords,
                                        dedupFunc=dedupFunc,
                                        dedupLim=dedupLim,
                                        windowsSize=windowsSize
                                        )
            extractors[key]=extractor
        # just for testing return jsonify([{'ngram':'hello','score':1}]), HTTPStatus.OK
        #Finally extarct the keywords
        keywords = extractor.extract_keywords(text)
        result  = [{"ngram":x[0] ,"score":x[1]} for x in keywords]
        
        #add user define keywords
        result = addDefinedKeyphrases(text,domainCode,result,language)#[:number_of_keywords]
        return jsonify(result), HTTPStatus.OK
    except IOError as e:
        logger.warning('Error', exc_info=True)
        return jsonify("Language not supported"), HTTPStatus.BAD_REQUEST
    except Exception as ex:
        logger.warning('Error', exc_info=True)
        return jsonify(str(''.join(traceback.format_exception(etype=type(ex), value=ex, tb=ex.__traceback__)))), HTTPStatus.BAD_REQUEST
       
       
        
#Check for additional key phrases that were added by the admin manually        
def addDefinedKeyphrases(text,domainCode,result,language):
    if domainCode=="NONE": return result
    if domainCode=="ALL":
        add_keyphrases = g_additionalKeyphrases_df.sort_values('Score').groupby('Keyphrase').first().reset_index()[['Keyphrase','Score']].values
    else:
        add_keyphrases = g_additionalKeyphrases_df[g_additionalKeyphrases_df.DomainCode==domainCode][['Keyphrase','Score']].values
    if len(add_keyphrases)==0: return result
    lowerText=text.lower()  
    
    
    for add_key in add_keyphrases:
        print(add_key)
        found=False
        kp = add_key[0]
        score=add_key[1]
        add_key_set=set(kp.lower().split())
        for i,item in enumerate(result):
            intersect = add_key_set.intersection(item['ngram'].lower().split())
            #TODO check for stop words
            if len(intersect) > 0 :  # We found the add key phrase inside the existing 
                found = True
                result[i]['score']=min(result[i]['score'],score) #TODO update the score ? 
        if not found:
            if add_key[0].lower() in lowerText:
                result.insert(0,{"ngram":add_key[0] ,"score":score})
    result = sorted(result, key=lambda tup: tup['score'])  #sort by score
    return  result  

def preprocess_text(text,language): 
    if language=='zh':        
        doc = zh_nlp(text)
        tokens = [token.text for token in doc]
        text = ' '.join(tokens)
    return text

#@swagger.validate('content')
@app.route('/add_keyphrase/',methods=['POST'])
def handle_add_keyphrase():
    """ 
    definitions:
      content:
        description: content object
        properties:
        'DomainCode':[],'Language':[],'Keyphrase'
          domainCode:
            type: string
          language:
            type: string
          keyphrase:
            type: string
        required:
          - domainCode
          - language
          - keyphrase
    """       
    try:
        global g_additionalKeyphrases_df
        domainCode =  request.json.get("domainCode",None)
        if (domainCode is None) or (domainCode=='ALL')or(domainCode=='NONE'): return jsonify("Invalid domainCode"), HTTPStatus.BAD_REQUEST
        language =  request.json.get("language",None)
        if (language is None) or (len(language)!=2): return jsonify("Invalid language"), HTTPStatus.BAD_REQUEST
        keyphrase =  request.json.get("keyphrase",None)
        if keyphrase is None: return jsonify("Invalid keyphrase"), HTTPStatus.BAD_REQUEST
        if keyphrase in g_additionalKeyphrases_df[(g_additionalKeyphrases_df.DomainCode==domainCode)&(g_additionalKeyphrases_df.Language==language)].Keyphrase.unique():
            return jsonify('OK'), HTTPStatus.OK
        score = float(request.json.get("score",0.1))
        df_new = pd.DataFrame({'DomainCode':[domainCode],'Language':[language],'Keyphrase':[keyphrase],'Score':[score]})
        try:
            df = pd.read_csv(AdditionalKeyphrases_file)
            df = pd.concat([df,df_new],sort='Score')
        except:
            df = df_new # no previous data
        df.to_csv(AdditionalKeyphrases_file,index=False)
        g_additionalKeyphrases_df = df  
        return jsonify('OK'), HTTPStatus.OK
    except Exception as e:
        print(e)
        return jsonify(str(e)), HTTPStatus.BAD_REQUEST

#@swagger.validate('content')
@app.route('/delete_keyphrase/',methods=['POST'])
def handle_delete_keyphrase():
    try:
        global g_additionalKeyphrases_df
        domainCode =  request.json.get("domainCode",None)
        if (domainCode is None) or (domainCode=='ALL')or(domainCode=='NONE'): return jsonify("Invalid domainCode"), HTTPStatus.BAD_REQUEST
        language =  request.json.get("language",None)
        if (language is None) or (len(language)!=2): return jsonify("Invalid language"), HTTPStatus.BAD_REQUEST
        keyphrase =  request.json.get("keyphrase",None)
        if keyphrase is None: return jsonify("Invalid keyphrase"), HTTPStatus.BAD_REQUEST
        g_additionalKeyphrases_df = pd.read_csv(AdditionalKeyphrases_file)
        remove_idx =  g_additionalKeyphrases_df[(g_additionalKeyphrases_df.DomainCode==domainCode)&(g_additionalKeyphrases_df.Language==language)&(g_additionalKeyphrases_df.Keyphrase==keyphrase)].index.values
        if len(remove_idx)>0:
            new_df = g_additionalKeyphrases_df[~g_additionalKeyphrases_df.index.isin(remove_idx)]
            new_df.to_csv(AdditionalKeyphrases_file,index=False)
            g_additionalKeyphrases_df = new_df  
        return jsonify('OK'), HTTPStatus.OK
    except IOError as e:
        return jsonify("Language not supported"), HTTPStatus.BAD_REQUEST
    except Exception as e:
        print(e)
        return jsonify(str(e)), HTTPStatus.BAD_REQUEST
      
#@swagger.validate('content')
@app.route('/list_keyphrase/',methods=['POST'])
def handle_list_keyphrase():
    return jsonify(g_additionalKeyphrases_df.to_dict('records')), HTTPStatus.OK
   

@app.route('/index.html',methods=['GET'])
def handle_index():
    text='Failed to read form'
    try:
        with open('UI_test_form.html') as afile:
            text = afile.read()
    except Exception as e:
        logger.warning('Failed to read form', exc_info=True)
    return text, HTTPStatus.OK
   
        
if __name__ == "__main__":
    port = 5000
    try:
        port = int(sys.argv[1])
    except:
        pass
    logger.info("Starting Server on port %s", port)
    app.run(host='0.0.0.0',port=port, debug=True)
