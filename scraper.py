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

# Initializing telegram bot
BOT_TOKEN = os.environ.get("BOT_TOKEN")
bot = telebot.TeleBot(BOT_TOKEN)

# Options for chrome driver
opts = ChromeOptions()
opts.add_argument("--headless=new")
# opts.page_load_strategy = 'eager'

# URL of the website to scrape
url = "https://www.eprocure.gov.bd/resources/common/StdTenderSearch.jsp?h=t"

# Webdriver assignment and implicit time delay assign
driver = webdriver.Chrome(options=opts)
driver.implicitly_wait(5)

# Current time assignment
c_time = datetime.now()

# Set the duration of tenders
c_time_delayed = c_time - timedelta(hours=1)

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
            time.sleep(2)
            table = WebDriverWait(driver, 10).until(EC.presence_of_element_located(By.ID, "resultTable"))
    return row_data

# For getting the tender data in list of json format
def get_tenders():
    driver.get(url)
    time.sleep(10)
    table_load = (By.ID, "resultTable")
    while True:
        try:
            WebDriverWait(driver, 10).until(EC.visibility_of_element_located(table_load))
            print("Table Loaded...")
            break
        except Exception as e:
            print("Failed to Load Table...")
            driver.quit()
            driver.get(url)
    columns = get_tenders_columns()
    data = []
    counter = 1
    while True:
        print(f"Page: {counter}")
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
            print("No More Next Button...Exiting...!")
            break
    driver.quit()
    return columns, data

def get_group_chat_id():
    updates = bot.get_updates()
    group_chat_ids = set()
    for update in updates:
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            group_chat_ids.add(update.message.chat.id)
    return list(group_chat_ids)

def send_tenders():
    group_ids = get_group_chat_id()
    print(group_ids)
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
                        bot.send_message(
                            chat_id = group_id,
                            text = msg,
                            allow_sending_without_reply = True,
                            parse_mode='HTML'
                            )
                    time.sleep(2)
                    break
                except ApiTelegramException as e:
                    retry+=1
                    retry_after = int(e.result_json['parameters']['retry_after'])
                    print(f"Retrying After {retry_after} seconds...")
                    time.sleep(retry_after)

def job_listener(event):
    if not isinstance(event, JobSubmissionEvent) and event.exception:
        print('The job crashed :(')
    else:
        print('The job worked :) ' + str(event))

if __name__ == "__main__":
    scheduler = BackgroundScheduler(daemon = True)
    scheduler.add_job(send_tenders, 'interval', minutes = 60)
    scheduler.start()
    scheduler.add_listener(job_listener)
    while True:
        i = input("Enter x to exit: ")
        if i == 'x':
            break
