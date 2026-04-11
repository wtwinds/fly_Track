from flask import Flask, render_template, request, redirect, flash, session
from pymongo import MongoClient
import bcrypt
from config import MONGO_URI, SECRET_KEY
import random
import re
from bson.objectid import ObjectId

app=Flask(__name__)
app.secret_key=SECRET_KEY

client=MongoClient(MONGO_URI)
db=client['flyTrack']
users=db['users']
baggage=db['baggage']
lost_baggage = db['lost_baggage']


#Login
@app.route('/' , methods=['GET', 'POST'])
def login():
    if request.method=='POST':
        email=request.form['email']
        password=request.form['password']

        user=users.find_one({"email": email})

        if user and bcrypt.checkpw(password.encode(), user['password']):
            session['user']=user['name']
            return redirect('/dashboard')
        else:
            flash("Invalid Email or Password", "danger")

    return render_template("login.html")

#Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method=='POST':
        name=request.form['name']
        email=request.form['email']
        password=request.form['password']
        confirm_password=request.form['confirm_password']

        if password!=confirm_password:
            flash("Passwords do not match", "warning")
            return redirect('/register')
        
        if users.find_one({"email": email}):
            flash("User already exists!!")
            return redirect('/register')
        
        hashed_pw=bcrypt.hashpw(password.encode(), bcrypt.gensalt())

        users.insert_one({
            "name":name,
            "email":email,
            "password": hashed_pw
        })

        session['user']=name
        flash("Registeration Successful")
        return redirect('/dashboard')
    
    return render_template("register.html")

#Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect('/')
    
    return render_template("dashboard.html", user=session['user'])

#Checkin
@app.route('/checkin', methods=['GET', 'POST'])
def checkin():
    if 'user' not in session:
        return redirect('/')
    
    if request.method == 'POST':
        form_data = {
            "name": request.form['name'],
            "flight": request.form['flight'],
            "destination": request.form['destination'],
            "weight": request.form['weight'],
            "contact": request.form['contact']
        }

        if not re.match(r'^[A-Z]{2}\d{3,4}$', form_data['flight']):
            flash("Invalid Flight Number Format (EX: AI202)")
            return render_template("checkin.html", form=form_data)

        bag_id = "BAG" + form_data['flight'][-3:] + form_data['contact'][-4:]

        baggage.insert_one({
            "user": session['user'],
            **form_data,
            "bag_id": bag_id
        })

        image_url = "https://images.unsplash.com/photo-1581553680321-4fffae59fccd"

        flash(f"Bag Tag Generated Successfully! ID: {bag_id}", "success")
        return redirect('/dashboard')

    # ✅ GET
    bag_id = session.pop('bag_id', None)
    image_url = session.pop('image', None)
    form_data = session.pop('form_data', {
        "name": "",
        "flight": "",
        "destination": "",
        "weight": "",
        "contact": ""
    })

    return render_template("checkin.html", bag_id=bag_id, image=image_url, form=form_data)

#History
@app.route('/history')
def history():
    if 'user' not in session:
        return redirect('/')

    data = baggage.find({"user": session['user']})
    return render_template("history.html", data=data)

@app.route('/delete/<id>')
def delete(id):
    baggage.delete_one({"_id": ObjectId(id)})
    return redirect('/history')

#Report
@app.route('/report', methods=['GET', 'POST'])
def report():
    if 'user' not in session:
        return redirect('/')

    if request.method == 'POST':
        data = {
            "user": session['user'],
            "name": request.form['name'],
            "bag_id": request.form['bag_id'],
            "flight": request.form['flight'],
            "description": request.form['description'],
            "contact": request.form['contact']
        }

        lost_baggage.insert_one(data)

        flash("Lost Baggage Report Submitted Successfully!")
        return redirect('/dashboard')

    return render_template("report.html")

#lost-history
@app.route('/lost-history')
def lost_history():
    if 'user' not in session:
        return redirect('/')

    data = lost_baggage.find({"user": session['user']})
    return render_template("lost_history.html", data=data)

#Delete
@app.route('/delete-lost/<id>')
def delete_lost(id):
    lost_baggage.delete_one({"_id": ObjectId(id)})
    return redirect('/lost-history')

#baggage list
@app.route('/baggage-list')
def baggage_list():
    if 'user' not in session:
        return redirect('/')

    data = list(baggage.aggregate([
        {
            "$group": {
                "_id": {
                    "flight": "$flight",
                    "destination": "$destination"
                },
                "total_bags": {"$sum": 1}
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

#Staff
@app.route('/staff')
def staff():
    if 'user' not in session:
        return redirect('/')

    staff_data = [
        {
            "name": "Ravi Das",
            "email": "ravi@gmail.com",
            "contact": "1234567890",
            "role": "Technical Staff",
            "age": 28
        },
        {
            "name": "Nisha Roy",
            "email": "nisharoy23@gmail.com",
            "contact": "0987654321",
            "role": "Air Hostess",
            "age": 24
        },
        {
            "name": "Amit Sharma",
            "email": "amit@gmail.com",
            "contact": "9876543210",
            "role": "Ground Staff",
            "age": 30
        },
        {
            "name": "Priya Singh",
            "email": "priya@gmail.com",
            "contact": "9123456780",
            "role": "Security",
            "age": 27
        }
    ]

    return render_template("staff.html", staff=staff_data)

#Logout
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

if __name__=="__main__":
    app.run(debug=True)