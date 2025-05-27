'''
@user_router.get("/admins")
def list_admins(db: Session = Depends(get_db)):
    return db.query(Model_User).filter(Model_User.role == UserRole.admin).all()


@user_router.post("/register_admin")
def register_admin(user_create: UserRegister, db: Session = Depends(get_db)) -> Response:
    if db.query(Model_User).filter(Model_User.email == user_create.email).first():
        raise HTTPException(
            status_code=400, detail="An account with this email already exists"
        )

    data = create_user(db=db, user_data=user_create, role=UserRole.admin)
    print(data)
    return Response(status_code=200)
'''
