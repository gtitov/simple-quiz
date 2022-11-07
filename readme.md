Для установки зависимостей в командной строке (PowerShell) выполнить

```PowerShell
pip install -r requirements.txt
```


В командной строке выполнить

```PowerShell
python -m uvicorn main:app --host=0.0.0.0
```


Интерфейс будет доступен по адресу работы uvicorn

```PowerShell
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)  # здесь фиксируем порт — это число после двоеточия
```


Для работы в локальной сети узнать адрес компьютера в локальной сети с помощью PowerShell

```PowerShell
Get-NetIPAddress
# (Get-NetIPAddress | Where-Object {$_.AddressState -eq "Preferred" -and $_.ValidLifetime -lt "24:00:00"}).IPAddress # не тестировал

IPAddress         : 123.32.43.54
InterfaceIndex    : 27
InterfaceAlias    : Подключение по локальной сети* 1
AddressFamily     : IPv4
Type              : Unicast
PrefixLength      : 16
PrefixOrigin      : WellKnown
SuffixOrigin      : Link
AddressState      : Tentative
ValidLifetime     : Infinite ([TimeSpan]::MaxValue)
PreferredLifetime : Infinite ([TimeSpan]::MaxValue)
SkipAsSource      : False
PolicyStore       : ActiveStore
```


В файле `gui/main.js` заменить все `localhost` на полученный ip-адрес, например, `123.32.43.54`, чтобы все запросы выполнялись к головному компьютеру

Для доступа к тесту с компьютера в локальной сети перейти по URL такого вида `ip-адрес:порт`, например, `123.32.43.54:8000`