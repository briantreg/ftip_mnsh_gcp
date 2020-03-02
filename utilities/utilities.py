import pandas as pd
import numpy as np
import datetime as dt


def dataLoadClean(file_name, first_year, exclude_finals):
    data = pd.read_pickle(file_name) #Read in the data
    
    data = data[data.year >= first_year].reset_index() #Filter the data toonly include data from years greater than or equal to <first_year>
    cols_drop = data.isna().any()
    
    data = data.loc[0:,~(cols_drop)] #Remove any columns that have NAs in the columns
    
    if exclude_finals == 1: #Drop all finals games when <exclude_finals> is 1
        data = data[data['final'] == 0]
    cols_drop = cols_drop[cols_drop].index
    #cols_drop = cols_drop[cols_drop].index
    return data, cols_drop

# =============================================================================
# 
# =============================================================================
def running_mean(x, N):
    cumsum = np.cumsum(np.insert(x, 0, 0)) 
    return (cumsum[N:] - cumsum[:-N]) / float(N)

def newMeanCol(df, col_nm, N):
    new_col = col_nm + '_mean' + str(N)
    x = df.loc[0:,col_nm]
    mean_vals = list(np.insert(
        running_mean(
            np.array(x), N), 0, [np.nan] * N))
    df[new_col] = mean_vals[0:len(x)]
    return df
# =============================================================================
# 
# =============================================================================
def colLookup(data, string):
    return data[[col for col in data.columns if string  in col]]
# =============================================================================
# 
# =============================================================================
#Where a row is na (i.e. it is in the first x games for that team and therefore has no mean), remove both rows of that game.
#This is for the instance when new teams join the league, can't calculate the score for the older team so have to remove both instances.
def NANConsolidate(df, col):
    na_game_ids = set(df[(df.isna().any(axis = 1))][col])
    return df[~df[col].isin(na_game_ids)]

def CheckTeam(df, team):
    df = df[df['team'] == team]
    min_game = min(df.date)
    max_game = max(df.date)
    n_na = sum(df.isna().any(axis=1))
    return print(min_game, max_game, n_na)

def calcScoreMarginWin(data):
    ###Create new score, margin, result and win variables
    data['ScoreTeam'] = (data['Goals_KickedTeam'] * 6) + data['Behinds_KickedTeam'] #Goals for the team * 6 plus behinds for the team is the score 
    data['ScoreOppnt'] = (data['Goals_KickedOppnt'] * 6) + data['Behinds_KickedOppnt'] #Goals for the opponent * 6 plus behinds for the opponent is the score 
    data['Margin'] = data['ScoreTeam'] - data['ScoreOppnt'] #The final margin calculated as the score for the team minus the score for the opponent 
    
    data.loc[data['Margin'] == 0, 'Result'] = 0 #When margin is 0, 0
    data.loc[data['Margin'] > 0, 'Result'] = 1 #When margin > 0, 1
    data.loc[data['Margin'] < 0, 'Result'] = -1 #When margin < 0, -1
    
    data.loc[:, 'Win'] = 0 #Make win a zero
    data.loc[data['Margin'] > 0, 'Win'] = 1 #When margin > 0 it's a win = 1
    
    return data

def appendModelTarget(data, col):
    data['model_target'] = data[[col]]
    return data


def createIndex(index_col_name, data, cols, cols_asc):
    index_data = data[0:][cols]
    index_data = index_data.drop_duplicates(subset = cols)
    index_data = index_data.sort_values(by = cols, 
                                        ascending = cols_asc).reset_index(drop=True)
    index_data[index_col_name] = list(range(len(index_data)))
    data = pd.merge(data, #Join the index back to the main data
            index_data,
            left_on = cols,
            right_on = cols,
            how = 'left')
    return data

