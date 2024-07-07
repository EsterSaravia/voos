import requests
from flask import Flask, render_template, request, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv
import folium

# Carregar variáveis de ambiente
load_dotenv()

# Substitua pela sua chave da API armazenada em variáveis de ambiente
api_key = os.getenv('YOUR_CLIMA_KEY')
ors_key = os.getenv('YOUR_ORS_KEY', '5b3ce3597851110001cf6248834e86d2919b4690b796ebffc5106980')
print(f"API Key Clima: {api_key}")
print(f"ORS Key: {ors_key}")


app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///previsao.db'
app.config['SECRET_KEY'] = 'chavealeatoria'

db = SQLAlchemy(app)
app.app_context().push()

class City(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    origem = db.Column(db.String(50), nullable=False)
    destino = db.Column(db.String(50), nullable=False)
    
db.create_all()
if not City.query.all():
    db.session.add(City(origem='New York', destino='Boston'))
    db.session.commit()

def consultarCidade(cidade):
    url = f'http://api.openweathermap.org/data/2.5/weather?q={cidade}&units=metric&appid={api_key}'
    resposta = requests.get(url)
    resposta.raise_for_status()  # Levanta um erro para códigos de status HTTP diferentes de 200
    resposta_json = resposta.json()
    print(f"Resposta OpenWeatherMap para {cidade}:{resposta}")
    return resposta_json

def padronizar_nome_cidade(nome_cidade):
    return nome_cidade.capitalize()

# Função para obter coordenadas de uma cidade usando OpenRouteService API
def obter_coordenadas_cidade(nome_cidade):
    base_url = 'https://api.openrouteservice.org/geocode/search'
    params = {
        'api_key': ors_key,
        'text': nome_cidade
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Lança um erro para códigos de status HTTP diferentes de 200
        data = response.json()
        print(f"Resposta OpenRouteService para {nome_cidade}: {data}")
        if 'features' in data and data['features']:
            primeira_feature = data['features'][0]
            coordenadas = primeira_feature['geometry']['coordinates']
            return {'lat': coordenadas[1], 'lng': coordenadas[0]}
        else:
            print(f"Erro: Nenhuma feature encontrada para '{nome_cidade}'")
            return None

    except requests.exceptions.RequestException as e:
        print(f"Erro na requisição HTTP: {e}")
        return None
    except KeyError as e:
        print(f"Erro ao acessar chave: {e}")
        return None

# Função para obter rota entre duas cidades usando OpenRouteService API
def obter_rota(cidade_origem, cidade_destino):
    url = f'https://api.openrouteservice.org/v2/directions/driving-car?api_key={ors_key}&start={cidade_origem["lng"]},{cidade_origem["lat"]}&end={cidade_destino["lng"]},{cidade_destino["lat"]}'
    
    try:
        resposta = requests.get(url)
        resposta.raise_for_status()
        rota_data = resposta.json()
        print(f"Resposta da API de Rota: {resposta}")  # Adicione um print para verificar a resposta
        if rota_data.get('features'):
           return rota_data['features'][0]['geometry']['coordinates']
        else:
            print("Erro: Nenhuma feature encontrada na resposta da API de rota.")
            return None
    except requests.exceptions.HTTPError as http_err:
        print(f"Erro HTTP ao obter rota: {http_err}")
        return None
    except Exception as err:
        print(f"Erro ao obter rota: {err}")
        return None

@app.route('/', methods=['GET', 'POST'])
def index_get():
    if request.method == 'POST':
        origem = padronizar_nome_cidade(request.form.get('origem'))
        destino = padronizar_nome_cidade(request.form.get('destino'))
        
        # Deleta a rota anterior, se existir
        City.query.delete()
        db.session.commit()
        rota = City(origem=origem, destino=destino)
        db.session.add(rota)
        db.session.commit()
        flash('Rota adicionada com sucesso!', 'success')
        return redirect(url_for('index_get'))

    cidades = City.query.all()
    dados_previsao = []
    mapas = []
    
    for cidade in cidades:
        resposta_origem = consultarCidade(cidade.origem)
        resposta_destino = consultarCidade(cidade.destino)
        print(resposta_origem, resposta_destino)
        
        chuva_origem = resposta_origem.get('rain', {}).get('1h', 0)
        chuva_destino = resposta_destino.get('rain', {}).get('1h', 0)
        neve_origem = resposta_origem.get('snow', {}).get('1h', 0)
        neve_destino = resposta_destino.get('snow', {}).get('1h', 0)
        precipitacao_origem = chuva_origem + neve_origem
        precipitacao_destino = chuva_destino + neve_destino
        print(f"Precipitação para origem{cidade.origem}: Chuva={chuva_origem}, Neve={neve_origem}, Total={precipitacao_origem}")  # Adiciona este print para verificar a precipitação
        print(f"Precipitação para origem{cidade.destino}: Chuva={chuva_destino}, Neve={neve_destino}, Total={precipitacao_destino}")
        
        temperatura_origem = {
            'cidade': cidade.origem,
            'temperatura': resposta_origem['main']['temp'],
            'descricao': resposta_origem['weather'][0]['description'],
            'precipitacao': precipitacao_origem
        }
        temperatura_destino = {
            'cidade': cidade.destino,
            'temperatura': resposta_destino['main']['temp'],
            'descricao': resposta_destino['weather'][0]['description'],
            'precipitacao': precipitacao_destino
        }
        dados_previsao.append(temperatura_origem)
        dados_previsao.append(temperatura_destino)
        
        coords_origem = obter_coordenadas_cidade(cidade.origem)
        coords_destino = obter_coordenadas_cidade(cidade.destino)

        # Obter coordenadas para o mapa (usando a primeira cidade fixa)
        if coords_origem and coords_destino:
            coordenadas_rota = obter_rota(coords_origem, coords_destino)

            if coordenadas_rota:
                mapa = {
                    'coords_origem': coords_origem,
                    'coords_destino': coords_destino,
                    'coordenadas_rota': coordenadas_rota,
                    'cidade_origem': cidade.origem,
                    'cidade_destino': cidade.destino,
                    'previsao_origem': resposta_origem,
                    'previsao_destino': resposta_destino
                }
                mapas.append(mapa)
                
    return render_template('previsao.html', dados_previsao=dados_previsao, mapas=mapas)

@app.route('/deleta_cidade/<cidade>', methods=['GET', 'POST'])
def deletar_cidade(cidade):
    cidade_a_deletar = City.query.filter_by(origem=cidade).first()
    if cidade_a_deletar:
        db.session.delete(cidade_a_deletar)
        db.session.commit()
        flash(f'Cidade {cidade} deletada com sucesso!', 'success')
    else:
        flash(f'Cidade {cidade} não encontrada.', 'error')
    return redirect(url_for('index_get'))

if __name__ == "__main__":
    app.run(debug=True)