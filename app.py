from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time
import datetime

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")
connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="uniti",
                             charset="utf8mb4",
                             port=3308,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)


def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)

    return dec


@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")


@app.route("/home")
@login_required
def home():
    username = session["username"]
    feedQuery = "SELECT * FROM Events NATURAL JOIN eventgoing WHERE attendee = %s"
    with connection.cursor() as cursor:
        cursor.execute(feedQuery, (username))
        feed_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("home.html", feed=feed_data, username=session["username"], login=login)

# create event page
@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/feed", methods=["GET"])
@login_required
def feed():
    status = "Feed"
    feedQuery = "SELECT * FROM Events ORDER BY eventID DESC LIMIT 10"
    with connection.cursor() as cursor:
        cursor.execute(feedQuery)
        feed_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("feed.html", status=status, feed=feed_data, login=login)


@app.route("/search", methods=["GET"])
@login_required
def search():
    status = "Search"
    event = request.args["event"]
    event = "%" + event + "%"
    searchQuery = "SELECT * FROM events WHERE eventName LIKE %s OR eventDescription LIKE %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (event, event))
        feed_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("feed.html", status=status, feed=feed_data, login=login)

@app.route("/profile", methods=["GET"])
@login_required
def profile():
    status = "Profile"
    searchQuery = "SELECT * FROM events WHERE eventOwner = %s Order BY eventID DESC"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (session["username"]))
        feed_data = cursor.fetchall()
    searchQuery = "SELECT * FROM person WHERE username = %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (session["username"]))
        user_data = cursor.fetchall()[0]
        today = datetime.date.today().strftime('%Y-%m-%d')
        age = int(today.split('-')[0]) - int(user_data["dob"].split('-')[0])
        if int(user_data["dob"].split('-')[1]) > int(today.split('-')[1]) or int((user_data["dob"].split('-')[1]) == int(today.split('-')[1]) and int(user_data["dob"].split('-')[2]) > int(today.split('-')[2])):
            age -= 1
    login = False
    if "username" in session:
        login = True    
    return render_template("profile.html", status=status, feed=feed_data, user=user_data, age=age, login=login)

@app.route("/event", methods=["GET"])
@login_required
def event():
    username = session["username"]
    eventID = request.args["eventID"]

    eventQuery = "SELECT * FROM Events WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery, (eventID))
        event_data = cursor.fetchall()

    attendanceQuery = "SELECT attendee FROM eventgoing WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(attendanceQuery, (eventID))
        attendance_data = cursor.fetchall()

    goingQuery = "SELECT * FROM eventgoing WHERE attendee = %s AND eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(goingQuery, (username, eventID))
        going_data = cursor.fetchall()
        if (len(going_data) == 0):
            attend = "Going"
        else:
            attend = "Not Going"
    login = False
    if "username" in session:
        login = True
    return render_template("event.html", eventInfo=event_data, attendance=attendance_data, attend=attend, login=login)


@app.route("/going", methods=["GET"])
@login_required
def going():
    username = session["username"]
    eventID = request.args["eventID"]
    attend = request.args["attend"]
    eventQuery = "SELECT * FROM Events WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery, (eventID))
        event_data = cursor.fetchall()

    with connection.cursor() as cursor:
        if (attend == "Going"):
            goingQuery = "INSERT INTO eventgoing (attendee, eventID) VALUES (%s, %s)"
            attend = "Not Going"
            cursor.execute(goingQuery, (username, eventID))
        elif (attend == "Not"):
            goingQuery = "DELETE FROM eventgoing WHERE attendee = %s AND eventID = %s"
            attend = "Going"
            cursor.execute(goingQuery, (username, eventID))

    attendanceQuery = "SELECT attendee FROM eventgoing WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(attendanceQuery, (eventID))
        attendance_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("event.html", eventInfo=event_data, attendance=attendance_data, attend=attend, login=login)


@app.route("/login", methods=["GET"])
def login():
    login = False
    if "username" in session:
        login = True
    return render_template("login.html", login=login)


@app.route("/register", methods=["GET"])
def register():
    login = False
    if "username" in session:
        login = True
    return render_template("register.html", login=login)


@app.route("/loginAuth", methods=["POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPassword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPassword.encode("utf-8")).hexdigest()
        print(hashedPassword)
        with connection.cursor() as cursor:
            query = "SELECT * FROM Person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    login = False
    if "username" in session:
        login = True
    return render_template("login.html", error=error, login=login)


@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        email = requestData["email"]
        username = requestData["username"]
        plaintextPassword = requestData["password"]
        hashedPassword = hashlib.sha256(plaintextPassword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        city = requestData["city"]
        state = requestData["state"]
        dob = requestData["dob"]      
        sex = requestData["sex"]       
        occupation = requestData["occupation"]        
        bio = requestData["bio"]     
        profilePic = requestData["profilePic"]
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO Person (username, password, firstName, lastName, city, state, email, dob, sex, occupation, bio, profilePic) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName, city, state, email, dob, sex, occupation, bio, profilePic))
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    login = False
    if "username" in session:
        login = True
    return render_template("register.html", error=error, login=login)


@app.route("/logout", methods=["GET"])
def logout():
    if "username" in session:
        session.pop("username")
    return redirect("/login")

# previously uploadimage
@app.route("/uploadEvent", methods=["POST"])
@login_required
def uploadEvent():
    if request.form:
        requestData = request.form
        print(requestData)
        event_owner = session["username"]
        event_name = requestData["event_name"]
        event_date = requestData["event_date"]
        event_location = requestData["event_location"]
        event_description = requestData["event_description"]
        uploadQuery = "INSERT INTO Events (eventOwner, eventName, eventDate, eventLocation, eventDescription) VALUES (%s, %s, %s, %s, %s)"
        with connection.cursor() as cursor:
            cursor.execute(uploadQuery, (event_owner, event_name, event_date, event_location, event_description))
        message = "Event Created"
    login = False
    if "username" in session:
        login = True
    return render_template("upload.html", message=message, login=login)

if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()
