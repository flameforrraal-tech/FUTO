# 🎓 School Bot System
### Main Bot + Department Bots for Federal Polytechnic

---

## How The System Works

```
Student sends /start to Main Bot
        ↓
Main Bot checks: Did they join the General Channel?
        ↓ (if not joined → sends them to join first)
Main Bot asks: What is your full name?
        ↓
Main Bot shows: 9 Schools to choose from
        ↓
Main Bot shows: Departments in that school
        ↓
Main Bot sends: Link to their Department Bot ✅
        ↓
Student opens Department Bot and gets:
  📂 Lecture notes, past questions, assignments
  🤖 AI academic assistant (Gemini AI)
  📣 Department announcements
  📌 Pinned department info
```

---

## STEP 1 — Create All Your Bots on Telegram

You need to create bots. Each bot is just a username — it is free and takes 30 seconds.

1. Open Telegram → Search for **@BotFather**
2. Send `/newbot`
3. Give it a name (e.g. `FPN Computer Science Bot`)
4. Give it a username ending in `bot` (e.g. `fpn_computer_sci_bot`)
5. Copy the **TOKEN** it gives you

**You need one bot for each thing:**

| Bot | Name example | Purpose |
|-----|-------------|---------|
| Main Bot | `fpn_main_bot` | Registers all students, sends them to dept |
| SICT - Computer Science | `fpn_comp_sci_bot` | Computer Science students |
| SICT - Information Tech | `fpn_info_tech_bot` | Info Tech students |
| SEET - Civil Eng | `fpn_civil_bot` | Civil Engineering students |
| ... and so on for each department | | |

**You do NOT have to create all departments at once.**
Start with just the Main Bot and a few department bots.
The main bot will say "coming soon" for departments without a bot yet.

---

## STEP 2 — Create Your General Channel

1. Open Telegram → tap the pencil/compose icon → New Channel
2. Give it a name like `Federal Polytechnic Students`
3. Make it **Public** and give it a username like `@fpn_students`
4. Add your Main Bot as an **Admin** of the channel
   (go to channel → Members → Add Admin → search your bot)
5. Copy the channel link e.g. `https://t.me/fpn_students`

---

## STEP 3 — Get Your Telegram User ID

1. Open Telegram → Search **@userinfobot**
2. Send it any message
3. It replies with your **ID** — a number like `123456789`
4. This makes you the Super Admin of all bots

---

## STEP 4 — Get Your Gemini AI Key (Free)

1. Go to **aistudio.google.com**
2. Sign in with Google
3. Click **Get API Key** → **Create API Key**
4. Copy it — looks like `AIzaSyXXXXXXXXXX`

---

## STEP 5 — Add Department Bot Links to the Code

Once you have created your department bot usernames, open `shared/schools.py` and fill in the links.

Find the section that says `DEPT_BOT_LINKS` and add your bot links:

```python
DEPT_BOT_LINKS = {
    "computer_sci":  "https://t.me/fpn_comp_sci_bot",
    "electrical":    "https://t.me/fpn_electrical_bot",
    "biochemistry":  "https://t.me/fpn_biochem_bot",
    # Leave others as None if not created yet
    "civil":         None,   # coming soon
}
```

---

## STEP 6 — Deploy on Render.com

You will deploy each bot separately on Render. Each one is free.

### Deploy the Main Bot

