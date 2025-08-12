# Recipe Ingestion System

A comprehensive Django application for ingesting recipes from multiple sources and normalizing them into a structured database format.

## 🚀 Features

### **Multi-Source Ingestion**
- **Image Upload**: OCR processing of cookbook pages, recipe cards, and packaging
- **Web URL Processing**: Scraping recipes from cooking websites and blogs
- **Manual Text Input**: Direct text entry for recipes
- **API Integration**: Programmatic recipe ingestion

### **Intelligent Data Extraction**
- **OCR with Preprocessing**: Advanced image processing for better text recognition
- **Web Scraping**: Handles both static and JavaScript-heavy websites
- **Recipe Parsing**: Extracts ingredients, instructions, and metadata
- **Ingredient Normalization**: Converts raw text to structured data

### **Data Normalization**
- **Ingredient Mapping**: Maps raw ingredient text to normalized ingredients
- **Unit Conversion**: Standardizes measurement units
- **Quantity Parsing**: Extracts and normalizes quantities
- **Preparation Methods**: Identifies cooking techniques (chopped, diced, etc.)

### **Quality Assurance**
- **Confidence Scoring**: Rates extraction quality
- **Processing Logs**: Detailed tracking of processing steps
- **Error Handling**: Graceful failure handling with detailed error messages
- **Validation**: Ensures data integrity before saving

## 🏗️ Architecture

### **Models**

#### Core Ingestion Models
- `IngestionSource`: Tracks the source of recipe data
- `IngestionJob`: Manages processing workflow
- `ExtractedRecipe`: Raw recipe data before normalization
- `IngredientMapping`: Maps raw text to normalized ingredients
- `ProcessingLog`: Detailed processing logs
- `RecipeTemplate`: Templates for different recipe formats

#### Integration with Main App
- Integrates with `plenary_pantry.models` for final recipe storage
- Uses existing `Recipe`, `Ingredient`, `Unit`, etc. models

### **Services**

#### `RecipeIngestionService`
Main orchestrator for recipe processing:
- Handles different source types (image, URL, text)
- Manages processing workflow
- Coordinates normalization and saving

#### `IngredientNormalizer`
Specialized ingredient processing:
- Parses quantities and units
- Identifies preparation methods
- Maps to normalized ingredients
- Maintains confidence scores

#### `RecipeParser`
Text-based recipe extraction:
- Splits content into recipe sections
- Extracts recipe names, ingredients, instructions
- Parses metadata (prep time, cook time, servings)
- Calculates confidence scores

## 🛠️ Installation & Setup

### **Prerequisites**
```bash
# Install system dependencies
brew install tesseract  # For OCR
brew install chromedriver  # For web scraping
```

### **Python Dependencies**
```bash
# Already included in pyproject.toml
uv sync
```

### **Database Setup**
```bash
# Create migrations
uv run python manage.py makemigrations

# Apply migrations
uv run python manage.py migrate
```

## 📖 Usage

### **Web Interface**

#### Dashboard
```
/ingestion/
```
- Overview of recent ingestion sources and jobs
- Statistics and success rates
- Quick access to all features

#### Image Upload
```
/ingestion/upload-image/
```
- Upload recipe images (JPEG, PNG, GIF)
- Automatic OCR processing
- Real-time status updates

#### URL Processing
```
/ingestion/process-url/
```
- Enter recipe URLs
- Automatic web scraping
- Handles JavaScript-heavy sites

#### Manual Input
```
/ingestion/manual-input/
```
- Direct text entry
- Supports multiple recipes per input
- Real-time parsing

#### Job Management
```
/ingestion/jobs/
/ingestion/job/<job_id>/
```
- View all processing jobs
- Detailed job information
- Processing logs and extracted recipes

### **API Endpoints**

#### Process Recipe Source
```http
POST /ingestion/api/process/
Content-Type: application/json

{
    "source_type": "url",
    "user_id": 1,
    "source_url": "https://example.com/recipe",
    "source_name": "My Recipe"
}
```

#### Check Job Status
```http
GET /ingestion/api/job/<job_id>/status/
```

### **Management Commands**

#### Test the System
```bash
uv run python manage.py test_ingestion --username admin
```

## 🔧 Configuration

