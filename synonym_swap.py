# -*- coding: utf-8 -*-
"""Synonym Swap.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/104YHPOc2X6kHd-Hk1JAV4MBvU2mxWqxR

# Synonym Swapper
Author: Nick Abegg, nicholas.abegg@stvincent.edu

Date Created: 6/21/23

Code used for reference:

Saranya Venkat UID Code

Jooyoung Lee GPT/LM Lecture/Lab

Description: Takes human samples from TuringBench dataset and then swaps a word in each sentence of each text with a suitable synonym replacement.
"""

from detector import OpenaiDetector
bearer_token = '' # enter bearer token from open AI

od = OpenaiDetector(bearer_token)

old_results = []
new_results = []

import torch
import pandas as pd
from transformers import AutoTokenizer, AutoModelForCausalLM
from transformers.tokenization_utils_base import BatchEncoding
import nltk
nltk.download('wordnet')
from nltk.corpus import wordnet

import nltk.data
from nltk.tokenize import word_tokenize
nltk.download('punkt')

from nltk.corpus import stopwords
nltk.download('stopwords')

import copy
import string
import re

import time


# loads the dataset
from datasets import load_dataset

dataset = load_dataset("turingbench/TuringBench")


human = []
# filters through the dataset for the first 50 human labeled text
i = 0
while len(human) < 50:
    if dataset['train'][i]['label'] == 'human':
        human.append(dataset['train'][i])
    i += 1
    
    
gpt3 = []
# filters through the dataset for the first 50 gpt3 generaetd text
i = 0
while len(gpt3) < 50:
    if dataset['train'][i]['label'] == 'gpt3':
        gpt3.append(dataset['train'][i])
    i += 1
    
# combines both datasets
human_gpt3 = human + gpt3


new_text_list = []
old_text_list = []


"""
Removes the special characters and punctuation from the given word.

Args:
    word (str): The word for which the special characters and punctuation is removed.

Returns:
    The word now with special characters and punctuation removed
"""

def remove_special_characters(word):
    # Remove punctuation
    word = word.translate(str.maketrans('', '', string.punctuation))

    # Remove special characters
    word = re.sub(r"[^a-zA-Z0-9]", "", word)

    return word


"""Extracts synonyms for a given phrase using WordNet.

Args:
    phrase (str): The phrase for which synonyms are to be extracted.

Returns:
    list: A list of synonyms for the given phrase.
"""

def synonym_extractor(phrase):
    from nltk.corpus import wordnet
    synonyms = []

    for syn in wordnet.synsets(phrase):
        for l in syn.lemmas():
          if l.name() != phrase:
            synonyms.append(l.name())

    return synonyms


"""Splits a string into a list of words.

Args:
    string (str): The input string to be split.

Returns:
    list: A list of words from the input string.
"""

def split_string(string):
    words = string.split()
    return words


"""Takes a sentence and a target word in that sentence and replaces the target with a suitable synonym.

Args: text (str): A senence that will be altered
      targeWord(str): A single word that is found in the text string

Returns: A new sentence that has had one word changed
"""

def synonym_Changer(text, targetWord):

    ####################################################
    ## Synonym extraciton and target masking ###########
    ####################################################

    text_ind = -1

    text_list = split_string(text)  #splits the text into a list of words

    # locate the target word
    for i in range(len(text_list)):
        if targetWord == remove_special_characters(text_list[i]):
            text_ind = i

    # if target word can't be found then do not change sentence
    if text_ind == -1:
        return text

    # get words up to the target word in the sentence
    sentence_to_target = text_list[0:text_ind]


    synonyms = synonym_extractor(targetWord)  # Extract the synonyms for the target word

    # if no synonyms for a word are found then do not change sentence
    if not synonyms:
        return text

    # places the masking token into the sentence
    text_list[text_ind] = "[MASK]"
    masked_token = "[MASK]"

    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    tokenizer.add_tokens(masked_token)  # adds the masking token to the GPT2 tokenizer

    model = AutoModelForCausalLM.from_pretrained("gpt2")


    text = ' '.join(text_list)
    text_to_target = ' '.join(sentence_to_target)   # combine the sentence again

    # generate tokens for the sentence up to the target
    ttt_input_ids = tokenizer.encode(text_to_target, return_tensors='pt')


    ####################################################
    ## Synonym Probability Calculation #################
    ####################################################

    # calculate the probability of the sentence up to the target
    with torch.no_grad():
        logits = model(input_ids=ttt_input_ids)[0]
    probabilities = torch.softmax(logits, dim=-1)

    synonyms_probs = {}

    # for all of the synonyms, calculate the probability of the synonym appearing next in the sentence
    for i in range(len(synonyms)):
        word_index = tokenizer.encode(synonyms[i])[0]
        probability = probabilities[0, -1, word_index].item()
        synonyms_probs[synonyms[i]] = probability

    # prints the probabilites of each synonym appearing
    #print(f"For the phrase '{text_to_target}', the probabilities of the synonyms of '{targetWord}' appearing next in the sentence are:")

    #print(f"\n'{synonyms_probs}'")

    # calculate synonym with highest chance of appearing in the sentence
    max_prob_word = max(synonyms_probs, key=synonyms_probs.get)
    max_prob = synonyms_probs[max_prob_word]

    #print("\nThe word with the highest probability is: " + max_prob_word + " with a probability of ", max_prob)


    ####################################################
    ## Updating sentence with most prob. word   ########
    ####################################################

    tok_sentence = tokenizer(text, return_tensors='pt')  # Generate the tokens for the sentence

    target_index = None
    for i in range(len(tok_sentence.input_ids[0])):  # Get the index of the masked_token
        if masked_token == tokenizer.decode([tok_sentence.input_ids[0][i].item()]):
            target_index = i

    # here we will now replace the masked_token with the most probable synonym that we just calculated
    sentence_list = []
    
    word_location = -1
    
    # if a target is properly located
    if target_index is not None:
        new_word = max_prob_word

        updated_sentence = tokenizer.decode(tok_sentence.input_ids[0])
        sentence_list = split_string(updated_sentence)
        
        # checks for the masking token and gets location
        for i in range(len(sentence_list)):
            if sentence_list[i] == '[MASK]':
                word_location = i
        
        # if found insert new word. If not return text
        if not(word_location == -1):
            sentence_list[word_location] = new_word
        else:
            return text

        # create the final sentence
        updated_sentence = ' '.join(sentence_list)


    return (updated_sentence)

