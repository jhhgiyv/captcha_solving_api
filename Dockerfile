# Start from the official Python 3.11 image
FROM python:3.11

# Set the working directory to /app
WORKDIR /app

# Copy the current directory contents into the container at /app
COPY . /app

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV CAPTCHA_SOLVING_API_USE_GPU=false
ENV CAPTCHA_SOLVING_API_DEVICE_ID=1
ENV CAPTCHA_SOLVING_API_FUNCAPTCHA_SERVER=http://localhost:8181
ENV CAPTCHA_SOLVING_API_CLIENT_KEY=your-api-key
ENV CAPTCHA_SOLVING_API_HEADLESS=true

# Make port 80 available to the world outside this container
EXPOSE 80

# Run the command to start uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80"]