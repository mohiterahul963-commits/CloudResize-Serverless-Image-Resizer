# CloudResize – Serverless Image Resizer


## Project Overview

CloudResize is an AWS serverless project that automatically resizes uploaded images into multiple sizes using AWS Lambda and Amazon S3. It also provides a simple website for uploading images and viewing resized results.

## Technologies Used

* **AWS Lambda** – Runs the image-resizing Python code.
* **Amazon S3** – Stores uploaded images and resized outputs.
* **Amazon API Gateway** – Provides API endpoints for uploading images and retrieving results.
* **Python** – Handles image processing.
* **Pillow (PIL)** – Resizes images.
* **HTML, CSS, JavaScript** – Builds the website.
* **GitHub Pages** – Hosts the frontend website.
* **Git and GitHub** – Stores and manages project code.

## Project Architecture

1. The user selects an image on the website.
2. API Gateway provides an upload URL.
3. The image is uploaded to the source S3 bucket.
4. An S3 event triggers the Lambda function.
5. Lambda uses Pillow to resize the image.
6. Resized images are stored in the destination S3 bucket.
7. The website retrieves links to the resized images through the API.

## Image Output Sizes

* Small
* Medium
* Large

## AWS Resources

* Source S3 bucket: `serverless-image-resizer-source-2026`
* Destination S3 bucket: `serverless-image-resizer-destination-2026`
* Lambda function: `serverless-image-resizer`
* AWS Region: `ap-south-1` (Mumbai)

## API Endpoints

* `POST /upload` – Generates a presigned URL for uploading an image.
* `GET /results` – Retrieves the status and links for resized images.

## Project Files

* `index.html` – Frontend website.
* `lambda_function.py` – AWS Lambda image-processing code.
* `README.md` – Project documentation.

## Key Learning Outcomes

* Learned how to connect Amazon S3 with AWS Lambda.
* Practiced event-driven serverless architecture.
* Learned image processing using Python and Pillow.
* Worked with API Gateway and presigned S3 URLs.
* Practiced version control using GitHub.
* Published a static website using GitHub Pages.

## Future Improvements

* Add support for more image formats.
* Improve error handling and upload validation.
* Add monitoring and logging with Amazon CloudWatch.
* Improve the website interface and user experience.

## Author

**Rahul Mohite**

GitHub: https://github.com/mohiterahul963-commits

## Note

AWS resources may incur charges depending on usage. Review your AWS resources and pricing before running the project.
<img width="1876" height="906" alt="Screenshot 2026-10-03 203222" src="https://github.com/user-attachments/assets/4c20a262-a050-41fc-b16f-be4a7274e470" />
<img width="1881" height="910" alt="Screenshot 2026-10-03 203243" src="https://github.com/user-attachments/assets/13e05c62-e94d-462b-b576-7a81a647e3b1" />


