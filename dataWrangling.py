#%%
import utilities.utilities as utl

def dataWrangling(new_data, outputType):
        
    # Initial load and clean data
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    data_file = 'afl_DF.pkl'
    first_year = 2012 #earliest year to include in data wrangling. Zero means, all of them.
    exclude_finals = 1 #1 = exclude, 0 = include
    ########################################################################################
    afl_DF, dropped_cols = utl.dataLoadClean(data_file, first_year, exclude_finals)
    
    # Impute new features with scraped data
    afl_DF = utl.calcScoreMarginWin(afl_DF)
    
    # Impute new features with scraped data
    if outputType == 'score' or outputType == 'scoreElo':
        afl_DF = utl.appendNewData(afl_DF, new_data)
    
    #Create model target feature
    afl_DF = utl.appendModelTarget(afl_DF, 'Win')
    
    #Create game and round indexes
    afl_DF = utl.createIndex('round_index', afl_DF, ['year', 'season_round'], [True, True])
    afl_DF = utl.createIndex('game_index', afl_DF, ['date','fw_game_id'], [True, True])
    
    # Remove features that are not wanted for the model
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    cols_to_drop= ['Kicks', 'Handballs','Marks', 'Tackles', 'Hitouts', 'Frees_For', 'Frees_Against',
           'Goals_Kicked', 'Behinds_Kicked', 'Rushed_Behinds', 'Disposals_Per_Goal', 'Clearances',
           'Clangers', 'In50s_Per_Scoring_Shot', 'Inside_50s_Per_Goal',  'In50s_Goal',
           'Contested_Possessions', 'Uncontested_Possessions', 'Effective_Disposals', 'Contested_Marks',
            'One_Percenters', 'Bounces', 'Turnovers', 'Intercepts', 'Tackles_Inside_50', 'Kick_to_Handball_Ratio']
    ########################################################################################
    afl_DF = utl.dropStatCols(afl_DF, cols_to_drop)
    
    # Create a column representing the % of each 'stat' achieved by "team"
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    pcnt_naming = 'Pcnt'
    ########################################################################################
    afl_DF = utl.calcStatPercentage(afl_DF, pcnt_naming)
    
    # Remove all of the columns that are include "Team" or "Oppnt"
    afl_DF = utl.dropRawStats(afl_DF)
    
    # Create moving averages of certain columns
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    mean_N = [8, 20] #list of average lengths i.e. [3,5] average of last 3 and average of last 5
    cols_to_apply = [col for col in afl_DF.columns if pcnt_naming in col] #All columns with pcnt are included
    cols_to_apply.extend(['Win','Margin']) #Additional columns to include
    ########################################################################################
    afl_DF = utl.calcStatMeans(afl_DF, mean_N, cols_to_apply)
    
    #Remove columns used to create means
    cols_to_apply.remove('Margin')
    afl_DF = utl.dropCols(afl_DF, cols_to_apply) 

    
    #Add opponent and team means into one data set
    afl_DF = utl.appendTeamOpponentMeans(afl_DF)
    
    # Create ratios from the means
    afl_DF = utl.createMeanRatio(afl_DF)
    
    # Difference the means (usually where a ratio would cause issues with inf)
    afl_DF = utl.createMeanDiff(afl_DF)
    
    # Remove all opponent and team mean columns (not differenced)
    afl_DF = utl.dropNormalMeanCols(afl_DF)
    
    # Remove draws
    afl_DF = utl.dropDraws(afl_DF)
    
    # Create probabilities from the odds for benchmarking
    afl_DF = utl.createOddsProb_MonashScore(afl_DF)
    
    if outputType == 'score':
        afl_DF, afl_NEW= utl.splitScoringTraining(afl_DF)
    
    # Decide what sort of game mix should be kept for training. All of the home or all away, a mix of both or all of the games
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    games_to_keep = 'mix' #'mix' = mix of home and away, 'home' 'away' = home and away respectively. Else
    ########################################################################################
    afl_DF = utl.createGameMix(afl_DF, games_to_keep)
    
    #Create ML data set
    #########<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
    drop_cols = ['season_round','round_char','date','location','attendance','final', # Drop columns that are not wanted in the ML data
                 'team_odds','oppnt_odds','team_line','oppnt_line', 'Margin','Result','Margin_ELO_m8','game_index',
                 'oppnt_oddsprob', 'team_oddsprob ', 'team_oddsprobwght', 'monash_scorewin', 'monash_scorelloss','monash_score']
    ########################################################################################
    afl_ML = utl.createMLData(afl_DF, drop_cols)
    if outputType == 'score':
        afl_NEW = utl.createMLData(afl_NEW, drop_cols)
        return afl_NEW

    elif outputType == 'scoreElo':
        return afl_DF
    else:
        return afl_ML, afl_DF
    