from pymongo import MongoClient
from pymongo.errors import DuplicateKeyError
from flask import Flask, request, jsonify, redirect, Response
import json
import uuid
import time
from bson.objectid import ObjectId

from werkzeug.datastructures import MIMEAccept
from werkzeug.wrappers import CommonResponseDescriptorsMixin

# Connect to our local MongoDB
client = MongoClient('mongodb://localhost:27017/')

# Choose database
db = client['DSMarkets']

# Choose collections
products = db['Products']
users = db['Users']

# Initiate Flask App
app = Flask(__name__)

users_sessions = {}

def create_session(username):
    user_uuid = str(uuid.uuid1())
    users_sessions[user_uuid] = [username, time.time()]
    return user_uuid  

def is_session_valid(user_uuid):
    return user_uuid in users_sessions

#Registering user
@app.route('/register', methods=['POST'])
def create_user():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json') 
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')

    if not "email" in data:
        return Response("Information incomplete - email is missing",status=500,mimetype="application/json")
    if not "name" in data:
        return Response("Information incomplete - name is missing",status=500,mimetype="application/json")
    if not "password" in data:
        return Response("Information incomplete - password is missing",status=500,mimetype="application/json")
    if not "category" in data:
        return Response("Information incomplete - category is missing ",status=500,mimetype="application/json")

    if data["category"].upper() not in ["ADMIN", "USER"]:
        return(Response(data["email"]+ " can not be added as category is incorrect (Allowed values are: Admin or User)", status=400, mimetype="application/json"))

    if not users.find_one({"email":data["email"]}) == None:
        return(Response(data["email"]+ " was not added to the database. It already exists", status=400, mimetype="application/json"))
    else:
        if data["category"].upper() == "USER":   #If user is not an admin we need to initialize orderHistory if not we don't
            user = {"email":data["email"], "name":data["name"], "password":data["password"], "category":data["category"], "orderHistory":[]}
        else:
            user = {"email":data["email"], "name":data["name"], "password":data["password"], "category":data["category"]}

        users.insert_one(user)
        return(Response(data["name"]+ " was added to the database.", status=200, mimetype="application/json"))

    

# Logging in user
@app.route('/login', methods=['POST'])
def login():
    # Request JSON data
    data = None 
    
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    
    if not "email" in data or not "password" in data:
        return Response("Information incomplete - email or password is missing",status=500,mimetype="application/json")

    if users.find_one({"email":data["email"]}) == None:
        return Response("Wrong email or password.", status=400, mimetype='application/json')
    else:
        if users.find_one({"password": {"$eq": data["password"]}}):
            user_uuid = create_session(data["email"])
            res = {"uuid": user_uuid, "email": data['email']}

            return Response(json.dumps(res), status=200, mimetype='application/json')
        else:
            return Response("Wrong username or password.", status=400, mimetype='application/json')

# Find product details
@app.route('/searchproduct', methods=['GET'])
def search_product():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')

    # # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')
    
    #Check against name - this has the highest priority!
    if "name" in data:
        products_res = products.find_one({"name":data["name"]})

        if products_res == None:
            return Response("Product not found", status=500, mimetype='application/json')

        return Response("We found your product \n" + "Name: " + products_res["name"] + "\n" + "Description: " + products_res["description"] + "\n" + "Price: " + products_res["price"] + "\n" + "Category: " + products_res["category"] + "\n" + "Stock: "+ products_res["stock"] + "\n" + "ID: "+ str(products_res["_id"]), status=200, mimetype='application/json') 

    if "category" in data: 
        products_res = products.find({"category": {"$eq": data["category"]}})

        if products_res == None:
            return Response("Product not found", status=500, mimetype='application/json')

        product_matching = []

        for pr in products_res:  # For each entry from the results
            pr_array = ["Name: " + pr["name"], "Price: " + pr["price"], "Description: " + pr["description"], "Category: " + pr["category"], "Stock: "+ pr["stock"] ]            
            product_matching.append(pr_array)  # Create a two-dimension list that is of format [[name, price, description, category, stock], [name, price, description, cateogory, stock]]
        
        return Response(json.dumps(sorted(product_matching, key=lambda x: x[1])), status=200, mimetype='application/json') #Most Expensive to least expensive
    
    if "_id" in data:  
        objInstance = ObjectId(data["_id"])  
        products_res = products.find_one({"_id":objInstance})

        if products_res == None:
            return Response("Product not found", status=500, mimetype='application/json')

        return Response("We found your product \n" + "Name: " + products_res["name"] + "\n" + "Description: " + products_res["description"] + "\n" + "Price: " + products_res["price"] + "\n" + "Category: " + products_res["category"] + "\n" + "Stock: "+ products_res["stock"] + "\n" + "ID: "+ str(products_res["_id"]), status=200, mimetype='application/json') 


