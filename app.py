from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import time
from datetime import datetime, timedelta
import os
import telebot
from telebot.apihelper import ApiTelegramException
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.events import JobSubmissionEvent
import logging
import random
from dotenv import load_dotenv
from selenium.common.exceptions import NoAlertPresentException

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

load_dotenv()

# Initializing telegram bot
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
]

# Options for chrome driver
opts = ChromeOptions()
# opts.add_argument("--headless=new")
opts.add_argument(f'user-agent={random.choice(user_agents)}')
opts.add_argument("--no-sandbox")
opts.add_argument("--disable-dev-shm-usage")
opts.add_argument("--window-size=1920,1080")
# opts.page_load_strategy = 'eager'

# --------------------- Tender Scraper Start -----------------------------------#

# URL of the website to scrape
url = "https://www.eprocure.gov.bd/resources/common/StdTenderSearch.jsp?h=t"

# Current time assignment
c_time = datetime.now()

# Set the duration of tenders
c_time_delayed = c_time - timedelta(hours=1)

# Webdriver assignment and implicit time delay assign
driver = webdriver.Chrome(options=opts)
driver.implicitly_wait(5)

driver_li = webdriver.Chrome(options=opts)
driver_li.implicitly_wait(5)

driver_ji = webdriver.Chrome(options=opts)
driver_ji.implicitly_wait(5)

driver_jb = webdriver.Chrome(options=opts)
driver_jb.implicitly_wait(5)

def data_saver(data, out_file):
    with open(out_file, "a") as f:
        f.write(data)
        f.write("\n")

# For getting the columns of the table
def get_tenders_columns():
    table = driver.find_element(By.ID, "resultTable")
    body = table.find_element(By.TAG_NAME, "tbody")
    rows = body.find_elements(By.TAG_NAME, "tr")
    table_heads = rows[0].find_elements(By.TAG_NAME, "th")
    columns = []
    for heads in table_heads:
        columns.append(heads.text)
    return columns

# Converting the time into datetime format
def get_timestamp(time_str):
    time_format = "%d-%b-%Y %H:%M"
    t_time = datetime.strptime(time_str, time_format)
    return t_time

# For getting the table data
def get_tenders_data():
    row_data = []
    table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "resultTable")))
    while True:
        try:
            body = table.find_element(By.TAG_NAME, "tbody")
            rows = body.find_elements(By.TAG_NAME, "tr")
            for row in rows[1:]:
                data = row.find_elements(By.TAG_NAME, "td")
                values = []
                for value in data:
                    values.append(value.text)
                t_time = str(data[-1].text).split(',')
                p_time = get_timestamp(t_time[0])
                if p_time > c_time_delayed:
                    row_data.append(values)
            break
        except StaleElementReferenceException as e:
            print(f"Exception in Telebot: {e}")
            time.sleep(2)
            table = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "resultTable")))
    return row_data

# For getting the tender data in list of json format
def get_tenders():
    driver.get(url)
    time.sleep(10)
    table_load = (By.ID, "resultTable")
    while True:
        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(table_load))
            logging.info("Table Loaded...")
            break
        except Exception as e:
            logging.info("Telebot: Failed to Load Table...")
    columns = get_tenders_columns()
    data = []
    counter = 1
    while True:
        pg_data = get_tenders_data()
        if len(pg_data) == 0:
            break
        data.extend(pg_data)
        try:
            btn = driver.find_element(By.XPATH,'//*[@id="btnNext"]')
            btn.click()
            counter+=1
            time.sleep(5)
        except:
            logging.info("Telebot: No More Next Button...Exiting...!")
            break
    logging.info(f"Telebot: Total Pages Scrapped: {counter}")
    return columns, data

def get_group_chat_id():
    updates = bot.get_updates()
    group_chat_ids = set()
    groups = []
    for update in updates:
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            group_chat_ids.add(update.message.chat.id)
    for id in group_chat_ids:
        try:
            status = bot.get_chat_member(chat_id=id, user_id=bot.get_me().id)
            if str(status.status) != "kicked":
                groups.append(id)
        except Exception as e:
            logging.info(f"Telebot: {e}")
    return groups