"""Takes a piece of text and parses through to find a suitable word in each sentence of the text. Then replaces that word with a synonym of that word. Prints the orignal sentence as well as the alternate sentence for each sentence in the text

Args: text(dictionary) A dictionary containing the generated text as well as the label that labels the text human generated

Returns: Nothing
"""

def start_parse_sentence(text):
    
    # parses out sentences
    sentences = tokenizer.tokenize(text['Generation'])

    old_sentences = copy.copy(sentences)    # makes a copy for comparison output

    # for every sentence, select a suitable word, then change that word with a suitable synonym
    for i in range(len(sentences)):

        # gets each word/character in each sentence
        words = word_tokenize(sentences[i])

        # if the sentence is long enough, pick a word in the "middle"
        if len(words) >= 3:
            word_index = int(len(words)/2)
            word = words[word_index]
        
            # until the word is not in stops, a piece of punctuation or has no synonyms keep looking for a more suitable replacement.
            while ((word in stops) or (word in punctuation_list) or not(synonym_extractor(word)) or len(word) < 2 or not(word.isalpha())) and word_index < len(words)-1:
                word_index += 1
                word = words[word_index]
            
            if not(word_index == len(words)):    
                # calls the method that changes the target word to the proper synonym
                sentences [i] = synonym_Changer(sentences[i], word)
            #print(sentences[i])

    #print ('\n-----\n'.join(sentences))

    # prints output of old and new sentence for easy comparison
    for i in range(len(sentences)):
      print(f"Old Sentence #'{i + 1}': ", old_sentences[i])
      print(f"New Sentence #'{i + 1}': ", sentences[i])
      print("\n")
      
    
    
    old_text = ' '.join(old_sentences)
    new_text = ' '.join(sentences)
    
    old_text_list.append(old_text)
    new_text_list.append(new_text)
    
    # old_results.append(od.detect(old_text))
    # # while(old_results[-1] == 'Check prompt, Length of sentence it should be more than 1,000 characters'):
    # #     old_results[-1] = od.detect(old_text)
        
    # new_results.append(od.detect(new_text))
    # # while(new_results[-1] == 'Check prompt, Length of sentence it should be more than 1,000 characters'):
    # #     new_results[-1] = od.detect(new_text)
    
    # time.sleep(18)

    print("\n Stop Point \n")


"""#############################
# Main ######################
#############################
"""

# setsup stop words using NLTK's stopword list
stops = set(stopwords.words('english'))

# setup punctuation list
punctuation_list = ['!', '"', '#', '$', '%', '&', "'", '(', ')', '*', '+', ',', '-', '.', '/', ':', ';', '<', '=', '>', '?', '@', '[', '\\', ']', '^', '_', '`', '{', '|', '}', '~']

# gets a tokenizer from nltk to parse out each respective sentence
tokenizer = nltk.data.load('tokenizers/punkt/english.pickle')

# used for only human data
# for i in range(len(human)):
#     start_parse_sentence(human[i])

# used for gpt3 only data
# for i in range(len(gpt3)):
#     start_parse_sentence(gpt3[i])

# used for combine data of gpt3 and human
for i in range(len(human_gpt3)):
    start_parse_sentence(human_gpt3[i])
    
for d in range(len(new_results)):
    print(new_results[d]['Class'])  
    
new_labels = [d['Class'] for d in new_results]
new_values = [d['AI-Generated Probability'] for d in new_results]

old_labels = [d['Class'] for d in old_results]
old_values = [d['AI-Generated Probability'] for d in old_results]