# Add to cart
@app.route('/addtocart', methods=['POST'])
def add_to_cart():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "_id" in data:
        return Response("Information incomplete - product id is missing",status=500,mimetype="application/json")

    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not have carts", status=400, mimetype='application/json')

    objInstance = ObjectId(data["_id"])  
    product = products.find_one({"_id":objInstance})

    if product == None:   #Checking if the product id is correct (exists in the collection of products)
        return Response("Incorrect ID - make sure to retype it", status=500, mimetype='application/json')

    user = users.find_one({"email":uuid_email, "cart": {"$exists": True}})  #Checking if user has a cart

    if user == None:  # If not, add an empty array "cart":[]
        users.update_one({'email': uuid_email}, { '$set': {'cart': []} }, True)  # Write
            
    user = users.find_one({'email': uuid_email})  #Get the user again (after update)
    user_cart = user["cart"]  # Get their cart 
    user_cart.append(data["_id"])  # Append the new item so that it is not overriden

    users.update_one({'email': uuid_email}, { '$set': {'cart': user_cart} }, True)  # Write
    
    return Response("Added product to the cart. The new cart includes" + str(user["cart"]), status=200, mimetype='application/json')


# Get cart details
@app.route('/showcart', methods=['GET'])
def show_cart():
    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not have carts", status=400, mimetype='application/json')

    user = users.find_one({"email":uuid_email, "cart": {"$exists": True}})  #Checking if user has a cart

    prid_in_cart = [] # Product IDs in Cart
    if user == None:  # If not, respond
        return Response("The user " + uuid_email + "has no cart ", status=200, mimetype='application/json')
    else: 
        for pr in user["cart"]:  # for products in user's cart
            prid_in_cart.append(pr)  # Add product id in the array

        product_full = []  # Full details of product
        for id in prid_in_cart:  # For id in the id's array 
            objInstance = ObjectId(id)  # Type cast object id
            
            products_res = products.find_one({"_id":objInstance})  # find product based on id
            product_full.append(["Name: "+ products_res["name"], "Price: "+ products_res["price"], "Description: "+ products_res["description"],  "Category: "+ products_res["category"],  "Stock: "+ products_res["stock"]])
            
    if len(product_full) == 0:
        return Response("User doesn't have any items in their cart", status=200, mimetype='application/json')

    return Response(json.dumps(product_full), status=200, mimetype='application/json')

# Delete item from cart
@app.route('/deletecartitem', methods=['POST'])
def delete_cart_item():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "_id" in data:
        return Response("Information incomplete - product id is missing",status=500,mimetype="application/json")

    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not have carts", status=400, mimetype='application/json')

    user = users.find_one({"email":uuid_email, "cart": {"$exists": True}})  #Checking if user has a cart

    prid_in_cart = [] # Product IDs in Cart
    if user == None:  # If not, respond
        return Response("The user " + uuid_email + "has no cart ", status=200, mimetype='application/json')
    else: 
        for pr in user["cart"]:  # for products in user's cart
            prid_in_cart.append(pr)  # Add product id in the array
            
        if not data["_id"] in prid_in_cart:
            return Response("That product is not in the cart", status=500, mimetype='application/json')
        else:
            prid_in_cart.remove(data["_id"])  #Remove from the array of ids the id the user added
        
        product_full = []  # Full details of product
        for id in prid_in_cart:  # For id in the id's array 
            objInstance = ObjectId(id)  # Type cast object id
            
            products_res = products.find_one({"_id":objInstance})  # find product based on id
            product_full.append(["Name: "+ products_res["name"], "Price: "+ products_res["price"], "Description: "+ products_res["description"],  "Category: "+ products_res["category"],  "Stock: "+ products_res["stock"]])
            
            users.update_one({'email': uuid_email}, { '$set': {'cart': prid_in_cart} }, True)  # Write the new array on the cart entry

    if len(product_full) == 0:
        return Response("User doesn't have any items in their cart", status=200, mimetype='application/json')

    return Response("Removed product with id "+ data["_id"] + "\n" + "New cart includes: " + json.dumps(product_full), status=200, mimetype='application/json')