def send_tenders():
    group_ids = get_group_chat_id()
    logging.info(f"Connected Group IDs: {group_ids}")
    columns, tenders = get_tenders()
    columns = [col.replace('\n','') for col in columns]
    if len(tenders) > 0:
        for tender in tenders:
            msg = f"<b>{str(columns[0])}</b> : {str(tender[0])}\n\n<b>{str(columns[1])}</b> : {str(tender[1])}\n\n<b>{str(columns[2])}</b> : {str(tender[2])}\n\n<b>{str(columns[3])}</b> : {str(tender[3])}\n\n<b>{str(columns[4])}</b> : {str(tender[4])}\n\n<b>{str(columns[5])}</b> : {str(tender[5])}"
            retry = 0
            max_try = 2
            while retry < max_try:
                try:
                    for group_id in group_ids:
                        # bot.send_message(
                        #     chat_id = group_id,
                        #     text = msg,
                        #     allow_sending_without_reply = True,
                        #     parse_mode='HTML'
                        #     )
                        data_saver(msg, "data/telebot.txt")
                    time.sleep(2)
                    break
                except ApiTelegramException as e:
                    retry+=1
                    retry_after = int(e.result_json['parameters']['retry_after'])
                    logging.info(f"Telebot: Retrying After {retry_after} seconds...")
                    time.sleep(retry_after)
    logging.info(f"Telebot: Total {int(len(tenders))+1} Tender Data sent...")

# --------------------- Tender Scraper END -----------------------------------#

# --------------------- Job Scraper Start -----------------------------------#

# loading the searching keys from text file
with open("search_keywords.txt", "r") as f:
    keyword_list = list(f.read().split("\n"))

#----------------------LinkedIn Scraper--------------------------------#

def linkedin_scraper():
    for keyword in keyword_list:
        count = 0
        base_url = f"https://www.linkedin.com/jobs/search?keywords={keyword}&location=Denmark&geoId=104514075&f_TPR=r86400&position=1&pageNum=0"
        driver_li.get(base_url)
        job_url= ""
        retry = 1
        max_retry = 5
        while retry<=max_retry:
            try:
                WebDriverWait(driver_li, 10).until(EC.visibility_of_all_elements_located((By.CSS_SELECTOR, ".jobs-search__results-list")))
                job_cards = driver_li.find_elements(By.CLASS_NAME, "base-card")
                break
            except Exception as e:
                retry+=1
                logging.info(f"linkedin: {e}")
        if retry >= max_retry:
            logging.info(f"linkedin: Couldn't search for {keyword}")
            continue
        logging.info(len(job_cards))
        for card in job_cards:
            while True:
                try:
                    WebDriverWait(driver_li, 10).until(EC.element_to_be_clickable(card))
                    card.click()

                except Exception as e:
                    print(f"linkedin: clicking card failed: {e}")
                    continue
                try:
                    WebDriverWait(driver_li, 10).until(lambda driver_li:driver_li.find_element(By.CSS_SELECTOR, ".topcard__link"))
                    script = f"return document.getElementsByClassName('topcard__link')[0].getAttribute('href');"
                    check_url = driver_li.execute_script(script)
                    print(f"--------{check_url}")
                except:
                    print(f"linkedin: Exce url failed: {e}")
                    continue
                try:
                    WebDriverWait(driver_li, 10).until(lambda driver_li:driver_li.find_element(By.CSS_SELECTOR, ".topcard__link").get_attribute("href")==check_url)
                    # WebDriverWait(driver_li, 10).until(lambda driver_li : driver_li.execute_script('return document.readyState')=='complete')
                    detail_card = driver_li.find_element(By.XPATH, "/html/body/div[1]/div/section/div[2]")
                    break
                except Exception as e:
                    time.sleep(2)
                    logging.info(f"linkedin: Detail Panel was not found: {e}")
            try:    
                job_pos = detail_card.find_element(By.CSS_SELECTOR, ".top-card-layout__title").text
                logging.info(f"linkedin: Job Position: {job_pos}")
            except Exception as e:
                logging.info(f"linkedin: Failed to fetch job position: {e}")    
            try:    
                location = detail_card.find_element(By.CSS_SELECTOR, "span.topcard__flavor:nth-child(2)").text
            except Exception as e:
                logging.info(f"linkedin: Failed to fetch location: {e}")
            try:        
                job_url_tag = detail_card.find_element(By.CSS_SELECTOR, ".topcard__link")
                job_url = job_url_tag.get_attribute("href")
            except Exception as e:
                logging.info(f"linkedin: Failed to fetch job URL: {e}")
            try:        
                description = detail_card.find_element(By.CSS_SELECTOR, ".show-more-less-html__markup").text
            except Exception as e:
                logging.info(f"linkedin: Failed to fetch description: {e}")    
                # time_ago = detail_card.find_element(By.CSS_SELECTOR, ".posted-time-ago__text").text
                # time_list = str(time_ago).split(' ')
                # if time_list[1] == 'minutes' or time_list[1] == 'minute':    
                # logging.info(job_pos, location)
                # print(description)
                # print(job_url)
                # print(time_ago)
                # print("=================")
                data_saver(job_pos+location+job_url, "data/linkedin.txt")
                count+=1
                time.sleep(5)
            # except Exception as e:
            #     logging.info(f"linkedin: Job position: {job_pos} \n {e}")
        data_saver(f"-----------{count}---------", "data/linkedin.txt")
