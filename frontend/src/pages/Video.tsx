import "./PageIndex.css"

type VideoStausProps = {
    VideoName: string
}

const Video = (props: VideoStausProps) =>{
    return(
        <div className="main">

            <div >
                <h1>
                    Learning Material
                </h1>
            </div >

            <input type="text" id="VideoID" name="VideoName" placeholder="影片連結(https://...)"/>
            <button><span>上傳影片連結</span></button>

            <div className="container">
                <div className="box">
                    {props.VideoName}
                </div>
                <div className="box">
                    {props.VideoName}
                </div>
                <div className="box">
                    {props.VideoName}
                </div>
            </div>
        </div>

    )

}
export default Video