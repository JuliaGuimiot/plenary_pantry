# 📱 Mobile Recipe Photo Upload API Guide

## 🎯 Overview
Upload recipe photos from your phone directly to the Plenary Pantry recipe database using OCR (Optical Character Recognition).

## 📋 API Endpoint
```
POST http://localhost:8000/ingestion/api/process/
Content-Type: multipart/form-data
```

## 📸 Supported Image Formats
- **JPEG/JPG** (recommended)
- **PNG**
- **HEIC/HEIF** (iPhone photos)

## 📏 File Size Limits
- **Single Image**: 10MB maximum
- **Multi-Image**: 10MB per image, 50MB total, up to 10 images
- **Recommended**: 2-5MB per image for best OCR results

## 🔧 API Parameters

### Required Fields
- `user_id`: Your user ID (integer)
- `image`: The recipe photo file (single image)
- `images`: Multiple recipe photo files (multi-image)

### Optional Fields
- `auto_normalize`: Set to "true" to automatically save to recipe database (default: true)
- `source_name`: Custom name for the upload (default: "Mobile Photo Upload")
- `upload_type`: "single" or "multi" (default: "single")
- `page_type_X`: Page type for multi-image uploads (ingredients, instructions, metadata, unknown)

## 📱 Example Usage

### Using cURL (for testing)

#### Single Image Upload
```bash
curl -X POST http://localhost:8000/ingestion/api/process/ \
  -F "user_id=1" \
  -F "image=@/path/to/your/recipe.jpg" \
  -F "auto_normalize=true" \
  -F "source_name=Grandma's Cookie Recipe"
```

#### Multi-Image Upload
```bash
curl -X POST http://localhost:8000/ingestion/api/process/ \
  -F "user_id=1" \
  -F "upload_type=multi" \
  -F "images=@/path/to/page1.jpg" \
  -F "images=@/path/to/page2.jpg" \
  -F "images=@/path/to/page3.jpg" \
  -F "page_type_0=ingredients" \
  -F "page_type_1=instructions" \
  -F "page_type_2=metadata" \
  -F "auto_normalize=true" \
  -F "source_name=Multi-Page Recipe"
```

### Using Python Requests

#### Single Image Upload
```python
import requests

url = "http://localhost:8000/ingestion/api/process/"
files = {'image': open('recipe.jpg', 'rb')}
data = {
    'user_id': '1',
    'auto_normalize': 'true',
    'source_name': 'Grandma\'s Cookie Recipe'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

#### Multi-Image Upload
```python
import requests

url = "http://localhost:8000/ingestion/api/process/"
files = [
    ('images', open('page1.jpg', 'rb')),
    ('images', open('page2.jpg', 'rb')),
    ('images', open('page3.jpg', 'rb'))
]
data = {
    'user_id': '1',
    'upload_type': 'multi',
    'page_type_0': 'ingredients',
    'page_type_1': 'instructions', 
    'page_type_2': 'metadata',
    'auto_normalize': 'true',
    'source_name': 'Multi-Page Recipe'
}

response = requests.post(url, files=files, data=data)
print(response.json())
```

### Using JavaScript/Fetch (for web apps)
```javascript
const formData = new FormData();
formData.append('user_id', '1');
formData.append('image', imageFile);
formData.append('auto_normalize', 'true');
formData.append('source_name', 'Grandma\'s Cookie Recipe');

fetch('http://localhost:8000/ingestion/api/process/', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => console.log(data));
```

## 📱 Mobile App Integration Examples

### iOS (Swift)
```swift
import UIKit

