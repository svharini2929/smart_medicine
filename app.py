from flask import Flask, render_template, request, redirect, url_for, session, flash
import json
import os
from datetime import datetime, date

app = Flask(__name__)
app.secret_key = "smart_medicine_secret_demo"

USERS_FILE = "users.json"
MEDICINES_FILE = "medicines.json"
APPOINTMENTS_FILE = "appointments.json"
CONTACTS_FILE = "contacts.json"
HISTORY_FILE = "history.json"


def read_json(file_path, default_data):
    if not os.path.exists(file_path):
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(default_data, f, indent=4)
        return default_data

    with open(file_path, "r", encoding="utf-8") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return default_data


def write_json(file_path, data):
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def initialize_files():
    read_json(USERS_FILE, [])
    read_json(MEDICINES_FILE, [])
    read_json(APPOINTMENTS_FILE, [])
    read_json(CONTACTS_FILE, [])
    read_json(HISTORY_FILE, [])


def is_logged_in():
    return "username" in session


def today_day_name():
    return datetime.now().strftime("%A")


def today_date():
    return date.today().isoformat()


@app.route("/")
def home():
    if is_logged_in():
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if is_logged_in():
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        users = read_json(USERS_FILE, [])

        for user in users:
            if user["username"] == username and user["password"] == password:
                session["username"] = user["username"]
                session["role"] = user.get("role", "patient")
                flash("Sign in successful.", "success")
                return redirect(url_for("dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Signed out successfully.", "success")
    return redirect(url_for("login"))


@app.route("/dashboard")
def dashboard():
    if not is_logged_in():
        return redirect(url_for("login"))

    medicines = read_json(MEDICINES_FILE, [])
    appointments = read_json(APPOINTMENTS_FILE, [])
    contacts = read_json(CONTACTS_FILE, [])
    history = read_json(HISTORY_FILE, [])

    current_day = today_day_name()
    current_date = today_date()

    todays_medicines = [m for m in medicines if m["day"] == current_day]

    today_history = [h for h in history if h["date"] == current_date]
    history_map = {h["medicine_id"]: h["status"] for h in today_history}

    for med in todays_medicines:
        med["status_today"] = history_map.get(med["id"], "Pending")

    total_today = len(todays_medicines)
    taken_count = sum(1 for m in todays_medicines if m["status_today"] == "Taken")
    skipped_count = sum(1 for m in todays_medicines if m["status_today"] == "Skipped")
    pending_count = sum(1 for m in todays_medicines if m["status_today"] == "Pending")

    appointments = sorted(appointments, key=lambda x: (x["date"], x["time"]))
    history = sorted(history, key=lambda x: (x["date"], x["updated_at"]), reverse=True)

    return render_template(
        "dashboard.html",
        username=session["username"],
        role=session.get("role", "patient"),
        today_name=current_day,
        today_date_value=current_date,
        medicines=todays_medicines,
        total_today=total_today,
        taken_count=taken_count,
        skipped_count=skipped_count,
        pending_count=pending_count,
        appointments=appointments,
        contacts=contacts,
        history=history
    )


@app.route("/mark/<int:medicine_id>/<status>", methods=["POST"])
def mark_status(medicine_id, status):
    if not is_logged_in():
        return redirect(url_for("login"))

    if status not in ["Taken", "Skipped"]:
        flash("Invalid status.", "danger")
        return redirect(url_for("dashboard"))

    medicines = read_json(MEDICINES_FILE, [])
    history = read_json(HISTORY_FILE, [])
    current_date = today_date()
    current_time = datetime.now().strftime("%H:%M:%S")

    medicine = next((m for m in medicines if m["id"] == medicine_id), None)
    if not medicine:
        flash("Medicine not found.", "danger")
        return redirect(url_for("dashboard"))

    existing = next(
        (h for h in history if h["medicine_id"] == medicine_id and h["date"] == current_date),
        None
    )

    if existing:
        existing["status"] = status
        existing["updated_at"] = current_time
    else:
        history.append({
            "medicine_id": medicine["id"],
            "medicine_name": medicine["name"],
            "date": current_date,
            "time": medicine["time"],
            "status": status,
            "updated_at": current_time
        })

    write_json(HISTORY_FILE, history)
    flash(f'{medicine["name"]} marked as {status}.', "success")
    return redirect(url_for("dashboard"))


@app.route("/add_medicine", methods=["POST"])
def add_medicine():
    if not is_logged_in():
        return redirect(url_for("login"))

    name = request.form.get("name", "").strip()
    dosage = request.form.get("dosage", "").strip()
    day = request.form.get("day", "").strip()
    time_value = request.form.get("time", "").strip()
    note = request.form.get("note", "").strip()

    if not all([name, dosage, day, time_value]):
        flash("Fill all medicine fields.", "danger")
        return redirect(url_for("dashboard"))

    medicines = read_json(MEDICINES_FILE, [])
    new_id = max([m["id"] for m in medicines], default=0) + 1

    medicines.append({
        "id": new_id,
        "name": name,
        "dosage": dosage,
        "day": day,
        "time": time_value,
        "note": note
    })

    write_json(MEDICINES_FILE, medicines)
    flash("Medicine added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_appointment", methods=["POST"])
def add_appointment():
    if not is_logged_in():
        return redirect(url_for("login"))

    doctor = request.form.get("doctor", "").strip()
    hospital = request.form.get("hospital", "").strip()
    date_value = request.form.get("date", "").strip()
    time_value = request.form.get("time", "").strip()
    purpose = request.form.get("purpose", "").strip()

    if not all([doctor, hospital, date_value, time_value, purpose]):
        flash("Fill all appointment fields.", "danger")
        return redirect(url_for("dashboard"))

    appointments = read_json(APPOINTMENTS_FILE, [])
    new_id = max([a["id"] for a in appointments], default=0) + 1

    appointments.append({
        "id": new_id,
        "doctor": doctor,
        "hospital": hospital,
        "date": date_value,
        "time": time_value,
        "purpose": purpose
    })

    write_json(APPOINTMENTS_FILE, appointments)
    flash("Appointment added successfully.", "success")
    return redirect(url_for("dashboard"))


@app.route("/add_contact", methods=["POST"])
def add_contact():
    if not is_logged_in():
        return redirect(url_for("login"))

    name = request.form.get("contact_name", "").strip()
    relation = request.form.get("relation", "").strip()
    phone = request.form.get("phone", "").strip()

    if not all([name, relation, phone]):
        flash("Fill all emergency contact fields.", "danger")
        return redirect(url_for("dashboard"))

    contacts = read_json(CONTACTS_FILE, [])
    new_id = max([c["id"] for c in contacts], default=0) + 1

    contacts.append({
        "id": new_id,
        "name": name,
        "relation": relation,
        "phone": phone
    })

    write_json(CONTACTS_FILE, contacts)
    flash("Emergency contact added successfully.", "success")
    return redirect(url_for("dashboard"))


if __name__ == "__main__":
    initialize_files()
    app.run(debug=True)