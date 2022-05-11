# Winvest API
## Install requirements
```bash
pip install -r requirements.txt
# or
pip install poetry
poetry install
```

## Start server
```bash
uvicorn winvest.api.serve:app
# or
python -m winvest.api
```

## Docker
```bash
docker-compose up -d
```

## Methods and documentation
- `[GET] /stocks` - List of stocks with current prices.
- `[GET] /stocks/{id}?h=0` - Info about stock with id = `{id}`.  
    - with key h = 1 can return history info too. [default: 0]
- `[GET] /history/stocks/{id}` - History data.
- `[POST] /register` - Registration method. Recive json body with login and password fields. Return status code 200 if registration succsess.
- `[POST] /login` - Recive json body with login and password field. Return json with token field if login succsess.
- `[GET] /portfolio` - Recive token from Authorization header. Return list of user-owned stocks or error 401 if authorization failed.
- `[POST] /stocks/add/{id}` - Recive token from Authorization header. Adding stock with id = `{id}` to user's portfolio.
- `[DELETE] /stocks/{id}` - Recive token from Authorization header. Removing stock with id = `{id}` from user's portfolio.
- `[GET] /predict/{id}` - Return predictions about stock with id = `{id}` (see Prediction format block).
- `[GET] /docs` - Documentation

## Prediction response format
Response on `/predict/{id}`
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

### Method types  
Method type can be one of the listed values:
 - `lin`
 - `quad`
 - `log`
 - `dots`  

`lin`, `quad` and `log` are default methods and response with this types return only required parametrs for calculating and building a plot after that.  
if type is `dots` data contains final values and can be drawed on plot in this form.

## GUI
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