FROM centos/python-38-centos7

# Set the working directory in the container
WORKDIR /app

# Copy the dependencies file to the working directory
COPY requirements.txt .

# Install any dependencies
# RUN apk add --no-cache gcc build-base libffi-dev openssl-dev
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code
COPY . .

# Command to run the application
CMD ["python3", "s3dmap.py"]
