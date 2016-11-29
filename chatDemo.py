#chatbot demo file - Foaad Khosmood
#You need the NLTK library for this.
#See http://www.nltk.org/api/nltk.chat.html



# We import four chatbots supported by NLTK
import sys
from nltk.chat import eliza,zen,rude,suntsu

bots = [("rude", rude.rude_chatbot), ("eliza", eliza.eliza_chatbot), ("zen", zen.zen_chatbot), ("Sun Tsu", suntsu.suntsu_chatbot)]

response = ""

print("Bots in this conversation: ",[b[0] for b in bots])

while response != "q" :
   response = input("] ").strip()
   for bot in bots:
      print(bot[0]+": ",bot[1].respond(response))


