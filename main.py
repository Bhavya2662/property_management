
from fastapi import FastAPI, Body
from pymongo.mongo_client import MongoClient
from bson import ObjectId
from pymongo.server_api import ServerApi
app = FastAPI()
uri = "mongodb+srv://bhavyasharma2662:123@property.pvwcg2j.mongodb.net/?retryWrites=true&w=majority&appName=property"
# Create a new client and connect to the server
client = MongoClient(uri, server_api=ServerApi('1'))
# Send a ping to confirm a successful connection
try:
    client.admin.command('ping')
    print("Pinged your deployment. You successfully connected to MongoDB!")
except Exception as e:
    print(e)

db = client["property_management"]
# Define property collection schema
properties = db["properties"]
property_schema = {
    "id": int,
    "name": str,
    "address": str,
    "city": str,
    "state": str,
    "area": int,
}

# Define city collection schema
cities = db["cities"]
city_schema = {
    "id": int,
    "name": str,
    "state_id": int,
    "state": str,
}
# Helper function to convert ObjectId to string
def convert_objectid_to_str(obj_id):
    return str(obj_id) if obj_id else None

state_id = 0
# 1. create_new_property
@app.post("/properties")
async def create_new_property(
    name: str = Body(...), address: str = Body(...), city: str = Body(...), state: str = Body(...), area: int = Body(...)
):
    global state_id
    state_id += 1
    new_property = {"name": name, "address": address, "city": city, "state": state, 'area': area}
    new_city = {"name": city, "state_id": state_id, "state": state}
    
    # Find city id by name (assuming city names are unique)
    city_data = cities.find_one({"name": city})
    property_data = properties.find_one({"name": name})
    if city_data and property_data:
        return {"error": "City not found"}
        
    else:
        new_property_id = properties.insert_one(new_property).inserted_id
        cities.insert_one(new_city)
        # Get all properties after insertion
        # all_properties = properties.find()
        # return [convert_objectid_to_str(p["_id"]) for p in all_properties]
        return str(properties.find_one({"_id": new_property_id}))


# 2. fetch_property_details
@app.get("/properties/city/{city_name}")
async def fetch_property_details(city_name: str):
    city_data = cities.find_one({"name": city_name})
    if city_data:
        city_id = city_data["name"]
        filtered_properties = properties.find({"city": city_id})
        return [str(p) for p in filtered_properties]  
    else:
        return {"error": "City not found"}


# 3. update_property_details
@app.put("/properties/{property_id}")
async def update_property(
    property_id: str,
    name: str = Body(None),
    address: str = Body(None),
    city: str = Body(None),
    state: str = Body(None),
    area: int = Body(None),
):
    # Convert property_id to ObjectId
    property_id = ObjectId(property_id)

    # Find existing property
    existing_property = properties.find_one({"_id": property_id})
    if not existing_property:
        return {"error": "Property not found"}

    # Prepare update data with only provided fields
    update_data = {"$set": {}}
    if name is not None:
        update_data["$set"]["name"] = name
    if address is not None:
        update_data["$set"]["address"] = address
    if city is not None:
        update_data["$set"]["city"] = city
    if state is not None:
        update_data["$set"]["state"] = state
    if area is not None:
        update_data["$set"]["area"] = area

    # Update property document
    properties.update_one({"_id": property_id}, update_data)

    # Update city schema if city or state changed
    if city is not None or state is not None:
        existing_city = cities.find_one({"name": existing_property["city"]})
        if existing_city:
            city_update = {}
            if city is not None:
                city_update["name"] = city
            if state is not None:
                city_update["state"] = state
                # Update city's state_id (assuming unique state names)
                new_state_id = cities.find_one({"state": state})["id"]
                city_update["state_id"] = new_state_id
            cities.update_one({"_id": existing_city["_id"]}, {"$set": city_update})

    # Fetch and return the updated property
    updated_property = properties.find_one({"_id": property_id})
    return convert_objectid_to_str(updated_property)

    

# 4. find_cities_by_state
@app.get("/cities/state/{state_id_or_name}")
async def find_cities_by_state(state_id_or_name: str):
    try:
        state_id = int(state_id_or_name)
        city_list = cities.find({"state_id": state_id})
    except ValueError:
        city_list = cities.find({"state": state_id_or_name})
    return  [str(p) for p in city_list]

@app.get("/properties/similar/{property_id}")
async def find_similar_properties(property_id: str):
    property_data = properties.find_one({"_id": ObjectId(property_id)})
    if property_data:
        area = property_data["area"]
        similar_properties = properties.find({"area": area})
        return [str(p) for p in similar_properties]
    else:
        return {"error": "Property not found"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)