def dropStatCols(data, cols_to_drop):
    cols_to_drop_fin = [string + 'Team' for string in cols_to_drop]
    cols_to_drop_fin .extend([string + 'Oppnt' for string in cols_to_drop])
    data = data[[col for col in data.columns if col not in cols_to_drop_fin]]
    return data 


def calcStatPercentage(data, pcnt_naming):
    team_array =  colLookup(data, 'Team').values #get all columns with "Team" in the name, then return the cell values
    oppnt_array =  colLookup(data, 'Oppnt').values #get all columns with "Opponent" in the name, then return the cell values
    diff_array = team_array / (team_array + oppnt_array + 0.00001) #Create an array of values which is the % of the stat belonging to team. Note: adding small positive value to avoid inf
    data[list( colLookup(data, 'Team').columns.str.replace('Team',pcnt_naming))] = pd.DataFrame(diff_array) #Create a new set of columns and insert the array of values back into main dataframe
    return data


def dropRawStats(data):
    return data[[col for col in data.columns if 'Team' not in col and 'Oppnt' not in col]]

def calcStatMeans(data, mean_N ,cols):

    data = data.sort_values(by = ['team','game_index'],# Sort data by team and game_index for running mean
                 ascending = [True, True]
                     ).reset_index(drop=True)
    
    for N in mean_N:
        for col in cols:
            data = data.groupby('team').apply(newMeanCol, col_nm = col, N = N)
    return data[~(data.isna().any(axis = 1))] #Remove na created in the process

def dropCols(data, cols):
    return data[[col for col in data.columns if col not in cols]]

def appendTeamOpponentMeans(data):
    feature_col = ['fw_game_id','team']
    feature_col.extend([col for col in data.columns if 'mean' in col])
    data_opp = data[feature_col]
    data_opp.columns = data_opp.columns.str.replace('team','opponent')
    data_opp.columns = data_opp.columns.str.replace('mean','O_mean')
    data.columns = data.columns.str.replace('mean','T_mean')
    
    data = pd.merge(data,
                     data_opp,
                     left_on = ['fw_game_id','opponent'],
                     right_on = ['fw_game_id','opponent'],
                     how='left')
    return data

def createMeanRatio(data):
    team_pcnt_col = [col for col in data.columns if 'T_mean' in col]#Cols to include
    team_pcnt_col = [col for col in team_pcnt_col if 'Win_' not in col and 'Margin_' not in col]#Cols to exclude
    oppnt_pcnt_col = [col for col in data.columns if 'O_mean' in col]
    oppnt_pcnt_col = [col for col in oppnt_pcnt_col if 'Win_' not in col and 'Margin_' not in col]
    
    team_pcnt_mean = data[team_pcnt_col].values #Create Array of value
    oppnt_pcnt_mean = data[oppnt_pcnt_col].values
    diff_pcnt_mean = team_pcnt_mean / (team_pcnt_mean + oppnt_pcnt_mean + 0.000001)#Ratio the two arrays
    
    data[[col.replace('T','D') for col in team_pcnt_col]] = pd.DataFrame(diff_pcnt_mean) #Join arrays back with "D" suffix
    
    return data

def createMeanDiff(data):
    team_other_col = [col for col in data.columns if ('Win_T' in col or 'Margin_T' in col) and '_T_' in col] #Cols to include 
    oppnt_other_col = [col for col in data.columns if ('Win_O' in col or 'Margin_O' in col) and '_O_' in col]
    
    team_other_mean = data[team_other_col].values #Create Array of value
    oppnt_other_mean = data[oppnt_other_col].values
    diff_other_mean = team_other_mean - oppnt_other_mean #Difference the two arrays
    
    data[[col.replace('T','D') for col in team_other_col]] = pd.DataFrame(diff_other_mean) #Join arrays back with "D" suffix
    return data

def dropNormalMeanCols(data):
    return data[[col for col in data.columns if '_T_' not in col and '_O_' not in col]]

def dropDraws(data):
    data = data[~(data.Result == 0)]
    return data

