from selenium import webdriver
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.by import By
import time
import pandas as pd
from datetime import datetime, timedelta


opts = ChromeOptions()
opts.add_argument("--headless=new")

url = "https://www.eprocure.gov.bd/resources/common/StdTenderSearch.jsp?h=t"

driver = webdriver.Chrome()
driver.implicitly_wait(5)

c_time = datetime.now()
c_time_delayed = c_time - timedelta(hours=2)

def get_tenders_columns():
    table = driver.find_element(By.ID, "resultTable")
    body = table.find_element(By.TAG_NAME, "tbody")
    rows = body.find_elements(By.TAG_NAME, "tr")
    table_heads = rows[0].find_elements(By.TAG_NAME, "th")
    columns = []
    for heads in table_heads:
        columns.append(heads.text)
    return columns

def get_timestamp(time_str):
    time_format = "%d-%b-%Y %H:%M"
    t_time = datetime.strptime(time_str, time_format)
    return t_time

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

def get_tenders():
    driver.get(url)
    time.sleep(2)
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
            print("No Button")
            break
    tenders = []
    for d in data:
        tender = {}
        for i in range(len(columns)):
            tender[columns[i]] = d[i]
        tenders.append(tender)
    driver.quit()
    return tenders

if __name__ == "__main__":
    tenders = get_tenders()
    print(tenders)