import asyncio, math
import sys
from datetime import datetime
from ib_insync import *
from PyQt5.QtCore import QTimer, Qt
from PyQt5.QtWidgets import QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget, QLineEdit, QPushButton, QMenu, QAction, QComboBox
from PyQt5.QtGui import QColor, QBrush
import qdarktheme
from datetime import date
import finviz
from finvizfinance.group.overview import Overview
import webbrowser
import concurrent.futures
import functools
from concurrent.futures import ThreadPoolExecutor
import yfinance as yf
from bs4 import BeautifulSoup
import pytz, requests
from fractions import Fraction

# Conectarse a la API de TWS
ib = IB()
ib.connect('127.0.0.1', 7497, clientId=1)


class MarketDataWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_symbols = set()  # Símbolos actuales en la tabla

        # Aplicar el estilo QDarkStyle
        self.setStyleSheet(qdarktheme.setup_theme())

        # Crear una tabla para mostrar los datos del mercado
        self.table = QTableWidget()
        self.table.setColumnCount(21)
        self.table.setHorizontalHeaderLabels(['Symbol', 'Halted', 'Sector', 'Industry', 'Close', 'Open', 'Gap', 'Last Price', 'Change', 'Float', 'Volumen', 'Vol/Float', 'News', 'Offerings Past', 'Offerings Future', 'Splits Past', 'Splits Future', 'Halteds Past', 'Halteds Future', 'Patrones Past', 'Patrones Future'])

        # Campo de entrada de texto para introducir los símbolos de los contratos
        self.symbolInput = QLineEdit()
        self.symbolInput.returnPressed.connect(self.add_symbols)

        # Botón para agregar los símbolos introducidos por el usuario
        self.addButton = QPushButton("Agregar")
        self.addButton.clicked.connect(self.add_symbols)

        # Configurar la tabla y los controles en un widget contenedor
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.addWidget(self.symbolInput)
        layout.addWidget(self.addButton)
        layout.addWidget(self.table)

        # Configurar el widget contenedor como el contenido central de la ventana principal
        self.setCentralWidget(widget)

        # Definir un diccionario para almacenar los precios del mercado
        self.last_price = {}
        self.get_ticker = {}
        self.sector_data = {}  # Almacenar los datos del sector por símbolo
        # Leer los símbolos desde el archivo y agregarlos a la tabla
        with open('symbols.txt', 'r') as file:
            symbols = [line.strip().split(',')[0] for line in file]
            contracts = [Stock(symbol.strip().upper(), 'SMART', 'USD') for symbol in symbols]
            for contract in contracts:
                asyncio.ensure_future(self.update_market_data(contract))
                asyncio.ensure_future(self.get_sectorindustriafloat_finviz_data(contract.symbol))  # Asynchronously get Finviz data
                asyncio.ensure_future(self.check_news_updates())# Iniciar la verificación de noticias

        # Ejecutar el bucle de eventos de asyncio mediante QTimer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_event_loop)
        self.timer.start(0)

        # Asignar el evento de menú contextual a la tabla
        self.table.setContextMenuPolicy(3)  # 3 corresponde a Qt.CustomContextMenu
        self.table.customContextMenuRequested.connect(self.context_menu_event)

        self.update_count = 0

    # Agregar los símbolos introducidos por el usuario como contratos a monitorear
    def add_symbols(self):
        symbols = self.symbolInput.text().split(',')
        contracts = [Stock(symbol.strip().upper(), 'SMART', 'USD') for symbol in symbols]

        unique_contracts = [contract for contract in contracts if contract.symbol not in self.current_symbols]

        if not unique_contracts:
            self.symbolInput.clear()
            return

        with open('symbols.txt', 'a') as file:
            for contract in unique_contracts:
                symbol = contract.symbol
                current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                file.write(f"{symbol},{current_date}\n")
                self.current_symbols.add(symbol)  # Agregar el símbolo a los símbolos actuales

        with open('symbols_history.txt', 'a') as file:
            for contract in unique_contracts:
                symbol = contract.symbol
                current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                file.write(f"{symbol},{current_date}, agregado\n")
                self.current_symbols.add(symbol)  # Agregar el símbolo a los símbolos actuales

        for contract in unique_contracts:
            print("probando")
            asyncio.ensure_future(self.update_market_data(contract))
            asyncio.ensure_future(self.get_sectorindustriafloat_finviz_data(contract.symbol))
            asyncio.ensure_future(self.check_news_updates())# Iniciar la verificación de noticias

        self.symbolInput.clear()

    def find_row_by_symbol(self, symbol):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)  # Assuming symbol is in the first column
            if item and item.text() == symbol:
                return row
        return -1  # Symbol not found

    async def check_news_updates(self):
        while True:
            current_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            
            for symbol in self.current_symbols:
                print("check_news_updates")
                dropdown = self.get_news(symbol)
                row = self.find_row_by_symbol(symbol)
                current_news = self.table.cellWidget(row, 12)
                if dropdown.currentText() != current_news.currentText():
                    self.table.setCellWidget(row, 12, dropdown)
                    dropdown.setStyleSheet("background-color: darkYellow")
            await asyncio.sleep(10)  # Verificar las noticias cada 60 segundos




    async def get_sectorindustriafloat_finviz_data(self, symbol):
        overview = Overview()
        ### HOT SECTORS AND INDUSTRIES
        def fetch_hot_sectors():
            hot_sectors = overview.screener_view(group='Sector', order='Change')
            return hot_sectors
        def fetch_hot_industries():
            hot_industries = overview.screener_view(group='Industry', order='Change')
            return hot_industries
        # Utiliza asyncio.gather para ejecutar las llamadas en paralelo
        screener_table_sectors, screener_table_industries, infofinviz = await asyncio.gather(
            asyncio.get_event_loop().run_in_executor(None, fetch_hot_sectors),
            asyncio.get_event_loop().run_in_executor(None, fetch_hot_industries),
            asyncio.get_event_loop().run_in_executor(None, finviz.get_stock, symbol)
        )
        screener_table_sorted_sectors = screener_table_sectors.sort_values(by='\n\nChange', ascending=False)
        name_change_df_sectors = screener_table_sorted_sectors[["Name", "\n\nChange"]]


        # Obtener los valores de los índices en variables
        sectornames = name_change_df_sectors["Name"].values
        changes = name_change_df_sectors["\n\nChange"].values
        name_change_dict_sector = {}
        for n, (name, change) in enumerate(zip(sectornames, changes), start=1):
            name_change_dict_sector[name] = {'id': n, 'change': change}

        screener_table_sorted_industries = screener_table_industries.sort_values(by='\n\nChange', ascending=False)
        name_change_df_industries = screener_table_sorted_industries[["Name", "\n\nChange"]]

        # Obtener los valores de los índices en variables
        industriesnames = name_change_df_industries["Name"].values
        changes = name_change_df_industries["\n\nChange"].values
        name_change_dict_industry = {}
        for n, (name, change) in enumerate(zip(industriesnames, changes), start=1):
            name_change_dict_industry[name] = {'id': n, 'change': change}

        ### SECTORS AND INDUSTRIES DE CADA COMPAÑIA
        if infofinviz['Sector'] not in ['Communication Services', 'Technology', 'Consumer Cyclical', 'Financial',
                                        'Basic Materials', 'Energy', 'Industrials', 'Healthcare',
                                        'Consumer Defensive', 'Real Estate', 'Utilities']:
            symbol = infofinviz['Company']
            sector = infofinviz['Industry']
            industry = infofinviz['Country']
            shares_float = infofinviz['Shs Float']
        else:
            symbol = infofinviz['Company']
            sector = infofinviz['Sector']
            industry = infofinviz['Industry']
            shares_float = infofinviz['Shs Float']

        self.sector_data[symbol] = (sector, industry, shares_float, name_change_dict_sector, name_change_dict_industry)





    # Definir una función asincrónica para solicitar los datos del mercado y actualizar la tabla
    async def update_market_data(self, contract):
        # Solicitar los datos del mercado
        ticker = ib.reqMktData(contract)
        # Guarda toda la info en esta lista aquí porque si se hace en el bucle la ventana va mal
        self.get_ticker[contract.symbol] = ticker
        
        while True:
            if ticker.last != self.last_price.get(contract.symbol):
                self.last_price[contract.symbol] = ticker.last
                self.update_table()

            # Verificar si el símbolo aún está presente en el archivo "symbols.txt"
            with open('symbols.txt', 'r') as file:
                symbols = [line.strip().split(',')[0] for line in file]

            if contract.symbol not in symbols:
                self.remove_symbol_from_table(contract.symbol)  # Eliminar el símbolo de la tabla
                del self.last_price[contract.symbol]  # Eliminar el símbolo del diccionario last_price
                break  # Salir del bucle while

            await asyncio.sleep(0.01)


    def context_menu_event(self, pos):
        context_menu = QMenu(self)

        remove_action = QAction("Eliminar", self)
        remove_action.triggered.connect(self.remove_symbol)
        context_menu.addAction(remove_action)

        # Obtener la posición del ítem seleccionado
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            symbol_item = self.table.item(selected_indexes[0].row(), 0)
            symbol = symbol_item.text()

            # Puedes agregar más acciones al menú contextual aquí

            # Ejecutar el menú contextual en la posición especificada
            context_menu.exec_(self.table.viewport().mapToGlobal(pos))

    def remove_symbol_from_table(self, symbol):
        rows = self.table.rowCount()
        for row in range(rows):
            symbol_item = self.table.item(row, 0)
            if symbol_item and symbol_item.text() == symbol:
                self.table.removeRow(row)
                break

    def remove_symbol(self):
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            symbol_item = self.table.item(selected_indexes[0].row(), 0)
            symbol = symbol_item.text()

            with open('symbols.txt', 'r') as file:
                lines = file.readlines()

            updated_lines = []
            for line in lines:
                stored_symbol = line.strip().split(',')[0]
                if stored_symbol != symbol:
                    updated_lines.append(line)

            with open('symbols.txt', 'w') as file:
                file.writelines(updated_lines)

            if symbol in self.current_symbols:  # Verificar si el símbolo existe en el conjunto
                self.table.removeRow(selected_indexes[0].row())
                self.current_symbols.remove(symbol)  # Eliminar el símbolo de los símbolos actuales
                del self.last_price[symbol]  # Eliminar el símbolo del diccionario last_price
                self.update_table()  # Actualizar la tabla con los datos modificados
                self.remove_symbol_from_table(symbol)  # Eliminar el símbolo de la tabla

            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            with open('symbols_history.txt', 'a') as file:
                file.write(f"{symbol},{current_date}, eliminado\n")

    def get_news(self, symbol):
        dropdown = QComboBox()
        results = []
        print("Checkeando noticias")
        def process_yahoo_news():
            try:
                # Obtain news with yfinance
                ticker = yf.Ticker(symbol)
                news = ticker.news
                for n in news:
                    titulo = n['title']
                    hora = n['providerPublishTime']
                    link = n['link']
                    dt = datetime.fromtimestamp(hora)
                    ny_timezone = pytz.timezone('America/New_York')
                    ny_dt = dt.astimezone(ny_timezone)
                    ny_time_str = ny_dt.strftime('%d-%m-%Y %H:%M:%S')

                    results.append((ny_time_str, f"YH = {symbol} | {ny_time_str} de NY | {titulo}", link))

            except Exception as e:
                print(f"Error al obtener noticias de Yahoo Finance para {symbol}: {e}")

        def process_stock_titan_news():
            try:
                # Obtain news from stock_titan
                url = 'https://www.stocktitan.net/news/' + symbol + '/'
                response = requests.get(url)
                soup = BeautifulSoup(response.content, 'html.parser')
                articles = soup.find_all('article')
                for article in articles:
                    hora = article.find('div', class_='date').text
                    hora = datetime.strptime(hora, "%m/%d/%y %I:%M %p")
                    hora = hora.strftime("%d-%m-%Y %H:%M:%S")
                    titulo = article.find('div', {'class': 'title'}).text
                    enlace = article.find('div', {'class': 'title'}).find('a')['href']

                    results.append((hora, f"ST = {symbol} | {hora} de NY | {titulo}", enlace))

            except Exception as e:
                print(f"Error al obtener noticias de Stock Titan para {symbol}: {e}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_yahoo = executor.submit(process_yahoo_news)
            future_stock_titan = executor.submit(process_stock_titan_news)

            # Esperar a que se completen las tareas en paralelo
            concurrent.futures.wait([future_yahoo, future_stock_titan])

        # Sort the results by time
        results = sorted(results, key=lambda x: datetime.strptime(x[0], '%d-%m-%Y %H:%M:%S'), reverse=True)

        # Show the results in the dropdown menu
        for index, result in enumerate(results):  # Added index variable here
            dropdown.addItem(result[1])
            dropdown.setItemData(index, result[2], Qt.UserRole)  # Added index variable here

        # Set colors if it has YH or ST
        for index, result in enumerate(results):
            news_date = datetime.strptime(result[0], '%d-%m-%Y %H:%M:%S').date()
            
            if news_date == date.today():
                # Aplicar estilo si la fecha es hoy
                dropdown.setStyleSheet("background-color: darkBlue")
            if 'YH' in result[1]:
                dropdown.setItemData(index, QBrush(QColor('#470463')), Qt.BackgroundRole)
                dropdown.setItemData(index, QBrush(QColor('white')), Qt.ForegroundRole)
            elif 'ST' in result[1]:
                dropdown.setItemData(index, QBrush(QColor('#020a40')), Qt.BackgroundRole)
                dropdown.setItemData(index, QBrush(QColor('white')), Qt.ForegroundRole)

        dropdown.activated.connect(self.open_news_link)

        return dropdown

    def get_splits(self, symbol):
        print('HACIENDO SPLITS')
        dropdown_splits = QComboBox()
        results_splits = []

        def process_splits():
            try:
                ticker = yf.Ticker(symbol)
                splits = ticker.splits

                for split_date, split_ratio in splits.items():
                    split_date_str = split_date.strftime("%d-%m-%Y")

                    if split_ratio > 1:
                        split_type = "Split"
                        precio_anterior = 5
                        new_price = precio_anterior / split_ratio
                        split_info = f"{symbol} - {split_date_str} - SPLIT (más acciones, menor precio) de {split_ratio} a 1. Si el precio anterior era de {precio_anterior}, ahora será de {new_price}. Dividir precio entre {split_ratio}"
                        #print(symbol, split_date_str, split_info)
                    else:
                        split_type = "Reverse split"
                        split_ratio = Fraction(1 / split_ratio).limit_denominator(1000)
                        precio_anterior = 5
                        new_price = precio_anterior * split_ratio
                        split_info = f"{symbol} - {split_date_str} - REVERSE SPLIT (menos acciones, mayor precio) de 1 a {split_ratio}. Si el precio anterior era de {precio_anterior}, ahora será de {new_price}. Multiplicar precio por {split_ratio}"
                        #print(symbol, split_date_str, split_info)
                    results_splits.append((symbol, "-", split_date_str, "-", split_type, split_info))

            except Exception as e:
                print(f"Error al obtener splits de Yahoo Finance para {symbol}: {e}")

        with concurrent.futures.ThreadPoolExecutor() as executor:
            future_splits = executor.submit(process_splits)
            # Esperar a que se completen las tareas en paralelo
            concurrent.futures.wait([future_splits])
        # Sort the results by time
        results_splits = sorted(results_splits, key=lambda x: datetime.strptime(x[2], '%d-%m-%Y'), reverse=True)
        # Show the results in the splits dropdown menu
        for index, result in enumerate(results_splits):
            dropdown_splits.addItem(result[5])  # Agregar result[5] en lugar de result[1]
            dropdown_splits.setItemData(index, result[5], Qt.UserRole)  # Usar result[5] en lugar de result[2]

        return dropdown_splits

    # Actualizar la tabla con los datos del mercado
    def update_table(self):
        self.table.setRowCount(len(self.last_price))
        row = 0
        for symbol, ticker in self.last_price.items():
            ticker = self.get_ticker.get(symbol)
            item_symbol = QTableWidgetItem(symbol)
            item_symbol.setTextAlignment(0x0084)  # Alinear el texto en mayúsculas
            item_halted = QTableWidgetItem(str(ticker.halted))
            if ticker.halted == 2.0 or ticker.halted == 1.0:
                item_halted.setBackground(Qt.darkRed)

            sector, industry, shares_float, name_change_dict_sector, name_change_dict_industry = self.sector_data.get(symbol, ("", "", "", {}, {}))
            changes_sectors = name_change_dict_sector.get(sector, {}).get('change', "")
            changes_industries = name_change_dict_industry.get(industry, {}).get('change', "")

            if changes_sectors:
                changes_sectors = f"{float(changes_sectors) * 100:.2f}%"
            item_sector = QTableWidgetItem(f"{name_change_dict_sector.get(sector, {}).get('id', '')} - {sector} ({changes_sectors})")
            if changes_sectors:
                changes_sectors = float(changes_sectors.strip("%"))
                if changes_sectors > 0:
                    item_sector.setBackground(Qt.darkYellow)  # Dark green


            
            if changes_industries:
                changes_industries = f"{float(changes_industries) * 100:.2f}%"
            item_industry = QTableWidgetItem(f"{name_change_dict_industry.get(industry, {}).get('id', '')} - {industry} ({changes_industries})")
            if changes_industries:
                changes_industries = float(changes_industries.strip("%"))
                if changes_industries > 0:
                    item_industry.setBackground(Qt.darkYellow)  # Dark green




            item_last_price = QTableWidgetItem(str(ticker.last))
            item_close = QTableWidgetItem(str(ticker.close))
            item_open = QTableWidgetItem(str(ticker.open))
            gap = (ticker.open - ticker.close) / ticker.close * 100
            item_gap = QTableWidgetItem(f"{gap:.2f}%")
            change = (ticker.last - ticker.close) / ticker.close * 100
            item_change = QTableWidgetItem(f"{change:.2f}%")

            item_float = QTableWidgetItem(str(shares_float))

            ## VOLUMEN
            # Convertir el volumen del día a una cadena formateada
            volume = ticker.volume * 100
            if volume >= 1_000_000:
                volume_str = f"{volume / 1_000_000:.2f}M"
            elif volume >= 1_000:
                volume_str = f"{volume / 1_000:.2f}k"
            else:
                volume_str = str(volume)

            item_volumenDelDia = QTableWidgetItem(volume_str)

            float_value = None  # Inicializar float_value
            if shares_float != '':
                value = float(shares_float[:-1])

                # Determinar el factor de conversión
                suffix = shares_float[-1]
                if suffix == 'M':
                    conversion_factor = 1000000  # Multiplicar por 1,000,000 para convertir de "M" a millones completos
                elif suffix == 'B':
                    conversion_factor = 1000000000  # Multiplicar por 1,000,000,000 para convertir de "B" a billones completos

                # Realizar la conversión
                float_value = value * conversion_factor

            # Obtener el volumen/float (%) y establecerlo en la columna 10
            item_volumenSobreFloat = QTableWidgetItem("")
            if float_value is not None and not math.isnan(float_value):
                item_volumenSobreFloat = QTableWidgetItem(f"{volume/float_value*100:.2f}%")



   
            self.table.setItem(row, 0, item_symbol)
            self.table.setItem(row, 1, item_halted)
            self.table.setItem(row, 2, item_sector)
            self.table.setItem(row, 3, item_industry)
            self.table.setItem(row, 4, item_close)
            self.table.setItem(row, 5, item_open)
            self.table.setItem(row, 6, item_gap)
            self.table.setItem(row, 7, item_last_price)
            self.table.setItem(row, 8, item_change)
            self.table.setItem(row, 9, item_float)
            self.table.setItem(row, 10, item_volumenDelDia)
            self.table.setItem(row, 11, item_volumenSobreFloat)

            # Verificar si ya se ha creado el widget de noticias para la fila actual
            if self.table.cellWidget(row, 12) is None:
                # Si el widget de noticias no existe, crearlo y establecerlo en la celda
                news_dropdown = self.get_news(symbol)
                self.table.setCellWidget(row, 12, news_dropdown)
            # Verificar si ya se ha creado el widget de noticias para la fila actual
            if self.table.cellWidget(row, 15) is None:
                # Si el widget de noticias no existe, crearlo y establecerlo en la celda
                splits_dropdown = self.get_splits(symbol)
                self.table.setCellWidget(row, 15, splits_dropdown)

            row += 1
        # Incrementar el contador en cada llamada a la función
        self.update_count += 1
        # Establecer el tamaño de las columnas para que se expandan
        if self.update_count == 100:
            print("\nAjustando columnas a texto")
            self.table.resizeColumnsToContents()

    def open_news_link(self, index):
        selected_item = self.sender()
        link = selected_item.itemData(index, Qt.UserRole)
        webbrowser.open(link)
    # Función para actualizar el bucle de eventos de asyncio
    def update_event_loop(self):
        asyncio.get_event_loop().stop()
        asyncio.get_event_loop().run_forever()

    def closeEvent(self, event):
        # Obtener las solicitudes de reqMktData pendientes
        pending_requests = ib.pendingTickers()

        # Mostrar las solicitudes pendientes
        for ticker in pending_requests:
            print("Símbolo:", ticker.contract.symbol)


        # Cancelar las solicitudes de reqMktData pendientes
        for ticker in pending_requests:
            ib.cancelMktData(ticker.contract)

        # Verificar que todas las solicitudes se hayan cancelado
        canceled_requests = ib.pendingTickers()
        if not canceled_requests:
            print("Todas las solicitudes de reqMktData se han cancelado correctamente")
        else:
            print("\n", canceled_requests)
            print("\nNo se pudieron cancelar todas las solicitudes de reqMktData")

        # Desconectar de Interactive Brokers
        ib.disconnect()
        # Llamar al método closeEvent de la clase base para realizar el cierre de la ventana
        super().closeEvent(event)

        print("Desconectado de IBKR")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    mainWindow = MarketDataWindow()
    mainWindow.resize(800, 800)
    mainWindow.show()
    sys.exit(app.exec_())