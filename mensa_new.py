import numpy as np
import matplotlib.pyplot as plt
import scipy.stats as stats
from scipy import optimize
from datetime import datetime, timedelta
from collections import Counter, defaultdict
from fpdf import FPDF
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
mid = 1 # Zeit in Tagen
show = False # Plots anzeigen


#================

# do not change
if not os.path.exists("pictures"):
    os.makedirs("pictures")

plot_names = ["torten_ort","meals","payed_time","guthaben","bezahlt","payed_day"]

class PDF(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, 'Statistiken zu den Ausgaben über den Studentenausweises', 0, 1, 'C')

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.cell(0, 10, title, 0, 1, 'C')
        self.ln(10)

    def chapter_body(self, body):
        self.set_font('Arial', '', 12)
        self.multi_cell(0, 10, body)
        self.ln()

    def add_image(self, image_path, x=None, y=None, w=0, h=0):
        self.image(image_path, x, y, w, h)
        self.ln(10)

    def add_images_side_by_side(self, image1_path, image2_path, image_width, image_height):
        y = 200
        self.image(image1_path, x=10,y = y, w=image_width)
        #self.image(image2_path, x=self.w / 2 + 10, w=image_width)
        self.image(image2_path, x=100, y = y , w = image_width)
        self.ln(image_width + 10)

    def add_text_and_image(self, text, image_path, image_width):
        # Text on the left
        self.set_xy(10, self.get_y())
        self.multi_cell(self.w / 2 - 15, 10, text)
        
        # Image on the right
        self.set_xy(self.w / 2 + 10, self.get_y() - (len(text.split('\n')) * 10))
        self.image(image_path, w=image_width)
        self.ln(image_width + 10)

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
    input(email, secret.login.email())
    # === LOGIN === 
    pword = driver.find_element(By.ID, "password")
    input(pword, secret.login.pw2())
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

# ====  Statistiken ====
def torten_ort(data, show = True):
    ort=[]
    k=len(data.transactions)
    for i in range(k):
        ort.append(data.transactions[i].ort)
    myset=set(ort)
    no=list(myset)

    wert=[]
    for i in range(len(no)):
        wert.append(ort.count(no[i]))

    explode = [0.05] * len(wert)

    plt.pie(wert,labels=no,autopct="%1.1f%%", pctdistance=0.85, explode = explode,startangle=90)
    centre_circle = plt.Circle((0,0),0.70,fc='white')
    fig = plt.gcf()
    fig.gca().add_artist(centre_circle)
    plt.axis('equal')  
    plt.tight_layout()
    plt.savefig("pictures/"+plot_names[0] + ".jpeg",dpi = 600)
    if show:
        plt.show()
    else:
        plt.close()



"""def wo_tag_zahl2(data):
    WT = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    k = len(data.transactions)

    # Initialisiere leere Series für Anzahl und Preise
    werte = pd.Series(0, index=WT)
    preise = pd.Series(0.0, index=WT)

    for i in range(k):
        if data.transactions[i].bezahlt < 0:
            continue
        day_of_week = data.transactions[i].datum.strftime("%A")
        if day_of_week in werte:
            werte[day_of_week] += 1
            preise[day_of_week] += data.transactions[i].bezahlt
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax2 = ax1.twinx()
    werte.plot(kind='bar', ax=ax1, color='blue', position=0, width=0.4, label='Anzahl der Käufe')
    preise.plot(kind='bar', ax=ax2, color='orange', position=1, width=0.4, label='Gesamtausgaben', alpha=0.7)


    ax1.set_xlabel('Uhrzeit')
    ax1.set_ylabel('Anzahl der Käufe')
    ax2.set_ylabel('Gesamtausgaben (€)')

    ax1.legend(loc='upper right')
    ax2.legend(loc='upper left')
    plt.title('Anzahl der Käufe und Gesamtausgaben pro Uhrzeit')
    plt.tight_layout()
    plt.savefig("pictures/"+plot_names[5]+".jpeg",dpi = 600)
    if show:
        plt.show()
    else:
        plt.close()"""
    
