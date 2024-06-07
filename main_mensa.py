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
import secret
import os
import pandas as pd

duration = [10] # time in days for mid value
fileName = "Mensa_Data" 
#fileName = "data.txt" 

def datatext(time, y): # console output
    gesamtString = ""
    sumValue = 0.0
    for i in range(len(y)):
        if y[i] >= 0:
            sumValue += y[i]


    gesamtString = "\nGesamtausgaben: " + str(sumValue) + "\n" + "Durchschnitt: " + str(sumValue/90) + "\n \n" + "Anzahl Transaktionen: " + str(len(y)) + "\n" + "Höchste Ausgabe: " + str(max(y)) + "\n"

    return gesamtString
def input(elem, text):
    elem.clear()
    elem.send_keys(text)
    return
def createData_auto():
    driver = webdriver.Firefox()  
    wait = WebDriverWait(driver, 10)
    driver.get("https://www.studentenwerk-goettingen.de/kartenservice")
    driver.fullscreen_window()
    dismiss_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cc-compliance .cc-btn.cc-dismiss")))
    #dismiss_button = driver.find_element(By.CSS_SELECTOR, ".cc-compliance .cc-btn.cc-dismiss")
    dismiss_button.click()
    # === KARTENNUMMER ===
    iframe = wait.until(EC.presence_of_element_located((By.NAME, "tx_iframe")))
    driver.switch_to.frame(iframe)
    knummer = wait.until(EC.visibility_of_element_located((By.NAME, "knr")))
    input(knummer, secret.secret.name())
    # === LOGIN === 
    pword = driver.find_element(By.NAME, "pw")
    input(pword, secret.secret.pw())
    # === BUTTON LOGIN === 
    button = wait.until(EC.visibility_of_element_located((By.NAME, "login")))
    button.submit()
    # === KONTOAUSZUG ===
    button = wait.until(EC.visibility_of_element_located((By.ID, "image-buttonb")))
    button.click()

    # === Werte einlesen === 
    rows = driver.find_elements(By.TAG_NAME, "tr")
    data = []
    time = []
    y = []
    go = False
    for row in rows:
        # Finde alle Zellen in der aktuellen Zeile
        cells = row.find_elements(By.TAG_NAME, "td")
        row_text = [cell.text for cell in cells]
        i = 0
        for cell in cells:
            if go == False:
                go = True
                break
            if i == 2:
                time.append(cell.text)
            elif i == 6:
                text = cell.text.replace(',', '.')
                if "," in cell.text:
                    if float(text) >= 0:
                        y.append(float(text))
                    else: 
                        y.append(0)
                else:
                    y.append(0.0)
            i +=  1

        # Füge den Zeilentext zum table_text hinzu, getrennt durch Tabulatoren und mit einem Zeilenumbruch am Ende
        data.append(row_text)
    driver.quit()

    # === DATAFRAME anpassen ===
    data.pop(0)
    df = pd.DataFrame(data)
    file_exists = os.path.isfile("Caphy_Data.csv")
    header = ["Kasse", "Name Kasse", "Datum", "Vorgang", "Loader", "Aufwertung", "Zahlung", "Saldo"]
    df.columns = header
    def convert_comma_and_float(value):
        try:
            if "," not in value:
                return value
            return float(value.replace(',', '.'))
        except ValueError:
            return 0.0
    df[header[2]] = pd.to_datetime(df[header[2]], format='%d.%m.%y', errors='coerce')
    df[header[5]] = df[header[5]].apply(convert_comma_and_float)
    df[header[6]] = df[header[6]].apply(convert_comma_and_float)
    df[header[7]] = df[header[7]].apply(convert_comma_and_float)



    if os.path.exists(fileName):
        df_existing = pd.read_csv(fileName + ".csv")
        df_existing[header[2]] = pd.to_datetime(df_existing[header[2]], format='%d.%m.%y', errors='coerce')
        latest_date = df_existing[header[2]].max()
        
        # Neue Daten filtern, um nur die Daten nach dem neuesten Datum zu behalten
        if df[df[header[2]]].max() > latest_date: 
            df = df[df[header[2]] > latest_date]
        else:
            print("bereits aktuell")
            df = df_existing
    else:
        df_existing = pd.DataFrame()

    # Die neuen Daten zur CSV-Datei hinzufügen
    df_combined = pd.concat([df_existing, df])
    df_combined.to_csv(fileName + ".csv", index=False,header=True)

    print("Data Loaded", time)
    date = [datetime.strptime(time, '%d.%m.%y') for time in time]

    return date, y


