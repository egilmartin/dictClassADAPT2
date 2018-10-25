# -*- coding: utf-8 -*-
# author: Kyusong Lee
from __future__ import unicode_literals  # at top of module

import random
import re

from nltk import tokenize
from pymongo import MongoClient

# redis is a data structure store used in communication with dialcrowd
from database.redis_api import RedisAPI

# Edu is the class for the cloze game which will be connected to dialcrowd
class Edu(object):
    # need to add text for extra divs - grid and scratchpad,
    # add SSML tabs to cut up speech or check if this is already being done using <p> tags (Tony?)
    # Expand game sequence to add scratchpad step
    def __init__(self):
        intro = "INTRODUCTION. Welcome to Dictogloss. Close your eyes and listen."
        #client = MongoClient(host="mongodb://kyusong:ianlee1022@ds251362.mlab.com:51362/dictclass")
        # this sets up access to the mongodb database where stories are kept
        client = MongoClient(host="mongodb://emerg55:emerg55@ds113703.mlab.com:13703/dictstories")


        # initiate list for answered words
        self.answered = []

        # choose a story at random from database
        sess = random.choice(list(client["dictstories"].sessions.find()))
        self.token_words = tokenize.word_tokenize(sess["text"])

        # set up List, which will hold a ____ for each word and the punctuation
        List = []

        # iterate through words in self.token_words. If it's a word, add a ____ to list, if not, keep (e.g. punctuation)
        for w in self.token_words:
            if re.match("^\w+$", w):
                List.append("____")
            else:
                List.append(w)

        # set up a hidden version of utterance - this outputs alternate text to speech bubble while tts speaks sys_utter
        self.hidden = " ".join(List) + "HIDDEN OK" + " <p>Right.Now, type your first word in the box"
        self.scratchpad = "This will be the scratchpad text appearing in extraDiv2 on dialcrowd side"
        self.grid = " ".join(List) + "<p>EXTRA DIV 1 OK" + " <p>Right. Now, type your first word in the box"
        self.original = sess["text"]
        self.sys_utter = 'system utterance ' + intro + sess["text"] + "SYS speaking, type your first word in the box."


    def forward(self, text):
        # moves game on after intro
        # check user has only typed one word for guess, reprompt if not, else send to check answer
        if len(text.split(" ")) > 1:
            self.set_utter("Please type one only word")
        else:
            self.check_answer(text)
        return

    def set_utter(self, text):
        # set system utterance
        self.sys_utter = text

    def check_answer(self, word):
        # generate list for blanks and answered words display
        List = []
        is_answer = False
        is_end = True
        self.set_utter(random.choice(["Sorry. ", "Not there, I'm afraid.  ",""]) + "Try again.")
        for w in self.token_words:
            if re.match("^\w+$", w) and not w.lower() == word.lower() and not w.lower() in self.answered:
                List.append("____")
                is_end = False
            elif w.lower() == word.lower():
                is_answer = True
                self.set_utter(random.choice(["Well done. ", "Great! ", "Fantastic. "]))
                List.append(w)
            else:
                List.append(w)
        # set hidden display to new grid
        self.hidden = self.get_utt() + "<p>" + " ".join(List)
        self.scratchpad = "This will STILL be the div 2 scratchpad"
        self.grid = "and this is still div 1 ".join(List)
        self.answered.append(word.lower())
        # ask kyusong what this does
        if is_end:
            self.__init__()
        return is_answer

    def get_utt(self):
        return self.sys_utter

    def get_hint(self):
        return

    def get_sys(self):
        return

    def get_display(self):
        return

class Game(object):
    def __init__(self):
        self.agent_pool = RedisAPI()
        self.edu = Edu()

    def start(self, sessionID):
        self.edu = Edu()
        self.agent_pool.refresh(sessionID)
        self.agent_pool.set(sessionID, self.edu)
        response = {"sessionID": sessionID, "sys": self.edu.sys_utter, "version": "1.0", "extraDiv1":"message extracdiv1",
                    "timeStamp": "yyyy-MM-dd'T'HH-mm-ss.SSS", "terminal": False, "display": self.edu.hidden
                    }
        return response

    def response(self, sessionID, text):
        agent = self.agent_pool.get(sessionID)
        agent.forward(text)
        self.agent_pool.set(sessionID, agent)
        response = {"sessionID": sessionID, "sys": agent.sys_utter, "version": "1.0-xxx", "extraDiv1":"message extracdiv1",
                    "timeStamp": "yyyy-MM-dd'T'HH-mm-ss.SSS", "display": agent.hidden,
                    "terminal": False}
        return response


if __name__ == "__main__":
    E = Edu()