def wo_tag_zahl(data):

    WT=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
    k=len(data.transactions)
    mo,di,mit,do,fr,sa,so = 0,0,0,0,0,0,0
    mop,dip,mitp,dop,frp,sap,sop=0,0,0,0,0,0,0
    for i in range(k):
        if data.transactions[i].bezahlt<0:
            continue
        if data.transactions[i].datum.strftime("%A")=="Monday":
            mo+=1
            mop+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Tuesday":
            di+=1
            dip+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Wednesday":
            mit+=1
            mitp+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Thursday":
            do+=1
            dop+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Friday":
            fr+=1
            frp+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Saturday":
            sa+=1
            sap+=data.transactions[i].bezahlt
        elif data.transactions[i].datum.strftime("%A")=="Sunday":
            so+=1
            sop+=data.transactions[i].bezahlt

    werte=[mo,di,mit,do,fr,sa,so]
    preise=[mop,dip,mitp,dop,frp,sap,sop]

    #Durchschnitt bestimmen
    for i in range(len(werte)):
        if werte[i] == 0:
            continue
        preise[i] = preise[i]/werte[i]
    fig, ax1 = plt.subplots(figsize=(12, 6))

    ax2 = ax1.twinx()

    bar_width = 0.4
    x = np.arange(len(WT))

    # Plot der Anzahl der Käufe mit einem Offset nach links
    ax1.bar(x - bar_width / 2, werte, bar_width, color='blue', label='Anzahl der Käufe')

    # Plot der Gesamtausgaben mit einem Offset nach rechts
    ax2.bar(x + bar_width / 2, preise, bar_width, color='orange', label='Durschnittliche Gesamtausgaben')

    ax1.set_xlabel('Wochentag')
    ax1.set_ylabel('Anzahl der Käufe')
    ax2.set_ylabel('Gesamtausgaben (€)')

    ax1.set_xticks(x)
    ax1.set_xticklabels(WT)

    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')

    ax1.set_axisbelow(True)
    ax1.yaxis.grid(color='gray', linestyle='dashed')

    plt.title('Anzahl der Käufe und Gesamtausgaben pro Wochentag')
    plt.tight_layout()
    plt.savefig("pictures/"+plot_names[5]+".jpeg", dpi=600)
    if show:
        plt.show()
    else:
        plt.close()


def meals(data, show = True):
    products = []

    # Daten sammeln
    for trans in data.transactions:
        for sub_trans in trans.sub_trans:
            products.append((sub_trans.produkt, sub_trans.preis, sub_trans.menge))

    # Anzahl der Käufe zählen
    product_counts = Counter()
    for product, _, menge in products:
        product_counts[product] += menge

    # Gesamtpreis berechnen
    total_prices = defaultdict(float)
    for product, price, menge in products:
        total_prices[product] += price

    # Kombinierte Liste erstellen: (Produkt, Anzahl, Gesamtpreis)
    combined_data = [(product, product_counts[product], total_prices[product]) for product in product_counts]

    # Sortieren nach der Anzahl der Käufe (und falls nötig, nach anderen Kriterien)
    sorted_by_count = sorted(combined_data, key=lambda item: item[1], reverse=True)[:10]
    sorted_by_total_price = sorted(combined_data, key=lambda item: item[2], reverse=True)[:10]

    # Benutzerspezifische Funktionen für autopct
    def make_autopct(values):
        def my_autopct(pct):
            total = sum(values)
            val = int(round(pct * total / 100.0))
            return f'{val:d}'
        return my_autopct

    # Tortendiagramme erstellen
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 12))
    plt.subplots_adjust(wspace=0.6)  # Abstand zwischen den Plots

    # Schriftgröße anpassen
    plt.rcParams.update({'font.size': 10})

    # Anzahl der Käufe
    labels_count = [item[0] for item in sorted_by_count]
    sizes_count = [item[1] for item in sorted_by_count]
    explode = [0.05] * len(sizes_count)

    ax1.pie(sizes_count, labels=labels_count, autopct=make_autopct(sizes_count), startangle=90, pctdistance=0.85, explode = explode)
    ax1.pie([1,2], colors = ["white","white"],radius = 0.7)
    ax1.set_title('Top 15 Products by Number of Purchases', fontsize=14)
    plt.axis('equal')  


    # Gesamtpreis
    labels_price = [item[0] for item in sorted_by_total_price]
    sizes_price = [item[2] for item in sorted_by_total_price]

    ax2.pie(sizes_price, labels=labels_price, autopct=make_autopct(sizes_price), startangle=90, pctdistance=0.85, explode = explode)
    ax2.pie([1,2], colors = ["white","white"],radius = 0.7)
    ax2.set_title('Top 15 Products by Total Spend', fontsize=14)
    plt.axis('equal')  

    plt.tight_layout()
    plt.savefig("pictures/"+plot_names[1] + ".jpeg",dpi = 600)
    if show:
        plt.show()
    else:
        plt.close()
    
