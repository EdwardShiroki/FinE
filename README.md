# Итоговый проект - поиск ивентов



### Инструкция по настройке проекта:
1. Склонировать проект
2. Открыть проект в PyCharm с наcтройками по умолчанию
3. Создать виртуальное окружение (через settings -> project "simple votings" -> project interpreter)
4. Открыть терминал в PyCharm, проверить, что виртуальное окружение активировано.
5. Обновить pip:
   ```bash
   pip install --upgrade pip
   ```
6. Установить в виртуальное окружение необходимые пакеты: 
   ```bash
   pip install -r requirements.txt
   ```

7. Создать уникальный ключ приложения.  
   Генерация делается в консоли Python при помощи команд:
   ```bash
   python manage.py shell -c "from django.core.management.utils import get_random_secret_key; get_random_secret_key()"
   ```
   Далее полученное значение подставляется в соответствующую переменную.
   Внимание! Без выполнения этого пункта никакие команды далее не запустятся.

8. Синхронизировать структуру базы данных с моделями: 
   ```bash
   python manage.py migrate
   ```

9. Создать конфигурацию запуска в PyCharm (файл `manage.py`, опция `runserver`)

Внимание! Создана отдельная модель пользователя в модуле `fine`! 
При создании ForeignKey'ев на User'а - использовать её при помощи встроенной функции `get_user_model`. 

* Создать документацию *(Windows)*:
   ```bash
   .\docs\make html
   ```
* Создать документацию *(Linux <- это кстати не точно)*:
   ```bash
   \docs\make html
   ```

* Создать суперпользователя:
   ```bash
   python manage.py shell -c "from django.contrib.auth import get_user_model; get_user_model().objects.create_superuser('vasya', '1@abc.net', 'promprog')"
   ```
  
* Накатить миграции: 
   ```bash
   python manage.py makemigrations
   ```
  
* Накатить миграции: 
   ```bash
   python manage.py migrate
   ```

* Запустить тесты джанги:
   ```bash
   python manage.py test
   ```

### PostgreSql moment(Ubuntu)

* Install postgresql-client:
   ```bash
   sudo apt install postgresql-client-14
   ```
* Install postgresql-client:
   ```bash
   sudo apt install postgresql
   ```
* Get postgresql version:
   ```bash
   sudo -u postgres psql -c "SELECT version();"
   ```
* Check postgres status
   ```bash
   pg_lsclusters
   ```
* Restart the pg_ctlcluster:
    > `pg_ctlcluster <version> <cluster> <action>`
   ```bash
   pg_ctlcluster 14 main start
   ```
* Restart the postgres server:
   ```bash
   sudo service postgresql restart
   ```
* Login in postgres:
   ```bash
   sudo -i -u postgres
   ```
   or
   ```bash
   su postgres
   ```
   ```bash
   psql
   ```
   or
   ```bash
   psql -U <dataBaseUserName> <dataBaseName>
   ```
* Create db:
   ```bash
   createdb mydb
   ```
* Delete db:
   ```bash
   dropdb mydb
   ```
* Create user to django:
   ```bash
   createuser admindb -P
   ```
    enter a password
* Docker pull postgres image:
   ```bash
   docker pull postgres:alpine
   ```
* Docker run command:
   ```bash
   docker run --name postgres-0 -e POSTGRES_PASSWORD=password -d postgres:alpine
   ```
* Open docker container:
   ```bash
   docker exec -it postgres-0 bash
   ```
* Login in psql:
   ```bash
   psql -U postgres
   ```


### Docker start guid

1. Download needed image
   ```bash
   docker pull python:3.10
   ```
2. Build your image
   ```bash
   docker build . --tag main
   ```
3. Run you image
   ```bash
   docker run -p 8000:8000 -d main
   ```
4. Stop you container
   ```bash
   docker stop CONTAINER_ID
   ```
5. Start you container
   ```bash
   docker start CONTAINER_ID
   ```
6. Logs of container
   ```bash
   docker logs CONTAINER_ID
   ```

### Tips and Tricks Docker

1. To show all images
    ```bash
       docker images
    ```
2. To show all containers
    ```bash
       docker ps
    ```
3. To show all containers (finished)
    ```bash
       docker ps -a
    ```
4. To delete image
    ```bash
       docker rmi IMAGE_ID(or image tag)
    ```
5. To delete container
    ```bash
       docker rm CONTAINER_ID
    ```
6. Log in container
    ```bash
       docker exec -it CONTAINER_ID
    ```

