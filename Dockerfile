# Use an official lightweight Python image
FROM python:3.11-slim

# Create a non-root user (Required by Hugging Face Spaces)
RUN useradd -m -u 1000 user
USER user

# Set environment variables
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1

# Set the working directory
WORKDIR $HOME/app

# Copy requirements and install them
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code
COPY --chown=user . .

# Hugging Face routes traffic to port 7860
EXPOSE 7860

# Run the application using Gunicorn 
CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]