# Buy items in cart
@app.route('/purchase', methods=['POST'])
def purchase():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "number" in data or len(data["number"]) < 16:
        return Response("Information incomplete - card number is incorrect",status=500,mimetype="application/json")

    # # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not purchase", status=400, mimetype='application/json')

    user = users.find_one({"email":uuid_email, "cart": {"$exists": True}})  #Checking if user has a cart

    prid_in_cart = [] # Product IDs in Cart
    if user == None:  # If not, respond
        return Response("The user " + uuid_email + "has no cart", status=200, mimetype='application/json')
    else: 
        for pr in user["cart"]:  # for products in user's cart
            prid_in_cart.append(pr)  # Add product id in the array

        product_full = []  # Full details of product
        for id in prid_in_cart:  # For id in the id's array 
            objInstance = ObjectId(id)  # Type cast object id
            
            products_res = products.find_one({"_id":objInstance})  # find product based on id

            old_stock = products_res["stock"]
            new_stock = int(old_stock) - 1

            if new_stock < 0:  #Check if product is out of stock
                return Response("Product " + products_res["name"] + " is out of stock. Your order was cancelled", status=500, mimetype='application/json')
           
            products.update_one({'_id': objInstance}, { '$set': {'stock': str(new_stock)} }, True)  # Update stock of product

            product_full.append(["Name: "+ products_res["name"], "Price: "+ products_res["price"], "Description: "+ products_res["description"],  "Category: "+ products_res["category"],  "Stock: "+ str(products_res["stock"])])

        if len(product_full) == 0:
            return Response("User doesn't have any items in their cart", status=200, mimetype='application/json')
        total = 0
        for price in product_full:
            total += float(price[1][len("Price:"):len(price[1])])  # product_full is multidimensional and includes string so convert to float from "price:" and after
        
        history = []
        for pr in user["orderHistory"]:
            history.append(pr)
        
        for pr in prid_in_cart:
            
            history.append(pr)
        users.update_one({'email': uuid_email}, { '$set': {'cart': []} }, True)  # Empty the cart
        print(history)

        users.update_one({'email': uuid_email}, { '$set': {'orderHistory': history} }, True)  # Write order History

        

        

        
        return Response("Total Price: "+ str(total) + "\n" + "Products: " + json.dumps(product_full) , status=200, mimetype='application/json')

        
# Get purchases
@app.route('/showpurchases', methods=['GET'])
def show_purchases():
    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')
    
    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not buy", status=400, mimetype='application/json')

    user = users.find_one({"email":uuid_email})  # Get user from DB

    prid_in_history = [] # Product IDs in Cart

    for pr in user["orderHistory"]:  # for products in user's order History
        prid_in_history.append(pr)  # Add product id in the array

    product_full = []  # Full details of product
    for id in prid_in_history:  # For id in the id's array 
        objInstance = ObjectId(id)  # Type cast object id
        
        products_res = products.find_one({"_id":objInstance})  # find product based on id
        product_full.append(["Name: "+ products_res["name"], "Price: "+ products_res["price"], "Description: "+ products_res["description"],  "Category: "+ products_res["category"],  "Stock: "+ products_res["stock"]])
            
    if len(product_full) == 0:
        return Response("User has never purchased before", status=200, mimetype='application/json')

    return Response(json.dumps(product_full), status=200, mimetype='application/json')

# Delete user
@app.route('/deleteuser', methods=['POST'])
def delete_user():
    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')
    
    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"user"}):
        return Response("Admins can not access this page", status=400, mimetype='application/json')

    users.delete_one({"email":uuid_email})  # Delete user from DB
    
    del users_sessions[request.headers.get("uuid")] # Remove uuid from dictionary

    return Response("User " + uuid_email + " has been deleted", status=200, mimetype='application/json')

