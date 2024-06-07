# Mensa ausgaben
## Einrichten
- **secret.py in folgender Form erstellen -> in selben Ordner speichern**
  ```py
  class secret:
    def name():
        return "Anmeldenummer"
    def pw():
        return "Password"
  ```
- main_mensa.py ist die Hauptdatei
- mensa.py lädt nur die Daten in eine Datei (unvollständig)

- gegebenfalls fehlende packages installieren
  
- Mensa_Data.csv und Mensa_Data.png werden erstellt

## Anpassen (alles in main_mensa.py)
### Produkte hinzufügen/entfernen
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

## Ausführen
- ausführen mit 
  ```
      python3 main_mensa.py
  ``` 
- WICHTIG secret.py muss mit eigenen Daten existieren

## Updates

- vlt später
  
