import requests
from bs4 import BeautifulSoup
import json
import pandas as pd
import secret

url = 'https://mensa.studierendenwerk-goettingen.de/'
data = {
  '_token': '-empty-',
  'email': secret.login.email,
  'password': secret.login.pw2,
  'button': ''
}

path_raw = 'data/raw_data/kasse'
path_df = 'data/cummulated_data/all-items'

transact_ids = range(0, 2000)    # Transactions ID gilt pro Kasse und wird täglich auf 0 gesetzt - max 2000, da vllt manche kassen so frequentiert sind
# kasse_ids = range(0, 4500)     # Range of Kasse IDs for testing / brute forcce to retrieve kasse_ids

kasse_ids = [1001,    # Aufwerter EC Caphy
             1002,    # Aufwerter Bar Caphy
             1005,    # Aufwerter EC Caphy Concar
             4031,    # Café Central 1
             4032,    # Café Central 2
             4071,    # Z-Mensa Kasse 1 (? geraten - keine Daten im Scan)
             4072,    # Z-Mensa Kasse 2
             4073,    # Z-Mensa Kasse 3
             4074,    # Z-Mensa Kasse 4
             4081,    # Z-Mensa Kasse 5
             4082,    # Z-Mensa Kasse 6
             4083,    # Z-Mensa Kasse 7
             4084,    # Z-Mensa Kasse 8
             4093,    # Aufwerter EC ZM Café Zent
             4095,    # Aufwerter EC ZM Foyer
             4097,    # Aufwerter EC ZM Foyer
             4100,    # Aufwerter ZM Foyer-Centr
             4102,    # Aufwerter ZM Foyer
             4151,    # Mensa am Turm 1 (? geraten - keine Daten im Scan)
             4152,    # Mensa am Turm 2
             4161,    # Café am Turm
             4193,    # Aufwerter EC ZM CZ Concar
             4201,    # Nordmensa Ks. 1
             4202,    # Nordmensa Ks. 2
             4203,    # Nordmensa Ks. 3
             4204,    # Nordmensa Ks. 4
             4207,    # Aufwerter EC Nordmensa
             4211,    # coffeebar ins grüne Ks.1
             4212,    # coffeebar ins grüne Ks.2 (? geraten - keine Daten im Scan - mir fehlt aber garantiert eine Transaktion in diesem café)
             4213,    # LunchBox Ks. 1
             4214,    # LunchBox Ks. 2
             4215,    # Aufwerter EC LunchBox 1
             4217,    # Café-Ecke Lunchbox
             4218,    # LunchBox Kasse ToGo
             4281,    # Cafeteria Neue Physik
             ]

def save_json_to_file(data, file_path):
    """
    This function saves a dictionary as a JSON file.
    
    Parameters:
        data (dict): The dictionary to be saved as JSON.
        file_path (str): The path to the file where the JSON data will be saved.
    """
    try:
        with open(f'{file_path}.json', 'w') as file:
            json.dump(data, file, indent=4)
        print(f"Data successfully saved to {file_path}")
    except IOError as e:
        print(f"Error: Unable to save to file {file_path}. {e}")

def get_all_items(session):
    """
    This function scans the web for possible transactions per checkout id

    Parameters:
        session (requests.Session()): The current session in web
    """
    list_all_items = list()
    
    for kasse_id in kasse_ids:
        print(f'Start loading Kasse ID: {kasse_id}')
        
        list_items = list()
        for transact_id in transact_ids:
            response_items = session.get(f'{url}/sales/{transact_id}/{kasse_id}/position')
            if response_items:
                list_items.extend(response_items.json())
                                  
        print(f'Loading transactions from Kasse ID: {kasse_id} done')
    
        if (len(list_items) > 0):
            save_json_to_file(list_items, f'{path_raw}-{kasse_id}')
        else:
            print(f'No transactions found for Kasse ID {kasse_id}')

        list_all_items.extend(list_items)
    return list_all_items

with requests.Session() as session:
    # --- first GET page ---
    response = session.get(f'{url}/login')

    # --- search fresh token in HTML ---
    soup = BeautifulSoup(response.text)
    token = soup.find('input', {'name': "_token"})['value']
    
    # --- run POST with new token and log in to website ---
    data['_token'] = token
    response = session.post(f'{url}/login', data=data, allow_redirects=False)

    # --- get all Items ---
    list_all_items = get_all_items(session)


    def change_items_type(items_df):
        items_df = items_df.astype({
            'kasse_id': 'int', 
            'menge': 'int',
            'epreis': 'float',
            'rabatt': 'float',
            'katrans_id': 'int'})
        items_df['datum'] = pd.to_datetime(items_df['datum'])
        items_df = items_df.convert_dtypes()
        return items_df

# change data type to usable types
df_all_items = change_items_type(pd.DataFrame(list_all_items))


# Save data with changed data types to csv and json

df_all_items.to_csv(f'{path_df}.csv', index=False)
df_all_items.to_json(f'{path_df}_records.json', orient="records", indent=4)
df_all_items.to_json(f'{path_df}_index.json', orient="index", indent=4)
df_all_items.to_json(f'{path_df}_table.json', orient="table", indent=4)