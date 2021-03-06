#imports: 
import pandas as pd
import matplotlib.pyplot as plt
from pylab import *
import os
import seaborn as sns
from scipy import stats

#Functions used in context with the transaction dataframe: 

def bud_total_per_year(grouped_trans_spent, trans_clean_hous_ind):
    """
    Calculates the total amount spent per household over a year (year 1 or 2)
    @input: 
    - [pd.DataFrame] grouped_trans_spent: df with transactions per family and information about those transactions. 
    - [pandas.core.indexes] trans_clean_hous_ind: household keys for the households participating that year

    @output: pandas dataframe with the total amount spent by each household in year i (1 or 2)
    """
    bud_total = [grouped_trans_spent.loc[i]['SALES_VALUE'].sum() for i in trans_clean_hous_ind]
    
    df = pd.DataFrame(index = trans_clean_hous_ind, data = {'yearly spending': bud_total})
    
    df.index.name = 'household_key'
    
    return df

def correlation_ratio(categories, measurements):
    """
    Calculates a correlation coefficient between a categorical variable and a continuous variable. 
    @input: 
    - [array of categorical variables] categories: categorical array
    - [array of continous variables] measurements: continuous array

    @output: correlation coefficient between 0 and 1
    """
    fcat, _ = pd.factorize(categories)
    cat_num = np.max(fcat) + 1
    y_avg_array = np.zeros(cat_num)
    n_array = np.zeros(cat_num)
    for i in range(0, cat_num):
        cat_measures = measurements.iloc[np.argwhere(fcat == i).flatten()]
        n_array[i] = len(cat_measures)
        y_avg_array[i] = np.average(cat_measures)

    y_total_avg = np.sum(np.multiply(y_avg_array, n_array)) / np.sum(n_array)
    numerator = np.sum(
        np.multiply(n_array, np.power(np.subtract(y_avg_array, y_total_avg),
                                      2)))
    denominator = np.sum(np.power(np.subtract(measurements, y_total_avg), 2))
    if numerator == 0:
        eta = 0.0
    else:
        eta = np.sqrt(numerator / denominator)
    return eta


def cramers_v(x, y):
    """
    Calculates a correlation coefficient between two categorical variables x and y. 
    @input: 
    - [categorical variable array] x,y
    
    @output: correlation coefficient between 0 and 1
    """
    confusion_matrix = pd.crosstab(x,y)
    chi2 = stats.chi2_contingency(confusion_matrix)[0]
    n = confusion_matrix.sum().sum()
    phi2 = chi2/n
    r,k = confusion_matrix.shape
    phi2corr = max(0, phi2-((k-1)*(r-1))/(n-1))
    rcorr = r-((r-1)**2)/(n-1)
    kcorr = k-((k-1)**2)/(n-1)
    return np.sqrt(phi2corr/min((kcorr-1),(rcorr-1)))


def create_weekly_cart_df(trans_clean, participation_per_hh):
    """
    Creates a dataframe with average weekly quantities of each label for each household
    @input: 
    - [pd.DataFrame] trans_clean: a dataframe with all the transactions per household. Ideally the labels should have been cleaned before.
    @output: dataframe with average weekly quantities of each label for each household
    """
    grouped_per_label = pd.DataFrame(trans_clean.groupby(['LABEL','household_key']).sum())
    
    index = trans_clean['household_key'].sort_values().unique()

    weekly_cart_df = pd.DataFrame(index = index)
    weekly_cart_df.index.name = 'household_key'

    for label in trans_clean['LABEL'].unique(): 
        data = [grouped_per_label.loc[label, i]['QUANTITY']/(participation_per_hh['participation_length'][i])  for i in grouped_per_label.loc[label].index]
        
        intermediary_df = pd.DataFrame(index = grouped_per_label.loc[label].index, data = {label +'_QUANT': data})

        weekly_cart_df = weekly_cart_df.join(intermediary_df)

    #Fill NaN values with 0.0:
    weekly_cart_df = weekly_cart_df.fillna(0.0)
    
    return weekly_cart_df

