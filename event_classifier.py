#Subigya Nepal. @SkNepal
#Text Classifier for TechBhet.com

from facepy import GraphAPI
from facepy.utils import get_extended_access_token
import json, time, pickle
import os, csv, re
import shelve
import sqlite3

class event_classifier(object):
    
    def load_classifier(self):
        self.clf = pickle.load(open(os.path.join('classifier.pkl'),'rb'))
        self.vect = pickle.load(open(os.path.join('vectorizer.pkl'),'rb')) 

    def check_time(self):
        self.shelfFile = shelve.open('lastrun')
        self.current_epoch_time = int(time.time())

    def load_groups(self):
        with open('groups.json') as groups_list:
            self.groups = json.load(groups_list)
            
    def get_token(self):     
        try:
            self.token = shelve.open('token')
            self.access_token = self.token['token']
            self.graph = GraphAPI(self.access_token)
            graph.get('/me')
        except:
            self.access_token = self.extend_token(self.access_token)
            self.token['token'] = self.access_token
            self.graph = GraphAPI(self.access_token)
        self.token.close()
                
    def extend_token(self, old_token):
        application_id = APP_KEY
        application_secret_key = APP_SECRET
        long_lived_access_token, expires_at = get_extended_access_token(old_token, application_id, application_secret_key)
        return long_lived_access_token
        
    def find_and_classify_events(self):    
        self.events_list = []
        self.events_dict = {}
        for key, value in self.groups.iteritems():
            group_id = str(value)
            data = self.graph.get( group_id + "/feed", retry=3,  since=self.shelfFile['since'], until=self.current_epoch_time)
            conn = sqlite3.connect('kb.sqlite')
            c = conn.cursor()
            c.execute('CREATE TABLE IF NOT EXISTS posts_db (id TEXT, time TEXT, message TEXT, label INTEGER, date TEXT)')
            for item in data["data"]:
                if 'message' in item:
                    message = item['message']
                    message_id = item['id']
                    message_time = item['updated_time']
                    link = "http://www.facebook.com/groups/" + message_id.split("_")[0] + "/" + message_id.split("_")[1]

                    tfidf_message = vect.transform([message])
                    prediction = clf.predict(tfidf_message)

                    c.execute("INSERT INTO posts_db VALUES (?, ?, ?, ?, DATETIME('now'))", (message_id, message_time, message, prediction[0]))
                    conn.commit()

                    if (1 in prediction):
                        self.events_dict = { 
                           'message': message,
                            'link'  : link
                        }

                        self.events_list.append(self.events_dict)
        conn.close()
      
        
    def remove_duplicates(self):
        self.seen_values = set()
        self.without_duplicates = []
        for text in self.events_list:
            value = text['message']
            if value not in self.seen_values:
                self.without_duplicates.append(text)
                self.seen_values.add(value)
                
    def send_email(self, send_from, send_to, subject, body, password ):      
        if (len(self.without_duplicates) > 0):

            import smtplib
            from email.MIMEMultipart import MIMEMultipart
            from email.MIMEText import MIMEText

            fromaddr = send_from 
            toaddr = send_to 
            msg = MIMEMultipart()
            msg['From'] = fromaddr
            msg['To'] = toaddr
            msg['Subject'] = subject 

            body = body
            body += "\n \n"
            for n,i in enumerate(self.without_duplicates):
                body += i.values()[1]
                body += "\n \n"

            msg.attach(MIMEText(body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(fromaddr, password)
            text = msg.as_string()
            server.sendmail(fromaddr, toaddr, text)
            server.quit()  
            
        self.shelfFile['since'] = self.current_epoch_time
        self.shelfFile.close()
        
        
find_me_some_events = event_classifier()
find_me_some_events.load_classifier()
find_me_some_events.check_time()
find_me_some_events.load_groups()
find_me_some_events.get_token()
find_me_some_events.find_and_classify_events()
find_me_some_events.remove_duplicates()
find_me_some_events.send_email(from, to, "New Events", 
                              "The following new events were found by the classifier: ", password )

