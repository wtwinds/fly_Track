from flask import Flask, render_template, request, redirect, flash, session, jsonify
from pymongo import MongoClient
from config import MONGO_URI, SECRET_KEY
import re
from bson.objectid import ObjectId

app = Flask(__name__)
app.secret_key = SECRET_KEY

# DB
client = MongoClient(MONGO_URI)
db = client['flyTrack']
users = db['users']
baggage = db['baggage']
lost_baggage = db['lost_baggage']
pnr_data = db['pnr_data']

# ================= LOGIN =================
@app.route('/', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = users.find_one({"email": email})

        # ✅ SIMPLE PASSWORD CHECK
        if user and user['password'] == password:
            session['user'] = user['name']
            return redirect('/dashboard')
        else:
            flash("Invalid Email or Password", "danger")

    return render_template("login.html")


# ================= REGISTER =================
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash("Passwords do not match", "warning")
            return redirect('/register')

        if users.find_one({"email": email}):
            flash("User already exists!", "warning")
            return redirect('/register')

        # ✅ SIMPLE PASSWORD SAVE
        users.insert_one({
            "name": name,
            "email": email,
            "password": password
        })

        session['user'] = name
        flash("Registration Successful", "success")
        return redirect('/dashboard')

    return render_template("register.html")


# ================= DASHBOARD =================
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    return render_template("dashboard.html")


# ================= AUTO PNR =================
@app.route('/get-pnr/<pnr>')
def get_pnr(pnr):
    data = pnr_data.find_one({"PNR Number": pnr.upper()})

    if data:
        return jsonify({
            "status": True,
            "data": {
                "name": data.get("Passenger Name"),
                "flight": data.get("Flight Number"),
                "destination": data.get("Destination"),
                "contact": data.get("Contact Number")
            }
        })
    return jsonify({"status": False})

# ================= CHECKIN =================
@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':

        pnr = request.form['pnr'].upper()

        # GET FROM pnr_data (NOT baggage)
        pnr_data_doc = pnr_data.find_one({"PNR Number": pnr})

        if not pnr_data_doc:
            flash("PNR not found!", "danger")
            return redirect('/checkin')

        # SAME USER SAME PNR BLOCK
        existing = baggage.find_one({
            "PNR Number": pnr,
            "user": session['user']
        })

        if existing:
            flash("You already checked-in this PNR!", "warning")
            return redirect('/checkin')

        # FORM DATA
        bags = int(request.form['bags'])
        weight = int(request.form['weight'])

        # BAG ID
        bag_id = "BAG" + pnr_data_doc['Flight Number'][-3:] + pnr_data_doc['Contact Number'][-4:]

        # INSERT ONLY USER DATA
        baggage.insert_one({
            "PNR Number": pnr,
            "Passenger Name": pnr_data_doc.get("Passenger Name"),
            "Flight Number": pnr_data_doc.get("Flight Number"),
            "Destination": pnr_data_doc.get("Destination"),
            "Contact Number": pnr_data_doc.get("Contact Number"),
            "user": session['user'],
            "bags": bags,
            "weight": weight,
            "bag_id": bag_id
        })

        flash(f"Bag Generated: {bag_id}", "success")
        return redirect('/dashboard')

    # ONLY ORIGINAL PNR SHOW
    pnr_list = pnr_data.distinct("PNR Number")

    return render_template("checkin.html", pnr_list=pnr_list)

# ================= HISTORY =================
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')

    data = []
    for item in baggage.find({
        "user": session['user'],
        "bag_id": {"$exists": True}
    }):
        data.append({
            "_id": item["_id"],
            "flight": item.get("Flight Number"),
            "destination": item.get("Destination"),
            "bag_id": item.get("bag_id")
        })

    return render_template("history.html", data=data)

@app.route('/delete/<id>')
def delete(id):
    baggage.delete_one({"_id": ObjectId(id)})
    return redirect('/history')


# ================= GET BAG ID =================
@app.route('/get-bag/<pnr>')
def get_bag(pnr):
    data = baggage.find_one({
        "PNR Number": pnr.upper(),
        "user": session['user']
        })

    if data and "bag_id" in data:
        return jsonify({
            "status": True,
            "bag_id": data.get("bag_id")
        })

    return jsonify({"status": False})

# ================= LOST REPORT =================
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':

        baggage_data = baggage.find_one({
            "PNR Number": request.form['pnr'],
            "user": session['user']
        })

        lost_baggage.insert_one({
            "user": session['user'],
            "flight": request.form['flight'],
            "destination": baggage_data.get("Destination") if baggage_data else "",
            "bag_id": request.form['bag_id'],
            "description": request.form['description']
        })

        flash("Lost Baggage Report Submitted Successfully!", "success")
        return redirect('/dashboard')

    # ONLY USER PNR
    pnr_list = baggage.distinct("PNR Number", {
        "user": session['user'],
        "bag_id": {"$exists": True}
    })

    return render_template("report.html", pnr_list=pnr_list)

@app.route('/lost-history')
def lost_history():
    if 'user' not in session:
        return redirect('/')

    data = lost_baggage.find({"user": session['user']})
    return render_template("lost_history.html", data=data)


@app.route('/delete-lost/<id>')
def delete_lost(id):
    lost_baggage.delete_one({"_id": ObjectId(id)})
    return redirect('/lost-history')


# ================= BAGGAGE LIST =================
@app.route('/baggage-list')
def baggage_list():
    if 'user' not in session:
        return redirect('/')

    data = list(baggage.aggregate([
        {
            "$match": {"bag_id": {"$exists": True}}
        },
        {
            "$group": {
                "_id": {
                    "flight": "$Flight Number",
                    "destination": "$Destination"
                },
                "total_bags": {"$sum": "$bags"}   # 🔥 FIX HERE
            }
        },
        {
            "$project": {
                "flight": "$_id.flight",
                "destination": "$_id.destination",
                "total_bags": 1,
                "_id": 0
            }
        }
    ]))

    return render_template("baggage_list.html", data=data)

# ================= STAFF =================
@app.route('/staff')
def staff():
    if 'user' not in session:
        return redirect('/')

    staff_data = [
        {"name": "Ravi Das", "email": "ravi@gmail.com", "contact": "1234567890", "role": "Technical Staff", "age": 28},
        {"name": "Nisha Roy", "email": "nisharoy23@gmail.com", "contact": "0987654321", "role": "Air Hostess", "age": 24},
        {"name": "Amit Sharma", "email": "amit@gmail.com", "contact": "9876543210", "role": "Ground Staff", "age": 30},
        {"name": "Priya Singh", "email": "priya@gmail.com", "contact": "9123456780", "role": "Security", "age": 27}
    ]

    return render_template("staff.html", staff=staff_data)


# ================= LOGOUT =================
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')


if __name__ == "__main__":
    app.run(debug=True)