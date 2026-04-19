import "./PageIndex.css"

type UserStausProps = {
    name: string
    email: string
    point: number
}

const Profile = (props: UserStausProps) =>{
    return(
        <div className="main">

            <div className="UserProfile">
                <h1 >
                    {props.name}
                </h1>

                <p >
                    {props.email}
                </p>
                <div className="AIPoint">
                    <span className="word"> point</span>
                    <span className="number">{props.point}</span>
                </div>
            </div>

        </div>

    )

}
export default Profile