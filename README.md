# Fault Injector TUI

A Terminal User Interface (TUI) application for chaos engineering with AI-powered analysis using Google's Gemini API.

## 🚀 Features

- **5-Screen Workflow**: Selection → Configuration → Confirmation → Monitoring → AI Report
- **AI Analysis**: Powered by Google Gemini API for intelligent chaos experiment analysis
- **File Export**: Save reports to timestamped markdown files
- **Safety Features**: Red confirmation screen before destructive operations
- **Real-time Monitoring**: Live log streaming during experiments

## 🔧 Setup

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <repository-url>
cd quickdemotui

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

Create a `.env` file in the project root:

```env
# Gemini AI API Key
GEMINI_API_KEY=your_api_key_here
```

### 3. Get Gemini API Key

1. Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Create a new API key
3. Copy the key to your `.env` file

### 4. Run the Application

```bash
python fault_injector_tui.py
```

## 📁 Project Structure

```
quickdemotui/
├── fault_injector_tui.py    # Main TUI application
├── fault_injector.tcss      # CSS styling  
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (not tracked)
├── .gitignore              # Git ignore rules
├── reports/                # Auto-generated report files
└── README.md               # This file
```

## 🛡️ Security

- **API Keys**: Stored in `.env` file (not tracked by Git)
- **Environment Variables**: Used for all sensitive configuration
- **Gitignore**: Comprehensive rules to prevent accidental key exposure

## 🎯 Usage Flow

1. **Select** chaos experiment type (Pod/Network faults)
2. **Configure** YAML parameters  
3. **Confirm** with red warning dialog
4. **Monitor** live logs during execution
5. **Review** AI analysis and export reports

## 📋 Requirements

- Python 3.11+
- Google Gemini API key
- Terminal with Unicode support

## 🤝 Contributing

1. Never commit API keys or sensitive data
2. Use environment variables for configuration
3. Follow the existing code style
4. Test all functionality before submitting

## 📄 License

This project is for educational purposes as part of Dell Technologies Summer Internship 2025.

---

**Original Notes:**
072125
https://excalidraw.com/#room=2def662f3f55327ea69d,_Pn9vIXH-po11qV_9qajfQ