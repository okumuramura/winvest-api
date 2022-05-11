# Winvest API  
Winvest - investment portfolio manager with monitoring of the current value of assets and forecasting tools. Winvest is not a broker or a tool to work with the market, it is designed to help you monitor your assets and train in market trading without financial risks.  
The winvest API supports several built-in prediction methods and a ready interface for adding new ones. The response that forms the prediction request combines an attempt to reduce the amount of information transferred and the versatility to add new prediction methods.  
### Install requirements
```bash
pip install -r requirements.txt
# or
pip install poetry
poetry install
```

### Start server
```bash
uvicorn winvest.api.serve:app
# or
python -m winvest.api
```

### Docker
```bash
docker-compose up -d
```

### Methods and documentation
- `[GET] /stocks?[offset, limit]` - List of stocks with current prices.
- `[GET] /stocks/{id}` - Info about stock with id = `{id}`.
- `[GET] /history/stocks/{id}` - History data.
- `[POST] /register` - Registration method. Recive json body with login and password fields. Return status code 201 if registration succsess.
- `[POST] /login` - Recive json body with login and password field. Return json with token field if login succsess. This token must be placed in the Autorization header in all other requests where authorization confirmation is required.  
- `[GET] /portfolio` - Recive token from Authorization header. Return list of user-owned stocks or error 401 if authorization failed.
- `[POST] /portfolio/add/{id}` - Recive token from Authorization header. Adding stock with id = `{id}` to user's portfolio.
- `[DELETE] /portfolio/{id}` - Recive token from Authorization header. Removing stock with id = `{id}` from user's portfolio.
- `[GET] /predict/{id}` - Return predictions about stock with id = `{id}` (see Prediction format block).
- `[GET] /operations?[offset, limit]` - Get user's operations (like add, remove stocks)
- `[GET] /docs` - Documentation

### Prediction response format
`GET http://127.0.0.1:8000/predict/{stock_id}`
```json
{
    "methods": [
        {
            "name": "method_name",
            "type": "lin/quad/log/dots",
            "data": [
                0.1,
                0.2,
                0.3,
                ...
            ],
            "error": 0.5
        },
        ...
    ]
}
```

#### Method types  
Method type can be one of the listed values:
 - `lin`
 - `quad`
 - `log`
 - `dots`  

`lin`, `quad` and `log` are default methods and response with this types return only required parametrs for calculating and building a plot after that.  
if type is `dots` data contains final values and can be drawed on plot in this form.
### Stock info example
`GET http://127.0.0.1:8000/stocks/2`
```json
{
    "id": 2,
    "fullname": "Yandex",
    "shortname": "YNDX",
    "currency": "eur",
    "price": 1690.0,
    "change": 0.12,
    "history": [],
    "volume_of_deals": 299389759.0,
    "owned": false,
    "quantity": 0,
    "profit": 0.0
}
```
### User operations example
`GET http://127.0.0.1:8000/operations`
```json
{
    "operations": [
        {
            "id": 1,
            "type": "REGISTER",
            "user": {
                "id": 1,
                "login": "okumuramura",
                "registered": "2022-05-10T21:49:02.203956"
            },
            "subject": null,
            "args": null
        },
        {
            "id": 2,
            "type": "SIGN_IN",
            "user": {
                "id": 1,
                "login": "okumuramura",
                "registered": "2022-05-10T21:49:02.203956"
            },
            "subject": null,
            "args": "{'token': '...'}"
        },
        {
            "id": 3,
            "type": "ADD",
            "user": {
                "id": 1,
                "login": "okumuramura",
                "registered": "2022-05-10T21:49:02.203956"
            },
            "subject": {
                "id": 1,
                "shortname": "SBER"
            },
            "args": "{'quantity': 12, 'by_price': 123.34}"
        },
        {
            "id": 4,
            "type": "REMOVE",
            "user": {
                "id": 1,
                "login": "okumuramura",
                "registered": "2022-05-10T21:49:02.203956"
            },
            "subject": {
                "id": 1,
                "shortname": "SBER"
            },
            "args": null
        }
    ],
    "total": 4,
    "offset": 0
}
```

### GUI
### Additional requirements
```
pip install PyQt5
```
### Start GUI
```
python -m winvest.gui
```
> API server must be running for correct operation!
### Alternative GUI
- Web interface via React JS: https://github.com/kulisk/winvest-frontend