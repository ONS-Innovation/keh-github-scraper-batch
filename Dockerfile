# Use an official Python runtime as a parent image
FROM public.ecr.aws/lambda/python:3.12.4

# Set the working directory in the container
WORKDIR /var/task

# Create a non-root user and group
RUN groupadd -r appuser && useradd -r -g appuser appuser

RUN pip install poetry==1.8.3

# Install the dependencies
RUN poetry install

COPY app.py /var/task/

# Change ownership of the application files to the non-root user
RUN chown -R appuser:appuser /var/task

# Switch to non-root user
USER appuser

# The CMD specifies the handler to use in AWS Lambda
CMD ["main.lambda_handler"]
