
from flask import Flask, request, redirect, render_template_string
import sqlite3
from datetime import date, timedelta

app = Flask(__name__)
DB = "study_balance.db"

# ---------- Database ----------

def setup():
    with sqlite3.connect(DB) as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                subject TEXT NOT NULL,
                deadline TEXT NOT NULL,
                priority TEXT NOT NULL,
                done INTEGER DEFAULT 0
            )
        """)

setup()

# ---------- Website design ----------

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>AI Study-Work Balance Assistant</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f2f4fb;
            color: #222;
            margin: 0;
        }
        header {
            background: linear-gradient(120deg,#3730a3,#818cf8);
            color: white;
            padding: 28px 7%;
        }
        header h1 { margin-bottom: 8px; }
        main { max-width: 950px; margin: 25px auto; padding: 0 16px; }
        .panel {
            background: white;
            padding: 22px;
            margin-bottom: 20px;
            border-radius: 14px;
            box-shadow: 0 3px 12px #0000000b;
        }
        .stats { display: flex; gap: 12px; flex-wrap: wrap; }
        .stat {
            flex: 1;
            min-width: 100px;
            background: #eef2ff;
            padding: 16px;
            border-radius: 10px;
        }
        .stat strong { display: block; font-size: 27px; color: #4338ca; }
        input, select {
            box-sizing: border-box;
            width: 100%;
            padding: 11px;
            margin: 6px 0 14px;
            border: 1px solid #ccc;
            border-radius: 7px;
        }
        button {
            border: 0;
            border-radius: 7px;
            padding: 10px 14px;
            background: #4f46e5;
            color: white;
            cursor: pointer;
            margin: 3px;
        }
        .delete { background: #dc2626; }
        .task {
            border-bottom: 1px solid #eee;
            padding: 13px 0;
        }
        .done { color: #888; text-decoration: line-through; }
        .tip {
            background: #eef2ff;
            padding: 12px;
            margin: 10px 0;
            border-left: 4px solid #4f46e5;
            border-radius: 5px;
        }
        .muted { color: #666; font-size: 14px; }
    </style>
</head>
<body>
<header>
    <h1>📚 AI Study-Work Balance Assistant</h1>
    <p>Manage your work, studies and assignments in one place.</p>
</header>
<main>

<section class="panel">
    <h2>📊 My Dashboard</h2>
    <div class="stats">
        <div class="stat">Total tasks<strong>{{ total }}</strong></div>
        <div class="stat">Pending<strong>{{ pending }}</strong></div>
        <div class="stat">Completed<strong>{{ completed }}</strong></div>
    </div>
</section>

<section class="panel">
    <h2>📅 Study Timetable Generator</h2>
    <form method="post" action="/plan">
        <label>Available study hours per day</label>
        <input type="number" name="hours" min="0.5" max="16"
               step="0.5" value="2" required>
        <label>Work hours per day</label>
        <input type="number" name="work" min="0" max="24"
               step="0.5" value="8" required>
        <label>Subjects (separate with commas)</label>
        <input name="subjects"
       value="Mathematics, Python, Networks"
       placeholder="Enter your subjects"
       required>
        <button type="submit">Generate Timetable</button>
    </form>

    {% if timetable is defined %}
        <h3>Your Study Plan</h3>
        {% for item in timetable %}
            <div class="tip">
                <strong>{{ item.subject }}</strong><br>
                {{ item.start }} - {{ item.end }}
                ({{ item.minutes }} minutes)
            </div>
        {% endfor %}
        <p class="muted">Example schedule starts at 6:00 PM.
        Adjust it to fit your actual work shift.</p>
    {% endif %}
</section>

<section class="panel">
    <h2>📝 Add Assignment or Task</h2>
    <form method="post" action="/add">
        <label>Task name</label>
        <input name="title" maxlength="120"
               placeholder="Complete mathematics assignment" required>
        <label>Subject</label>
        <input name="subject" maxlength="80"
               placeholder="Discrete Mathematics" required>
        <label>Deadline</label>
        <input type="date" name="deadline"
               min="{{ today }}" required>
        <label>Priority</label>
        <select name="priority">
            <option>High</option>
            <option selected>Medium</option>
            <option>Low</option>
        </select>
        <button type="submit">Add Task</button>
    </form>
</section>

<section class="panel">
    <h2>📋 My Tasks and Deadlines</h2>
    {% for task in tasks %}
        <div class="task">
            <strong class="{% if task[5] %}done{% endif %}">
                {{ task[1] }}
            </strong>
            <p>{{ task[2] }} | Deadline: {{ task[3] }}</p>
            <p>Priority: {{ task[4] }}
            {% if task[3] < today and not task[5] %}
                | ⚠ OVERDUE
            {% endif %}
            </p>
            <form method="post" action="/toggle/{{ task[0] }}"
                  style="display:inline">
                <button type="submit">
                    {% if task[5] %}Undo{% else %}Complete{% endif %}
                </button>
            </form>
            <form method="post" action="/delete/{{ task[0] }}"
                  style="display:inline">
                <button class="delete" type="submit">Delete</button>
            </form>
        </div>
    {% else %}
        <p>No tasks yet. Add your first assignment above!</p>
    {% endfor %}
</section>

<section class="panel">
    <h2>🤖 AI Study Recommendations</h2>
    {% for tip in tips %}
        <div class="tip">💡 {{ tip }}</div>
    {% endfor %}
    <p class="muted">Recommendations use Python rules, not a trained AI model.</p>
</section>

</main>
</body>
</html>
"""

