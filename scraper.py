from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
from datetime import datetime, timedelta
import os
import telebot
from telebot.apihelper import ApiTelegramException

# Initializing telegram bot
# BOT_TOKEN = os.environ.get("BOT_TOKEN")
BOT_TOKEN = "7201255523:AAEhjZjp0g0YtBmVH1qv0GstvXQg4WbaVK4"
bot = telebot.TeleBot(BOT_TOKEN)

# Options for chrome driver
opts = ChromeOptions()
opts.add_argument("--headless=new")

# URL of the website to scrape
url = "https://www.eprocure.gov.bd/resources/common/StdTenderSearch.jsp?h=t"

# Webdriver assignment and implicit time delay assign
driver = webdriver.Chrome()
driver.implicitly_wait(5)

# Current time assignment
c_time = datetime.now()

# Set the duration of tenders
c_time_delayed = c_time - timedelta(hours=2)

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
    table = driver.find_element(By.ID, "resultTable")
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
    return row_data

# For getting the tender data in list of json format
def get_tenders():
    driver.get(url)
    time.sleep(2)
    try:
        WebDriverWait(driver, 60).until(
            EC.presence_of_all_elements_located(By.ID, "resultTable")
        )
        print(f"The page fully loaded...")
    except:
        print(f"Failed to load the full page...")
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
    for update in updates:
        if update.message and update.message.chat.type in ['group', 'supergroup']:
            return update.message.chat.id

if __name__ == "__main__":
    group_id = get_group_chat_id()
    columns, tenders = get_tenders()
    if len(tenders) > 0:
        for tender in tenders:
            print(tender)
            msg = f"{str(columns[0])}: {str(tender[0])}\n{str(columns[1])}: {str(tender[1])}"
            while True:
                try:
                    bot.send_message(
                        chat_id = group_id,
                        text = msg,
                        allow_sending_without_reply = True
                        )
                    time.sleep(2)
                    break
                except ApiTelegramException as e:
                    retry_after = int(e.result_json['parameters']['retry_after'])
                    print(f"Retrying After {retry_after} seconds...")
                    time.sleep(retry_after)
