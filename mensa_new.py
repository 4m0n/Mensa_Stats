import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy import optimize
from datetime import datetime, timedelta
import requests
import time
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException

import secret
import os
import pandas as pd
import json

class Mensa:
    def __init__(self,transactions = None):
        if transactions is None:
            transactions = []
        self.transactions = transactions
    def append(self, data):
        self.transactions.append(data)
    def to_dict(self):
        return {
            "transactions": [t.to_dict() for t in self.transactions]
        }
    def length(self):
        return len(self.transactions)
    def print_all_values(self):
        for index, transaction in enumerate(self.transactions, start=1):
            print(f"Transaction {index}:")
            print(f"  Datum: {transaction.datum}")
            print(f"  Ort: {transaction.ort}")
            print(f"  Guthaben: {transaction.guthaben}€")
            print(f"  Bezahlt: {transaction.bezahlt}€")
            print("  Sub-Transaktionen:")
            for sub_trans in transaction.sub_trans:
                print(f"    Datum: {sub_trans.datum}")
                print(f"    Ort: {sub_trans.ort}")
                print(f"    Kasse: {sub_trans.kasse}")
                print(f"    Menge: {sub_trans.menge}")
                print(f"    Produkt: {sub_trans.produkt}")
                print(f"    Preis: {sub_trans.preis}€")
            print("")  # Leerzeile zwischen den Transaktionen

class Sub_Trans:
    def __init__(self, datum="", ort="", kasse="", menge=0, produkt="", preis=0.0):
        self.datum = datum
        self.ort = ort
        self.kasse = kasse
        self.menge = menge
        self.produkt = produkt
        self.preis = preis
    def to_dict(self):
        return {
            "datum": self.datum,
            "ort": self.ort,
            "kasse": self.kasse,
            "menge": self.menge,
            "produkt": self.produkt,
            "preis": self.preis
        }

class Transaction:
    def __init__(self, datum="", ort="", guthaben=0.0, bezahlt=0.0, sub_trans=None):
        self.datum = datum
        self.ort = ort
        self.guthaben = guthaben
        self.bezahlt = bezahlt
        if sub_trans is None:
            sub_trans = [Sub_Trans()]
        self.sub_trans = sub_trans

    def to_dict(self):
        return {
            "datum": self.datum,
            "ort": self.ort,
            "guthaben": self.guthaben,
            "bezahlt": self.bezahlt,
            "sub_trans": [st.to_dict() for st in self.sub_trans]
        }


def read_data(driver,wait, button):
    guthaben = wait.until(EC.visibility_of_element_located((By.ID, "umsatzSaldo"))).text
    bezahlt = wait.until(EC.visibility_of_element_located((By.ID, "umsatzGegeben"))).text
    datum = driver.find_element(By.CSS_SELECTOR, "a.text-blue-600.mb-sales-1").text 
    ort = driver.find_element(By.CSS_SELECTOR, "p.text-sm.mt-1.text-center.cursor-pointer").text

    #guthaben = 
    try:
        # Finde das <tbody>-Element mit der id "positionTable"
        time.sleep(1)
        tbody = wait.until(EC.presence_of_element_located((By.ID, "positionTable")))
        # Finde alle <tr>-Elemente innerhalb des <tbody>
        rows = tbody.find_elements(By.TAG_NAME, "tr")
        sub_trans = []
        for row in rows:
            cells = row.find_elements(By.TAG_NAME, "td")
            if len(cells) == 5:
                datum2 = cells[0].text.strip()
                ort2 = cells[1].text.strip()
                menge = cells[2].text.strip()
                produkt = cells[3].text.strip()
                preis = cells[4].text.strip()
                sub_trans.append(Sub_Trans(datum=datum2, ort=ort2, kasse="4281", menge=menge, produkt=produkt, preis=preis))

                #kasse = cells[0]
            else:
                print("Sub_Trans kleiner als 5")

    except Exception as e:
        print("Fehler beim Suchen des Elements:", e)
    trans = Transaction(datum=datum,ort=ort, guthaben=guthaben, bezahlt=bezahlt, sub_trans=sub_trans)
    return trans



def input(elem, text):
    elem.clear()
    elem.send_keys(text)
    return


def createData_auto():
    mensa = Mensa()
    driver = webdriver.Firefox()  
    wait = WebDriverWait(driver, 10)
    driver.get("https://mensa.studierendenwerk-goettingen.de/login")
    driver.fullscreen_window()
    # === KARTENNUMMER ===
    email = wait.until(EC.presence_of_element_located((By.ID, "email")))
    input(email, secret.secret.email())
    # === LOGIN === 
    pword = driver.find_element(By.ID, "password")
    input(pword, secret.secret.pw2())
    # === BUTTON LOGIN === 
    button = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "button.bg-red-500")))
    button.submit()
    # === BEZAHLHISTORIE ===
    button = wait.until(EC.visibility_of_element_located((By.CSS_SELECTOR, "a[href='https://mensa.studierendenwerk-goettingen.de/sales']")))
    button.click()
    # === BESTELLUNGEN === 
    transactions = []
    open_next = True
    while open_next: 
        # ITERRIERE ÜBER ALLE BESTELLUNGEN
        #transactId
        tbody = driver.find_element(By.TAG_NAME, "tbody")
        links = tbody.find_elements(By.TAG_NAME, "a")
        try:
            next_site = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "Zurück »")))
            for button in links:
                button.click()
                print(f"button text: \n{button.text}")
                transactions.append(read_data(driver,wait,button))
                mensa.append(read_data(driver,wait,button))
                #mensa.print_all_values()
            next_site.click()
        except:
            open_next = False
        print(f"len {mensa.length()}")
        if mensa.length() >= 2:
            break

    driver.close()
    print("done")
    mensa_dict = mensa.to_dict()
    print(f"Dic: {mensa_dict}")
    # Konvertieren in JSON
    json_data = json.dumps(mensa_dict, indent=2)
    # Speichern in eine JSON-Datei
    print("Saving!\n\n")
    with open('mensa_data.json', 'w') as json_file:
        json_file.write(json_data)

createData_auto()