import asyncio, math
import finviz
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
import PyQt5.QtWidgets as qt
# import PySide6.QtWidgets as qt
import qdarktheme
from ib_insync import IB, util
from ib_insync.contract import * 
from datetime import datetime
from finvizfinance.group.overview import Overview
import webbrowser



class TickerTable(qt.QTableWidget):

    headers = ['Symbol', 'Halted', 'Sector', 'Industry', 'Close', 'Open', 'Gap', 'Last', 'Change', 'Float', 'Volume', 'Vol/Float', 'News', 'Offerings Past', 'Offerings Future', 'Splits Past', 'Splits Future', 'Halteds Past', 'Halteds Future', 'Patrones Past', 'Patrones Future']
    headers_for_ticker = [header.lower() for header in headers]

    def __init__(self, parent=None):
        qt.QTableWidget.__init__(self, parent)
        self.setStyleSheet(qdarktheme.setup_theme())
        self.conId2Row = {}
        self.setColumnCount(len(self.headers))
        self.setHorizontalHeaderLabels(self.headers)
        self.setAlternatingRowColors(True)
        self.horizontalHeader().sectionClicked.connect(self.sortByColumn)

    def sortByColumn(self, column):
        self.sortItems(column, Qt.DescendingOrder)

    def deleteRow(self, row):
        if row < self.rowCount():
            item = self.item(row, 0)
            symbol = item.text()
            conId = None
            for key, value in self.conId2Row.items():
                if value == row:
                    conId = key
                    break
            if conId:
                del self.conId2Row[conId]
            self.removeRow(row)

            with open('symbols.txt', 'r') as file:
                lines = file.readlines()

            with open('symbols.txt', 'w') as file:
                for line in lines:
                    if not line.startswith(symbol + ','):
                        file.write(line)




    def __contains__(self, contract):
        assert contract.conId
        return contract.conId in self.conId2Row

    def addTicker(self, ticker):
        row = self.rowCount()
        self.insertRow(row)
        self.conId2Row[ticker.contract.conId] = row
        for col in range(len(self.headers)):
            item = qt.QTableWidgetItem('')
            self.setItem(row, col, item)
            item.setTextAlignment(Qt.AlignCenter)
        item = self.item(row, 0)
        item.setText(ticker.contract.symbol)
        self.resizeColumnsToContents()

    def clearTickers(self):
        self.setRowCount(0)
        self.conId2Row.clear()

    def onPendingTickers(self, tickers):
        headers_to_skip = {'sector', 'industry', 'float', 'vol/float', 'news', 'offerings past', 'offerings future', 'splits past', 'splits future', 'halteds past', 'halteds future', 'patrones past', 'patrones future'}
        
        for ticker in tickers:
            if ticker.contract.conId in self.conId2Row:
                row = self.conId2Row[ticker.contract.conId]
                if row < self.rowCount():
                    for col, header in enumerate(self.headers_for_ticker):
                        if col == 0:
                            continue
                        item = self.item(row, col)
                        if item:
                            if header == 'gap':
                                open_val = getattr(ticker, 'open')
                                close_val = getattr(ticker, 'close')
                                gap_val = (open_val - close_val) / close_val * 100
                                new_text = f"{gap_val:.2f}%"
                            elif header == 'change':
                                last_val = getattr(ticker, 'last')
                                close_val = getattr(ticker, 'close')
                                change_val = (last_val - close_val) / close_val * 100
                                new_text = f"{change_val:.2f}%"

                            elif header in headers_to_skip:
                                continue
                            else:
                                val = getattr(ticker, header)
                                if header == 'volume':
                                    val = val * 100
                                    if val >= 1_000_000:
                                        val = f"{val/1_000_000:.2f}M"
                                    elif val >= 1_000:
                                        val = f"{val/1_000:.2f}k"
                                new_text = str(val)

                            if new_text != item.text():  # Verificar si el nuevo valor es diferente
                                item.setText(new_text)
                            if header == 'halted' and (float(new_text) == 1 or float(new_text) == 2):
                                item.setBackground(Qt.darkRed)