# ---------- Main dashboard ----------

def read_tasks():
    with sqlite3.connect(DB) as con:
        return con.execute(
            "SELECT * FROM tasks ORDER BY done ASC, deadline ASC"
        ).fetchall()

def recommendations(tasks):
    today = date.today()
    pending = [t for t in tasks if not t[5]]
    tips = []

    overdue = [t for t in pending if t[3] < today.isoformat()]
    urgent = [
        t for t in pending
        if today.isoformat() <= t[3]
        <= (today + timedelta(days=2)).isoformat()
    ]

    if overdue:
        tips.append(
            f"You have {len(overdue)} overdue task(s). "
            "Review them and make a realistic catch-up plan."
        )
    if urgent:
        tips.append(
            f"{len(urgent)} task(s) have deadlines within two days. "
            "Prioritize these first."
        )
    if not pending:
        tips.append("No pending tasks! Use some time for revision.")
    else:
        tips.append(
            "Try focused 25–50 minute study sessions with short breaks."
        )
        tips.append(
            "Start with a high-priority assignment or your nearest deadline."
        )

    return tips

@app.route("/")
def home():
    tasks = read_tasks()
    return render_template_string(
        HTML,
        tasks=tasks,
        total=len(tasks),
        pending=sum(not t[5] for t in tasks),
        completed=sum(t[5] for t in tasks),
        today=date.today().isoformat(),
        tips=recommendations(tasks)
    )

# ---------- Add task ----------

@app.route("/add", methods=["POST"])
def add():
    title = request.form.get("title", "").strip()
    subject = request.form.get("subject", "").strip()
    deadline = request.form.get("deadline", "")
    priority = request.form.get("priority", "Medium")

    try:
        date.fromisoformat(deadline)
        valid_date = True
    except ValueError:
        valid_date = False

    if (title and subject and len(title) <= 120
            and len(subject) <= 80 and valid_date
            and deadline >= date.today().isoformat()
            and priority in ("High", "Medium", "Low")):
        with sqlite3.connect(DB) as con:
            con.execute(
                """INSERT INTO tasks(title, subject, deadline, priority)
                   VALUES (?, ?, ?, ?)""",
                (title, subject, deadline, priority)
            )
    return redirect("/")

# ---------- Complete or undo task ----------

@app.route("/toggle/<int:task_id>", methods=["POST"])
def toggle(task_id):
    with sqlite3.connect(DB) as con:
        con.execute(
            """UPDATE tasks SET done = 1 - done WHERE id = ?""",
            (task_id,)
        )
    return redirect("/")

# ---------- Delete task ----------

@app.route("/delete/<int:task_id>", methods=["POST"])
def delete(task_id):
    with sqlite3.connect(DB) as con:
        con.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return redirect("/")

# ---------- Timetable generator ----------

@app.route("/plan", methods=["POST"])
def plan():
    try:
        hours = float(request.form.get("hours", 2))
        work = float(request.form.get("work", 8))
    except ValueError:
        return redirect("/")

    if not (0 < hours <= 16 and 0 <= work <= 24):
        return redirect("/")

    subjects = [
        s.strip()
        for s in request.form.get("subjects", "").split(",")
        if s.strip()
    ][:10]

    if not subjects:
        return redirect("/")

    remaining = int(hours * 60)
    clock = 18 * 60
    timetable = []

    for subject in subjects:
        if remaining < 15:
            break

        minutes = min(50, remaining)
        end = clock + minutes

        def format_time(value):
            value %= 1440
            suffix = "AM" if value < 720 else "PM"
            h = (value // 60) % 12 or 12
            return f"{h}:{value % 60:02d} {suffix}"

        timetable.append({
            "subject": subject,
            "start": format_time(clock),
            "end": format_time(end),
            "minutes": minutes
        })

        remaining -= minutes + 10
        clock = end + 10

    tasks = read_tasks()
    return render_template_string(
        HTML,
        tasks=tasks,
        total=len(tasks),
        pending=sum(not t[5] for t in tasks),
        completed=sum(t[5] for t in tasks),
        today=date.today().isoformat(),
        tips=recommendations(tasks),
        timetable=timetable
    )

if __name__ == "__main__":
    app.run(debug=True)
