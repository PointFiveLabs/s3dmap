# <img src="app/static/favicon.ico" alt="S3DMap Logo" height="25"/> S3DMap

<img src="app/static/s3dmap.gif" alt="S3DMap TreeMap GIF"/>


**S3DMap** provides an interactive 3D Tree Map of your S3 bucket, to aid in S3 cost optimization and object management.  
Use S3DMap to gain an intuitive visual map of your S3 bucket, at the prefix-level.  
It is based on the suggested cost optimization methodology: Prefix Oriented Object Management (POOM).  
Presented in [PlatformCon2024](https://platformcon.com/talks/s3dmap-a-visual-storage-map-for-prefixlevel-cost-optimization-methodology):
* [Presentation slides](Resources/Presentation/S3DMap_%20A%203D%20Storage%20Map%20for%20S3%20Prefix-Level%20Cost%20Optimization%20Methodology%20-%20Dor%20Azouri.pdf)
* [YouTube video](https://www.youtube.com/watch?v=6F0WZjjVG-I)

The methodology and tool emerged from extensive research performed by the **5x** team at **PointFive** and are based on real-world case studies.

Inspired by SpaceMonger from the 2000s, the tool enables interactive treemap browsing of your bucket's storage with configurable layers of insights.

Think of it as a self-serve tool for mining cost optimization opportunities, based on your S3 Bucket Inventory export.

🚀 Please do contribute and share your use cases and ideas, via:
* Github [Discussions](https://github.com/PointFiveLabs/s3dmap/discussions)/[Issues](https://github.com/PointFiveLabs/s3dmap/issues)
* [LinkedIn](https://www.linkedin.com/in/dorazouri/)
* [Twitter/X](https://x.com/bemikre)
* [dorazouri@pointfive.co](mailto:dorazouri@pointfive.co)

For a fully managed experience and automatic cost optimization recommendations across all dimensions and use cases, feel free to [reach out and get PointFive platform on your environment](https://pointfive.co)!

## ✨ Features
- 🧮 **Interactive treemap** browsing of S3 bucket storage
- 📟 **Detailed prefix-level analysis**, using configurable layers of insights
- 📜 **Direct SQL interface** on the Object level and Prefix level, for custom advanced research
- 🤡 **Anonymizer script** to share bucket structure without conveying objects names


## 🌟 Example Use Cases
<p float="left">
  <img src="Resources/Use Cases Slides/1.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/2.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/3.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/4.png" width="24.5%" />
</p>
<p float="left">
  <img src="Resources/Use Cases Slides/5.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/6.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/7.png" width="24.5%" />
  <img src="Resources/Use Cases Slides/8.png" width="24.5%" />
</p>

## 🎯 The Goal: Efficient Buckets Architecture

Choose the correct storage class for all objects given their usage pattern and attributes.

## 🧩 The Methodology

### Prefix-Oriented Objects Management (POOM)

From AWS Official Documentation:
> A prefix is a string of characters at the beginning of the object key name. A prefix can be any length, subject to the maximum length of the object key name (1,024 bytes). You can think of prefixes as a way to organize your data in a similar way to directories. However, prefixes are not directories.

While the ideal architecture strives to create the "designated bucket" (coined by @omritsa) with a well defined purpose, you likely already have huge "generalized buckets" in your cloud environment. And you would probably prefer any activity rather than migrate those existing piles of data to new buckets...  

🏮 **The remedy comes in the form of designated-prefixes!** 🏮

#### In a nutshell:
- The bucket is **only a semantic wrapper** for the actual cost-driving entities: the prefixes (directories)
- S3 storage is not hierarchial (excluding the new Express One Zone), but prefixes and sub-prefixes **essentially create a hierarchial tree structure**
- Moreover, it is common for objects’ attributes to be fairly **consistent within a specific prefix branch**
- The **prefixes are the tangible organizational units** in S3 for storage class management via Lifecycle Policies (a bucket does not have a storage class)
    - Lifecycle Policies, Expiration Policies and Intelligent Tiering, in turn, are the toolset for you to achieve the goal of the game
- There are an **order of magnitude** fewer prefixes than objects, making management possible to handle and grasp.
- Under the hood, prefixes are implicit instructions for S3 to partition the physical data storage. Thus, **most relevant S3 mechanisms work by the prefix**:
    - Lifecycle Policies
    - Intelligent Tiering
    - Expiration Policies
    - API (prefixes actually let you horizontally scale API requests per second!)
    - Inventory
    - ...

## 🚀 Getting Started

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

1. Open browser at: https://localhost:2323/ and hit "*Update Treemap*"  

That will allow you to browse the preloaded sample-bucket out-of-the-box

## 📚 Usage Guides

### Loading your own Bucket

This is where it gets interesting and you can start mining insights visually! Really just by looking at the map!

##### CSV
1. [Create the CSV S3 Inventory export for your bucket](https://docs.aws.amazon.com/AmazonS3/latest/userguide/configure-inventory.html#configure-inventory-console).  
When creating the export, choose as much optional columns to be included as desired. Non-checked columns will limit the tool's dimensions options.
1. Put the CSV files under `user_input_data/inventories/<BUCKET_NAME>/csv` along with the [corresponding `manifest.json`](https://docs.aws.amazon.com/AmazonS3/latest/userguide/storage-inventory-location.html#storage-inventory-location-manifest).
1. Run:
    ```sh
    make full
    ```
1. Open browser at: https://localhost:2323/
1. Fill your `<BUCKET_NAME>` as the bucket name and hit Enter
##### Parquet
Not supported yet. Accepting PRs!

### Run your own SQL Queries on Inventory and Prefixes

For advanced research and custom investigations - you may directly query the raw `inventory` table, or the transformed `prefixes` table, using the underlying Postgres DB.

1. Load your bucket inventory as instructed above.
1. Run `make sql QUERY="<YOUR QUERY>;"`  
    
Example usage:
```sh
make sql QUERY="select * from inventory limit 10;"
```
```sh
make sql QUERY="select * from prefixes limit 10;"
```

### Anonymize your Bucket Object Names
In case you want to show/share/screenshot your bucket's map but not convey real object names, you may anonymize the bucket's inventory.

1. Load your bucket inventory as instructed above.
1. Run:
    ```sh
    make anonymize BUCKET_NAME=<BUCKET_NAME>
    ```
    This will deep copy your bucket's inventory data using randomly mangled names, as a new bucket called `sample-bucket`
1. Open browser at: https://localhost:2323/
1. Fill `sample-bucket` as the bucket name and hit Enter

## 🌟 Future Plans

Accepting PRs!

- Support Parquet Inventory input (available in our [platform](https://pointfive.co))
- Automate Inventory export creation, using AWS CLI or IaC files (Terraform/CloudFormation) (available in our [platform](https://pointfive.co))
- Obtain an existing Inventory export directly from the target bucket
- Ingesting and processing other GIS-like layers of insights (available in our [platform](https://pointfive.co)):
    - Cost (CUR)
    - Access Logs
    - Lifecycle Rules
    - Object Attributes
    - CloudFront
