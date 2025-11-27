FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
#The image must install all dependencies

COPY . .
#copy source files

EXPOSE 5000
#expose port 5000

CMD ["python", "app.py"]
#run the Flask server
