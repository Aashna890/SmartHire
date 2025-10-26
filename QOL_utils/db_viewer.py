import sqlite3
from tabulate import tabulate

def list_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    return [row[0] for row in cursor.fetchall()]

def table_info(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({table});")
    return [(col[1], col[2]) for col in cursor.fetchall()]

def count_rows(conn, table):
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    return cursor.fetchone()[0]

def dump_table(conn, table, limit=5):
    cursor = conn.cursor()
    cursor.execute(f"SELECT * FROM {table} LIMIT {limit}")
    rows = cursor.fetchall()
    headers = [desc[0] for desc in cursor.description]
    print(f"\nFirst {limit} rows of '{table}':")
    if rows:
        print(tabulate(rows, headers=headers, tablefmt="grid"))
    else:
        print("(no rows)")

def search_table(conn, table, column, keyword):
    cursor = conn.cursor()
    try:
        query = f"SELECT * FROM {table} WHERE {column} LIKE ?"
        cursor.execute(query, (f"%{keyword}%",))
        rows = cursor.fetchall()
        headers = [desc[0] for desc in cursor.description]
        print(f"\nSearch in {table}.{column} for '{keyword}':")
        if rows:
            print(tabulate(rows, headers=headers, tablefmt="grid"))
        else:
            print("(no matches)")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

def delete_row(conn, table, column, value, related_tables=None, reference_column="user_id"):
    cursor = conn.cursor()
    try:
        # find IDs of rows to delete (supports any column)
        cursor.execute(f"SELECT id FROM {table} WHERE {column} = ?", (value,))
        rows_to_delete = cursor.fetchall()
        if not rows_to_delete:
            print(f"No rows found where {column} = '{value}' in table '{table}'")
            return

        # extract IDs
        ids = [row[0] for row in rows_to_delete]

        # delete related rows in other tables if provided
        if related_tables:
            for t in related_tables:
                cursor.execute(
                    f"DELETE FROM {t} WHERE {reference_column} IN ({','.join(['?']*len(ids))})", ids
                )
        
        # delete from main table
        cursor.execute(
            f"DELETE FROM {table} WHERE id IN ({','.join(['?']*len(ids))})", ids
        )
        conn.commit()
        print(f"Deleted rows where {column} = '{value}' in table '{table}' and related tables {related_tables if related_tables else '[]'}")
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

def explore_db(conn):
    tables = list_tables(conn)

    print("\nTables in database:")
    for t in tables:
        print(f" - {t}")

    for t in tables:
        print(f"\nStructure of '{t}':")
        for name, col_type in table_info(conn, t):
            print(f" - {name} ({col_type})")

        count = count_rows(conn, t)
        print(f"Rows: {count}")

        dump_table(conn, t, limit=5)

def print_table(conn, table, limit=10):
    try:
        print(f"\nStructure of '{table}':")
        for name, col_type in table_info(conn, table):
            print(f" - {name} ({col_type})")

        count = count_rows(conn, table)
        print(f"Rows: {count}")

        dump_table(conn, table, limit=limit)
    except sqlite3.OperationalError as e:
        print(f"Error: {e}")

def list_related_tables(conn, reference_column="user_id"):
    related_tables = []
    tables = list_tables(conn)
    for t in tables:
        columns = [col[0] for col in table_info(conn, t)]
        if reference_column in columns:
            related_tables.append(t)
    print(f"\nTables related via '{reference_column}': {related_tables}")
    return related_tables

if __name__ == "__main__":
    db_path = "db.sqlite3" # path db
    conn = sqlite3.connect(db_path)

    # prints all tables in db
    explore_db(conn)  # would recommend turning this off since prints alot of things

    # print particular table
    print_table(conn, "accounts_developerprofile", 5 ) # table name - "accounts_dev..." rows to print - 5

    # list_related_tables(conn, "username") # prints tables that are related with username 

    # Search example
    #search_table(conn, "accounts_recruiterprofile", "username", "Mayuresh")  # Look inside the table - "accounts_developer..." coloumn - "username" contain - "sunil" (Can be used for other things)

    #related = list_related_tables(conn, "user_id")  # automatically find related tables

    # WARNING !!!!! Delete main row and all related rows
    #delete_row(conn, "accounts_developerprofile", "id", "2") # WARNING!!!!! actually deletes no joke !! Parameters same as search table


    conn.close()