def max_tag(data):
    preis = []
    datum = []
    current_date = data.transactions[0].datum
    bezahlt = 0
    for trans in data.transactions:
        if current_date == trans.datum:
            if trans.bezahlt < 0 and trans.datum == current_date:
                continue
            elif trans.bezahlt < 0:
                preis.append(bezahlt)
                datum.append(current_date)
            else:
                bezahlt += trans.bezahlt
        else:
            preis.append(bezahlt)
            datum.append(current_date)
            if trans.bezahlt < 0:
                bezahlt = 0
            else:
                bezahlt = trans.bezahlt
            current_date = trans.datum

    index = preis.index(max(preis))
    if type(index) == type([1,2,3]):
        index = index[0]
    print(datum[index], preis[index])
def payed_at_time(data, show = True):
    def rounder(t):
        if t.minute >= 30:
            return t.replace(second=0, minute=0, hour=t.hour+1)
        else:
            return t.replace(second=0, minute=0)
    
    payed = []
    times = []
    payed2 = 0.0
    times2 = None
    for trans in data.transactions:
        for sub_trans in trans.sub_trans:
            if sub_trans.preis > 0: 
                payed2+=sub_trans.preis
                times2 = rounder(sub_trans.datum)
            if times2 == None:
                continue
            times.append(times2)
            payed.append(payed2)
            payed2 = 0.0
            times2 = None

    df = pd.DataFrame({'zeit': times, 'price': payed})

    # Alle möglichen abgerundeten Zeiten innerhalb des Zeitraums erstellen
    start_time = min(times).replace(minute=0, second=0, hour=6)
    end_time = max(times).replace(minute=0, second=0, hour=20)
    all_times = pd.date_range(start=start_time, end=end_time, freq='h').to_pydatetime().tolist()

    # Sicherstellen, dass alle Zeiten im DataFrame vorhanden sind
    all_times_df = pd.DataFrame({'zeit': all_times})
    df = pd.merge(all_times_df, df, on='zeit', how='left').fillna(0)

    # Anzahl der Käufe pro abgerundeter Uhrzeit
    counts = df['zeit'].value_counts().sort_index()

    # Gesamtausgaben pro abgerundeter Uhrzeit
    total_spent = df.groupby('zeit')['price'].sum()

    #counts auf 0 setzen da sonst immer 1 gezählt wird auch wenn nichts gekauft wurde
    for i in range(len(total_spent)):
        if total_spent.iloc[i] == 0:
            counts.iloc[i] = 0

    #Durchschnitt bestimmen
    for i in range(len(counts)):
        if counts.iloc[i] == 0:
            continue
        total_spent.iloc[i] = total_spent.iloc[i]/counts.iloc[i]
    # Plotting
    fig, ax1 = plt.subplots(figsize=(12, 6))
    ax2 = ax1.twinx()
    counts.plot(kind='bar', ax=ax1, color='blue', position=1, width=0.4, label='Anzahl der Käufe')
    total_spent.plot(kind='bar', ax=ax2, color='orange', position=0, width=0.4, label='Durschnittliche Gesamtausgaben', alpha=0.7)

    ax1.set_xlabel('Uhrzeit')
    ax1.set_ylabel('Anzahl der Käufe')
    ax2.set_ylabel('Gesamtausgaben (€)')

    ax2.legend(loc='upper right')
    ax1.legend(loc='upper left')
    ax1.set_xticklabels([dt.strftime('%H:%M') for dt in counts.index], rotation=45)
    
    ax1.set_axisbelow(True)
    ax1.yaxis.grid(color='gray', linestyle='dashed')

    plt.title('Anzahl der Käufe und Gesamtausgaben pro Uhrzeit')
    plt.tight_layout()
    plt.savefig("pictures/"+plot_names[2]+".jpeg",dpi = 600)
    if show:
        plt.show()
    else:
        plt.close()



