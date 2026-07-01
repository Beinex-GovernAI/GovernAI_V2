# GovernAI UI Upgrade — Complete Guide

## What We Are Doing
Upgrading all 5 pages to a unified dark theme. No emojis, no hardcoded colors, consistent status badges and typography across all pages.

---

## Step 1: Create the Assets Folder and CSS File

Inside your `governai/` folder, create a new folder called `assets`.
Inside `assets/`, create a file called `styles.css`.
Paste the following into `styles.css`:

```css
/* GovernAI — Global Stylesheet */

/* ── Base ── */
[data-testid="stAppViewContainer"] {
    background-color: #0D1117;
    color: #E6EDF3;
}

[data-testid="stSidebar"] {
    background-color: #0D1117;
    border-right: 1px solid #21262D;
}

[data-testid="stSidebar"] * {
    color: #E6EDF3 !important;
}

/* ── Typography ── */
h1 {
    font-size: 1.8rem !important;
    font-weight: 700 !important;
    letter-spacing: -0.5px !important;
    color: #E6EDF3 !important;
    border-bottom: 1px solid #21262D;
    padding-bottom: 0.5rem;
    margin-bottom: 1.5rem !important;
}

h2, h3 {
    color: #E6EDF3 !important;
    font-weight: 600 !important;
}

/* ── Metric Cards ── */
[data-testid="metric-container"] {
    background-color: #161B22;
    border: 1px solid #21262D;
    border-left: 3px solid #00C4B4;
    border-radius: 6px;
    padding: 1rem !important;
}

[data-testid="metric-container"] label {
    color: #7D8590 !important;
    font-size: 0.75rem !important;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: #E6EDF3 !important;
    font-size: 2rem !important;
    font-weight: 700 !important;
}

/* ── Cards / Expanders ── */
[data-testid="stExpander"] {
    background-color: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 6px !important;
}

[data-testid="stExpander"] summary {
    color: #E6EDF3 !important;
    font-weight: 500 !important;
}

/* ── Buttons ── */
[data-testid="stButton"] button {
    background-color: #00C4B4 !important;
    color: #0D1117 !important;
    border: none !important;
    border-radius: 4px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    padding: 0.4rem 1.2rem !important;
    transition: opacity 0.15s ease !important;
}

[data-testid="stButton"] button:hover {
    opacity: 0.85 !important;
}

/* ── Selectbox / Inputs ── */
[data-testid="stSelectbox"] > div,
[data-testid="stTextInput"] > div > div,
[data-testid="stTextArea"] > div > div {
    background-color: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 4px !important;
    color: #E6EDF3 !important;
}

/* ── Tables / Dataframes ── */
[data-testid="stDataFrame"] {
    background-color: #161B22 !important;
    border: 1px solid #21262D !important;
    border-radius: 6px !important;
}

/* ── Status Badges ── */
.status-compliant {
    display: inline-block;
    background-color: #1A3A2A;
    color: #3FB950;
    border: 1px solid #3FB950;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.status-noncompliant {
    display: inline-block;
    background-color: #3A1A1A;
    color: #E05252;
    border: 1px solid #E05252;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.status-atrisk {
    display: inline-block;
    background-color: #3A2A0A;
    color: #F0A500;
    border: 1px solid #F0A500;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

.status-pending {
    display: inline-block;
    background-color: #1A1F2A;
    color: #7D8590;
    border: 1px solid #7D8590;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.3px;
}

/* ── Risk Tier Badges ── */
.tier-high {
    display: inline-block;
    background-color: #3A1A1A;
    color: #E05252;
    border-left: 3px solid #E05252;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

.tier-limited {
    display: inline-block;
    background-color: #3A2A0A;
    color: #F0A500;
    border-left: 3px solid #F0A500;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

.tier-minimal {
    display: inline-block;
    background-color: #1A3A2A;
    color: #3FB950;
    border-left: 3px solid #3FB950;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

.tier-pending {
    display: inline-block;
    background-color: #1A1F2A;
    color: #7D8590;
    border-left: 3px solid #7D8590;
    border-radius: 4px;
    padding: 2px 10px;
    font-size: 0.78rem;
    font-weight: 600;
}

/* ── Section Label ── */
.section-label {
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    color: #7D8590;
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
}

/* ── Info/Alert Boxes ── */
[data-testid="stInfo"] {
    background-color: #161B22 !important;
    border-left: 3px solid #00C4B4 !important;
    color: #E6EDF3 !important;
    border-radius: 4px !important;
}

[data-testid="stWarning"] {
    background-color: #2A2010 !important;
    border-left: 3px solid #F0A500 !important;
    color: #E6EDF3 !important;
    border-radius: 4px !important;
}

[data-testid="stError"] {
    background-color: #2A1010 !important;
    border-left: 3px solid #E05252 !important;
    color: #E6EDF3 !important;
    border-radius: 4px !important;
}

[data-testid="stSuccess"] {
    background-color: #102A15 !important;
    border-left: 3px solid #3FB950 !important;
    color: #E6EDF3 !important;
    border-radius: 4px !important;
}

/* ── Progress Bar ── */
[data-testid="stProgress"] > div > div {
    background-color: #00C4B4 !important;
}

/* ── File Uploader ── */
[data-testid="stFileUploader"] {
    background-color: #161B22 !important;
    border: 1px dashed #21262D !important;
    border-radius: 6px !important;
}

/* ── Tabs ── */
[data-testid="stTabs"] [role="tab"] {
    color: #7D8590 !important;
    font-weight: 500 !important;
}

[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: #00C4B4 !important;
    border-bottom: 2px solid #00C4B4 !important;
}

/* ── Sidebar Navigation ── */
[data-testid="stSidebarNav"] a {
    color: #7D8590 !important;
    font-size: 0.85rem !important;
}

[data-testid="stSidebarNav"] a:hover,
[data-testid="stSidebarNav"] a[aria-current="page"] {
    color: #00C4B4 !important;
}
```