### **Environment Variables**
```env
# OCR Configuration
TESSERACT_CMD=/usr/local/bin/tesseract

# Web Scraping
SELENIUM_DRIVER_PATH=/usr/local/bin/chromedriver

# File Upload
FILE_UPLOAD_MAX_MEMORY_SIZE=10485760  # 10MB
```

### **Settings**
```python
# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# File upload limits
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
```

## 🔍 Processing Workflow

### **1. Source Creation**
- User uploads image, enters URL, or provides text
- System creates `IngestionSource` record
- Validates input and prepares for processing

### **2. Content Extraction**
- **Images**: OCR with preprocessing (noise reduction, thresholding)
- **URLs**: Web scraping with fallback to Selenium
- **Text**: Direct parsing

### **3. Recipe Parsing**
- Splits content into recipe sections
- Extracts recipe names, ingredients, instructions
- Parses metadata (times, servings, difficulty)
- Calculates confidence scores

### **4. Ingredient Normalization**
- Parses quantities and units
- Identifies preparation methods
- Maps to existing ingredients or creates new ones
- Maintains mapping history for future use

### **5. Data Validation**
- Ensures required fields are present
- Validates data types and formats
- Checks for duplicates

### **6. Recipe Saving**
- Creates normalized `Recipe` records
- Links to existing categories (cuisine, diet, etc.)
- Saves ingredient relationships
- Updates processing logs

## 📊 Data Quality

### **Confidence Scoring**
- **Recipe Level**: Based on completeness of extraction
- **Ingredient Level**: Based on parsing success
- **Overall**: Weighted average of all components

### **Validation Rules**
- Recipe must have name, ingredients, and instructions
- Ingredients must have valid quantities and units
- All foreign keys must reference existing records

### **Error Handling**
- Graceful degradation for partial failures
- Detailed error logging
- User-friendly error messages
- Recovery mechanisms for common issues

## 🔄 Integration Points

### **With Main Recipe System**
- Uses existing `Recipe`, `Ingredient`, `Unit` models
- Maintains referential integrity
- Supports all existing features (menus, shopping lists, etc.)

### **With User System**
- User-specific ingestion sources
- Personalized ingredient mappings
- User preferences integration

### **With Inventory System**
- Ingredient normalization supports inventory tracking
- Quantity parsing enables accurate inventory updates
- Unit standardization for consistent tracking

## 🚀 Performance Considerations

### **Optimization Strategies**
- Asynchronous processing for large files
- Caching of ingredient mappings
- Batch processing for multiple recipes
- Database indexing for frequent queries

### **Scalability**
- Modular service architecture
- Configurable processing pipelines
- Support for distributed processing
- Horizontal scaling capabilities

## 🔒 Security

### **File Upload Security**
- File type validation
- Size limits
- Virus scanning (configurable)
- Secure file storage

### **API Security**
- Authentication required
- Rate limiting
- Input validation
- SQL injection prevention

## 🧪 Testing

### **Unit Tests**
```bash
uv run python manage.py test recipe_ingestion
```

### **Integration Tests**
- End-to-end processing workflows
- Database integration tests
- API endpoint tests

### **Performance Tests**
- Large file processing
- Concurrent user testing
- Database performance

## 📈 Monitoring & Analytics

### **Processing Metrics**
- Success/failure rates
- Processing times
- Quality scores
- User engagement

### **System Health**
- Error rates
- Performance metrics
- Resource usage
- Database performance

## 🔮 Future Enhancements

### **Planned Features**
- **Machine Learning**: Improved ingredient recognition
- **Multi-language Support**: International recipe processing
- **Recipe Validation**: AI-powered recipe validation
- **Batch Processing**: Bulk recipe import
- **API Rate Limiting**: Advanced API management
- **Real-time Processing**: WebSocket-based updates

### **Integration Opportunities**
- **Recipe APIs**: Integration with external recipe services
- **Social Media**: Recipe sharing and discovery
- **Mobile Apps**: Native mobile integration
- **Voice Input**: Voice-to-recipe processing

## 🤝 Contributing

### **Development Setup**
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

### **Code Standards**
- Follow PEP 8
- Add docstrings
- Include type hints
- Write comprehensive tests

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

### **Documentation**
- This README
- Django documentation
- API documentation

### **Issues**
- GitHub Issues
- Stack Overflow
- Community forums

### **Contact**
- Project maintainers
- Development team
- User community