#----------------------Jobindex Scraper--------------------------------#
def ignoring_popups(url, driver):
    driver.get(url)
    WebDriverWait(driver, 30).until(EC.visibility_of_element_located((By.CLASS_NAME, "modal-content")))
    try:
        btn = driver.find_element(By.XPATH, '//*[@id="jix-cookie-consent-accept-all"]')
        btn.click()
        logging.info("Cookies Accepted...")
        cross_btn = driver.find_element(By.XPATH, '//*[@id="jobmail_popup"]/div/div/div/button/span')
        cross_btn.click()
        time.sleep(2)
    except Exception as e:
        logging.info(f"Pop up: {e}")

def jobindex_scraper():
    ignoring_popups("https://www.jobindex.dk/jobsoegning/danmark?jobage=1&lang=en", driver_ji)
    for keyword in keyword_list:
        keyword = keyword.replace(" ", "+")
        base_url = f"https://www.jobindex.dk/jobsoegning/danmark?jobage=1&lang=en&q={keyword}"
        driver_ji.get(base_url)
        while True:
            WebDriverWait(driver_ji, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "jobsearch-result")))
            results = driver_ji.find_elements(By.CLASS_NAME, "jobsearch-result")
            logging.info(len(results))
            for result in results:
                WebDriverWait(driver_ji, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "jix_robotjob--area")))
                job_pos = result.find_element(By.TAG_NAME, "h4").text               
                try:
                    location_tag = result.find_element(By.CLASS_NAME, "jix_robotjob--area")
                except:
                    location_tag = result.find_element(By.CLASS_NAME, "jobad-element-area")
                location = location_tag.text
                descriptions = result.find_elements(By.TAG_NAME, "p")
                job_url_tag = result.find_element(By.CLASS_NAME, "seejobdesktop")
                job_url = job_url_tag.get_attribute("href")
                description = ""
                for d in descriptions:
                    description = description+d.text
                # logging.info(f"Position: {job_pos}")
                # logging.info(f"Locations: {location}")
                # logging.info(f"Job URL: {job_url}")
                # logging.info(f"JD: {description}")
                # logging.info("===================")
                data_saver(job_pos+location+job_url+description, "data/jobindex.txt")
                time.sleep(2)
            try:
                pag = driver_ji.find_element(By.CLASS_NAME, "jix_pagination")
                nxt_pag = pag.find_element(By.CLASS_NAME, "page-item-next")
                link = nxt_pag.find_element(By.TAG_NAME, "a")
                url = link.get_attribute("href")
                driver_ji.get(url)
                time.sleep(2)
            except:
                logging.info("jobindex: No more pages...")
                time.sleep(2)
                break

