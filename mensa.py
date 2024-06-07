import requests
import time
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import secret
import os

def input(elem, text):
    elem.clear()
    elem.send_keys(text)
    return

driver = webdriver.Firefox()  
wait = WebDriverWait(driver, 10)
driver.get("https://www.studentenwerk-goettingen.de/kartenservice")
driver.fullscreen_window()
#time.sleep(4)
dismiss_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cc-compliance .cc-btn.cc-dismiss")))
#dismiss_button = driver.find_element(By.CSS_SELECTOR, ".cc-compliance .cc-btn.cc-dismiss")
dismiss_button.click()

#time.sleep(2)
# === KARTENNUMMER ===
iframe = wait.until(EC.presence_of_element_located((By.NAME, "tx_iframe")))
driver.switch_to.frame(iframe)
knummer = wait.until(EC.visibility_of_element_located((By.NAME, "knr")))
input(knummer, secret.secret.name())
# === LOGIN === 
pword = driver.find_element(By.NAME, "pw")
input(pword, secret.secret.pw())
# === BUTTON LOGIN === 
#time.sleep(2)
button = wait.until(EC.visibility_of_element_located((By.NAME, "login")))
button.submit()
# === KONTOAUSZUG ===
#time.sleep(2)
button = wait.until(EC.visibility_of_element_located((By.ID, "image-buttonb")))
button.click()

# === Werte einlesen === 
rows = driver.find_elements(By.TAG_NAME, "tr")
data = ""
for row in rows:
    # Finde alle Zellen in der aktuellen Zeile
    cells = row.find_elements(By.TAG_NAME, "td")
    print(f"zelle 0: {cells.text} \n\n")
    print(f"zelle: {cells.text}")
    row_text = [cell.text for cell in cells]

    # Füge den Zeilentext zum table_text hinzu, getrennt durch Tabulatoren und mit einem Zeilenumbruch am Ende
    data += "\t".join(row_text) + "\n"



file_exists = os.path.isfile("Caphy_Data.txt")
mode = 'a' if file_exists else 'w'

with open("Caphy_Data.txt", mode) as f:
    f.write(data)
print(f"0: {data[0]}")
print(f"1: {data[1]}")
print(f"2: {len(data)}")
time.sleep(20)
driver.quit()
print("Fertig")


