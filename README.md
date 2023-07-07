Remember that you need to install TWS in order to run watchlist.py. https://www.interactivebrokers.com/en/trading/tws.php. You don't need to create an account when you download it, there's an option: 'Try demo'. When you click on it you just need to write some random email to log in. Then to set up the API you have to go to File -> Global Configuration -> API -> Settings -> Enable ActiveX and Socket clients and also uncheck Read-Only API.

Updated 07-07-2023

watchlist.py -> main and final code

news.py -> approach to get news every second and updating the GUI only when we get a new one

splits.py -> initial approach for the watchlist project. Here we can use the method for retrieving data for Sector, Industry, News, and Splits past. However, these data sources do not update every second in this implementation, and they cause the GUI to become unresponsive. So this file won't be the final one.


Watchlist:

DONE (seems to work fine):

-Read symbols from symbols.txt and add them to the GUI (check ERRORS)

-Manually add symbols from line edit to the file and GUI.

-Delete symbol and row from GUI and file (check ERRORS)

-Writes a symbols_history.txt file that records the symbols added and deleted along with the date.

-Obtain real-time data from Interactive Brokers in columns: Symbol, Halted, Close, Open, Gap (open-closex100), Last, Change(last-closex100), Volume. This data is being updated properly in real time.

-Get Sector, Industry and Float for each symbol from finviz library. Then calculate Volume/Float (volume/floatx100), from Interactive/Finviz data sources.

What it shows right now:
![image](https://github.com/Keukoo/Stocks-Watchlist/assets/138369317/468ac89e-d80d-4520-b798-579a27c77cea)



TO DO:

-I need all of the data from the columns 'News', 'Sector', 'Industry', 'Splits Past', to be checking for new info every second, but only upload the pyqt table when there is new info or different info.

-News column, data source: yfinance and stocktitan.net. News should appear in a dropdown list for each symbol, sorted from most recent to oldest, along with the data source, date and headline, as shown in the screenshot below. Additionally, clicking on a headline from the dropdown should redirect to the corresponding Yahoo Finance or Stock Titan link (refer to splits.py -> get_news for an example). If a headline corresponds to the current day, change the cell color to blue, similar to the behavior in splits.py (refer to the screenshot below).

-"Sector" and "Industry" columns, data source: finviz module, I need to display not only the sector and industry for each symbol but also the daily growth ranking number and the growth percentage of the sector and industry, as shown in the screenshot. For example, "5- Healthcare (-1.04%)" would mean that after checking with finviz for the sectors and industries with the highest percentage growth today, the Healthcare sector is in the top 5 but has lost 1.04% today. (check splits.py -> get_splits for an example, but they do not upload every second). If the sector or industry has a positive % then change the cell color to darkgold like in splits.py (check screenshot below)
![image](https://github.com/Keukoo/Stocks-Watchlist/assets/138369317/a20c2e55-ebcc-45a0-bea6-4a3cb5c3424a)

-"Splits Past" column, data source: yfinance. I want the data to appear as shown in this screenshot (check funcion get_splits from splits.py):
![image](https://github.com/Keukoo/Stocks-Watchlist/assets/138369317/e9f646a0-503c-4326-958c-f10a1274ba92)


-Implement the ability to delete symbols with a right-click option, in addition to the existing option of using the Delete key.

ERRORS:

-When deleting a row using the Delete key, the data for each symbol gets mixed up or it gets frozen, probably data is not attached correctly to each symbol.

-When loading symbols, some get this Error 200, reqId 23: The contract description specified for CRBU is ambiguous., contract: Stock(symbol='CRBU', exchange='SMART', currency='USD'). Maybe try this https://stackoverflow.com/questions/27495333/ibrokers-reqmktdata-results-in-error-saying-ticker-is-ambiguous -> Catch the ambiguous error in your handler and resend again by trying all the primaryExchanges one by one (NYSE, NASDAQ, BATS, ARCA etc).