def create_weekly_dep_df(trans_clean, participation_per_hh):
    
    grouped_per_dep = pd.DataFrame(trans_clean.groupby(['DEPARTMENT','household_key']).sum())
    index = trans_clean['household_key'].sort_values().unique()

    weekly_dep_df = pd.DataFrame(index = index)
    weekly_dep_df.index.name = 'household_key'

    for dep in trans_clean['DEPARTMENT'].unique(): 
        data = [grouped_per_dep.loc[dep, i]['QUANTITY']/(participation_per_hh['participation_length'][i])\
                for i in grouped_per_dep.loc[dep].index]
        
        intermediary_df = pd.DataFrame(index = grouped_per_dep.loc[dep].index, data = {dep +'_QUANT': data})

        weekly_dep_df = weekly_dep_df.join(intermediary_df)

    #Fill NaN values with 0.0:
    weekly_dep_df = weekly_dep_df.fillna(0.0)
    
    return weekly_dep_df

def df_weekly_spending(df_trans):
    """
    Creates a dataframe with the mean weekly spending for each household
    @input: 
    - [pd.DataFrame] df_trans: dataframe with all transactions per household. 

    @output: pandas dataframe with mean weekly spending per household

    """
    index = df_trans['household_key'].sort_values().unique()
    
    grouped_per_hh = spending_per_household_per_trans(df_trans)
    
    mean_per_fam = [grouped_per_hh.loc[i]['SALES_VALUE'].sum() / len(grouped_per_hh.loc[i]['WEEK_NO'].unique()) for i in index]
    
    mean_budget_week = pd.DataFrame(index = index, data = {'mean weekly spending': mean_per_fam})
    
    mean_budget_week.index.name = 'household_key'
    
    return mean_budget_week 


def mean_yearly_spending(budget_first_year, budget_second_year):
    """
    Calculates the mean of yearly spending per household
    @input: 
    - [pd.Series] budget_first_year, budget_second_year: spending per household for year 1 and 2
    """
    mean_yearly_spend = budget_first_year.join(budget_second_year, lsuffix='_1')
    
    mean_yearly_spend['mean yearly spending'] = mean_yearly_spend.mean(axis=1)
    
    mean_yearly_spend = mean_yearly_spend.drop(
        ['yearly spending', 'yearly spending_1'], axis=1)
    return mean_yearly_spend



def spending_per_household_per_trans(trans_clean):
    """
    Creates a new dataframe with the spending per household 
    @input: 
    - [pd.DataFrame] trans_clean: df with total transactions that have clean labels

    @output: pandas dataframe that groups the spending per households and adds columns 
    of "WEEK_NO", "TRANS_TIME", "DAY" for when these transactions occured. 
    """
    grouped = trans_clean.groupby(['household_key', 'BASKET_ID']).sum()
    grouped_count = trans_clean.groupby(['household_key', 'BASKET_ID']).size()

    grouped_trans_spent = pd.DataFrame(grouped[['SALES_VALUE','QUANTITY']])

    grouped_trans_spent['WEEK_NO'] = grouped['WEEK_NO']/grouped_count
    grouped_trans_spent['TRANS_TIME'] = grouped['TRANS_TIME']/grouped_count
    grouped_trans_spent['DAY'] = grouped['DAY']/grouped_count

    return grouped_trans_spent


def trans_per_year(trans_clean_year_i, trans_clean_hous_ind_i):
    """
    Creates a dataframe with the total number of transactions per year for each household.
    @input:
    - [pd.DataFrame] trans_clean_year_i: datframe with all transactions and cleaned labels for year i (1 or 2)
    - [pandas.core.indexes] trans_clean_hous_ind_i: household keys for all households in the cleaned transaction df for year i (1 or 2)

    @output: dataframe with total number of transactions per year per household. 
    """
    grouped_trans_yeari = trans_clean_year_i.groupby(['household_key','BASKET_ID']).size()
    
    purch_per_hous_yeari = pd.DataFrame(index = trans_clean_hous_ind_i)
    
    total_transactioni = [len(grouped_trans_yeari.loc[i]) for i in trans_clean_hous_ind_i]
    
    purch_per_hous_yeari['total purchase per year'] = total_transactioni
    
    return purch_per_hous_yeari
