from mysql import connector
import os

host = os.getenv("MYSQL_HOSTNAME", "localhost")
username = os.getenv("MYSQL_USER", "steve")
password = os.getenv("MYSQL_PASSWORD", "changeme")
database = os.getenv("MYSQL_DATABASE", "stevedb")


def insert_list_into_table(host, username, password, database, table_name, data_list):
    try:
        # Connect to MySQL
        connection = connector.connect(
            host=host, user=username, password=password, database=database
        )

        if connection.is_connected():
            print("Connected to MySQL database")

            # Get cursor
            cursor = connection.cursor()

            # Prepare INSERT INTO query
            query = "INSERT INTO {} ({}) VALUES ({})".format(
                table_name,
                ", ".join(data_list[0].keys()),
                ", ".join(["%s"] * len(data_list[0])),
            )

            # Extract values from the data_list
            values = [[row[column] for column in data_list[0]] for row in data_list]

            # Execute query to insert data
            cursor.executemany(query, values)

            # Commit changes
            connection.commit()

            print("Data inserted successfully")
    except connector.Error as error:
        print("Error while connecting to MySQL", error)

    finally:
        # Close connection
        if "connection" in locals() and connection.is_connected():
            cursor.close()
            connection.close()
            print("MySQL connection is closed")


def add_charge_points_to_steve(charge_point_ids: list[str]):
    values = [
        {
            "charge_box_id": charge_point_id,
            "insert_connector_status_after_transaction_msg": 0,
            "registration_status": "Accepted",
        }
        for charge_point_id in charge_point_ids
    ]
    insert_list_into_table(host, username, password, database, "charge_box", values)


def add_ocpp_tags_to_steve(ocpp_tags: list[str]):
    values = [{"id_tag": tag, "max_active_transaction_count": "1"} for tag in ocpp_tags]
    insert_list_into_table(host, username, password, database, "ocpp_tag", values)