def createOddsProb_MonashScore(data):
    oppnt_odds = data[['oppnt_odds']]
    oppnt_oddsprob = 1 / (oppnt_odds + 0.000000000001)
    data['oppnt_oddsprob'] = oppnt_oddsprob
    team_odds = data[['team_odds']]
    team_oddsprob = 1 / (team_odds + 0.000000000001)
    data['team_oddsprob '] = team_oddsprob
    data['team_oddsprobwght'] = (data['team_oddsprob '] + (1 - data['oppnt_oddsprob']) ) / 2
    data['monash_scorewin'] = (1 + np.log2(pd.to_numeric(data['team_oddsprobwght']) ) ) * data['model_target']
    data['monash_scorelloss'] = (1 + np.log2(1 - pd.to_numeric(data['team_oddsprobwght']) ) ) * (1 - data['model_target'])
    data['monashOddsscore'] = data['monash_scorewin'] + data['monash_scorelloss']
    
    return data
def createGameMix(data, mix):
    if mix not in ['mix','home','away','all']:
        print('error, <games_to_keep> variable not set correctly')
    elif mix == 'mix':
        odds = [x for x in data.fw_game_id if int(x) % 2 > 0]
        evens = [x for x in data.fw_game_id if int(x) % 2 == 0]
        a = data[data.fw_game_id.isin(odds)]
        b = data[data.fw_game_id.isin(evens)]
        a = a[a.home_game == 0] 
        b = b[b.home_game == 1] 
        data = pd.concat([a,b])
        del a, b
    elif mix == 'home':
        data = data[data.home_game == 1]
    elif mix == 'away':
        data = data[data.home_game == 0]
    return data

def createMLData(data, drop_ml_cols):
    drop_ml_cols = [col for col in drop_ml_cols if col in data.columns]
    data = data.drop(drop_ml_cols, axis = 1)

    cols = list(data.columns) # Move the model_target to be the last feature
    cols.remove('model_target')
    cols.append('model_target')
    data = data[cols]
    
    return data

# =============================================================================
# Scoring Utilities
# =============================================================================
def createScoringData(teams, opponents, games, round_n, year):
    data_home = pd.DataFrame({'team':teams, 
          'opponent':opponents, 
          'home_game': 1, 
          'Result': 1, 
          'fw_game_id': games, 
          'date':dt.datetime(2099, 12, 31), 
          'season_round': round_n, 
          'round_char': str(round_n),
          'year': year,
          'new_data': 1})
    data_away = pd.DataFrame({'team':opponents, 
          'opponent':teams, 
          'home_game': 0, 
          'Result': 1, 
          'fw_game_id': games, 
          'date':dt.datetime(2099, 12, 31), 
          'season_round': round_n, 
          'round_char': str(round_n),
          'year': year,
          'new_data': 1})
    return pd.concat([data_home, data_away], sort = False)

def appendNewData(data, new_data):
    data['new_data'] = 0
    new_data = pd.concat([data[data['team'] ==  'none'], new_data], sort = False)
    new_data = new_data.fillna(0.0)
    data = pd.concat([data, new_data], sort=False)
    return data

def splitScoringTraining(data):
    data_NEW = data[data.new_data == 1]
    data = data[data.new_data == 0]
    return data, data_NEW 

def combineHAScores(scored_data):
    scored_data_x = scored_data[['Win', 'team', 'opponent', 'home_game']]
    scored_data_y = scored_data[['Lose', 'opponent']] 
    scored_data_y.columns = ['Win','team']
    
    scored_data = pd.merge(scored_data_x,
          scored_data_y,
          on = 'team',
          how = 'left')
    true_win = (scored_data.Win_x + scored_data.Win_y) / 2
    scored_data['Win'] = true_win
    scored_data = scored_data[scored_data['home_game'] == 1]
    return scored_data [['team', 'opponent', 'Win']] 