class Window(qt.QWidget):

    def __init__(self, host, port, clientId):
        qt.QWidget.__init__(self)
        self.table = TickerTable()

        self.symbolLineEdit = qt.QLineEdit()
        self.addButton = qt.QPushButton("Agregar")

        layout = qt.QVBoxLayout(self)
        layout.addWidget(self.symbolLineEdit)
        layout.addWidget(self.addButton)
        layout.addWidget(self.table)

        self.table.cellDoubleClicked.connect(self.openWebpage)
        self.connectInfo = (host, port, clientId)
        self.ib = IB()
        self.ib.pendingTickersEvent += self.table.onPendingTickers

        self.addButton.clicked.connect(self.addSymbolFromLineEdit)
        self.symbolLineEdit.returnPressed.connect(self.addSymbolFromLineEdit)
        self.columnsResized = False
        self.overview = Overview()
        # Create QTimer instance
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_info)


    @pyqtSlot()
    def update_info(self):
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.update_stock_info())
        if not self.columnsResized:
            self.table.resizeColumnsToContents()
            self.columnsResized = True

    async def get_stock_info(self, ticker):
        try:
            infofinviz = await asyncio.get_event_loop().run_in_executor(None, finviz.get_stock, ticker)
            #print(infofinviz)
            if infofinviz['Sector'] not in ['Communication Services', 'Technology', 'Consumer Cyclical', 'Financial',
                                            'Basic Materials', 'Energy', 'Industrials', 'Healthcare',
                                            'Consumer Defensive', 'Real Estate', 'Utilities']:
                symbol = infofinviz['Company']
                sector = infofinviz['Industry']
                industry = infofinviz['Country']
                shares_float = infofinviz['Shs Float']
                return symbol, sector, industry, shares_float
            else:
                symbol = infofinviz['Company']
                sector = infofinviz['Sector']
                industry = infofinviz['Industry']
                shares_float = infofinviz['Shs Float']
                return symbol, sector, industry, shares_float
        except:
            return None  # Devuelve None si la empresa no se encuentra en Finviz

    async def update_stock_info(self):
        tickers = [self.table.item(row, 0).text() for row in range(self.table.rowCount())]
        tasks = [self.get_stock_info(ticker) for ticker in tickers]
        results = await asyncio.gather(*tasks)
        try:
            # Llenar la tabla con los resultados
            for row, result in enumerate(results):
                symbol, sector, industry, shares_float = result


                #print("SECTOR", sector, "SELF =", self.table.item(row, 8).text())
                self.table.setItem(row, 2, qt.QTableWidgetItem(sector))

                self.table.setItem(row, 3, qt.QTableWidgetItem(industry))

                self.table.setItem(row, 9, qt.QTableWidgetItem(shares_float))

                if shares_float != ''and shares_float != '-':
                    # Detecta el float con M o k
                    value = float(shares_float[:-1])

                    # Determinar el factor de conversión
                    suffix = shares_float[-1]
                    if suffix == 'M':
                        conversion_factor = 1000000  # Multiplicar por 1,000,000 para convertir de "M" a millones completos
                    elif suffix == 'B':
                        conversion_factor = 1000000000  # Multiplicar por 1,000,000,000 para convertir de "B" a billones completos
                    elif suffix == 'k':
                        conversion_factor = 1000  # Multiplicar por 100,000 para convertir de "k" a miles
                    # Realizar la conversión
                    float_value = value * conversion_factor
                    # Obtener el valor de la columna 10 y convertirlo a float
                    volume_val = self.table.item(row, 10).text()

                    if volume_val != '' and volume_val != 'na':
                        try:
                            value = float(volume_val[:-1])
                            # Determinar el factor de conversión
                            suffix = volume_val[-1]

                            if suffix == 'M':
                                conversion_factor = 1000000  # Multiplicar por 1,000,000 para convertir de "M" a millones completos
                            elif suffix == 'B':
                                conversion_factor = 1000000000  # Multiplicar por 1,000,000,000 para convertir de "B" a billones completos
                            elif suffix == 'k':
                                conversion_factor = 1000  # Multiplicar por 100,000 para convertir de "k" a miles
                            else:
                                conversion_factor = 1  # Si no llega a 1000 de volumen simplemente multiplica por 1
                            vol_val = value * conversion_factor
                            vol_val = vol_val / float_value * 100
                            new_text = f"{vol_val:.2f}%"
                            self.table.setItem(row, 11, qt.QTableWidgetItem(new_text))
                        except ValueError:
                            # Handle the case when the conversion fails
                            pass
        except:
            print("Error")

    def deleteSelectedRow(self):
        selected_indexes = self.table.selectedIndexes()
        if selected_indexes:
            selected_row = selected_indexes[0].row()
            self.table.deleteRow(selected_row)

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


            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            with open('symbols_history.txt', 'a') as file:
                file.write(f"{symbol},{current_date}, eliminado\n")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.remove_symbol()
            self.deleteSelectedRow()

    def addSymbolFromLineEdit(self):
        symbol = self.symbolLineEdit.text()
        if symbol:
            self.addSymbol(symbol)
        self.symbolLineEdit.clear()

    def addSymbol(self, symbol):
        contract = Stock(symbol, 'SMART', 'USD')
        if (contract and self.ib.qualifyContracts(contract)
                and contract not in self.table):
            ticker = self.ib.reqMktData(contract, '', False, False, None)
            self.table.addTicker(ticker)
        with open('symbols.txt', 'a') as file:
            symbol = contract.symbol
            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            file.write(f"{symbol},{current_date}\n")

        with open('symbols_history.txt', 'a') as file:
            symbol = contract.symbol
            current_date = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            file.write(f"{symbol},{current_date}, agregado\n")


    def add(self, contract):
        if (contract and self.ib.qualifyContracts(contract)
                and contract not in self.table):
            ticker = self.ib.reqMktData(contract, '', False, False, None)
            self.table.addTicker(ticker)


    def openWebpage(self, row, column):
        if column == 0:
            item = self.table.item(row, column)
            if item is not None:
                symbol = item.text()
                url = f"https://finviz.com/quote.ashx?t={symbol}"
                webbrowser.open(url)




    def onConnect(self):
        self.ib.connect(*self.connectInfo)
        if datetime.now().hour >= 10:
            print('Datos en tiempo real')
            self.ib.reqMarketDataType(3) #1 para datos en tiempo real, #2 para datos cuando el mercado esté cerrado
        else:
            print('Datos con delay porque el mercado está cerrado')
            self.ib.reqMarketDataType(3)
        with open('symbols.txt', 'r') as file:
            symbols = [line.strip().split(',')[0] for line in file]
        for symbol in symbols:
            self.add(Stock(symbol, 'SMART', 'USD'))
        self.timer.start(1000)  # Consigue cada 1 segundo sector, float e industria y si cambia lo muestra en la tabla


    def closeEvent(self, ev):
        loop = util.getLoop()
        loop.stop()


if __name__ == '__main__':
    util.patchAsyncio()
    util.useQt()
    # util.useQt('PySide6')
    window = Window('127.0.0.1', 7497, clientId=0)
    window.resize(900, 800)
    window.show()
    window.onConnect()
    IB.run()
