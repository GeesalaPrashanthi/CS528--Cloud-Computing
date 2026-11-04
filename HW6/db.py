"""Connect through an existing local proxy, or the managed Cloud SQL connector."""
import os
import pymysql


def connect(database="default"):
    kwargs = dict(user=os.getenv('DB_USER','root'), password=os.environ['DB_PASSWORD'],
                  database=os.getenv('DB_NAME','cs528_hw6') if database=='default' else database)
    if os.getenv('INSTANCE_CONNECTION_NAME'):
        from google.cloud.sql.connector import Connector
        connector = Connector()
        try:
            connection = connector.connect(os.environ['INSTANCE_CONNECTION_NAME'], 'pymysql',
                                           **kwargs)
        except BaseException:
            connector.close()
            raise
        # Keep connector alive until connection closes.
        close = connection.close
        def close_all():
            try: close()
            finally: connector.close()
        connection.close = close_all
        return connection
    return pymysql.connect(host=os.getenv('DB_HOST','127.0.0.1'),
        port=int(os.getenv('DB_PORT','3307')), connect_timeout=30, read_timeout=120, **kwargs)