#-----------------------it-jobbank-----------------------#

def jobbank_scrapper():
    ignoring_popups("https://www.it-jobbank.dk/jobsoegning/danmark?jobage=1&lang=en", driver_jb)
    for keyword in keyword_list:
        keyword = keyword.replace(" ", "+")
        base_url = f"https://www.it-jobbank.dk/jobsoegning/danmark?jobage=1&lang=en&q={keyword}"
        driver_jb.get(base_url)
        time.sleep(60)
        while True:
            WebDriverWait(driver_jb, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "results")))
            results = driver_jb.find_elements(By.CLASS_NAME, "jobsearch-result")
            logging.info(len(results))
            for result in results:
                WebDriverWait(driver_jb, 10).until(EC.presence_of_all_elements_located((By.CLASS_NAME, "job-location")))
                job_head = result.find_element(By.TAG_NAME, "h3")
                job_pos = job_head.text             
                try:
                    location_tag = result.find_element(By.CLASS_NAME, "job-location")
                except:
                    location_tag = result.find_element(By.CLASS_NAME, "jobad-element-dialog-link")
                location = location_tag.text
                descriptions = result.find_elements(By.TAG_NAME, "p")
                job_url_tag = job_head.find_element(By.TAG_NAME, "a")
                job_url = job_url_tag.get_attribute("href")
                description = ""
                for d in descriptions:
                    description = description+d.text
                # logging.info(f"Position: {job_pos}")
                # logging.info(f"Locations: {location}")
                # logging.info(f"Job URL: {job_url}")
                # logging.info(f"JD: {description}")
                # logging.info("===================")
                data_saver(job_pos+location+job_url+description, "data/jobbank.txt")
                time.sleep(2)
            try:
                pag = driver_jb.find_element(By.CLASS_NAME, "jix_pagination")
                nxt_pag = pag.find_element(By.CLASS_NAME, "page-item-next")
                link = nxt_pag.find_element(By.TAG_NAME, "a")
                url = link.get_attribute("href")
                driver_jb.get(url)
                time.sleep(2)
            except:
                logging.info(f"jobbank: No more pages...")
                time.sleep(2)
                break


#---------------------indeed scraper----------------------#

# def indeed_scraper():
#     for keyword in keyword_list:
#         keyword = keyword.replace(" ", "+")
#         base_url = f"https://www.indeed.com/jobs?q={keyword}&l=Denmark&fromage=1&vjk=fe184b987b836188"
#         driver_in.get(base_url)
#         time.sleep(20)
        # retry = 1
        # max_retry = 5
        # while retry<=max_retry:
        #     try:
        #         WebDriverWait(driver_in, 10).until(EC.visibility_of_element_located((By.CLASS_NAME, "jcs-JobTitle")))
        #         job_cards = driver_in.find_elements(By.CLASS_NAME, "resultContent")
        #         break
        #     except Exception as e:
        #         retry+=1
        #         print(e)
        # if retry >= max_retry:
        #     print(f"Couldn't search for {keyword}")
        #     continue

        # print(len(job_cards))
        


# --------------------- Job Scraper End -----------------------------------#

def job_listener(event):
    if not isinstance(event, JobSubmissionEvent) and event.exception:
        logging.info('The job crashed :(')
    else:
        logging.info('The job worked :) ' + str(event))

# if __name__ == "__main__":
#     scheduler = BlockingScheduler()
#     scheduler.add_job(send_tenders, 'interval', minutes = 60)
#     scheduler.add_job(linkedin_scraper, 'interval', minutes = 60)
#     scheduler.add_job(jobindex_scraper, 'interval', minutes = 60)
#     scheduler.add_job(jobbank_scrapper, 'interval', minutes = 60)
#     scheduler.start()
#     scheduler.add_listener(job_listener)
#     driver.quit()
#     driver_li.quit()

if __name__ == "__main__":
    linkedin_scraper()
    driver_li.quit()