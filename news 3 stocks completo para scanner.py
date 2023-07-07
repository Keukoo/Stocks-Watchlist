import threading
from bs4 import BeautifulSoup
from datetime import datetime
import yfinance as yf
import datetime, pytz, requests
from PyQt5.QtWidgets import QApplication, QWidget, QVBoxLayout, QComboBox
import threading, time
import webbrowser
from PyQt5.QtCore import QTimer, Qt


# Conjunto para almacenar los títulos de noticias existentes
existing_news = set()

# Función para obtener las noticias de un símbolo en particular
def get_news(symbol, combo_box):

    results = []

    try:
        # Tratar de obtener las noticias con yfinance
        ticker = yf.Ticker(symbol)
        news = ticker.news
        for n in news:
            titulo = n['title']
            hora = n['providerPublishTime']
            link = n['link']
            dt = datetime.datetime.fromtimestamp(hora)
            ny_timezone = pytz.timezone('America/New_York')
            ny_dt = dt.astimezone(ny_timezone)
            ny_time_str = ny_dt.strftime('%d-%m-%Y %H:%M:%S')

            # Verificar si el título de la noticia ya existe en el conjunto de noticias existentes
            if titulo not in existing_news:
                print(ny_time_str, titulo)
                # Agregar la nueva noticia a la lista desplegable y al conjunto de noticias existentes
                existing_news.add(titulo)
                results.append((ny_time_str, f"YH = {symbol} | {ny_time_str} de NY | {titulo}", link))

        # Ahora con stock_titan
        url = 'https://www.stocktitan.net/news/' + symbol + '/'
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')
        articles = soup.find_all('article')
        for article in articles:
            hora = article.find('div', class_='date').text
            hora = datetime.datetime.strptime(hora, "%m/%d/%y %I:%M %p")
            hora = hora.strftime("%d-%m-%Y %H:%M:%S")
            titulo = article.find('div', {'class': 'title'}).text
            enlace = article.find('div', {'class': 'title'}).find('a')['href']

            # Verificar si el título de la noticia ya existe en el conjunto de noticias existentes
            if titulo not in existing_news:
                # Agregar la nueva noticia a la lista desplegable y al conjunto de noticias existentes
                existing_news.add(titulo)
                results.append((hora, f"ST = {symbol} | {hora} de NY | {titulo}", enlace))

        # Ordenar los resultados por hora
        results = sorted(results, key=lambda x: datetime.datetime.strptime(x[0], '%d-%m-%Y %H:%M:%S'), reverse=True)

        # Agregar los resultados al ComboBox
        for result in results:
            combo_box.addItem(result[1])
        combo_box.activated.connect(open_news_link)
    except IndexError:
        print(f"{symbol} no se encuentra en stock titan ni en yahoo")

# Función que se ejecutará en segundo plano para actualizar las noticias en intervalos regulares
def update_news_loop(symbols, combo_box):
    while True:
        for symbol in symbols:
            get_news(symbol, combo_box)

        # Permitir que la interfaz gráfica se actualice
        QApplication.processEvents()

        # Intervalo de tiempo para actualizar las noticias (en segundos)
        time.sleep(1)

def open_news_link(index):
    selected_item = combo_box.itemData(index, Qt.UserRole)
    link = selected_item
    webbrowser.open(link)


# Obtener los símbolos de alguna manera
symbols = ['AAPL', 'GOOGL', 'MSFT']

# Crear una aplicación de PyQt
app = QApplication([])
widget = QWidget()

# Crear un layout vertical
layout = QVBoxLayout(widget)

# Crear un ComboBox
combo_box = QComboBox()

# Agregar el ComboBox al layout
layout.addWidget(combo_box)

# Mostrar la ventana
widget.show()

# Iniciar el hilo para actualizar las noticias
thread = threading.Thread(target=update_news_loop, args=(symbols, combo_box))
thread.start()

# Ejecutar la aplicación de PyQt
app.exec_()