def createData_old(): # read data from file

    try:
        with open(fileName, 'r') as datei:
            text = datei.read()

        # Ausgabe des eingelesenen Strings
        print("Eingelesener String:")

    except Exception as e:
        print(f"Fehler beim Einlesen der Datei: {e}")
    data = [[]]
    date = []
    i = 1
    zahlen = ["0","1","2","3","4","5","6","7","8","9",",",".","-"]
    num = ""
    numint = 0.0

    while True:
        if text[i] == "\n":
            data.append([])
        else:
            if text[i] in zahlen and (text[i] == "." and text[i-1] in zahlen or text[i] != "."):
                if text[i] == ",":
                    num += "."
                else:
                    num += text[i]
            if text[i] not in zahlen:
                if num != "":
                    if num.count(".") < 2:
                        numint = float(num)
                        data[-1].append(numint)
                        num = ""
                        numint = 0.0
                    else:
                        date.append(num)
                        num = ""
                        numint = 0.0

        if text[i] == "@":
            break    
        i += 1

    for i in reversed(range(len(data))):
        if data[i] == []:
            data.pop(i)
    for i in range(len(data)):
        if len(data[i]) == 5:
            data[i].pop(1)

    time = [datetime.strptime(date, '%d.%m.%y') for date in date]

    x = []
    y = []
    for i in range(len(data)):
        if data[i][1] != 5.0: # Geld aufladen
            x.append(i)
            y.append(data[i][2])
        else:
            x.append(i)
            y.append(0)
    return time,y


def medData(time,y,duration): # medium values for different time intervalls
    zeit = []
    wert = []
    for l in range(len(duration)):
        time2 = []
        y2 =[]
        y1 = 0.0
        # set k = 0 for mid payment price or set k = duration for mid payment per duration periode
        k = 0 
        k = duration[l] 
        start = time[0]
        print(duration[l])

        for i in range(len(time)):
            #k +=1
            if start - timedelta(days=duration[l]) <= time[i]:
                y1 += y[i]
            else:
                time2.append(time[i-1] + timedelta(days=duration[l]/2))
                y2.append(y1/k)
                y1 = y[i]
                start = time[i]
                #k = 0
        if y1 != 0.0:
            time2.append(time[-1])
            y2.append(y1/k)
        zeit.append(time2)
        wert.append(y2)
    return zeit,wert
def plotData(time,y,time2 = None,y2 = None, fileName = "plot"):
    plt.figure(figsize=(10,8))
    plt.gca().xaxis.set_major_formatter(plt.matplotlib.dates.DateFormatter('%d.%m.%y'))

    plt.grid()
    plt.scatter(time,y, label="Messwerte", color='blue' , alpha = 0.5)

    plt.axhline(y=0.85, color='brown', linestyle='--', label='Schoko Milch')
    plt.axhline(y=2.1, color='red', linestyle='--', label='Bockwurst-Brot')
    plt.axhline(y=1.8, color='green', linestyle='--', label='Kuchen')
    #plt.axhline(y=1.0, color='orange', linestyle='--', label='Wäsche')
    if time2 != None:
        for i in range(len(time2)):
            plt.plot(time2[i],y2[i])

    print(datatext(time,y))

    plt.legend()
    plt.title(fileName)
    plt.savefig(fileName + ".png")
    #plt.show()



#time,y = createData()
time, y = createData_auto()
time2, y2 = medData(time,y,duration)
print(datatext(time,y))
plotData(time,y,time2,y2,fileName)


