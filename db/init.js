use('nutri_pilot');

db.sessions.insertOne({
    "user_id":ObjectId('66f4a76e9b9d9a71c7e61e0c'),
    "expire_at":new Date()
})

db.otps.insert({
    "email": "ee",
    "otp": "123456",
    "bus_id": 1,
    "expire_at": new Date()
})

db.users.insert({
    "email":"wangtie_913@outlook.com",
    "password":"123456",
    "name":"Tie",
    "status":1
})

db.sessions.createIndex({expire_at:1}, {expireAfterSeconds:0})
db.otps.createIndex({expire_at:1}, {expireAfterSeconds:0})
db.users.createIndex({email:1}, {unique:true})




db.chronics.insertOne({"name":"Hypertension"});
db.chronics.insertOne({"name":"Stroke"});
db.chronics.insertOne({"name":"Asthma"});
db.chronics.insertOne({"name":"Gout"});
db.chronics.insertOne({"name":"Obesity"});
db.chronics.insertOne({"name":"Epilepsy"});


db.chronics.createIndex({
    "name":1
}, {
    "unique":true
})


db.allergics.insertOne({"name":"Peanuts"});
db.allergics.insertOne({"name":"Eggs"});
db.allergics.insertOne({"name":"Fish"});
db.allergics.insertOne({"name":"Gluten"});

db.allergics.createIndex({
    "name":1
}, {
    "unique":true
})


db.wellness.insertOne({
    "user_id": ObjectId("68fd58dd220815d496c6c0fd"),
    "chronics":[],
    "allergies":[]
})


db.wellness.createIndex({
    "user_id":1
}, {
    "unique": true
})