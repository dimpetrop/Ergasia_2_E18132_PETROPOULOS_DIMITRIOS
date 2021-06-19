# Ergasia_2_E18132_PETROPOULOS_DIMITRIOS

## Installation
Python Flask 1.1.2 is a requirement
Docker and MongoCompass are also required

MongoDB must run on port 27017

All API requests are send via Postman by requesting on port 5000 (Flask port)


## Registering a user (/register)

For a user to register, the below information in the post request is mandatory:
1. Email
2. Name
3. Password
4. Category

There is a check on whether the category value is admin or user. This is in caps so that it accepts all values
After that, the app is checking the database for the email, if the email exists the corresponding response goes out. In other case, the program will also check if the user's category is admin or user. If it is user, then we need the orderHistory entry as well, if they are an admin, we don't.

## Logging in (/login)

For a user to login, the below information in the post request is mandatory:
1. Email
2. Password

There is a check for the email (if exists) and after that, another check against the password. When they login, the app will create a UUID which is stored in a dictionary of uuids of the format `dictionary[uuid] = [email, time]`. All other get and post requests, require that UUID to be sent within the headers of the request.

## Searching for a product (/searchproduct)
To search a product, the user must be logged in (uuid must be in the headers of the request)

There is a check against the dictionary and after a check against the search method. 
The priority of the search is as follows: Name, Category, ID

In the category search, there is an initialization of a for loop which will loop through the dictionary of items that were returned from the `find()` function. 
`product_matching` variable is a multi-dimensional array of format `[[name, price, description, category, stock], [name, price, description, cateogory, stock]]`. That so json dumping is easier. The sorting is done using the built-in sorted function and is from the most expensive to the least expensive. I use the the price as the lambda key `x[1]`

Searching using an id was tricky, I had to type cast the id to an `ObjectId`, but that was simple after a point.

## Adding product to cart (/addtocart)
The below data is mandatory:
1. id
From now on, there won't be a mention on authentication as it is the same for every function. The app checks the headers against the uuid dictionary.

Admins can not have carts, and therefore we check for that. As we are looking into adding products using IDs we need to typecast them again into an `ObjectId`. There is a check if the id is correct (exists in the collection of products).

After that, we need to check if the user has a cart, if not we need to give them an empty cart `{"cart": []}`. Once that is done, we need to grab the user again (cause there might have been an update cause of the above check) and get their cart (all existing products). Remind you, that the cart entry is an `Array` entry, therefore iteration is simple. 

Once we get the `user_cart` array with all the already existing products, we will append the new product and then `update_one()` the database.

## Show cart products (/showcart)

Again, admins can not have cards. 

We also check if the user had a cart. If they don't, message is thrown. They will need to `/addcart`.

In the `else` section, what we do is getting all IDs existing in the cart of the user and adding them in an array `prid_in_cart` (product ids in cart) and then running a second loop which will fill the `product_full` array with all information about the product. There is a check against each id using `find_one()` and the result is appended. 

There is also a check on whether the product_full is empty, if it is then the appropriate message is shown, if not then the cart is shown

## Delete Cart Product (/deletecartitem)
The below data is mandatory:
1. id
Logic is the same, with the difference that the product ids in the cart are kept so that they can be checked against the `data["_id"]` and simillary the `product_full` array is filled with products that exist.

Before the products are shown, and on the `else` case on the check on whether the ID exists, the product with id `data["_id"]` is removed using the `array.remove()` function. That makes sense, as the `update_one()` basically rewrites the whole `cart` entry with the `prid_in_cart` array. If the `data["_id"]` is not included, then it is also removed from the collection entry.

## Buy Products (/purchase)
Same logic. The difference though is that there is a check against the product's stock which if it is not enough will throw the appropriate response. 
(please find comments on code which explain stuff better).

Worth to mention that the cart is set to `{"cart": []}` (empty) and that `{"orderHistory": }` is filled with the ids of the cart. That is done via iterating through the `{"orderHistory": }` entry and `prid_in_cart` array and appending their values together then writing them on `update_one()` 

## Show Purchases (/showpurchases)
Same logic, but now check is against the orderHistory.
(please find comments on code which explain stuff better).

## Delete User (/deleteuser)
Admins can not access this. Simple checks for email existance and then deletion using the `delete_one()` based on email. 

Worths to mention that the uuid of the user (the one gotten during /login) is also removed from the dictionary of uuids.

## Add Product as Admin (/admin/addproduct)
The below data is mandatory:
1. Name
2. Price
3. Description
4. Category
5. Stock

Before anything, there is a check for the price and stock price. They need to be a number and nothing else. The app will `try... except` to typecase to float. If there is an error then it is not a number and therefore the appropriate response will be sent.

After that check, the app will check if the user is verified (using the UUIDs from /login) and check if they are an admin. If all is good, then the product is added.

## Delete Product from Collection (/admin/deleteproduct)
The below data is mandatory:
1. id

The app will check if the user is verified (using the UUIDs from /login) and check if they are an admin. If all is good, there will be a typecast for the `_id` and check against the collection if the id exists. If not the appropriate response throws, else the product is deleted using the `delete_one()` function.

## Update Product (/admin/updateproduct)
The below data is mandatory:
1. id


The app will check if the user is verified (using the UUIDs from /login) and check if they are an admin. If all is good, there will be a typecast for the `_id` and check against the collection if the id exists. If not the appropriate response throws, else the app will start updating each value based on the request. If for example there is `name` and `description` on the request, then these values will be updated on the mongodb entry.

Once they are updated, the app will fetch the product again and show the updated values.
