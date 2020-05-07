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
    #feedQuery = "SELECT * FROM events NATURAL JOIN eventgoing WHERE attendee = (SELECT usernameFollowed FROM follow WHERE usernameFollower = %s)"
    #with connection.cursor() as cursor:
    #    cursor.execute(feedQuery, (username))
    #    feed_data = cursor.fetchall()
    login = False
    eventQuery = "SELECT * FROM events"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery)
        event_data = cursor.fetchall()
        print(event_data)
    eventAttendedQuery = "SELECT * FROM events WHERE eventID = (SELECT eventID FROM eventgoing WHERE attendee = %s)"
    with connection.cursor() as cursor:
        cursor.execute(eventAttendedQuery, (username))
        eventAttending_data = cursor.fetchall()
        print(eventAttending_data)
    if "username" in session:
        login = True
    return render_template("home.html", feed=event_data, username=session["username"], login=login, eventsAttending=eventAttending_data)

# create event page
@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/feed", methods=["GET"])
@login_required
def feed():
    feedQuery = "SELECT * FROM Events ORDER BY eventID DESC LIMIT 10"
    with connection.cursor() as cursor:
        cursor.execute(feedQuery)
        feed_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("feed.html", feed=feed_data, login=login)


@app.route("/searchEvent", methods=["GET"])
@login_required
def searchEvent():
    event = request.args["event"]
    event = "%" + event + "%"
    searchQuery = "SELECT * FROM events WHERE eventName LIKE %s OR eventDescription LIKE %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (event, event))
        feed_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("searchEvent.html", feed=feed_data, login=login)


@app.route("/searchUser", methods=["GET"])
@login_required
def searchUser():
    user = request.args["user"]
    user = "%" + user + "%"
    searchQuery = "SELECT * FROM person WHERE username LIKE %s OR firstName LIKE %s OR lastName LIKE %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (user, user, user))
        user_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("searchUser.html", users=user_data, login=login)


@app.route("/followers", methods=["GET"])
@login_required
def followers():
    user = request.args["user"]
    followQuery = "SELECT * FROM person WHERE username = (SELECT usernameFollower FROM follow WHERE usernameFollowed = %s)"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (user))
        follow_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("searchUser.html", users=follow_data, login=login)


@app.route("/following", methods=["GET"])
@login_required
def following():
    user = request.args["user"]
    followQuery = "SELECT * FROM person WHERE username = (SELECT usernameFollowed FROM follow WHERE usernameFollower = %s)"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (user))
        follow_data = cursor.fetchall()
    login = False
    if "username" in session:
        login = True
    return render_template("searchUser.html", users=follow_data, login=login)


@app.route("/checkUser", methods=["GET"])
@login_required
def checkUser():
    user = request.args["user"]
    searchQuery = "SELECT * FROM events WHERE eventOwner = %s Order BY eventID DESC"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (user))
        feed_data = cursor.fetchall()
    searchQuery = "SELECT * FROM person WHERE username = %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (user))
        user_data = cursor.fetchall()[0]
        today = datetime.date.today().strftime('%Y-%m-%d')
        age = int(today.split('-')[0]) - int(user_data["dob"].split('-')[0])
        if int(user_data["dob"].split('-')[1]) > int(today.split('-')[1]) or int(
                                (user_data["dob"].split('-')[1]) == int(today.split('-')[1]) and int(
                        user_data["dob"].split('-')[2]) > int(today.split('-')[2])):
            age -= 1
    eventQuery = "SELECT * FROM events WHERE eventOwner = %s"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery, (user))
        try:
            event_data = cursor.fetchall()[0]
        except:
            event_data = None

    followQuery = "SELECT * FROM follow WHERE usernameFollowed = %s AND usernameFollower = %s"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (user, session["username"]))
        follow_data = cursor.fetchall()
        if (len(follow_data) == 0):
            followStatus = "Follow"
        else:
            followStatus = "Unfollow"
    followQuery = "SELECT usernameFollower FROM follow WHERE usernameFollowed = %s"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (user))
        try:
            follow = cursor.fetchall()
            print(follow)
            follow_count = str(len(follow))
            print(follow_count)
        except: follow_count = 0
    followedQuery = "SELECT usernameFollowed FROM follow WHERE usernameFollower = %s"
    with connection.cursor() as cursor:
        cursor.execute(followedQuery, (user))
        try:
            followed = cursor.fetchall()
            print(followed)
            followed_count = str(len(followed))
            print(followed_count)
        except: followed_count = 0
    login = False
    if "username" in session:
        login = True
    return render_template("otherUserprofile.html", feed=feed_data, user=user_data, age=age, followStatus=followStatus, login=login, follow=follow_count, followed=followed_count, event=event_data)


