copy this files to paste to new directly.
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
open -> http://127.0.0.1:8000/

Note:
    frontend -> html,css,javascript
    backend -> python(fastapi)
    database -> Mysql(sqlalchemy)