1. Push all files to GitHub (create account → New Repo → upload files)
2. Go to **render.com** → New → **Web Service**
3. Connect your GitHub repo
4. Settings:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python main_bot/main_bot.py`
5. Add these Environment Variables:

| Key | Value |
|-----|-------|
| `MAIN_BOT_TOKEN` | Token from BotFather for main bot |
| `SUPER_ADMIN_ID` | Your Telegram user ID |
| `SCHOOL_NAME` | Federal Polytechnic Nekede |
| `GENERAL_CHANNEL_ID` | @yourschoolchannel |
| `GENERAL_CHANNEL_LINK` | https://t.me/yourschoolchannel |
| `MAIN_BOT_LINK` | https://t.me/your_main_bot |
| `GEMINI_API_KEY` | Your Gemini AI key |

6. Click **Create Web Service** → your main bot is live!

---

### Deploy Each Department Bot

For EACH department bot, create a new Render Web Service with:

- Build Command: `pip install -r requirements.txt`
- Start Command: `python dept_bot/dept_bot.py`

Environment Variables:

| Key | Value |
|-----|-------|
| `DEPT_BOT_TOKEN` | Token for THIS department bot |
| `DEPT_KEY` | Department key (see table below) |
| `SCHOOL_KEY` | School key (see table below) |
| `SUPER_ADMIN_ID` | Your Telegram user ID |
| `SCHOOL_NAME` | Federal Polytechnic Nekede |
| `GEMINI_API_KEY` | Your Gemini AI key |
| `MAIN_BOT_LINK` | https://t.me/your_main_bot |

---

## DEPT_KEY and SCHOOL_KEY Reference

Use exactly these values when setting up each department bot:

### SAAT — School of Agriculture And Agricultural Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Crop Production & Horticulture | `crop` | `saat` |
| Soil Science & Land Management | `soil` | `saat` |
| Animal Production & Health | `animal` | `saat` |
| Agricultural Extension & Management | `agric_ext` | `saat` |
| Food Technology | `food_tech` | `saat` |
| Agricultural Economics | `agric_econ` | `saat` |

### SOHT — School of Health Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Medical Laboratory Science | `med_lab` | `soht` |
| Health Information Management | `health_info` | `soht` |
| Dental Technology | `dental_tech` | `soht` |
| Optometry | `optometry` | `soht` |
| Radiography | `radiology` | `soht` |
| Nutrition & Dietetics | `nutrition` | `soht` |
| Environmental Health Technology | `environ_hlth` | `soht` |

### SBMS — School of Basic Medical Science
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Anatomy | `anatomy` | `sbms` |
| Physiology | `physiology` | `sbms` |
| Biochemistry | `biochemistry` | `sbms` |
| Microbiology | `microbiology` | `sbms` |
| Pharmacology | `pharmacology` | `sbms` |

### SICT — School of Information and Communication Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Computer Science | `computer_sci` | `sict` |
| Information Technology | `info_tech` | `sict` |
| Cyber Security | `cyber_security` | `sict` |
| Software Engineering | `software_eng` | `sict` |
| Data Management Technology | `data_mgt` | `sict` |
| Library & Information Science | `library_info` | `sict` |

### SOBS — School of Biological Science
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Biology | `biology` | `sobs` |
| Botany | `botany` | `sobs` |
| Zoology | `zoology` | `sobs` |
| Genetics & Biotechnology | `genetics` | `sobs` |
| Ecology & Environmental Biology | `ecology` | `sobs` |

### SLIT — School of Logistics and Innovation Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Logistics & Supply Chain Management | `logistics` | `slit` |
| Procurement & Supply Chain | `procurement` | `slit` |
| Transport Management | `transport` | `slit` |
| Innovation & Entrepreneurship | `innovation` | `slit` |
| Business Management Technology | `business_mgt` | `slit` |

### SEET — School of Engineering and Engineering Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Civil Engineering Technology | `civil` | `seet` |
| Mechanical Engineering Technology | `mechanical` | `seet` |
| Chemical Engineering Technology | `chemical` | `seet` |
| Industrial & Production Engineering | `industrial` | `seet` |
| Petroleum Engineering Technology | `petroleum` | `seet` |
| Welding & Fabrication Technology | `welding` | `seet` |
| Polymer Technology | `polymer` | `seet` |

### SOPS — School of Physical Science
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Physics | `physics` | `sops` |
| Chemistry | `chemistry` | `sops` |
| Mathematics & Statistics | `mathematics` | `sops` |
| Geology & Mineral Science | `geology` | `sops` |
| Science Laboratory Technology | `science_lab` | `sops` |

### SESET — School of Electrical Systems and Engineering Technology
| Department | DEPT_KEY | SCHOOL_KEY |
|------------|----------|------------|
| Electrical Engineering Technology | `electrical` | `seset` |
| Electronics Engineering Technology | `electronics` | `seset` |
| Telecommunications Engineering | `telecomms` | `seset` |
| Computer Engineering Technology | `computer_eng` | `seset` |
| Instrumentation & Control Technology | `instrumentation` | `seset` |
| Mechatronics Engineering Technology | `mechatronics` | `seset` |

---

## ADMIN COMMANDS

### In the Main Bot
| Command | What it does |
|---------|-------------|
| /admin | View stats (students per school) |
| /ban USER_ID | Ban a student |
| /unban USER_ID | Unban a student |
| /broadcast | Send a message to ALL students |

### In Each Department Bot
| Command | What it does |
|---------|-------------|
| /broadcast | Send message to all department members |
| /ban USER_ID | Ban from this department bot |
| /unban USER_ID | Unban from this department bot |

---

## STUDENT COMMANDS

### Main Bot
| Command | What it does |
|---------|-------------|
| /start | Register or view your info |
| /mystatus | Check your registration details |
| /change | Change your school or department |
| /help | Show help |

### Department Bot
| Command | What it does |
|---------|-------------|
| /start | Open main menu |
| /request | Request upload access |
| /help | Show help |
| /cancel | Cancel current action |

---

## FILE STRUCTURE

```
schoolbot2/
├── shared/
│   ├── schools.py    ← All 9 schools + departments + bot links (EDIT THIS)
│   └── db.py         ← Data storage helpers
├── main_bot/
│   └── main_bot.py   ← Main registration bot
├── dept_bot/
│   ├── dept_bot.py   ← Department bot (same file for ALL departments)
│   └── dept_ai.py    ← Gemini AI for department bots
├── requirements.txt
├── .env.example
└── README.md
```

---

## IF SOMETHING GOES WRONG

| Problem | Fix |
|---------|-----|
| Main bot not responding | Check Render — make sure it is Running |
| "Channel check failed" | Make sure your bot is an Admin of the channel |
| Bot gives wrong department link | Update DEPT_BOT_LINKS in shared/schools.py |
| AI not answering | Check GEMINI_API_KEY is correct in Render env vars |
| "DEPT_KEY not set" | Add DEPT_KEY to that Render service's env variables |
| Department says "coming soon" | Add the bot link to DEPT_BOT_LINKS in schools.py |
