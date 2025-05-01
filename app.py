from flask import Flask, render_template, request, redirect, url_for, jsonify
import json

app = Flask(__name__)

# Data structure to store trip data
trips = []

def calculate_contributions(trip):
    """
    Calculates who owes how much to whom based on events in the trip.
    """
    contributions = {person["name"]: 0 for person in trip["persons"]}
    num_persons = trip["num_persons"]

    # Calculate total contribution for each person
    for event in trip["events"]:
        paid_by = event["person"]
        amount = event["amount"]
        involved_persons = event["involved"]

        # Contribution logic for only involved persons
        num_involved = len(involved_persons)
        contributions[paid_by] += amount
        share = amount / num_involved
        for person in involved_persons:
            contributions[person] -= share

    # Prepare a report of payments
    report = []
    creditors = [(person, amount) for person, amount in contributions.items() if amount > 0]
    debtors = [(person, -amount) for person, amount in contributions.items() if amount < 0]

    creditors.sort(key=lambda x: -x[1])  # Largest creditors first
    debtors.sort(key=lambda x: -x[1])  # Largest debtors first

    while creditors and debtors:
        creditor, credit_amount = creditors.pop(0)
        debtor, debt_amount = debtors.pop(0)

        payment = min(credit_amount, debt_amount)
        report.append(f"{debtor} owes {creditor} ₹{payment:.2f}")

        if credit_amount > payment:
            creditors.insert(0, (creditor, credit_amount - payment))
        if debt_amount > payment:
            debtors.insert(0, (debtor, debt_amount - payment))

    return report

@app.route("/")
def index():
    return render_template("index.html", trips=trips)

@app.route("/new_trip", methods=["POST"])
def new_trip():
    trip_name = request.form["trip-name"]
    num_persons = int(request.form["num-persons"])
    persons = []
    for i in range(num_persons):
        person_name = request.form[f"person-name-{i}"]
        persons.append({"name": person_name})

    # Create a new trip dictionary
    trip = {
        "name": trip_name,
        "num_persons": num_persons,
        "persons": persons,
        "events": [],
        "history": []  # New key to store event history
    }

    # Add the trip to the trips list
    trips.append(trip)

    # Redirect to the trip dashboard page
    return redirect(url_for("trip_dashboard", trip_index=len(trips) - 1))

@app.route("/trip_dashboard/<int:trip_index>")
def trip_dashboard(trip_index):
    global trips
    if trip_index < 0 or trip_index >= len(trips):
        return "Trip not found", 404
    trip = trips[trip_index]
    contributions = calculate_contributions(trip)
    return render_template("trip_dashboard.html", trip=trip, trip_index=trip_index, contributions=contributions)

@app.route("/add_event/<int:trip_index>", methods=["GET", "POST"])
def add_event(trip_index):
    global trips
    if trip_index < 0 or trip_index >= len(trips):
        return "Trip not found", 404
    trip = trips[trip_index]

    if request.method == "POST":
        # Get form data
        person = request.form["person"]
        paid_for = request.form["paid-for"]
        amount = float(request.form["amount"])
        involved = request.form.getlist("involved")  # List of involved persons

        # Append the new event to the trip's events
        event = {
            "person": person,
            "paid_for": paid_for,
            "amount": amount,
            "involved": involved
        }
        trip["events"].append(event)

        # Append the event to the trip history
        trip["history"].append(event)

        # Redirect back to the trip dashboard
        return redirect(url_for("trip_dashboard", trip_index=trip_index))

    # Render the add_event.html form
    return render_template("add_event.html", trip=trip, trip_index=trip_index)

@app.route("/history/<int:trip_index>")
def view_history(trip_index):
    global trips
    if trip_index < 0 or trip_index >= len(trips):
        return "Trip not found", 404
    trip = trips[trip_index]
    history = trip.get("history", [])
    return render_template("history.html", trip=trip, history=history, trip_index=trip_index)

@app.route("/report/<int:trip_index>")
def report(trip_index):
    global trips
    if trip_index < 0 or trip_index >= len(trips):
        return "Trip not found", 404
    trip = trips[trip_index]
    contributions = calculate_contributions(trip)

    # Prepare data for charts
    spending_data = {}
    individual_data = {}
    for event in trip["events"]:
        category = event["paid_for"]
        person = event["person"]
        amount = event["amount"]

        # Aggregate spending by category
        if category in spending_data:
            spending_data[category] += amount
        else:
            spending_data[category] = amount

        # Aggregate spending by individual
        if person in individual_data:
            individual_data[person] += amount
        else:
            individual_data[person] = amount

    return render_template(
        "report.html",
        trip=trip,
        contributions=contributions,
        trip_index=trip_index,
        spending_data=json.dumps(spending_data),  # JSON-safe data
        individual_data=json.dumps(individual_data)  # JSON-safe data
    )

@app.route("/delete_trip/<int:trip_index>", methods=["POST"])
def delete_trip(trip_index):
    global trips
    if 0 <= trip_index < len(trips):
        trips.pop(trip_index)
        return {"success": True}, 200
    return {"success": False}, 404

if __name__ == "__main__":
    app.run(debug=True)
