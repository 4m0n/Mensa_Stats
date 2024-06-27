# Mensa ausgaben

- main_mensa.py für die alte Version
  
- mensa_new.py für die neue Version

## General Setup
- **secret.py in folgender Form erstellen -> in selben Ordner speichern**
  ```py
  class login:
    def name():
        return "Anmeldenummer"
    def pw():
        return "Pw für alte Seite"
    def email():
        return "your.email@stud.uni-goettingen.de"
    def pw2():
        return "Pw für neue Seite"
  ```
- diese code in secret.py kopieren udn speichern
- gegebenfalls fehlende packages installieren
## Setup neue Version
- secret.py erstellen und pw2 und email eingeben
- Inputs können ganz oben nach den Imports geändert werden
- mid = Anzahl an Tagen über die gemittelt werden soll 
- -show = Boolean ob die Plots angezeigt werden sollen (sonst werden sie nur )
### Ausführen

- ausführen mit 
  ```
      python3 mensa_new.py
  ``` 

## Setup alte Version


Folgende Zeilen:
```py
    plt.axhline(y=0.85, color='brown', linestyle='--', label='Schoko Milch')
    plt.axhline(y=2.1, color='red', linestyle='--', label='Bockwurst-Brot')
    plt.axhline(y=1.8, color='green', linestyle='--', label='Kuchen')
```
können an beliebge Preise und Produkte angepasst werden (es können auch weitere ergänzt werden)

### Mittelwert

```py
    duration = [10]
```
steht ganz oben und gibt die Anzahl der Tage an, über die eine Linie gemittelt werden soll

### Ausführen
- ausführen mit 
  ```
      python3 main_mensa.py
  ``` 

# Updates

- vlt später
  
