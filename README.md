# VideoCreator

A Django-based video creation and processing application that automates video production workflows.

## Features

- **Video Processing**: Automated video rendering and processing
- **B-roll Management**: Intelligent B-roll clip selection and integration
- **Caption Generation**: Automatic caption generation and overlay
- **Template System**: Configurable video templates
- **Media Management**: Upload and organize video assets
- **Preproduction Tools**: Video planning and organization utilities

## Project Structure

```
videocreator/
├── video_template_django/     # Django project settings
├── renderer/                  # Video rendering and processing app
├── preproduction/            # Preproduction planning app
├── templates/                # Django templates
├── media/                    # Media files (uploads, outputs)
├── assets/                   # Static assets
└── requirements.txt          # Python dependencies
```

## Installation

### Prerequisites

- Python 3.8+
- Django 5.1.5
- FFmpeg (for video processing)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/chrisneedham262/VideoCreator.git
   cd VideoCreator
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Database Setup**
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Run the development server**
   ```bash
   python manage.py runserver
   ```

## Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# Django Settings
SECRET_KEY=your-secret-key-here
DEBUG=True

# Database
DATABASE_URL=sqlite:///db.sqlite3

# Allowed Hosts (comma-separated)
ALLOWED_HOSTS=localhost,127.0.0.1,your.dev.host.com

# CSRF Trusted Origins (comma-separated)
CSRF_TRUSTED_ORIGINS=http://localhost:8000,http://127.0.0.1:8000,https://your.dev.host.com

# Media and Static Files
MEDIA_ROOT=media
STATIC_URL=static/
```

## Usage

### Video Processing

1. Upload your main video content
2. Add B-roll clips to enhance your video
3. Configure video templates
4. Process videos through the rendering pipeline

### B-roll Management

- Upload B-roll clips to the system
- Organize clips by category or tags
- Automatically select relevant B-roll based on content

### Caption Generation

- Generate captions from video audio
- Customize caption styling and positioning
- Export captions in various formats

## API Endpoints

- `/renderer/` - Video rendering interface
- `/preproduction/` - Preproduction planning tools
- `/admin/` - Django admin interface

## Development

### Running Tests

```bash
python manage.py test
```

### Code Style

This project follows PEP 8 guidelines. Use a code formatter like `black` for consistent formatting.

### Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Dependencies

Key dependencies include:

- **Django 5.1.5** - Web framework
- **Django REST Framework** - API development
- **Pillow** - Image processing
- **OpenAI** - AI integration
- **Anthropic** - Claude AI integration
- **LangChain** - AI workflow management

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions, please open an issue on GitHub or contact the development team.

## Changelog

### Version 1.0.0
- Initial release
- Basic video processing functionality
- B-roll management system
- Caption generation
- Template system
