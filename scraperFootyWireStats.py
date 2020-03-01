year_start = 2007
year_end = 2019

import urllib.request
from bs4 import BeautifulSoup
import pandas as pd
import datetime
import re
import os
import sys

def monthToNum(shortMonth):
    return{
            'January' : 1,
            'February' : 2,
            'March' : 3,
            'April' : 4,
            'May' : 5,
            'June' : 6,
            'July' : 7,
            'August' : 8,
            'September' : 9, 
            'October' : 10,
            'November' : 11,
            'December' : 12
    }[shortMonth]

def finalRoundNum(final):
    return{
        'First Qualifying Final' : 30,
        'Second Qualifying Final' : 30,
        'Qualifying Final' : 30,
        'First Elimination Final' : 30,
        'Second Elimination Final' : 30,
        'Elimination Final' : 30,
        'First Semi Final' : 31,
        'Second Semi Final' : 31,
        'First Semi-Final' : 31,
        'Second Semi-Final' : 31,
        'Semi Final' : 31,
        'First Preliminary Final': 32,
        'Second Preliminary Final': 32,
        'Preliminary Final': 32,
        'Grand Final' : 33
    }[final]

def getOdds(data):
    try:
        odds = data.str.split(',')
        odds = odds[0][0]
        odds = float(odds.split(': Win ')[1])
    except:
        odds = 0
    return odds
def getLine(data):
    try:
        line = data.str.split(',')[0][1]
        line = re.sub(' @ 1.92','', re.sub(' Line ', '', line))
    except:
        line = 0
    return line
def getSoup(url):
    html = urllib.request.urlopen(url)
    soup = BeautifulSoup(html, 'html.parser')
    return soup

def infoTable(some_soup):
    info_table = some_soup.find('table', border="0", cellpadding="0", cellspacing="0", width="525") #find the first table with this info
    info_table = pd.read_html(str(info_table))
    info_table = info_table[0]
    return info_table
def dateTime(the_info_table):
    date_time = the_info_table.iloc[2]
    date_time = date_time.str.split(',')
    date = date_time[0][1].split(' ')
    day = re.sub('[^0-9]','',date[1])
    year = date[3]
    month = monthToNum(date[2])
    time = date_time[0][2].split(' ')
    date = datetime.datetime(int(year), month, int(day))
    return date
def getGameInfo(the_info_table):
    game_info = the_info_table.iloc[1]
    game_info = game_info.str.split(',')
    return game_info
def getStatTable(some_soup):
    stat_table = some_soup.find('table', border="0", cellpadding="0", cellspacing="0", width="575") #find the first table with this info
    stat_table = pd.read_html(str(stat_table))[0]
    return stat_table
def getStats(the_stat_table, team, stat_type):
    if team == 'home':
        col_num = 0
    if team == 'away':
        col_num = 2
    if stat_type == 'basic':
        last_row = 27
    if stat_type == 'advanced':
        last_row = 22
    stats = pd.Series(data =  the_stat_table.iloc[2:last_row,col_num]).str.replace('%','').astype('float')
    return stats
def replacePcnt(data):
    data = data.str.replace('% ','').str.replace(' %','').str.replace('%','').str.replace(' ', '_')
    return data

