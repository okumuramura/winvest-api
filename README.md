# Winvest API
## Install requirements
```
pip install -r requirements.txt
```
## Start server
```
uvicorn serve:app
```
## Methods and documentation
- `[GET] /stocks` - List of stocks with current prices.
- `[GET] /stocks/{id}?h=0` - Info about stock with id = `{id}`.  
    - with key h = 1 can return history info too. [default: 0]
- `[GET] /history/stocks/{id}` - History data.
- `[POST] /register` - Registration method. Recive json body with login and password fields. Return status code 200 if registration succsess.
- `[POST] /login` - Recive json body with login and password field. Return json with token field if login succsess.
- `[GET] /portfolio` - Recive token from Authorization header. Return list of user-owned stocks or error 401 if authorization failed.
- `[POST] /stocks/add/{id}` - Recive token from Authorization header. Add stock with id = `{id}` to user portfolio.
- `[GET] /predict/{id}` - ...
- `[GET] /docs` - Documentation