func uploadRecipeImage(image: UIImage, userId: String) {
    let url = URL(string: "http://localhost:8000/ingestion/api/process/")!
    var request = URLRequest(url: url)
    request.httpMethod = "POST"
    
    let boundary = UUID().uuidString
    request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
    
    var body = Data()
    
    // Add user_id
    body.append("--\(boundary)\r\n".data(using: .utf8)!)
    body.append("Content-Disposition: form-data; name=\"user_id\"\r\n\r\n".data(using: .utf8)!)
    body.append("\(userId)\r\n".data(using: .utf8)!)
    
    // Add image
    if let imageData = image.jpegData(compressionQuality: 0.8) {
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"image\"; filename=\"recipe.jpg\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: image/jpeg\r\n\r\n".data(using: .utf8)!)
        body.append(imageData)
        body.append("\r\n".data(using: .utf8)!)
    }
    
    body.append("--\(boundary)--\r\n".data(using: .utf8)!)
    request.httpBody = body
    
    URLSession.shared.dataTask(with: request) { data, response, error in
        if let data = data {
            let result = try? JSONSerialization.jsonObject(with: data)
            print("Upload result:", result)
        }
    }.resume()
}
```

### Android (Kotlin)
```kotlin
import okhttp3.*

fun uploadRecipeImage(imageFile: File, userId: String) {
    val client = OkHttpClient()
    
    val requestBody = MultipartBody.Builder()
        .setType(MultipartBody.FORM)
        .addFormDataPart("user_id", userId)
        .addFormDataPart("image", "recipe.jpg", 
            RequestBody.create("image/jpeg".toMediaTypeOrNull(), imageFile))
        .addFormDataPart("auto_normalize", "true")
        .addFormDataPart("source_name", "Mobile Recipe Upload")
        .build()
    
    val request = Request.Builder()
        .url("http://localhost:8000/ingestion/api/process/")
        .post(requestBody)
        .build()
    
    client.newCall(request).enqueue(object : Callback {
        override fun onResponse(call: Call, response: Response) {
            val result = response.body?.string()
            println("Upload result: $result")
        }
        
        override fun onFailure(call: Call, e: IOException) {
            println("Upload failed: ${e.message}")
        }
    })
}
```

## 📊 Response Format

### Success Response
```json
{
    "success": true,
    "job_id": "cfa17583-bd2c-41b1-9388-d61608c17c33",
    "status": "completed",
    "recipes_found": 1,
    "recipes_saved": 1,
    "auto_normalized": true,
    "file_name": "recipe.jpg",
    "file_size": 48119
}
```

### Error Response
```json
{
    "error": "No image file provided"
}
```

## 🎯 Best Practices for Mobile Photos

### 📸 Photo Tips for Better OCR
1. **Good Lighting**: Ensure the recipe is well-lit
2. **Clear Text**: Make sure text is readable and not blurry
3. **Flat Surface**: Place recipe on a flat surface
4. **Avoid Shadows**: Minimize shadows on the text
5. **High Resolution**: Use the highest quality setting
6. **Straight Angle**: Take photo from directly above

### 📄 Multi-Page Recipe Tips
1. **Page Order**: Upload pages in the correct order (ingredients first, then instructions)
2. **Page Types**: Specify page types for better parsing:
   - `ingredients`: Page with ingredient lists
   - `instructions`: Page with cooking instructions
   - `metadata`: Page with prep time, cook time, servings, etc.
3. **Consistent Lighting**: Use the same lighting for all pages
4. **Page Numbers**: Include page numbers if available
5. **Complete Coverage**: Make sure all text is visible in each photo

### 📱 Recommended Photo Settings
- **Resolution**: 12MP or higher
- **Format**: JPEG
- **Quality**: High/Ultra
- **Flash**: Auto (if needed for lighting)
- **Focus**: Tap to focus on the text

## 🔍 Troubleshooting

### Common Issues
1. **"No image file provided"**: Check that the image field is properly set
2. **"File too large"**: Compress the image or reduce resolution
3. **"Unsupported file type"**: Convert to JPEG or PNG
4. **Poor OCR results**: Retake photo with better lighting/angle

### OCR Quality Tips
- **Clean background**: Use white/light background
- **Contrast**: Ensure good contrast between text and background
- **Font size**: Larger, clearer fonts work better
- **Multiple photos**: Take multiple angles if needed

## 🚀 Quick Test

Test the API with a sample image:
```bash
# Create a test image and upload it
python test_image_upload.py
```

## 📞 Support

If you encounter issues:
1. Check the server logs
2. Verify image format and size
3. Test with a simple, clear recipe image
4. Ensure the Django server is running

---

**Happy Recipe Ingestion! 🍳📱**
