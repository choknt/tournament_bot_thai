# 🏆 Tournament Bot

A Discord bot for managing game tournaments — registration, scheduling, results, and more.  
Built with **discord.py v2**, **MongoDB (Motor)**, and **Pillow**.

---

## 📁 Project Structure

```
tournament_bot/
│
├── main.py                  ← Entry point — run this
├── config.py                ← All tunable settings (colours, sizes, channel IDs…)
├── db.py                    ← MongoDB helper layer
├── requirements.txt
├── .env                     ← Your secrets (not committed)
├── .env.example
│
├── fonts/                   ← Put bold.ttf and regular.ttf here
├── img/                     ← Put bg1.png bg2.png bg3.png here
│
├── cogs/
│   ├── events_group.py      ← Shared /events group definition
│   ├── send_regis.py        ← /send_regis
│   ├── staff_data.py        ← /staff_data
│   ├── config_cmd.py        ← /config set | edit | show | switch
│   ├── events_create.py     ← /events create
│   ├── events_edit.py       ← /events edit
│   ├── events_delete.py     ← /events delete
│   ├── events_show.py       ← /events show
│   └── events_results.py    ← /events results
│
└── utils/
    ├── events_helpers.py    ← Shared embed builders, StaffView, autocomplete
    └── image_gen.py         ← Pillow match-card generator
```

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure secrets
```bash
cp .env.example .env
```
Edit `.env`:
```
DISCORD_TOKEN=your_bot_token_here
MONGO_URI=mongodb://localhost:27017
```

### 3. Add your assets
- Place `bold.ttf` and `regular.ttf` in `fonts/`
- Place `bg1.png`, `bg2.png`, `bg3.png` in `img/`

### 4. Run
```bash
python main.py
```

---

## 🚀 Upload to GitHub

Run these commands inside the `tournament_bot/` folder:

```bash
# 1. Initialise git (first time only)
git init
git branch -M main

# 2. Connect to your GitHub repo
#    (create an empty repo on GitHub first — no README, no .gitignore)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# 3. Stage everything
git add .

# 4. First commit
git commit -m "feat: initial tournament bot"

# 5. Push
git push -u origin main
```

For every update after that:
```bash
git add .
git commit -m "your message here"
git push
```

---

## 📋 Commands

| Command | Who can use | Description |
|---|---|---|
| `/send_regis` | Manage Guild | Post registration embed |
| `/staff_data` | Anyone | Submit staff profile |
| `/config set` | Admin | Create tournament + full config |
| `/config edit` | Admin | Edit active config |
| `/config show` | Admin | View current config |
| `/config switch` | Admin | Switch active tournament |
| `/events create` | bot_op_role | Schedule a match |
| `/events edit` | bot_op_role | Edit a scheduled match |
| `/events delete` | bot_op_role | Delete a match |
| `/events show` | bot_op_role | View match details |
| `/events results` | bot_op_role | Post match results |
