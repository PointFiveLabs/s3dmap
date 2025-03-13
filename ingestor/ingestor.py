#!/usr/bin/env python3

import os
import pandas as pd
import dask.dataframe as dd
from dask.distributed import Client, LocalCluster
import psycopg2
from psycopg2.extras import execute_values
import logging
import json
import inflection
import re


# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s"
)


class Ingestor:
    DEFAULT_HEADER_COLUMNS = [
        "bucket",
        "key",
        "version_id",
        "is_latest",
        "is_delete_marker",
        "size",
        "last_modified_date",
        "e_tag",
        "storage_class",
        "is_multipart_uploaded",
        "replication_status",
        "encryption_status",
        "intelligent_tiering_access_tier",
    ]

    def __init__(self):
        self.file_handlers = {
            "csv": self.ingest_csv_dir,
            "parquet": self.ingest_parquet_dir,
        }

        self.user_input_dir = os.getenv("USER_INPUT_DIR")
        self.inventories_dir = os.path.join(self.user_input_dir, "inventories")
        # Adjust based on your memory constraints
        self.chunk_size = int(os.getenv("CHUNK_SIZE", 5000))
        # Maximum number of chunks to process
        self.max_chunks = int(os.getenv("MAX_CHUNKS", 2))
        
        # Set up Dask cluster
        n_workers = 4
        threads_per_worker = 2
        logging.info(f"Initializing Dask cluster with {n_workers} workers, {threads_per_worker} threads per worker")
        
        # Start Dask client
        self.cluster = LocalCluster(n_workers=n_workers, threads_per_worker=threads_per_worker)
        self.client = Client(self.cluster)
        logging.info(f"Dask dashboard available at: {self.client.dashboard_link}")

        self.conn, self.cur = self.__connect_to_db()

    def __connect_to_db(self):
        # Database connection parameters
        self._db_params = {
            "host": os.getenv("PG_HOST"),
            "port": os.getenv("PG_PORT"),
            "dbname": os.getenv("PG_DBNAME"),
            "user": os.getenv("PG_USER"),
            "password": os.getenv("PG_PASSWORD"),
        }
        try:
            conn = psycopg2.connect(**self._db_params)
            cur = conn.cursor()
            logging.info("Database connection established.")
            return conn, cur
        except Exception as e:
            logging.error(f"Failed to connect to the database: {e}")
            raise e

    def __del__(self):
        try:
            self.cur.close()
            self.conn.close()
            # Close Dask client and cluster
            self.client.close()
            self.cluster.close()
        except:
            pass
        logging.info("Database connection and Dask cluster closed.")

    def refresh_materialized_views(self):
        # Refresh the materialized views
        logging.info("Refreshing materialized views...")
        materialized_views = [
            os.getenv("INVENTORY_FLATTEN_MATERIALIZED_VIEW"),
            os.getenv("PREFIXES_MATERIALIZED_VIEW"),
        ]
        for view in materialized_views:
            self.cur.execute(f"REFRESH MATERIALIZED VIEW {view};")
            self.conn.commit()
            logging.info(f"Materialized view {view} refreshed.")

    def ingest_parquet_dir(self, parquet_dir):
        raise NotImplementedError("Parquet ingestion is not implemented yet.")

    def _get_header_columns_for_csv(self, manifest_filepath):
        logging.debug(
            f"Adding header columns from manifest JSON (if exists): {manifest_filepath}"
        )
        # If the manifest JSON file exists, parse it to get the header columns
        if os.path.exists(manifest_filepath):
            logging.debug(f"Manifest JSON found: {manifest_filepath}")
            with open(manifest_filepath, "r") as f:
                manifest = json.load(f)
                return [inflection.underscore(column) for column in manifest["fileSchema"].split(", ")]
        else:
            logging.debug(
                f"Manifest JSON not found: {manifest_filepath}. Using default."
            )
            return self.DEFAULT_HEADER_COLUMNS

    def ingest_csv_dir(self, csv_dir):
        # Process each CSV file in the directory
        header_columns = self._get_header_columns_for_csv(
            os.path.join(csv_dir, "manifest.json"))
        logging.info(f"Header columns: {header_columns}")
        
        # Get all CSV files for parallel processing
        csv_files = []
        for filename in os.listdir(csv_dir):
            if filename == ".DS_Store":
                continue
            if filename.endswith(".csv.gz"):
                csv_filepath = os.path.join(csv_dir, filename)
                csv_files.append(csv_filepath)
        
        # Process files in parallel using Dask
        if csv_files:
            self.process_files_with_dask(csv_files, header_columns)

    def ingest_inventory_files(self):
        logging.info(os.listdir(self.inventories_dir))
        # Process each CSV file in the directory
        for bucket_dir in os.listdir(self.inventories_dir):
            if bucket_dir == ".DS_Store":
                continue
            else:
                logging.info(f"Processing bucket directory: {bucket_dir}")
                bucket_dir = os.path.join(self.inventories_dir, bucket_dir)
                for inventory_type in os.listdir(bucket_dir):
                    logging.info(f"Processing inventory type: {inventory_type}")
                    if inventory_type == ".DS_Store":
                        continue
                    else:
                        if inventory_type in self.file_handlers:
                            inventory_type_dir = os.path.join(
                                bucket_dir, inventory_type)
                            try:
                                self.file_handlers[inventory_type](inventory_type_dir)
                            except Exception as e:
                                logging.error(
                                    f"Failed to process {inventory_type_dir}: {e}")
                                raise e
                        else:
                            logging.warning(
                                f"Unsupported inventory type: {inventory_type}")

    def _add_header_to_csv_from_manifest_json(self, filepath):
        pass

    def process_files_with_dask(self, file_list, header_columns):
        """Process multiple CSV files in parallel with Dask"""
        logging.info(f"Processing {len(file_list)} CSV files with Dask")
        
        # Create a list of tasks, one for each file
        tasks = []
        for filepath in file_list:
            # Submit task to Dask for parallel processing
            task = self.client.submit(
                self.process_single_file, 
                filepath, 
                header_columns, 
                self._db_params.copy(),
                self.chunk_size,
                self.max_chunks
            )
            tasks.append(task)
        
        # Wait for all tasks to complete
        results = self.client.gather(tasks)
        total_rows = sum(results)
        logging.info(f"Total rows inserted: {total_rows}")
    
    @staticmethod
    def process_single_file(filepath, header_columns, db_params, chunk_size, max_chunks):
        """Process a single CSV file and insert its contents into the database.
        This is a static method so it can be serialized and sent to workers."""
        logging.info(f"Processing file: {filepath}")
        
        total_rows = 0
        is_limited_chunks = max_chunks > 0
        current_chunk = 0
        
        # Process the file in chunks
        with pd.read_csv(
            filepath,
            header=None,
            names=header_columns,
            usecols=range(len(header_columns)),
            compression='gzip',
            chunksize=chunk_size
        ) as reader:
            for chunk in reader:
                current_chunk += 1
                
                # Stop if we've reached the maximum number of chunks
                if is_limited_chunks and current_chunk > max_chunks:
                    break
                
                # Drop the column object_access_control_list
                if "object_access_control_list" in chunk.columns:
                    chunk.drop(columns=["object_access_control_list"], inplace=True)
                
                # Process the data
                try:
                    # Normalize the key column (remove double slashes)
                    def normalize_key(x):
                        if pd.isna(x) or x is None:
                            return ""
                        return re.sub(r'\/\/+', '/', str(x))
                    
                    key_normalized = chunk.key.apply(normalize_key)
                    chunk = chunk.assign(key=key_normalized)
                    
                    # Add a suffix column based on the key
                    def extract_suffix(x):
                        if pd.isna(x) or x is None:
                            return None
                        x_str = str(x)
                        return x_str.split(".")[-1] if "." in x_str and x_str.rfind(".") > x_str.rfind("/") else None
                    
                    suffix_series = chunk.key.apply(extract_suffix)
                    chunk = chunk.assign(suffix=suffix_series)
                    
                    # Add depth column based on the key
                    def calculate_depth(x):
                        if pd.isna(x) or x is None:
                            return 0
                        return str(x).count("/")
                    
                    depth_series = chunk.key.apply(calculate_depth)
                    chunk = chunk.assign(depth=depth_series)
                    
                    # Normalize column names (make them lowercase)
                    chunk.columns = [c.lower() for c in chunk.columns]
                    
                    # Prepare data tuple list for insertion
                    tuples = [tuple(x) for x in chunk.to_numpy(na_value=None)]
                    
                    # Compose the query dynamically based on the CSV columns
                    cols = ",".join(list(chunk.columns))
                    query = f"INSERT INTO inventory ({cols}) VALUES %s"
                    
                    # Insert data into database
                    with psycopg2.connect(**db_params) as conn:
                        with conn.cursor() as cur:
                            execute_values(cur, query, tuples)
                            conn.commit()
                    
                    # Update row count
                    total_rows += len(tuples)
                    logging.info(f"Inserted {len(tuples)} rows from {os.path.basename(filepath)} (Chunk {current_chunk})")
                
                except Exception as e:
                    logging.error(f"Error processing chunk {current_chunk} from {filepath}: {e}")
        
        logging.info(f"Completed file {os.path.basename(filepath)} - Inserted {total_rows} rows")
        return total_rows

    def insert_csv_to_db(self, filepath, header_columns):
        """Insert CSV file into the database table in chunks"""
        # Read the CSV in chunks
        max_chunks = self.max_chunks
        is_limited_chunks = max_chunks > 0
        with pd.read_csv(
            filepath,
            chunksize=self.chunk_size,
            header=None,
            names=header_columns,
            usecols=range(len(header_columns)),
            low_memory=False  # Added to prevent DtypeWarning
        ) as reader:
            for i, chunk in enumerate(reader):
                logging.info(f"max_chunks: {max_chunks}")
                max_chunks -= 1
                if is_limited_chunks and max_chunks < 0:
                    return
                # Drop the column object_access_control_list
                if "object_access_control_list" in chunk.columns:
                    chunk.drop(
                        columns=["object_access_control_list"], inplace=True)
                # Normalize the key column (remove double slashes)
                key_normalized = chunk.key.apply(
                    lambda x: re.sub(r'\/\/+', '/', x))
                chunk = chunk.assign(key=key_normalized)
                # Add a suffix column based on the key
                suffix_series = chunk.key.apply(
                    lambda x: (
                        x.split(".")[-1]
                        if "." in x and x.rfind(".") > x.rfind("/")
                        else None
                    )
                )
                chunk = chunk.assign(suffix=suffix_series)
                # Add depth column based on the key
                depth_series = chunk.key.apply(lambda x: x.count("/"))
                chunk = chunk.assign(depth=depth_series)
                # Normalize column names (make them lowercase)
                chunk.columns = [c.lower() for c in chunk.columns]
                # chunk.rename(columns={"unnamed: 0": "id"}, inplace=True)
                # Prepare data tuple list for insertion
                tuples = [tuple(x) for x in chunk.to_numpy(na_value=None)]
                # Compose the query dynamically based on the CSV columns
                cols = ",".join(list(chunk.columns))
                values = ",".join(["%s" for _ in chunk.columns])
                query = f"INSERT INTO inventory ({cols}) VALUES %s"
                # Log the query and number of rows
                logging.info(
                    f"Inserting {len(tuples)} rows from {os.path.basename(filepath)} (Chunk {i+1})"
                )
                # Execute the query
                execute_values(self.cur, query, tuples)
                self.conn.commit()
                logging.info(
                    f"Inserted {len(tuples)} rows from {os.path.basename(filepath)} (Chunk {i+1})"
                )


def main():
    ingestor = Ingestor()
    try:
        #ingestor.ingest_inventory_files()
        ingestor.refresh_materialized_views()
    except Exception as e:
        logging.error(f"Failed to ingest inventory files: {e}")
    del ingestor


if __name__ == "__main__":
    main()