def to_pdf():
    pdf = PDF()
    pdf.add_page()
    image_folder = 'pictures'  # Passe diesen Pfad an

    #Guthaben und Ausgaben
    pdf.chapter_title("Kontostand")
    image = str(plot_names[4]+".jpeg")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20) 
    pdf.chapter_body("Zu sehen ist der Kontostan im Verlauf der Zeit. Es sollte zu erkennen sein, wann Geld aufgeladen wurde und in welchen Abständen dinge gekauft wurden.")
    #Ausgaben
    pdf.add_page()
    pdf.chapter_title(f"Durchschnittliche Ausgaben pro: {mid}Tage")
    image = str(plot_names[3]+".jpeg")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20) 
    pdf.chapter_body(f"In Diesem Diagram sind die Ausgaben dargestellt. Es wurde ein Intervall festgelegt, indem alle Transaktionen zusammen gerechnet werden, dieses beträgt hier {mid}Tage.")
    #Ausgaben nach Menge und Geld
    pdf.add_page()
    pdf.chapter_title("Top Produkte nach Menge und Preis")
    image = str(plot_names[1]+".jpeg")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20) 
    pdf.chapter_body(f"Hier wird dargestellt, wieviel Produkte der selben Art man gekauft hat. Ausserdem ist zu sehen, wieviel man insgesamt für diese Produkte bezahlt hat. Dabei werden nur die Top 15 Produkte angezeigt.")
    # Kuchendiagram Orte
    pdf.add_page()
    image = str(plot_names[0]+".jpeg")
    pdf.chapter_title("Dargestellt ist die Verteilung der am häufigst besuchten Einrichtungen")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20)  
    #Tages vergleich
    pdf.add_page()
    image = str(plot_names[5]+".jpeg")
    pdf.chapter_title("Verteilung der Ausgaben über die Wochentage")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20)  
    pdf.chapter_body("Es wurde der pro Tage ausgegebene Betrag dargestellt, somit kann dem Diagram entnommen werden, zu welchen Tagen am meisten Geld ausgegeben wurde.")
    # Zeit vergleichen
    image = str(plot_names[2]+".jpeg")
    pdf.chapter_title("Verteilung der Ausgaben über die Uhrzeit")
    pdf.add_image(os.path.join(image_folder, image), w=pdf.w - 20)  
    pdf.chapter_body("Es wurde der pro Stunde ausgegebene Betrag dargestellt, somit kann dem Diagram entnommen werden, zu welchen Zeiten am meisten Geld ausgegeben wurde. Zu erkennen sind möglicherweise Mittags und Kaffeepause, sowie möglicherweise ein Anstieg Abends, bevor die Cafeterien schließen.")
   

    pdf.output("Statistik.pdf")
    print("\n==============\n\n\n\n\nPDF READY\n\n\n\n\n==============\n")


# ==== PLOTTING ====

def plot_transactions(data,color,value, show = True):
    name = plot_names[3]
    if mid == 0:
        x,y,x2,z = data.get_simple_plot()
    else:
        x,y,x2,z = data.simple_mid_plot(mid)
    if value == "guthaben":
        y = z
        x = x2
        name = plot_names[4]
    plt.grid()
    plt.grid(zorder=0)
    plt.fill_between(x,y,color=color, alpha = 0.2, zorder = 2)
    plt.bar(x,y, color=color, alpha = 0.6,edgecolor = "black", label = value, zorder = 3)
    plt.legend()
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.savefig("pictures/"+name+".jpeg",dpi = 600)
    if show:
        plt.show()
    else:
        plt.close()

data = createData_auto(False)
#payed_at_time(data,show)
#meals(data, show)
#torten_ort(data, show)
#plot_transactions(data, "blue", "price", show)
#plot_transactions(data, "red","guthaben",show)
#wo_tag_zahl(data)
max_tag(data)
to_pdf()
