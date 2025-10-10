import json
import ee

# Initialize Earth Engine (you need to authenticate first)


def authentication(user):
    ee.Authenticate()
    with open("user_details.json", "r") as file:
        users = json.load(file)
    if user in users:
        ee.Initialize(project=users[user]["ee_project"])
    else:
        user_project = get_user_project()
        # Step 1: Load existing JSON data
        ee.Initialize(user_project)
        with open("user_details.json", "r") as file:
            users = json.load(file)

        # Step 2: Add a new user
        users[user] = {"project": user_project}

        # Step 3: Save updated data back to the file
        with open("user_details.json", "w") as file:
            json.dump(users, file, indent=4)
    return


def get_user_project():
    project = input("What is your earth engine project name?")
    return project


user = input("what is your username?: ")
authentication(user)
