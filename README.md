# <img src="app/static/favicon.ico" alt="S3DMap Logo" height="22"/> S3DMap

<img src="app/static/s3dmap.gif" alt="S3DMap Logo"/>


S3DMap is a new visual open-source tool that aids in S3 cost optimization. It is based on the suggested S3 prefix-level cost optimization methodology (POOM), [presented in PlatformCon2024](https://platformcon.com/talks/s3dmap-a-visual-storage-map-for-prefixlevel-cost-optimization-methodology).

The methodology and tool emerged from extensive research performed by the 5x team at PointFive and are based on real-world case studies.

Inspired by SpaceMonger from the 2000s, the tool enables interactive treemap browsing of your bucket's storage with configurable layers of insights.

Think of it as a self-serve tool for mining cost optimization opportunities, based on your S3 Bucket Inventory export.

Please do contribute and share your use cases and ideas (Email: dorazouri@pointfive.co)!

For a full managed experience and automatic cost optimization recommendations across all dimensions and use cases, feel free to [contact us and get PointFive platform on your environment](https://pointfive.co)!

## The Goal: Efficient Buckets Architecture

Choose the correct storage class for all objects given their usage pattern and attributes.

## The Methodology

### Prefix-Oriented Objects Management (POOM)

From AWS Official Documentation:
> A prefix is a string of characters at the beginning of the object key name. A prefix can be any length, subject to the maximum length of the object key name (1,024 bytes). You can think of prefixes as a way to organize your data in a similar way to directories. However, prefixes are not directories.

Under the hood, prefixes are implicit instructions for S3 to partition the physical data storage. Thus, most relevant S3 mechanisms work by the prefix:

- Lifecycle Policies
- Intelligent Tiering
- Expiration Policies
- API (prefixes actually let you horizontally scale API requests per second!)
- Inventory
- ...

## Features
- Interactive treemap browsing of S3 bucket storage
- Detailed prefix-level analysis
- Configurable layers of insights
- Anonymizer script to share bucket structure without conveying objects names

## Future
- Adding other GIS-like layers of insights: Cost, Access Logs, Lifecycle Rules, Object Attributes, CloudFront
- Support Parquet Inventory input

## Getting Started
### Prerequisites
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/PointFiveLabs/s3dmap.git
   ```
1. Enter the s3dmap directory:
   ```sh
   cd s3dmap
   ```
1. End-to-end docker-compose build:
   ```sh
   make full
   ```

1. Open browser at: https://localhost:2323/  
That will allow you to see the preloaded sample-bucket out-of-the-box

## Usage Guides
### Loading your own Bucket
#### CSV Inventory Export
1. [Create the CSV S3 Inventory export for your bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/configure-inventory.html#configure-inventory-console).  
When creating the export, choose as much optional columns to be included as desired. Non-checked columns will limit the tool's dimensions options.
1. Put the CSV files under `user_input_data/inventories/<BUCKET_NAME>/csv` along with the [corresponding `manifest.json`](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-inventory-location.html#storage-inventory-location-manifest).
1. Run:
    ```sh
    make full
    ```
1. Open browser at: https://localhost:2323/
1. Fill your `<BUCKET_NAME>` as the bucket name and hit Enter

### Anonymize your Bucket Object Names
1. Load your bucket inventory as instructed above.
1. Run:
    ```sh
    make anonymize BUCKET_NAME=<BUCKET_NAME>
    ```
    This will deep copy your bucket's inventory data using randomly mangled names, as a new bucket called `sample-bucket`
1. Open browser at: https://localhost:2323/
1. Fill `sample-bucket` as the bucket name and hit Enter

### Run your own SQL Queries on Inventory and Prefixes
1. Load your bucket inventory as instructed above.
1. Run `make sql`  
1. The main tables at your command:
    1. `inventory`
    1. `prefixes`

Example usage:
```sh
make sql QUERY="select * from inventory limit 10;"
```
```sh
make sql QUERY="select * from prefixes limit 10;"
```