#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>
# slight modifications by Foaad Khosmood
# modified for CPE 582 Lab 4 by Logan Williams and Justin Postigo
#   based on info from http://cplug.org/about/a-brief-history-of-cplug/
#
# command to add bot to irc: python3 ircbot582.py irc.freenode.net "#CPE582" botname 

"""A simple example bot.
This is an example bot that uses the SingleServerIRCBot class from
irc.bot.  The bot enters a channel and listens for commands in
private messages and channel traffic.  Commands in channel messages
are given by prefixing the text by the bot name followed by a colon.
It also responds to DCC CHAT invitations and echos data sent in such
sessions.
The known commands are:
    stats -- Prints some channel information.
    disconnect -- Disconnect the bot.  The bot will try to reconnect
                  after 60 seconds.
    die -- Let the bot cease to exist.
    dcc -- Let the bot invite you to a DCC CHAT connection.
"""

import irc.bot
import irc.strings
from irc.client import ip_numstr_to_quad, ip_quad_to_numstr
import json
import re, time
import nltk


with open('songs.json') as data_file:
    data = json.load(data_file)

for song in data:
    data[song]["bigrams"] = list(nltk.bigrams(nltk.word_tokenize(data[song]["lyrics"])))

def get_song_match(comment_bigrams):
    for song in data:
        for song_bigram in data[song]['bigrams']:
            if song_bigram in comment_bigrams:
                regex = r"[^\/]*" + re.escape(" ".join(song_bigram)) + r"[^\/]*\/[^\/]*"
                matches = re.search(regex, data[song]['lyrics'])
                if matches:
                    lyrics_snippet = matches.group(0)
                    return (song, lyrics_snippet)
    return (None,None) # no bigram match

class TestBot(irc.bot.SingleServerIRCBot):
    previous_song = ""

    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel

    def on_nicknameinuse(self, c, e):
        c.nick(c.get_nickname() + "_")

    def on_welcome(self, c, e):
        c.join(self.channel)

    def on_privmsg(self, c, e):
        self.do_command(e, e.arguments[0])

    def on_pubmsg(self, c, e):
        a = e.arguments[0].split(":", 1)
        if len(a) > 1 and irc.strings.lower(a[0]) == irc.strings.lower(self.connection.get_nickname()):
            self.do_command(e, a[1].strip())
        else:
            comment_bigrams = list(nltk.bigrams(nltk.word_tokenize(e.arguments[0])))
            song_match,lyrics_snippet = get_song_match(comment_bigrams)
            if lyrics_snippet:
                time.sleep(3)
                c.privmsg(self.channel, lyrics_snippet)
                self.previous_song = song_match

    def on_dccmsg(self, c, e):
        # non-chat DCC messages are raw bytes; decode as text
        text = e.arguments[0].decode('utf-8')
        c.privmsg("You said: " + text)

    def on_dccchat(self, c, e):
        if len(e.arguments) != 2:
            return
        args = e.arguments[1].split()
        if len(args) == 4:
            try:
                address = ip_numstr_to_quad(args[2])
                port = int(args[3])
            except ValueError:
                return
            self.dcc_connect(address, port)

    def do_command(self, e, cmd):
        time.sleep(2)

        nick = e.source.nick
        c = self.connection

        if cmd == "disconnect":
            self.disconnect()
        elif cmd == "die":
            self.die()
        elif cmd == "stats":
            for chname, chobj in self.channels.items():
                c.notice(nick, "--- Channel statistics ---")
                c.notice(nick, "Channel: " + chname)
                users = sorted(chobj.users())
                c.notice(nick, "Users: " + ", ".join(users))
                opers = sorted(chobj.opers())
                c.notice(nick, "Opers: " + ", ".join(opers))
                voiced = sorted(chobj.voiced())
                c.notice(nick, "Voiced: " + ", ".join(voiced))
        elif cmd == "dcc":
            dcc = self.dcc_listen()
            c.ctcp("DCC", nick, "CHAT chat %s %d" % (
                ip_quad_to_numstr(dcc.localaddress),
                dcc.localport))
        #elif cmd in initial_greetings:
        #    c.notice(nick, cmd + " back to you!")
        elif cmd == "*forget":
            #forgets stuff
            self.previous_song = ""
        elif cmd == "about":
            c.privmsg(self.channel, "I was made by Justin Postigo and Logan Williams for Foaad Khosmood for the CPE 582 class in Fall 2016.")
        elif cmd.lower() in ['hi','hello']:
            c.privmsg(self.channel, str(nick) + ": Hello!")
        elif cmd.lower() in ['how are you?',"what's happening?"]:
            c.privmsg(self.channel, str(nick) + ": I'm fine")
            time.sleep(1)
            c.privmsg(self.channel, str(nick) + ": how about you?")
        elif cmd.lower() == "who sings that?":
            if self.previous_song != "":
                c.privmsg(self.channel, str(data[self.previous_song]["artist"]))
            else:
                c.privmsg(self.channel, "I don't know what you mean!")
        elif cmd.lower() == "what is that song?":
            if self.previous_song != "":
                c.privmsg(self.channel, "It's " + str(self.previous_song) + " by " +
                          str(data[self.previous_song]["artist"]))
            else:
                c.privmsg(self.channel, "I don't know what you mean!")
        elif cmd.lower() == "what year did that song come out?":
            if self.previous_song != "":
                c.privmsg(self.channel, str(data[self.previous_song]["year"]))
            else:
                c.privmsg(self.channel, "I don't know what you mean!")
        elif cmd.lower() in ["i'm fine", "i'm good", "i'm fine, thanks for asking"]:
            pass
        else:
            c.notice(nick, "Not understood: " + cmd)



def main():
    import sys
    if len(sys.argv) != 4:
        print("Usage: testbot <server[:port]> <channel> <nickname>")
        sys.exit(1)

    s = sys.argv[1].split(":", 1)
    server = s[0]
    if len(s) == 2:
        try:
            port = int(s[1])
        except ValueError:
            print("Error: Erroneous port.")
            sys.exit(1)
    else:
        port = 6667
    channel = sys.argv[2]
    nickname = sys.argv[3]

    bot = TestBot(channel, nickname, server, port)
    bot.start()

if __name__ == "__main__":
    main()