def scrapeGameData(soup):
    #isolate table with the initial info and get date and year
    info_table = infoTable(soup)
    date = dateTime(info_table)
    year = date.year

    #get the round, location and attendance for the game from the table with initial info
    game_info = getGameInfo(info_table)
    the_round = game_info[0][0]
    
    #if the round is a final use the final name and the number from the function finalRoundNum, else use the actual number. Ac 
    if 'Final' in the_round:
        round_char = the_round
        season_round = finalRoundNum(the_round)
        final = 1
    else:
        round_char = re.sub('[^0-9]', '', the_round)
        season_round = int(re.sub('[^0-9]', '', the_round))
        final = 0
    location = game_info[0][1]
    attendance = int(re.sub(' Attendance: ', '', game_info[0][2]))

    #get the odds and line from the table with initial info
    try:
        home_odds = getOdds(info_table.iloc[3])
    except:
        home_odds = 0
    try:
        away_odds = getOdds(info_table.iloc[4])
    except:
        away_odds = 0
    try:
        home_line = getLine(info_table.iloc[3])
    except:
        home_line = 0        
    try:
        away_line = getLine(info_table.iloc[4])
    except:
        away_line = 0 
    #isolate the stats table, get basic stats and home/away teams
    bsc_stat_tbl = getStatTable(soup)
    bsc_home_stats = getStats(bsc_stat_tbl, 'home', 'basic')
    bsc_away_stats = getStats(bsc_stat_tbl, 'away', 'basic')
    bsc_stat_lbl = replacePcnt(pd.Series(data =  bsc_stat_tbl.iloc[2:27,1]))
    home_team = bsc_stat_tbl.iloc[1,1]
    away_team = bsc_stat_tbl.iloc[1,3]

    #create the column names for the data frame
    header_cols = pd.Series(['fw_game_id', 'year', 'season_round',  'round_char', 'date', 'team', 'opponent', 'home_game', 'location', 'attendance', 'final',
               'team_odds', 'oppnt_odds', 'team_line', 'oppnt_line'])

    try:
        #scrape the advanced stats table
        afl_adv_url = afl_url + '&advv=Y'
        advanced_soup = getSoup(afl_adv_url)

        #scrape the advanced stat
        adv_stat_tbl = getStatTable(advanced_soup)
        adv_home_stats = getStats(adv_stat_tbl, 'home', 'advanced')
        adv_away_stats = getStats(adv_stat_tbl, 'away', 'advanced')
        adv_stat_lbl = replacePcnt(pd.Series(data =  adv_stat_tbl.iloc[2:22,1]))

        header_cols = pd.concat([header_cols,
                  bsc_stat_lbl + 'Team', adv_stat_lbl + 'Team',
                   bsc_stat_lbl + 'Oppnt', adv_stat_lbl + 'Oppnt'], 
                 axis = 0).reset_index(drop=True)
        
    #when there are no advanced stats....
    except:
        header_cols = pd.concat([header_cols,
                  bsc_stat_lbl + 'Team', bsc_stat_lbl + 'Oppnt'], 
                 axis = 0).reset_index(drop=True)

    #create the data frame with column names
    game_DF = pd.DataFrame(columns = header_cols)

    #add the home team data to the data frame
    game_meta = pd.Series([game_id, year, season_round, round_char, date, home_team, away_team, 1, location, attendance, final,
               home_odds, away_odds, home_line, away_line])
    game_stats = pd.concat([bsc_home_stats, adv_home_stats, bsc_away_stats, adv_away_stats])
    game_data = pd.concat([game_meta, game_stats])
    game_data.index = header_cols
    game_DF = game_DF.append(game_data, ignore_index=True)

    #add the away team data to the data frame
    game_meta = pd.Series([game_id, year, season_round, round_char, date, away_team, home_team, 0, location, attendance, final,
               away_odds, home_odds, away_line, home_line])
    game_stats = pd.concat([bsc_away_stats, adv_away_stats, bsc_home_stats, adv_home_stats])
    game_data = pd.concat([game_meta, game_stats])
    game_data.index = header_cols
    game_DF = game_DF.append(game_data, ignore_index=True)
    #clean up columns, remove nan
    game_DF = game_DF[[col for col in game_DF.columns if str(col) != 'nan']]
    game_DF = game_DF.loc[:,~game_DF.columns.duplicated()]
    return game_DF

game_ids = []
for year in range(year_start,year_end + 1):
    try:
        afl_year_url = 'https://www.footywire.com/afl/footy/ft_match_list?year=' + str(year)
        soup = getSoup(afl_year_url)
        for a in soup.find_all("a", href=re.compile(r"^ft_match_statistics")):
            game_ids.append(
                int(a['href'].replace('ft_match_statistics?mid=',''))
            )
    except urllib.error.URLError:
        print('No internet connection')
        break
    
if os.path.isfile('./afl_DF.pkl'):
    afl_DF = pd.read_pickle('afl_DF.pkl')

if 'afl_DF' in locals():
    scraped_ids = list(afl_DF.loc[0:]['fw_game_id'].astype('int'))
    game_ids = [x for x in game_ids if x not in scraped_ids]
    
for game_id in game_ids:
    #scrape the data from the game page on footywire.com
    game_id =  str(game_id)
    afl_url = 'https://www.footywire.com/afl/footy/ft_match_statistics?mid=' + game_id
    try:
        soup = getSoup(afl_url)
    except:
        continue
    new_game = scrapeGameData(soup) 
    if 'afl_update' not in locals():
        afl_update = new_game
    else:
        afl_update  = afl_update.append(new_game, ignore_index=True)
    sys.stdout.flush()
    print(min(new_game.year),
    min(new_game.round_char))
    
if 'afl_update' in locals():
    if 'afl_DF' not in locals():
        afl_DF = afl_update
    else:
        afl_DF = afl_DF.append(afl_update, ignore_index = True, sort = True)
    afl_DF.to_pickle('afl_DF.pkl')    
    del afl_update
else:
    print('afl_update does not exist')
