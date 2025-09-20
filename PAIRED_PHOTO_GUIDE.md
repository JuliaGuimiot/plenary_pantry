# Paired Photo Recipe Upload Guide

This guide explains how to use the new simplified OCR system that allows users to take separate photos of ingredients and directions for better recipe recognition.

## Overview

The paired photo system simplifies recipe ingestion by:
- Taking separate photos of ingredients and directions
- Using a pairing token to keep them linked together
- Processing each photo separately for better OCR accuracy
- Automatically combining the results into a complete recipe

## How It Works

### 1. Create a Pairing Token
- User starts by creating a pairing token
- This token links the ingredients and directions photos together
- Can be shared between devices for collaborative uploads

### 2. Upload Photos
- Take a photo of the ingredients list
- Take a photo of the cooking directions
- Photos are uploaded separately but linked by the pairing token

### 3. Automatic Processing
- When both photos are uploaded, processing starts automatically
- Each photo is processed with OCR separately
- Results are combined into a single recipe

## API Endpoints

### Create Pairing Token
```
POST /recipe-ingestion/api/paired/create-token/
Content-Type: application/json

{
    "user_id": 1,
    "recipe_name": "Chocolate Chip Cookies"
}
```

Response:
```json
{
    "success": true,
    "pairing_token": "a1b2c3d4",
    "paired_source_id": "uuid-here",
    "status": "pending"
}
```

### Upload Photo
```
POST /recipe-ingestion/api/paired/upload/
Content-Type: multipart/form-data

pairing_token: a1b2c3d4
photo_type: ingredients  # or "directions"
user_id: 1
photo: [image file]
```

Response:
```json
{
    "success": true,
    "photo_type": "ingredients",
    "status": "ingredients_uploaded",
    "is_complete": false,
    "auto_process": false
}
```

### Check Status
```
GET /recipe-ingestion/api/paired/{pairing_token}/status/?user_id=1
```

Response:
```json
{
    "success": true,
    "pairing_token": "a1b2c3d4",
    "recipe_name": "Chocolate Chip Cookies",
    "status": "completed",
    "is_complete": true,
    "ingredients_uploaded": true,
    "directions_uploaded": true,
    "job": {
        "id": "job-uuid",
        "status": "completed",
        "recipes_found": 1,
        "recipes_processed": 1
    }
}
```

## Web Interface

### Paired Photo Upload Page
Visit `/recipe-ingestion/paired-upload/` for a mobile-friendly interface that:
- Guides users through the photo upload process
- Shows real-time status updates
- Handles file uploads with camera capture
- Displays pairing tokens for sharing

## Email Integration

The system automatically detects when emails contain multiple image attachments and processes them as paired photos:
- 2+ image attachments are grouped into pairs
- First image becomes ingredients, second becomes directions
- Automatic processing and recipe creation

## Benefits

1. **Better OCR Accuracy**: Separate processing of ingredients and directions improves text recognition
2. **Simplified Workflow**: Users don't need to fit everything in one photo
3. **Mobile-Friendly**: Optimized for smartphone camera usage
4. **Collaborative**: Pairing tokens allow multiple people to contribute photos
5. **Automatic Processing**: No manual intervention needed once both photos are uploaded

## Technical Details

### Models
- `PairedPhotoSource`: Tracks paired photo uploads and their status
- `PairedPhotoJob`: Manages processing jobs for paired photos

### Processing Flow
1. Create pairing token and source record
2. Upload ingredients photo → status: "ingredients_uploaded"
3. Upload directions photo → status: "directions_uploaded"
4. Automatic processing starts when both photos are present
5. OCR processing for each photo separately
6. Text combination and recipe parsing
7. Recipe normalization and saving

### File Storage
- Ingredients photos: `recipe_sources/paired/ingredients/`
- Directions photos: `recipe_sources/paired/directions/`

## Usage Examples

### Mobile App Integration
```javascript
// Create pairing token
const response = await fetch('/recipe-ingestion/api/paired/create-token/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, recipe_name: 'My Recipe' })
});
const { pairing_token } = await response.json();

// Upload ingredients photo
const formData = new FormData();
formData.append('pairing_token', pairing_token);
formData.append('photo_type', 'ingredients');
formData.append('user_id', userId);
formData.append('photo', ingredientsFile);

await fetch('/recipe-ingestion/api/paired/upload/', {
    method: 'POST',
    body: formData
});

// Upload directions photo
formData.set('photo_type', 'directions');
formData.set('photo', directionsFile);

await fetch('/recipe-ingestion/api/paired/upload/', {
    method: 'POST',
    body: formData
});
```

### Email Usage
Simply send an email with two image attachments to the configured email address. The system will:
1. Detect multiple image attachments
2. Create a paired photo source
3. Process both images
4. Create a complete recipe

## Configuration

No additional configuration is needed beyond the existing email ingestion settings. The paired photo system works with the existing OCR and recipe processing infrastructure.
