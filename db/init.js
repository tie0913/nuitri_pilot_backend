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
db.session.createIndex({user_id:1}, {unique:true})
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


db.allergies.insertOne({"name":"Peanuts"});
db.allergies.insertOne({"name":"Eggs"});
db.allergies.insertOne({"name":"Fish"});
db.allergies.insertOne({"name":"Gluten"});

db.allergies.createIndex({
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


db.suggestions.insertOne({
  "mark": 75,
  "feedback": {
    "level": 2,
    "explaination": "This food is moderately healthy, but it contains added sugars and sodium, which may not be ideal for your hypertension. Monitor your intake and consider alternatives."
  },
  "recommendation": [
    "Oatmeal with fruits",
    "Whole grain rice cakes",
    "Nut-free granola bars",
    "Vegetable sticks with hummus"
  ],
  "user_id": {
    "$oid": "68fd58dd220815d496c6c0fd"
  },
  "thumbnail": "data:image/webp;base64,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",
  "time": {
    "$date": "2025-11-18T23:11:26.279Z"
  }
})

db.suggestions.createIndex({
    'user_id':1,
    '_id':-1
})

db.cooldowns.insertOne({
  _id: "123:/suggestion/ask",
  start_at: new Date(),
  expire_at: new Date(Date.now() + 30000)
})

db.cooldowns.createIndex(
  { expire_at: 1 },
  { expireAfterSeconds: 0 }
)