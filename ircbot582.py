#! /usr/bin/env python
#
# Example program using irc.bot.
#
# Joel Rosdahl <joel@rosdahl.net>
# slight modifications by Foaad Khosmood
# modified for CPLUG questions by Logan Williams
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
from bs4 import BeautifulSoup
import requests
import re, time

class TestBot(irc.bot.SingleServerIRCBot):
    url = "http://cplug.org/about/a-brief-history-of-cplug/"
    years = {}

    def __init__(self, channel, nickname, server, port=6667):
        irc.bot.SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
        self.channel = channel
        self.years_pos_people = {} 
        self.update()
           
    # Takes in a string like "2003-2005" and returns a list
    # like [2003, 2004, 2005]
    def yr_range_to_list(self, yr_range):
        begin = int(yr_range.split('-')[0])
        end = int(yr_range.split('-')[1])
        yr_list = []
        yr_list.append(begin)
        cur = begin
        while (cur < end):
            cur += 1
            yr_list.append(cur)
        yr_list.append(end)

        return yr_list

    def update(self):
        # scrapes the url and updates self.data
        myRequest = requests.get(self.url)
        soup = BeautifulSoup(myRequest.text, "html.parser")
        cur_p = soup.find('p')
        
        cur_p = cur_p.find_next('p')
        while (cur_p != None):
           years = cur_p.contents[0]
           match = re.search('^(\d+-\d+)', years)
           if (match == None):
              print("ERROR: regex match on years somehow got None")
           else:
              years = match.group(1)
           
           pos_person_dict = {}
           cur_p = cur_p.find_next('ul')
           pre_people = list(filter(lambda a: a != '\n', cur_p.contents))
           for pos_person in pre_people:
              pos_person = pos_person.string
              #pos_person = pos_person.replace('â', '\'')
              pos_person = pos_person.replace('<li>', '')
              pos_person = pos_person.replace('</li>', '')
              splitted = pos_person.split(':')
              if (len(splitted) == 2):
                 pos_person_dict[splitted[0].lower().strip()] = splitted[1].lower().strip()
           
           if (len(pos_person_dict) > 0):
              for yr in self.yr_range_to_list(years):
                  self.years_pos_people[yr] = pos_person_dict
           
           cur_p = cur_p.find_next('p')


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
        return

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
        elif cmd == "*forget":
            #forgets stuff
            pass
        elif re.search('who was ([\w ]+) in (\d+)?', cmd.lower()): 
            match = re.search('who was ([\w ]+) in (\d+)?', cmd.lower())
            if (match == None):
                print("ERROR: expected match on who was question, got None")
            else: 
                pos = match.group(1).lower()
                year = int(match.group(2))
                if year not in self.years_pos_people:
                    c.privmsg(self.channel, "Sorry, I only know info for years 2003-2016.")
                else:
                    if pos not in self.years_pos_people[year]:
                        c.privmsg(self.channel, "Sorry, I don't know who was " + pos + " in " + str(year) + ".")
                    else:
                        person = self.years_pos_people[year][pos]
                        c.privmsg(self.channel, str(person).title() + " was " + pos + " in " + str(year) + ".")
        elif re.search('when was ([\w ]+) the ([\w ]+)?', cmd.lower()): 
            match = re.search('when was ([\w ]+) the ([\w ]+)?', cmd.lower())
            person = match.group(1).lower()
            pos = match.group(2).lower()
            years = []
            for yr in self.years_pos_people.keys():
                if pos in self.years_pos_people[yr]:
                    if person == self.years_pos_people[yr][pos]:
                        years.append(yr)
            if len(years) > 0:
                result_msg = str(person).title() + " was " + pos + " in " + str(years).replace('[', '').replace(']', '') + "."
            else: 
                result_msg = "It looks like " + person.title() + " was never the " + pos + "."
            c.privmsg(self.channel, result_msg)
        elif cmd == "about":
            c.privmsg(self.channel, "I was made by Logan Williams for Foaad Khosmood for the CPE 466 class in Spring 2016")
        elif cmd == "usage":
            c.privmsg(self.channel, "I can answer questions like this: \"Who was [CLUB_POSITION] in [YEAR]?\" or \"When was [NAME] the [CLUB_POSITION]?\" Some positions include: president, vice president, treasurer, secretary, and webmaster. Note: not every year has info for every position.") 
        else:
            c.notice(nick, "Not understood: " + cmd)


        time.sleep(1)

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
