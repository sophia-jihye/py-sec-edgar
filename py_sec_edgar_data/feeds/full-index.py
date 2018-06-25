
#######################
# FULL-INDEX FILINGS FEEDS (TXT)
# https://www.sec.gov/Archives/edgar/full-index/
# "./{YEAR}/QTR{NUMBER}/"

import os
import os.path
from urllib.parse import urljoin

import pandas as pd
from py_sec_edgar_data.utilities import format_filename
from py_sec_edgar_data.celery_producer_filings import CONFIG
from py_sec_edgar_data.feeds import CONFIG
from py_sec_edgar_data.gotem import Gotem

full_index_files = ["company.gz",
                    "company.idx",
                    "company.Z",
                    "company.zip",
                    "crawler.idx",
                    "form.gz",
                    "form.idx",
                    "form.Z",
                    "form.zip",
                    "master.gz",
                    "master.idx",
                    "master.Z",
                    "master.zip",
                    "sitemap.quarterlyindex1.xml",
                    "xbrl.gz",
                    "xbrl.idx",
                    "xbrl.Z",
                    "xbrl.zip"]

def download_latest_quarterly_full_index_files():
    g = Gotem()
    for i, file in enumerate(full_index_files):
        item = {}
        item['OUTPUT_FOLDER'] = 'full-index'
        item['RELATIVE_FILEPATH'] = '{}'.format(file)
        item['OUTPUT_MAIN_FILEPATH'] = CONFIG.SEC_FULL_INDEX_DIR
        item['URL'] = urljoin(CONFIG.edgar_Archives_url, 'edgar/full-index/{}'.format(file))
        item['OVERWRITE_FILE'] = True
        dir_name = os.path.dirname(os.path.join(CONFIG.SEC_FULL_INDEX_DIR, item['RELATIVE_FILEPATH']))

        if not os.path.exists(dir_name):
            os.makedirs(dir_name)

        # celery version of download
        # py_sec_edgar_data.celery_consumer_filings.consume_sec_filing_txt.delay(json.dumps(item))
        g.GET_FILE(item['URL'], os.path.join(item['OUTPUT_MAIN_FILEPATH'], item['RELATIVE_FILEPATH']))


def download_latest_master_idx():
    # load lookup column
    df_tickers_cik = pd.read_excel(CONFIG.tickercheck)
    df_tickers_cik = df_tickers_cik.assign(EDGAR_CIKNUMBER=df_tickers_cik['EDGAR_CIKNUMBER'].astype(str))

    local_idx = os.path.join(CONFIG.SEC_FULL_INDEX_DIR, "master.idx")
    url = CONFIG.edgar_full_master
    # local_idx = os.path.join(CONFIG.SEC_FULL_INDEX_DIR, "xbrl.idx")
    # url = CONFIG.edgar_full_master.replace("master.idx", "xbrl.idx")
    # for time being just delete most recent and download newest

    if os.path.exists(local_idx):
        os.remove(local_idx)

    g = Gotem()
    print("Downloading Latest {}".format(CONFIG.edgar_full_master))
    g.GET_FILE(url, local_idx)

    df = pd.read_csv(local_idx, skiprows=10, names=['CIK', 'Company Name', 'Form Type', 'Date Filed', 'Filename'], sep='|', engine='python', parse_dates=True)
    df = df[-df['CIK'].str.contains("---")]
    df = df.sort_values('Date Filed', ascending=False)
    df = df.assign(published=pd.to_datetime(df['Date Filed']))

    df['link'] = df['Filename'].apply(lambda x: urljoin(CONFIG.edgar_Archives_url, x))
    df['edgar_ciknumber'] = df['CIK'].astype(str)
    df['edgar_companyname'] = df['Company Name']
    df['edgar_formtype'] = df['Form Type']

    df_with_tickers = pd.merge(df, df_tickers_cik, how='left', left_on=df.edgar_ciknumber, right_on=df_tickers_cik.EDGAR_CIKNUMBER)
    df_with_tickers = df_with_tickers.sort_values('Date Filed', ascending=False)

    df_with_tickers.to_csv(local_idx.replace(".idx", ".csv"))

def download_filings_from_idx():
    # todo: allow for ability to filter forms dynamically

    forms_list = ['10-K']

    idx_filename = "{}.csv".format(format_filename(CONFIG.edgar_full_master))

    df_with_tickers = pd.read_csv(os.path.join(CONFIG.DATA_DIR, idx_filename))

    df_with_tickers = df_with_tickers[df_with_tickers['Form Type'].isin(forms_list)]

    df_with_tickers = df_with_tickers.assign(published=pd.to_datetime(df_with_tickers['published']))

    # i, feed_item = list(df_with_tickers.to_dict(orient='index').items())[0]
    for i, feed_item in df_with_tickers.to_dict(orient='index').items():

        # 'C:\\sec_gov\\Archives\\edgar\\filings\\2018\\QTR2'
        folder_dir = os.path.basename(feed_item['Filename']).split('.')[0].replace("-","")
        folder_path_cik = CONFIG.SEC_TXT_FILING_DIR.replace("CIK", str(feed_item['CIK'])).replace("FOLDER", folder_dir)
        # 'C:\\sec_gov\\Archives\\edgar\\filings\\cik\\1050825'
        # folder_path_cik_other = os.path.join(CONFIG.SEC_TXT_DIR, 'cik', feed_item['edgar_ciknumber'])

        if not os.path.exists(folder_path_cik):
            os.makedirs(folder_path_cik)

        filepath_feed_item = os.path.join(folder_path_cik, os.path.basename(feed_item['Filename']))

        if not os.path.exists(filepath_feed_item):
            g = Gotem()

            g.GET_FILE(feed_item['link'], filepath_feed_item)
            # todo: celery version of download full
            # consume_complete_submission_filing_txt.delay(feed_item, filepath_cik)
        else:
            print("Filepath Already exists\n\t {}".format(filepath_feed_item))
            # parse_and_download_quarterly_idx_file(CONFIG.edgar_full_master, local_master_idx)