---

## Step 2: How to Load CSS in Every Page

Every page file must load the shared CSS. Add this block right after `st.set_page_config(...)` in each page:

```python
import os

def load_css():
    css_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()
```

For `app.py` specifically (since it's in the root, not inside `pages/`), use this path instead:

```python
def load_css():
    css_path = os.path.join(os.path.dirname(__file__), 'assets', 'styles.css')
    with open(css_path) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

load_css()
```

---

## Step 3: Status Badge Usage

Never use plain text for status. Always use these badges:

```python
# Compliance Status badges
st.markdown('<span class="status-compliant">Compliant</span>', unsafe_allow_html=True)
st.markdown('<span class="status-noncompliant">Non-Compliant</span>', unsafe_allow_html=True)
st.markdown('<span class="status-atrisk">At Risk</span>', unsafe_allow_html=True)
st.markdown('<span class="status-pending">Pending</span>', unsafe_allow_html=True)

# Risk Tier badges
st.markdown('<span class="tier-high">High</span>', unsafe_allow_html=True)
st.markdown('<span class="tier-limited">Limited</span>', unsafe_allow_html=True)
st.markdown('<span class="tier-minimal">Minimal</span>', unsafe_allow_html=True)
st.markdown('<span class="tier-pending">Pending</span>', unsafe_allow_html=True)

# Section labels
st.markdown('<p class="section-label">Section Title Here</p>', unsafe_allow_html=True)
```

---

## Step 4: Design Rules

1. No emojis anywhere in the UI
2. No hardcoded colors in Python — all colors come from `styles.css`
3. Status always uses badges, never plain `st.write()` text
4. Coordinate in group chat before touching `app.py` or `styles.css`

---

## Step 5: Design Tokens Reference

| Token | Value | Usage |
|---|---|---|
| Background | `#0D1117` | Page background |
| Surface | `#161B22` | Cards, expanders |
| Border | `#21262D` | All borders |
| Accent | `#00C4B4` | Buttons, active states |
| Text Primary | `#E6EDF3` | Headings, body |
| Text Muted | `#7D8590` | Labels, secondary |
| Success | `#3FB950` | Compliant |
| Warning | `#F0A500` | At Risk |
| Danger | `#E05252` | Non-Compliant |

---

## Step 6: Task Split

### Grishma
- `pages/1_Dashboard.py`
- `pages/4_Compliance.py`
- `pages/5_Monitoring.py`

### Abhay
- `pages/2_Inventory.py`
- `pages/3_Risk_Setup.py`
- `app.py`

---

## Step 7: Git Workflow

```bash
# Before starting
git checkout main
git pull origin main
git checkout -b yourname/ui-upgrade

# After finishing your pages
git add .
git commit -m "UI upgrade: [your pages]"
git push origin yourname/ui-upgrade
```

Then open a Pull Request on GitHub for Abhay to review and merge.

---

## File Structure After Setup

```
governai/
├── assets/
│   └── styles.css          ← shared stylesheet
├── pages/
│   ├── 1_Dashboard.py      ← Grishma
│   ├── 2_Inventory.py      ← Abhay
│   ├── 3_Risk_Setup.py     ← Abhay
│   ├── 4_Compliance.py     ← Grishma
│   └── 5_Monitoring.py     ← Grishma
└── app.py                  ← Abhay
```