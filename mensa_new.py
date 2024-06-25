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
import re
import secret
import os
import pandas as pd
import json

# ==== INPUTS ====
fav_items = {"Item": ["Schoko-Milch", "Bockwurst-Brot-2xSenf", "Kuchen"], "Price":[0.85,1.95,1.8]}
mid = 1 #time in days



#================
fav_items = pd.DataFrame(fav_items)

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
    def last_trans(self):
        return self.transactions[-1]
    def get_simple_plot(self):
        x,y, z = [],[],[]
        for val in self.transactions:
            if val.bezahlt <= 0:
                continue
            x.append(val.datum)
            y.append(val.bezahlt)
            z.append(val.guthaben)
        return x,y,z
    def simple_mid_plot(self,mid):
        x1,y1,z1 = self.get_simple_plot()
        print("ehhh \n\n")
        # Überprüfen, ob die Eingabelisten gleich lang sind
        if len(x1) != len(y1):
            raise ValueError("Die Listen x und y müssen die gleiche Länge haben.")
        x = [x1[0]]
        y = [y1[0]]
        for i in range(1,len(x1)-1):
            if x1[i] == x1[i-1]:
                y[-1]+=y1[i]
            else:
                x.append(x1[i])
                y.append(y1[i])

        avg_y = []

        # Berechnung der nicht-überlappenden Durchschnitte
        min_date = min(x) 
        max_date = max(x)

        date_list = []
        current_date = min_date
        
        while current_date <= max_date:
            date_list.append(current_date)
            current_date += timedelta(days=mid)
        if date_list[-1] < max_date:
            date_list.append(max_date)

        avg_y =np.zeros(len(date_list))
        for x2,y2 in zip(x,y):
            for i in range(1,len(date_list)):
                if x2 <= date_list[i] and x2 > date_list[i-1]:
                    avg_y[i]+=y2 

        return date_list, avg_y, x1, z1


    def convert_types(self):
        for t in self.transactions:
            t.convert_types()


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
    def convert_types(self):
        if len(self.datum) < 8: 
            self.datum += ":00"
        self.datum = datetime.strptime(self.datum, "%H:%M:%S")
        self.preis = self.preis.replace(",",".")
        self.preis = -float(re.sub(r'[^\d.-]', '', self.preis)) #minues sieht schöner aus
        self.menge = self.menge.replace(",",".")
        self.menge = float(re.sub(r'[^\d.-]', '', self.menge)) 


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
    def convert_types(self):
        self.datum = datetime.strptime(self.datum, '%d.%m.%Y')
        self.guthaben = self.guthaben.replace(",",".")
        self.guthaben = float(re.sub(r'[^\d.-]', '', self.guthaben))
        self.bezahlt = self.bezahlt.replace(",",".")
        self.bezahlt = -float(re.sub(r'[^\d.-]', '', self.bezahlt)) #minus sieht schöner aus
        for st in self.sub_trans:
            st.convert_types()


def read_data(driver,wait, datum,ort,guthaben,bezahlt):
    guthaben = guthaben
    bezahlt = bezahlt
    datum = datum
    ort = ort

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
# === LOADING DATA ===

def from_dict(sub_trans_dict):
    return Sub_Trans(
        datum=sub_trans_dict["datum"],
        ort=sub_trans_dict["ort"],
        kasse=sub_trans_dict["kasse"],
        menge=sub_trans_dict["menge"],
        produkt=sub_trans_dict["produkt"],
        preis=sub_trans_dict["preis"]
    )

def transaction_from_dict(transaction_dict):
    sub_trans_list = [from_dict(st) for st in transaction_dict["sub_trans"]]
    return Transaction(
        datum=transaction_dict["datum"],
        ort=transaction_dict["ort"],
        guthaben=transaction_dict["guthaben"],
        bezahlt=transaction_dict["bezahlt"],
        sub_trans=sub_trans_list
    )

def mensa_from_dict(mensa_dict):
    transactions_list = [transaction_from_dict(t) for t in mensa_dict["transactions"]]
    return Mensa(transactions_list)

# ============================

def createData_auto(skip = False):
    # Pfad zur JSON-Datei
    latest_trans = None
    mensa_old = None
    file_path = 'mensa_data.json'
    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        with open(file_path, 'r') as f:
            mensa_dict = json.load(f)
        # In Klassenobjekt umwandeln
        mensa_old = mensa_from_dict(mensa_dict)
        mensa_old.transactions.reverse()
        latest_trans = mensa_old.last_trans()
        latest_trans = latest_trans.to_dict()
    else:
        print("Die Datei existiert nicht oder ist leer.")
    if skip:
        return mensa_old
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
        button_list = tbody.find_elements(By.TAG_NAME, "a")
        links = tbody.find_elements(By.TAG_NAME, "tr")
        try:
            next_site = wait.until(EC.visibility_of_element_located((By.LINK_TEXT, "Zurück »")))
            for index, site in enumerate(links):
                button = button_list[index]
                button.click()

                lines = site.text.split("\n")
                datum = lines[0]
                ort = lines[1]
                preis_parts = lines[2].split()
                guthaben = preis_parts[0]
                bezahlt = preis_parts[1]
                trans = read_data(driver,wait,datum,ort,guthaben,bezahlt)
                #print(f"\nCompare:\nN:{trans.to_dict()}\n\nO:{latest_trans}\n====================\n")
                if trans.to_dict() == latest_trans:
                    print("up to date")
                    open_next = False
                    break
                transactions.append(trans)
                mensa.append(trans)
                #mensa.print_all_values()

            next_site.click()
        except:
            open_next = False
        if mensa.length() >= 2:
            #break #break early
            continue
    driver.close()
    if mensa_old != None:
        mensa.transactions.reverse()
        for val in mensa.transactions:
            mensa_old.append(val)
        mensa = mensa_old
        mensa.transactions.reverse()
    mensa_dict = mensa.to_dict()
    # Konvertieren in JSON
    json_data = json.dumps(mensa_dict, indent=2)
    # Speichern in eine JSON-Datei
    with open('mensa_data.json', 'w') as json_file:
        json_file.write(json_data)
    mensa.convert_types()
    print("Saved...\n")
    return mensa

# ==== PLOTTING ====
def plot_transactions(data,color,value):
    if mid == 0:
        x,y,x2,z = data.get_simple_plot()
    else:
        x,y,x2,z = data.simple_mid_plot(mid)
    if value == "guthaben":
        y = z
        x = x2
    plt.grid()
    plt.scatter(x,y)
    plt.fill_between(x,y,color=color, alpha = 0.2)
    for i in range(len(fav_items)):
        item = fav_items["Item"][i]
        price = fav_items["Price"][i]
        if (type(price) == type(np.float64(3.14))) != (type(price) == type(np.int64(42))):
            plt.axhline(y=price, linestyle='--', label=item)
    plt.legend()
    plt.show()

data = createData_auto(False)
plot_transactions(data, "blue", "price")
plot_transactions(data, "red","guthaben")