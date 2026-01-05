# ENBD & EIB Pipeline Dashboard

A professional Streamlit dashboard for monitoring collections pipeline and agent performance metrics for ENBD and EIB clients.

## Features

- 🔐 User authentication with admin/viewer roles
- 📊 Real-time dashboards with interactive charts
- 💾 Data upload and processing for masterlist data
- 📈 Agent performance metrics and WOA tracking
- 💳 Payment and PTP (Promise To Pay) monitoring
- 📋 Multiple client support (ENBD & EIB)

## Local Development

### Prerequisites

- Python 3.8+
- pip or conda

### Installation

1. Clone the repository:
```bash
git clone https://github.com/ctbonifacio/streamlit-dashboard.py.git
cd streamlit-dashboard.py
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the app:
```bash
streamlit run streamlit-dashboard.py
```

The app will be available at `http://localhost:8501`

## Deployment to Streamlit Cloud

### Option 1: Deploy with Streamlit Cloud (Recommended)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click "New app"
4. Select your repository and branch
5. Set main file path to `streamlit-dashboard.py`
6. Click "Deploy"

### Option 2: Deploy to Heroku

1. Create `Procfile`:
```
web: streamlit run streamlit-dashboard.py --server.port $PORT --server.address 0.0.0.0
```

2. Deploy:
```bash
heroku create your-app-name
git push heroku main
```

## Default Credentials

```
Username: ctbonifacio
Password: Generated dynamically (mmddyyyy0 + attempt count)
```

## Support

For issues or questions, please create an issue on GitHub.
