db.createUser(
    {
        user: "flaskuser",
        pwd: "your_mongodb_password",
        roles: [
            {
                role: "readWrite",
                db: "flaskdb"
            }
        ]
    }
);
