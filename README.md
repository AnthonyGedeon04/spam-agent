# Gmail spam agent (LangChain + Claude)

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![LangChain](https://img.shields.io/badge/LangChain-1.x-1C3C3C?logo=langchain&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Haiku%204.5-D97757?logo=anthropic&logoColor=white)
![Gmail API](https://img.shields.io/badge/Gmail%20API-v1-EA4335?logo=gmail&logoColor=white)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS-lightgrey)
![Tests](https://img.shields.io/badge/tests-pytest-0A9EDC?logo=pytest&logoColor=white)

This program reads your new Gmail inbox mail, decides what each email is, and tidies it up:

| What the email is | What happens to it |
|---|---|
| Something you want (people, recruiters, receipts, codes, tickets) | Nothing, it stays in your inbox |
| Job alert | Gets the `jobs/internships` label and stays in your inbox |
| Newsletter or promo | Gets the `spam-agent/promo` label and is archived |
| Cold sales pitch | Gets the `spam-agent/cold-pitch` label and is archived |
| Phishing | Gets the `spam-agent/phishing` label and is archived |

Nothing is ever deleted. Archived mail is still in Gmail under its label.

Follow the steps below in order. You only do steps 1 to 6 once.

---

## Step 1. Make the folder on your computer

Create a folder called `spam-agent` somewhere easy to find, for example in your Documents folder.
Download every file from this project's `spam-agent` folder into it, keeping the same sub-folders.

When you are done, the folder must look exactly like this:

```
spam-agent/
├── README.md              (this guide)
├── requirements.txt       (list of Python libraries to install)
├── .env.example           (template for your API key)
├── .gitignore
├── spam_agent/            (the program itself)
│   ├── __init__.py
│   ├── classifier.py      (the LangChain + Claude part)
│   ├── config.py          (sender lists and settings you can edit)
│   ├── gmail.py           (talks to Gmail)
│   ├── main.py            (runs everything)
│   └── rules.py           (sender rules)
└── tests/
    └── test_agent.py
```

In the next steps you will add three files of your own to the **top level** of `spam-agent/` (next to `README.md`, not inside `spam_agent/`):

```
spam-agent/
├── .env                   (step 4: your Anthropic API key)
├── credentials.json       (step 5: your Google login file)
└── token.json             (created automatically the first time you run it)
```

Never share these three files or upload them anywhere. They give access to your Gmail and your Anthropic account.
Later, the program also creates `state.json` here, which remembers which emails it already handled.

> Files whose names start with a dot (`.env`, `.gitignore`, `.env.example`) are hidden by default.
> On Mac, press `Cmd + Shift + .` in Finder to show them. On Windows, in File Explorer choose View > Show > Hidden items.

## Step 2. Install Python

You need Python 3.10 or newer. Check with:

- Mac: open **Terminal** and type `python3 --version`
- Windows: open **PowerShell** and type `python --version`

If it says "not found" or a version below 3.10, install it from https://www.python.org/downloads/.
On Windows, tick **"Add python.exe to PATH"** on the first installer screen.

## Step 3. Install the libraries

Open Terminal (Mac) or PowerShell (Windows) and go into the folder. Replace the path with where you put it:

```bash
cd ~/Documents/spam-agent                # Mac
cd $HOME\Documents\spam-agent            # Windows
```

Create a private Python environment for this project and install the libraries:

**Mac**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

If Windows refuses to run `Activate.ps1`, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then try again.

You will see `(.venv)` at the start of the line. That means the environment is active.
Every time you open a new Terminal window to use the agent, `cd` into the folder and run the `activate` line again.

## Step 4. Get an Anthropic API key and put it in `.env`

1. Go to https://console.anthropic.com/, sign in, and add a small amount of credit under **Billing** (a few dollars lasts a long time with the default model).
2. Go to **API keys** > **Create key**, give it a name like `spam-agent`, and copy the key (it starts with `sk-ant-`).
3. Open Terminal (Mac) or PowerShell / Command Prompt (Windows) and go into your `spam-agent` folder, as in step 3 (skip this if you are already in it).
4. Create the `.env` file with one command. Replace `sk-ant-xxxx` with the key you copied:

   **Mac**
   ```bash
   echo "ANTHROPIC_API_KEY=sk-ant-xxxx" > .env
   ```

   **Windows, PowerShell** (the prompt starts with `PS`)
   ```powershell
   Set-Content -Path .env -Value "ANTHROPIC_API_KEY=sk-ant-xxxx" -Encoding ascii
   ```

   **Windows, Command Prompt** (the prompt looks like `C:\...>`; keep the parentheses)
   ```bat
   (echo ANTHROPIC_API_KEY=sk-ant-xxxx)> .env
   ```
5. Check it: `cat .env` (Mac), `Get-Content .env` (PowerShell) or `type .env` (Command Prompt) should print that one line.

`.env` is just a plain text file named exactly `.env` (nothing before the dot, no `.txt` after). The program reads your key from it automatically.
(`.env.example` shows the same format if you prefer to copy it and edit it by hand, but text editors like Notepad often save it as `.env.txt` by mistake, which won't work.)

## Step 5. Let the program use your Gmail (`credentials.json`)

Google requires you to create your own small "app" so the program can sign in as you.

1. Go to https://console.cloud.google.com/ and sign in with `anthonygedeon2004@gmail.com`.
2. At the top, click the project picker > **New project**. Name it `spam-agent` and click **Create**. Make sure it is selected.
3. Search for **Gmail API** in the top search bar, open it, and click **Enable**.
4. Open the left menu > **APIs & Services** > **OAuth consent screen** (it may be called **Google Auth Platform**).
   - Click **Get started**. App name: `spam-agent`. Support email: your Gmail.
   - Audience: **External**.
   - Contact email: your Gmail. Accept the policy and click **Create**.
5. Still there, open **Audience** > **Test users** > **Add users**, add `anthonygedeon2004@gmail.com`, and save.
6. Open **Clients** (or **Credentials** > **Create credentials** > **OAuth client ID**):
   - Application type: **Desktop app**. Name: `spam-agent`. Click **Create**.
   - Click **Download JSON**.
7. Rename the downloaded file to exactly `credentials.json` and move it into the top level of your `spam-agent` folder.

## Step 6. First run (dry run, changes nothing)

With `(.venv)` active and inside the folder, run:

```bash
python -m spam_agent.main
```

The first time, a browser window opens to sign in to Google:

- Choose your Gmail account.
- You will see **"Google hasn't verified this app"**. That is expected, because it is your own app. Click **Continue**.
- Allow access to Gmail.

The browser then says you can close it, and `token.json` appears in the folder.

The program prints a list like this and **does not change anything in Gmail**:

```
12 new message(s) matching 'in:inbox newer_than:2d'

DRY RUN (nothing changed in Gmail; add --apply to act)
- [job_alert       ] LinkedIn <jobalerts-noreply@linkedin.com> | 5 new jobs for Data Scientist
    label jobs/internships (rule): matched a sender rule
- [newsletter_promo] Zalando Privé <message@prive.zalando.fr>   | -70% this weekend
    label spam-agent/promo, archive (rule): matched a sender rule
- [keep            ] Marie <marie@example.com>                  | Dinner Saturday?
    leave as is (llm): Personal message from a friend.
```

Read through it. If something is wrong, see "Fixing mistakes" below before going further.
To check more mail at once: `python -m spam_agent.main --query "in:inbox newer_than:7d" --limit 100`

## Step 7. Let it actually sort your mail

When the dry run looks right, add `--apply`:

```bash
python -m spam_agent.main --apply
```

Now it labels and archives for real. Open Gmail and look at the new `spam-agent` labels in the left sidebar.

## Step 8 (optional). Run it automatically

**Mac**: run `crontab -e`, add this line (change the path), and save. It runs every 30 minutes while your Mac is awake:

```
*/30 * * * * cd ~/Documents/spam-agent && .venv/bin/python -m spam_agent.main --apply >> run.log 2>&1
```

**Windows**: open **Task Scheduler** > **Create Basic Task**:
1. Name: `Spam agent`. Trigger: **Daily**, recur every 1 day. Action: **Start a program**.
2. Program/script (with quotes): `"C:\Users\<you>\...\spam-agent\.venv\Scripts\pythonw.exe"`
   (`pythonw.exe` runs without flashing a black window.)
3. Add arguments: `-m spam_agent.main --apply`
4. Start in (no quotes): `C:\Users\<you>\...\spam-agent`
5. Tick "Open the Properties dialog when I click Finish", click Finish. In **Triggers** > Edit, tick **Repeat task every 30 minutes** for **Indefinitely**. On a laptop, in **Conditions**, untick "Start the task only if the computer is on AC power".
6. Test it: right-click the task > **Run**, then check Gmail.

**Important for scheduled runs**: while your Google app is in "Testing" mode, the sign-in expires every 7 days and scheduled runs silently stop. In Google Cloud, open **Audience** and click **Publish app** (no review is needed for your own use).

---

## Fixing mistakes

- **An email was archived by mistake**: in Gmail, open its `spam-agent/...` label, select it, and click **Move to inbox**.
- **A sender is always sorted wrong**: open `spam_agent/config.py` and add the sender to the right list:
  `ALWAYS_KEEP`, `JOB_ALERT_SENDERS`, `KNOWN_PROMO_SENDERS` or `KNOWN_COLD_PITCH_SENDERS`.
  Use the full address (`news@shop.com`) or a whole domain with `@` in front (`@shop.com`).
- **Re-check emails it already handled**: add `--reprocess`.

## Common errors

| Message | What to do |
|---|---|
| `ANTHROPIC_API_KEY is missing` | `.env` is not in the top level of the folder, or got saved as `.env.txt`. Redo step 4 with the command. |
| `credentials.json is missing` | Put the Google file in the top level of the folder with exactly that name (step 5). |
| `No module named spam_agent` | You are not inside the `spam-agent` folder. `cd` into it first. |
| `No module named langchain_anthropic` | The environment is not active. Run the `activate` line from step 3. |
| `access_denied` or `Error 403` in the browser | Your Gmail is not added as a test user (step 5.5). |
| `invalid_grant` or `Token has been expired` | Delete `token.json` and run again to sign in. While the Google app is in "Testing" mode this happens every 7 days. To stop it, open **Audience** in Google Cloud and click **Publish app**. |
| `credit balance is too low` | Add credit in the Anthropic console (step 4.1). |

## How it decides (for the curious)

1. **Sender rules** in `spam_agent/config.py`, built from a survey of your inbox, sort known senders without calling the model.
2. **Claude through LangChain** (`spam_agent/classifier.py`) handles every other email and returns a category, a confidence score, and a one-line reason.
3. **Safety nets**: a junk verdict below 0.75 confidence keeps the email; an error keeps the email; something that looks like a login code is labeled but left in the inbox; a conversation that also contains an email worth keeping is not moved.

The default model is Claude Haiku 4.5, the cheapest and fastest. To change it, add `SPAM_AGENT_MODEL=...` to `.env`.

To run the offline tests (no Gmail or API calls): `pip install pytest`, then `python -m pytest -q tests`.