@app.route("/profile", methods=["GET"])
@login_required
def profile():
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
    followQuery = "SELECT usernameFollower FROM follow WHERE usernameFollowed = %s"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (session["username"]))
        try:
            follow = cursor.fetchall()
            print(follow)
            follow_count = str(len(follow))
            print(follow_count)
        except: follow_count = 0
    followedQuery = "SELECT usernameFollowed FROM follow WHERE usernameFollower = %s"
    with connection.cursor() as cursor:
        cursor.execute(followedQuery, (session["username"]))
        try:
            followed = cursor.fetchall()
            print(followed)
            followed_count = str(len(followed))
            print(followed_count)
        except: followed_count = 0
    login = False
    if "username" in session:
        login = True    
    return render_template("profile.html", feed=feed_data, user=user_data, age=age, login=login, follow=follow_count, followed=followed_count)


@app.route("/follow", methods=["GET"])
@login_required
def follow():
    followStatus = request.args["followStatus"]
    followed = request.args["user"]
    follower = session["username"]

    with connection.cursor() as cursor:
        if (followStatus == "Follow"):
            goingQuery = "INSERT INTO follow (usernameFollowed, usernameFollower) VALUES (%s, %s)"
            followStatus = "Unfollow"
            cursor.execute(goingQuery, (followed, follower))
        elif (followStatus == "Unfollow"):
            goingQuery = "DELETE FROM follow WHERE usernameFollowed = %s AND usernameFollower = %s"
            followStatus = "Follow"
            cursor.execute(goingQuery, (followed, follower))

    searchQuery = "SELECT * FROM events WHERE eventOwner = %s Order BY eventID DESC"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (followed))
        feed_data = cursor.fetchall()
    searchQuery = "SELECT * FROM person WHERE username = %s"
    with connection.cursor() as cursor:
        cursor.execute(searchQuery, (followed))
        user_data = cursor.fetchall()[0]
        today = datetime.date.today().strftime('%Y-%m-%d')
        age = int(today.split('-')[0]) - int(user_data["dob"].split('-')[0])
        if int(user_data["dob"].split('-')[1]) > int(today.split('-')[1]) or int(
                                (user_data["dob"].split('-')[1]) == int(today.split('-')[1]) and int(
                    user_data["dob"].split('-')[2]) > int(today.split('-')[2])):
            age -= 1
    followQuery = "SELECT usernameFollower FROM follow WHERE usernameFollowed = %s"
    with connection.cursor() as cursor:
        cursor.execute(followQuery, (followed))
        try:
            follow = cursor.fetchall()
            print(follow)
            follow_count = str(len(follow))
            print(follow_count)
        except: follow_count = 0
    followedQuery = "SELECT usernameFollowed FROM follow WHERE usernameFollower = %s"
    with connection.cursor() as cursor:
        cursor.execute(followedQuery, (followed))
        try:
            followed = cursor.fetchall()
            print(followed)
            followed_count = str(len(followed))
            print(followed_count)
        except: followed_count = 0
    login = False
    if "username" in session:
        login = True
    return render_template("otherUserprofile.html", feed=feed_data, user=user_data, age=age, followStatus=followStatus, login=login, follow=follow_count, followed=followed_count)


@app.route("/event", methods=["GET"])
@login_required
def event():
    username = session["username"]
    eventID = request.args["eventID"]

    eventQuery = "SELECT * FROM Events WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery, (eventID))
        event_data = cursor.fetchall()

    if event_data[0]["eventOwner"] == username:
        userisHost = 1
    else:
        userisHost = 0

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
    return render_template("event.html", eventInfo=event_data, attendance=attendance_data, attend=attend, userisHost=userisHost, login=login)


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


@app.route("/deleteEvent", methods=["GET"])
@login_required
def deleteEvent():
    username = session["username"]
    eventID = request.args["eventID"]

    goingQuery = "DELETE FROM eventgoing WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(goingQuery, (eventID))

    eventQuery = "DELETE FROM events WHERE eventID = %s"
    with connection.cursor() as cursor:
        cursor.execute(eventQuery, (eventID))

    feedQuery = "SELECT * FROM events NATURAL JOIN eventgoing WHERE attendee = (SELECT usernameFollowed FROM follow WHERE usernameFollower = %s)"
    with connection.cursor() as cursor:
        cursor.execute(feedQuery, (username))
        feed_data = cursor.fetchall()

    login = False
    if "username" in session:
        login = True
    return render_template("home.html", feed=feed_data, username=session["username"], login=login)

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
