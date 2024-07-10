import os
import requests
import pandas as pd
import time
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

# Substitua pela sua chave da API armazenada em variáveis de ambiente
API_KEY = os.getenv('OPENCAGE_API_KEY')

# Cache para coordenadas
coords_cache = {}

def geocode_airport(airport_code):
    if airport_code in coords_cache:
        return coords_cache[airport_code]
    
    url = f'https://api.opencagedata.com/geocode/v1/json?q={airport_code}&key={API_KEY}'
    response = requests.get(url)
    data = response.json()
    if data['results']:
        latitude = data['results'][0]['geometry']['lat']
        longitude = data['results'][0]['geometry']['lng']
        coords_cache[airport_code] = (latitude, longitude)
        return latitude, longitude
    else:
        coords_cache[airport_code] = (None, None)
        return None, None

# Testar a função de geocodificação com um código de aeroporto
print(geocode_airport('LGA'))

# Carregar os dados
try:
    df = pd.read_csv(r'dataset/flights.csv')  # Use r'' para tratar a string como uma string bruta
    print("CSV carregado com sucesso!")
    print(df.head())
except FileNotFoundError:
    print("Arquivo CSV não encontrado. Verifique o nome e o caminho do arquivo.")
except Exception as e:
    print(f"Erro ao carregar o CSV: {e}")

# Adicionar colunas de latitude e longitude com verificações
try:
    df['ORIGIN_LAT'] = df['ORIGIN'].apply(lambda x: geocode_airport(x)[0] if x else None)
    df['ORIGIN_LON'] = df['ORIGIN'].apply(lambda x: geocode_airport(x)[1] if x else None)
    time.sleep(1)  # Adicionar um pequeno atraso para evitar limite de taxa da API
    
    df['DEST_LAT'] = df['DEST'].apply(lambda x: geocode_airport(x)[0] if x else None)
    df['DEST_LON'] = df['DEST'].apply(lambda x: geocode_airport(x)[1] if x else None)
    time.sleep(1)  # Adicionar um pequeno atraso para evitar limite de taxa da API

    # Verificar as primeiras linhas após adicionar as coordenadas
    print("Dados com coordenadas:")
    print(df.head())

    # Salvar o DataFrame atualizado
    df.to_csv('com_coordenadas.csv', index=False)
    print("CSV criado com sucesso!")
except Exception as e:
    print(f"Erro ao processar os dados: {e}")