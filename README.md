# S3DMap

<img src="app/static/s3dmap.png" alt="S3DMap Logo" width="200"/>

S3DMap is a new visual open-source tool that aids in S3 cost optimization. It is based on the suggested S3 prefix-level cost optimization methodology (POOM), as [presented in #PlatformCon2024](https://platformcon.com/talks/s3dmap-a-visual-storage-map-for-prefixlevel-cost-optimization-methodology).

The methodology and tool emerged from extensive research performed by the 5x team at PointFive and are based on real-world case studies.

Inspired by SpaceMonger from the 2000s, the tool enables interactive treemap browsing of your bucket's storage with configurable layers of insights. S3DMap will become public on the day of the event via GitHub.

![Demo GIF Placeholder](path/to/demo.gif)

## The Goal: Efficient Buckets Architecture

### The Ultimate Goal
Choose the correct storage class for all objects given their usage pattern and attributes.

## The Methodology
Prefix-Oriented Objects Management (POOM)

“A prefix is a string of characters at the beginning of the object key name. A prefix can be any length, subject to the maximum length of the object key name (1,024 bytes). You can think of prefixes as a way to organize your data in a similar way to directories. However, prefixes are not directories.”

Under the hood, prefixes are implicit instructions for S3 to partition the physical data storage. Thus, most relevant S3 mechanisms work by the prefix:

- Lifecycle Policies
- Expiration Policies
- API (prefixes actually let you horizontally scale API requests per second!)
- Intelligent Tiering
- Inventory

## Features
- Interactive treemap browsing of S3 bucket storage
- Configurable layers of insights
- Real-time cost optimization recommendations
- Detailed prefix-level analysis

## Getting Started
### Prerequisites
- [Docker Compose](https://docs.docker.com/compose/install/)

### Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/PointFiveLabs/s3dmap.git
   cd s3dmap
   make full
   ```
2. Open browser on: https://localhost:2323/