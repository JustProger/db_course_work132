import psycopg2
from psycopg2 import Error
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from faker import Faker
from faker.providers import DynamicProvider

import time
import os.path
from config import user, password, host, port, database
import queries_and_views
import fk_tables_filling

start_time = time.time()
connection = None


def db_create(cursor):
    with open('bd_create_script.sql', 'r') as f:
        cursor.execute(f.read())


def create_provider_and_upload_data(provider_name: str, path: str, cursor, fake):
    '''
        provider_name - название нового провайдера faker
        path - путь до файла .txt с данными для добавления в таблицу (название файла - название соответствующей таблицы)
        cur - объект типа psycopg2.cursor (для выполнения SQL команд на бд)
    '''

    # массив для хранения строк файла
    # path - путь до файла .txt
    table_name = os.path.basename(os.path.splitext(path)[0])
    temp = []

    if (table_name == 'ensembles'):
        with open(path, 'r') as f:
            while (tstr := f.readline()):
                processed_tstr = '. '.join((tstr.split('\n')[0].split('. '))[1:])
                cursor.execute('''SELECT type_of_ensemble_id FROM types_of_ensemble WHERE name = %s LIMIT 1;''', (fake.type_of_ensemble(),))
                random_type_of_ensemble_id = int(cursor.fetchone()[0])
                cursor.execute('''INSERT INTO ensembles (name, type_of_ensemble) VALUES (%s, %s);
                            ''', (processed_tstr, random_type_of_ensemble_id))
                temp.append(processed_tstr)

    elif (table_name == 'musical_works'):
        with open(path, 'r') as f:
            while (tstr := f.readline()):
                processed_tstr = '. '.join((tstr.split('\n')[0].split('. '))[1:])
                cursor.execute('''SELECT musician_id FROM musicians WHERE name = %s LIMIT 1;''', (fake.musician(),))
                random_musician_id = int(cursor.fetchone()[0])
                cursor.execute('''INSERT INTO musical_works (name, author) VALUES (%s, %s);
                            ''', (processed_tstr, random_musician_id))
                temp.append(processed_tstr)

    else:
        with open(path, 'r') as f:
            while (tstr := f.readline()):
                processed_tstr = '. '.join((tstr.split('\n')[0].split('. '))[1:])
                cursor.execute(sql.SQL('''INSERT INTO {table} (name) VALUES (%s);
                            ''').format(table=sql.Identifier(table_name)), (processed_tstr,))
                temp.append(processed_tstr)

    return DynamicProvider(provider_name=provider_name, elements=temp)


def main():
    try:
        # Подключение к существующей базе данных
        connection = psycopg2.connect(
            user=user,
            # пароль, который указали при установке PostgreSQL
            password=password,
            host=host,
            port=port,
            database=database)

        connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Курсор для выполнения операций с базой данных
        with connection.cursor() as cursor:

            # Создаём таблицы БД по заранее составленному SQL скрипту
            db_create(cursor)

            # Непосредственное заполнение БД
            # Загрузка данных в некоторые таблицы бд и создание провайдеров для работы модуля faker
            fake = Faker()
            fake.add_provider(create_provider_and_upload_data('album', 'data/albums.txt', cursor, fake))
            fake.add_provider(create_provider_and_upload_data('type_of_ensemble', 'data/types_of_ensemble.txt', cursor, fake))
            fake.add_provider(create_provider_and_upload_data('musical_instrument', 'data/musical_instruments.txt', cursor, fake))
            fake.add_provider(create_provider_and_upload_data('musician', 'data/musicians.txt', cursor, fake))
            fake.add_provider(create_provider_and_upload_data('role', 'data/roles.txt', cursor, fake))
            # Эти провайдеры при создании используют некоторые провайдеры выше (нужно, чтобы он уже были созданы, поэтому провайдеры musical_work и ensemble создаём в последнюю очередь)
            fake.add_provider(create_provider_and_upload_data('musical_work', 'data/musical_works.txt', cursor, fake))
            fake.add_provider(create_provider_and_upload_data('ensemble', 'data/ensembles.txt', cursor, fake))
            # Заполнение оставшихся 3х таблиц: musicians_and_ensembles, Recordings, Instruments_of_the_performer_of_a_musical_work
            # Добавляем 15 рандомно сгенерированных записей в таблицу musicians_and_ensembles
            fk_tables_filling.fill_in_musicians_and_ensembles(15, cursor, fake)
            # Добавляем 1500 рандомно сгенерированных записей в таблицу musicians_and_ensembles
            fk_tables_filling.fill_in_recordings(1500, cursor, fake)
            # Добавляем 15 рандомно сгенерированных записей в таблицу instruments_of_the_performer_of_a_musical_work
            fk_tables_filling.fill_in_musicians_and_ensembles(15, cursor, fake)

            # Выполнить сложные запросы
            queries_and_views.main(cursor)
            # Выполнить сложные отчёты: views (представления)

    except (Exception, Error) as error:
        print("Ошибка при работе с PostgreSQL", error)
    finally:
        if connection:
            connection.close()
            print("-------------------------------")
            print("Соединение с PostgreSQL закрыто")

    print("--- %s seconds ---" % (time.time() - start_time))


main()