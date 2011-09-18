import gametime
import sqlite3

def get_generic(new_object, row, include_extras=False):
    if row:
        for index, value in enumerate(row):
            key = row.keys()[index]
            if include_extras or key in new_object.__dict__:
                new_object.__dict__[key] = value
    return new_object

def delete(id_value, id_column, filename, table_name):
    query = "DELETE FROM [{0}] WHERE [{1}] = ?".format(table_name, id_column)
    db_execute(filename, query, [id_value])

def insert_or_update_generic(object, filename, table_name, provider=None):
    query = "SELECT [{0}] FROM [{1}] WHERE [{0}] = ?".format("id" if not provider else provider.id_column, table_name)
    if db_fetch_one(filename, query, [object.id if not provider else provider.get_id(object)]):
        update_generic(object, filename, table_name, provider)
    else:
        insert_generic(object, filename, table_name, provider, False)
    
def insert_generic(object, filename, table_name, provider=None, replace_into=False):
    keys = []
    values = []
    columns_str = None
    values_str = None
    for key, value in vars(object).items():
        if value and (provider is None or not key in provider.ignore_list):
            keys.append(key)
            values.append(value)
            if columns_str:
                columns_str = "{0},[{1}]".format(columns_str, key)
            else:
                columns_str = "[{0}]".format(key)
            if values_str:
                values_str = values_str + ",?"
            else:
                values_str = "?"
    query = "INSERT{0} INTO [{1}] ({2}) VALUES ({3})".format(" OR REPLACE" if replace_into else "", table_name, columns_str, values_str)
    return db_execute(filename, query, values)
    
def update_generic(object, filename, table_name, provider=None):
    id_value = object.id if not provider else provider.get_id(object)
    id_column = "id" if not provider else provider.id_column
    keys = []
    values = []
    set_str = None
    for key, value in vars(object).items():
        if value and (provider is None or not key in provider.ignore_list):
            keys.append(key)
            values.append(value)
            if set_str:
                set_str = "{0},[{1}]=?".format(set_str, key)
            else:
                set_str = "[{0}]=?".format(key)
    query = "UPDATE [{0}] SET {1} WHERE [{2}]=?".format(table_name, set_str, id_column)
    values.append(id_value)
    db_execute(filename, query, values)

def db_fetch_one(filename, query, values=[]):
    conn = sqlite3.connect(filename)
    conn.row_factory = sqlite3.Row
    return conn.execute(query, values).fetchone()

def db_fetch_all(filename, query, values=[]):
    conn = sqlite3.connect(filename)
    conn.row_factory = sqlite3.Row
    return conn.execute(query, values).fetchall()
    
def db_execute(filename, query, values=[]):
    last_id = None
    conn = sqlite3.connect(filename)
    cursor = conn.cursor()
    try:
        cursor.execute(query, values)
    except:
        print 'Error executing on database:'
        print '"{0}"'.format(query)
        print values
    finally:
        last_id = cursor.lastrowid
        conn.commit()
        cursor.close()
    return last_id
        