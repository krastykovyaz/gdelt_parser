import os

from joblib import Parallel, delayed

import pandas as pd
import numpy as np

from pqdm.processes import pqdm

import re
import requests
from bs4 import BeautifulSoup

from urllib.request import urlretrieve

from tqdm.auto import tqdm
from joblib import Parallel

from selenium import webdriver

import zipfile

import warnings


warnings.filterwarnings('ignore')

def unzip_file(zip_path, extract_to='.'):
    try:
        # Ensure the zip file exists
        if not os.path.isfile(zip_path):
            return

        # Open the zip file
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Extract all the contents to the specified directory
            zip_ref.extractall(extract_to)
    except zipfile.BadZipFile:
        pass
    except Exception as e:
        pass
        
class ProgressParallel(Parallel):
    def __init__(self, use_tqdm=True, total=None, *args, **kwargs):
        self._use_tqdm = use_tqdm
        self._total = total
        super().__init__(*args, **kwargs)

    def __call__(self, *args, **kwargs):
        with tqdm(disable=not self._use_tqdm, total=self._total) as self._pbar:
            return Parallel.__call__(self, *args, **kwargs)

    def print_progress(self):
        if self._total is None:
            self._pbar.total = self.n_dispatched_tasks
        self._pbar.n = self.n_completed_tasks
        self._pbar.refresh()

def get_request(names, pattern, formatted_dates, i):
    urlretrieve(pattern, 'dat_' + formatted_dates[i] + '.zip')
    unzip_file('dat_' + formatted_dates[i] + '.zip')
    name_of_file = formatted_dates[i] + '.export.csv' 
    df_tmp = pd.read_csv(name_of_file, sep='\t', on_bad_lines='skip') 
    df_tmp = df_tmp[df_tmp.columns[-2:]]
    df_tmp = df_tmp.rename(columns={
        df_tmp.columns[0] : 'month',
        df_tmp.columns[1]: 'link'
    })
    words_to_check = names
    filtered_df = df_tmp[df_tmp['link'].str.contains('|'.join(words_to_check))]
    df_tmp = filtered_df.reset_index()
    os.remove('dat_' + formatted_dates[i] + '.zip')
    os.remove(name_of_file)
    df_tmp['link'].drop_duplicates(inplace=True)
    return df_tmp
    
def get_data(names, start, end, parallel=False):
    '''
    Return dataframe file with news links and created time. 
        Parameters:
            names (list): list of all news sources: bloomberg, reuters, etc.
            start (str): start date string (format: YYYY-MM-DD)
            end (str): end date string (format: YYYY-MM-DD)
    '''

    start_date = start
    end_date = end
    
    dates = pd.date_range(start=start_date, end=end_date, freq='MS')  # 'MS' stands for Month Start
    
    formatted_dates = dates.strftime('%Y%m%d').tolist()
    
    patterns = [f'http://data.gdeltproject.org/events/{d}.export.CSV.zip' for d in formatted_dates]
    dfs = []

    if parallel is False:
        from tqdm import tqdm
        for i, pattern in tqdm(enumerate(patterns)):
            dfs.append(get_request(names, pattern, formatted_dates, i))
    else:
        dfs = ProgressParallel(n_jobs=-1)(delayed(get_request)(names, pattern, formatted_dates, i) for i, pattern in enumerate(patterns))

    return pd.concat(dfs)[['month', 'link']].drop_duplicates(subset=['link'])

def get_body(link):
    options = webdriver.ChromeOptions()
    options.add_argument("headless")
    driver = webdriver.Chrome(options=options)
    driver.get(link)
    page_source = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page_source)
    paragraphs = [p.text for p in soup.find_all('p')]
    if 'seekingalpha' in link:
        return ' '.join(paragraphs[:-3])
    elif 'bloomberg' in link:
        return ' '.join(paragraphs[-2:])
    else:
        raise "No such data"

def get_bodies(df, time_to_wait=100):
    '''
    Return list of (month, body)
    [Currently works for bloomberg and seekingalpha]
    '''
    
    if 'link' not in df.columns:
        raise "There is no link column in data"

    bodies = []
    
    for i, link in enumerate(df.link.values): 
        try:
            body = get_body(link)
            bodies.append((df.month.values[i], body))
            time.sleep(time_to_wait) # I'm not sure how long need to wait
        except:
            pass

    return bodies
            