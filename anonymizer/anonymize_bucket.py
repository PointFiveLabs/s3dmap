import psycopg2
from psycopg2 import sql
import regex as re
import random
from tokens import potential_tokens as base_tokens
import os
import sys
from dotenv import load_dotenv

# Read the environment variables from the .env file, located in the project root
load_dotenv("./.env")


def anonymize_bucket(cur, bucket_name, anonymized_bucket_name, columns):

    # Replacement mapping dictionary
    replacement_mapping = {}

    # Query all rows from the prefixes view
    cur.execute(
        f"SELECT * FROM {os.getenv('PREFIXES_MATERIALIZED_VIEW')} where bucket = '{bucket_name}'"
    )
    rows = cur.fetchall()
    print(f"Anonymizing {len(rows)} rows...")

    used_tokens = []
    # Anonymize and insert new rows
    for row in rows:
        row = list(row)  # Convert tuple to list for mutability
        prefix_index = columns.index("prefix")
        bucket_index = columns.index("bucket")

        row[bucket_index] = anonymized_bucket_name  # Replace bucket name

        # Anonymize the prefix
        original_prefix = row[prefix_index]
        tokens = re.findall(r"\b\w+\b", original_prefix)
        new_prefix = original_prefix

        for token in tokens:
            if token not in replacement_mapping:
                random_token = random.choice(base_tokens)
                while random_token in used_tokens:
                    random_token = random.choice(base_tokens)
                replacement_mapping[token] = random_token
                used_tokens.append(random_token)

            # Replace tokens in the original prefix with the mapped tokens
            new_prefix = re.sub(
                r"\b{}\b".format(re.escape(token)),
                replacement_mapping[token],
                new_prefix,
            )
        print(f"Original prefix: {original_prefix} -> Anonymized prefix: {new_prefix}")
        row[prefix_index] = new_prefix  # Update prefix with anonymized version

        # Insert the new row into the new table
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(os.getenv("PREFIXES_DEMO_TABLE")),
            sql.SQL(", ").join(map(sql.Identifier, columns)),
            sql.SQL(", ").join(sql.Placeholder() for _ in columns),
        )
        cur.execute(insert_query, row)


def connect_to_postgres():
    conn = psycopg2.connect(
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host="localhost",
        port=os.getenv("POSTGRES_PORT_EXPOSE"),
    )
    cur = conn.cursor()
    return conn, cur


def get_materialized_view_schema_details(cur, m_view_name):
    cur.execute(
        f"""
    SELECT attname AS column_name, format_type(atttypid, atttypmod) AS data_type
    FROM   pg_attribute
    WHERE  attrelid = 's3dmap.{m_view_name}'::regclass
    AND    NOT attisdropped
    AND    attnum > 0
    ORDER  BY attnum;
    """
    )
    schema = cur.fetchall()
    columns, types = zip(*schema)
    return schema, columns, types


def create_table_replica(cur, source_schema, target_table_name):
    # Create new table demo table with the same schema
    cur.execute(sql.SQL(f"DROP TABLE IF EXISTS {target_table_name}"))
    create_table_query = sql.SQL("CREATE TABLE {} ({})").format(
        sql.Identifier(target_table_name),
        sql.SQL(", ").join(
            sql.Identifier(name) + sql.SQL(" ") + sql.SQL(type)
            for name, type in source_schema
        ),
    )
    cur.execute(create_table_query)


def main(bucket_name, anonymized_bucket_name="sample-bucket"):
    # Connect to the Postgres database
    conn, cur = connect_to_postgres()
    # Get the schema of the "prefixes" materialized view
    schema, columns, _ = get_materialized_view_schema_details(
        cur, os.getenv("PREFIXES_MATERIALIZED_VIEW")
    )
    # Create a replica table with the same schema
    create_table_replica(cur, schema, os.getenv("PREFIXES_DEMO_TABLE"))
    # Anonymize the bucket
    anonymize_bucket(cur, bucket_name, anonymized_bucket_name, columns)
    # Commit changes and close the connection
    conn.commit()
    cur.close()
    conn.close()
    print("Data anonymization completed successfully.")
    print(f"Anonymized data saved in the {anonymized_bucket_name} bucket.")


if __name__ == "__main__":
    main(sys.argv[1])
