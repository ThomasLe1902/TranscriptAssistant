# TranscriptAssistant - Clean Architecture

## Cấu trúc thư mục

```
TranscriptAssistant/
├── 📄 app.py                          # Main application entry point
├── 📄 requirements.txt                # Python dependencies
├── 📄 README.md                       # This file
│
├── 📁 src/                           # Source code chính
│   ├── 📄 main.py                    # Main entry point
│   │
│   ├── 📁 app/                       # FastAPI Application Layer
│   │   ├── 📄 __init__.py
│   │   ├── 📄 main.py                # FastAPI app configuration
│   │   │
│   │   ├── 📁 middlewares/           # Middleware layer
│   │   │   └── 📄 __init__.py
│   │   │
│   │   ├── 📁 routes/                # API Routes
│   │   │   └── 📄 __init__.py
│   │   │
│   │   └── 📁 schemas/               # Pydantic Schemas
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 config/                    # Configuration Layer
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 core/                      # Business Logic Layer
│   │   ├── 📄 __init__.py
│   │   ├── 📄 chat_service.py        # Chat business logic
│   │   ├── 📄 chunking.py            # Text chunking utilities
│   │   ├── 📄 pinecone_storage.py    # Pinecone storage logic
│   │   ├── 📄 summarize.py           # Summarization logic
│   │   ├── 📄 transcript.py          # Transcript processing logic
│   │   └── 📁 utils/                 # Utility functions
│   │       ├── 📄 __init__.py
│   │       └── 📄 quota_manager.py   # API quota management
│   │
│   ├── 📁 domain/                    # Domain Models
│   │   └── 📄 __init__.py
│   │
│   ├── 📁 infra/                     # Infrastructure Layer
│   │   ├── 📄 __init__.py
│   │   │
│   │   ├── 📁 db/                    # Database Adapters
│   │   │   └── 📄 __init__.py
│   │   │
│   │   ├── 📁 file_storage/          # File Storage Adapters
│   │   │   ├── 📄 __init__.py
│   │   │   └── 📁 files/             # File parsers
│   │   │       ├── 📄 __init__.py
│   │   │       ├── 📄 parse_files.py
│   │   │       ├── 📄 sbv_parser.py
│   │   │       ├── 📄 srt_parser.py
│   │   │       └── 📄 vtt_parser.py
│   │   │
│   │   ├── 📁 llm/                   # LLM Adapters
│   │   │   └── 📄 __init__.py
│   │   │
│   │   ├── 📁 queue/                 # Queue Adapters
│   │   │   └── 📄 __init__.py
│   │   │
│   │   └── 📁 vector_store/          # Vector Store Adapters
│   │       └── 📄 __init__.py
│   │
│   ├── 📁 prompts/                   # Prompt Templates
│   │   ├── 📄 chat_prompt.py         # Chat prompts
│   │   ├── 📄 grammar_prompt.py      # Grammar correction prompts
│   │   └── 📄 summarize_prompt.py    # Summarization prompts
│   │
│   └── 📁 tests/                     # Test Suite
│       ├── 📄 __init__.py
│       ├── 📁 fixtures/              # Test fixtures
│       │   └── 📄 __init__.py
│       ├── 📁 integration/           # Integration tests
│       │   └── 📄 __init__.py
│       └── 📁 unit/                  # Unit tests
│           └── 📄 __init__.py
│
├── 📁 backup/                        # Backup files
├── 📁 uploads/                       # Uploaded files
└── 📁 venv/                          # Python virtual environment
```

## Cách chạy

```bash
# Chạy từ thư mục gốc
python app.py

# Hoặc chạy từ src
python src/main.py
```

## Kiến trúc

- **app/**: FastAPI application layer
- **core/**: Business logic layer
- **infra/**: Infrastructure layer (database, file storage, etc.)
- **domain/**: Domain models
- **config/**: Configuration
- **prompts/**: Prompt templates
- **tests/**: Test suite