# Add product as admin
@app.route('/admin/addproduct', methods=['POST'])
def addProduct():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "name" in data:
        return Response("Information incomplete - product name is missing",status=500,mimetype="application/json")
    if not "price" in data:
        return Response("Information incomplete - price is missing",status=500,mimetype="application/json")
    if not "description" in data:
        return Response("Information incomplete - description is missing",status=500,mimetype="application/json")
    if not "category" in data:
        return Response("Information incomplete - category is missing",status=500,mimetype="application/json")
    if not "stock" in data:
        return Response("Information incomplete - stock is missing",status=500,mimetype="application/json")

    # If there is an error while typecasting then the data is not convertable to float therefore it is not a number
    try:
        price = float(data["price"])
    except:
        return Response("Information incomplete - price is incorrect, use integers or floating point values ",status=500,mimetype="application/json")

    try:
        stock = float(data["stock"])
    except: 
        return Response("Information incomplete - stock is incorrect, use integers ",status=500,mimetype="application/json")

    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"admin"}):
        return Response("Admin only area", status=400, mimetype='application/json')
    else:
        product = {"name":data["name"], "price":data["price"], "description":data["description"], "category":data["category"], "stock":data["stock"]}
        products.insert_one(product)


        return Response("Product has been added succesfully!", status=200, mimetype='application/json')

# Delete product from collection
@app.route('/admin/deleteproduct', methods=['POST'])
def delete_product():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "_id" in data:
        return Response("Information incomplete - product id is missing",status=500,mimetype="application/json")

    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"admin"}):
        return Response("Admin only area", status=400, mimetype='application/json')
    
    objInstance = ObjectId(data["_id"])  
    product = products.find_one({"_id":objInstance})

    if product == None:
        return Response("Product ID is not correct", status=200,mimetype="application/json")

    products.delete_one({"_id":objInstance})  # Delete product from DB

    return Response("Removed product with id "+ data["_id"], status=200, mimetype='application/json')


# Update product 
@app.route('/admin/updateproduct', methods=['POST'])
def update_product():
    # Request JSON data
    data = None 
    try:
        data = json.loads(request.data)
    except Exception as e:
        return Response("bad json content",status=500,mimetype='application/json')
    if data == None:
        return Response("bad request",status=500,mimetype='application/json')
    if not "_id" in data:
        return Response("Information incomplete - product id is missing",status=500,mimetype="application/json")

    # Check if user is verified
    if not is_session_valid(request.headers.get("uuid")):
        return Response("User is not verified, please login first", status=401, mimetype='application/json')

    # Check if user is not an admin via the user_sessions dictionary
    uuid_email = users_sessions[request.headers.get("uuid")][0] # user_sessions is of format user_sessions["278-12ffd-df-34"] = [test@example.com, time]

    if not users.find_one({"email":uuid_email, "category":"admin"}):
        return Response("Admin only area", status=400, mimetype='application/json')
    
    objInstance = ObjectId(data["_id"])  
    product = products.find_one({"_id":objInstance})
    if product == None:
        return Response("Product ID is not correct", status=200,mimetype="application/json")

    if "name" in data: 
        products.update_one({'_id': objInstance}, { '$set': {'name': data["name"]} }, True)  # Update name if exists in data
    if "price" in data: 
        products.update_one({'_id': objInstance}, { '$set': {'price': data["price"]} }, True)  # Update price if exists in data
    if "description" in data: 
        products.update_one({'_id': objInstance}, { '$set': {'description': data["description"]} }, True)  # Update description if exists in data
    if "category" in data: 
        products.update_one({'_id': objInstance}, { '$set': {'category': data["category"]} }, True)  # Update category if exists in data
    if "stock" in data: 
        products.update_one({'_id': objInstance}, { '$set': {'stock': data["stock"]} }, True)  # Update category if exists in data


    product = products.find_one({"_id":objInstance}) # get updated product
    updated_product = ["Name: "+ product["name"], "Price: "+ product["price"], "Description: "+ product["description"],  "Category: "+ product["category"],  "Stock: "+ product["stock"]]
    return Response("Product "+ product["name"] + " has been updated" + "\n " + "New details: " + json.dumps(updated_product), status=200, mimetype='application/json')


# Εκτέλεση flask service σε debug mode, στην port 5000. 
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
