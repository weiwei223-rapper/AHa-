import "./PageIndex.css"

type UserStausProps = {
    name: string
}

const Home = (props: UserStausProps) =>{
    return(
        <div className="main">

            <div className="Welcome">
                <h1>
                    Welcome Back, {props.name}!
                </h1>
            </div>
            <div className="container">
                <div className="box">
                    學習影片
                </div>
                <div className="box">
                    剩餘點數
                </div>
                <div className="box">
                    完成測驗
                </div>
                <div className="box">
                    平均正確率
                </div>
            </div>
        </div>

    )

}
export default Home