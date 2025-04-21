FROM mcr.microsoft.com/playwright/python:v1.51.0-jammy

# Install any additional dependencies (if needed)
# RUN pip install your-packages

# Copy app files
COPY . /app
WORKDIR /app

# Expose port (if using uvicorn on 8000)
EXPOSE 8000

# Run your FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
