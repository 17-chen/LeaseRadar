// Offline compositor: static product screenshots + explicit labels + local synthetic voice.
import Foundation
import AppKit
import AVFoundation

struct Scene: Decodable { let image:String; let audio:String; let title:String; let caption:String; let narration:String }
struct Story: Decodable { let scenes:[Scene] }
enum BuildError: Error { case invalid(String) }
let width=1920, height=1080, fps:Int32=10

func buffer(_ scene:Scene, index:Int, pool:CVPixelBufferPool) throws -> CVPixelBuffer {
    var pixel:CVPixelBuffer?
    guard CVPixelBufferPoolCreatePixelBuffer(nil,pool,&pixel)==kCVReturnSuccess, let pixel else { throw BuildError.invalid("pixel buffer") }
    CVPixelBufferLockBaseAddress(pixel,[])
    defer { CVPixelBufferUnlockBaseAddress(pixel,[]) }
    guard let ctx=CGContext(data:CVPixelBufferGetBaseAddress(pixel),width:width,height:height,bitsPerComponent:8,
        bytesPerRow:CVPixelBufferGetBytesPerRow(pixel),space:CGColorSpaceCreateDeviceRGB(),
        bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue),
        let image=NSImage(contentsOfFile:scene.image)?.cgImage(forProposedRect:nil,context:nil,hints:nil) else { throw BuildError.invalid("image") }
    ctx.setFillColor(NSColor(calibratedRed:0.96,green:0.97,blue:0.94,alpha:1).cgColor)
    ctx.fill(CGRect(x:0,y:0,width:width,height:height))
    let scale=min(1840/CGFloat(image.width),800/CGFloat(image.height))
    let w=CGFloat(image.width)*scale,h=CGFloat(image.height)*scale
    ctx.draw(image,in:CGRect(x:(1920-w)/2,y:190+(800-h)/2,width:w,height:h))
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current=NSGraphicsContext(cgContext:ctx,flipped:false)
    let ink=NSColor(calibratedRed:0.12,green:0.25,blue:0.2,alpha:1)
    func text(_ value:String,_ rect:NSRect,_ size:CGFloat,_ bold:Bool=false){
        let style=NSMutableParagraphStyle();style.lineBreakMode = .byWordWrapping
        (value as NSString).draw(in:rect,withAttributes:[.font:bold ? NSFont.boldSystemFont(ofSize:size):NSFont.systemFont(ofSize:size),.foregroundColor:ink,.paragraphStyle:style])
    }
    text("LeaseRadar 铺讯 | 合成DEMO · 静态分镜（非连续录屏）",NSRect(x:55,y:1020,width:1810,height:48),31,true)
    text(String(format:"%02d",index+1)+"  "+scene.title,NSRect(x:65,y:126,width:1790,height:50),34,true)
    text(scene.caption,NSRect(x:65,y:45,width:1790,height:75),28)
    text("本地审阅草稿 · 系统合成旁白 · 无真实外部投递或试用业绩",NSRect(x:65,y:9,width:1790,height:28),19)
    NSGraphicsContext.restoreGraphicsState()
    return pixel
}

@main struct Render {
    static func main() async throws {
        if CommandLine.arguments.count==5 && CommandLine.arguments[1]=="--mux" {
            try await mux(CommandLine.arguments[2],CommandLine.arguments[3],CommandLine.arguments[4]);return
        }
        guard CommandLine.arguments.count==3 else { throw BuildError.invalid("manifest output.mp4") }
        let manifest=URL(fileURLWithPath:CommandLine.arguments[1]),output=URL(fileURLWithPath:CommandLine.arguments[2])
        guard !FileManager.default.fileExists(atPath:output.path) else { throw BuildError.invalid("output exists") }
        let story=try JSONDecoder().decode(Story.self,from:Data(contentsOf:manifest))
        guard !story.scenes.isEmpty && story.scenes.count<=20 else {throw BuildError.invalid("scene count")}
        let silent=manifest.deletingLastPathComponent().appendingPathComponent("silent.mp4")
        let writer=try AVAssetWriter(outputURL:silent,fileType:.mp4)
        let input=AVAssetWriterInput(mediaType:.video,outputSettings:[AVVideoCodecKey:AVVideoCodecType.h264,
            AVVideoWidthKey:width,AVVideoHeightKey:height,
            AVVideoCompressionPropertiesKey:[AVVideoAverageBitRateKey:2_500_000,AVVideoMaxKeyFrameIntervalKey:20]])
        input.expectsMediaDataInRealTime=false
        let adaptor=AVAssetWriterInputPixelBufferAdaptor(assetWriterInput:input,sourcePixelBufferAttributes:[
            kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String:width,kCVPixelBufferHeightKey as String:height,
            kCVPixelBufferCGImageCompatibilityKey as String:true,kCVPixelBufferCGBitmapContextCompatibilityKey as String:true])
        writer.add(input)
        guard writer.startWriting() else {throw writer.error ?? BuildError.invalid("start writer")}
        writer.startSession(atSourceTime:.zero)
        guard let pool=adaptor.pixelBufferPool else {throw BuildError.invalid("pool")}
        var frame:Int64=0,timeline:[[String:Any]]=[],segments:[(AVURLAsset,CMTime,CMTime)]=[]
        for (i,scene) in story.scenes.enumerated(){
            let audio=AVURLAsset(url:URL(fileURLWithPath:scene.audio)),duration=try await audio.load(.duration)
            guard duration.seconds.isFinite && duration.seconds>0 && duration.seconds<=90 else {throw BuildError.invalid("audio duration")}
            let start=CMTime(value:frame,timescale:fps),frames=Int64(ceil((duration.seconds+1)*Double(fps)))
            let image=try buffer(scene,index:i,pool:pool)
            for _ in 0..<frames {
                while !input.isReadyForMoreMediaData {
                    if writer.status == .failed {throw writer.error ?? BuildError.invalid("writer failed")}
                    try await Task.sleep(nanoseconds:1_000_000)
                }
                guard adaptor.append(image,withPresentationTime:CMTime(value:frame,timescale:fps)) else {throw writer.error ?? BuildError.invalid("append frame")}
                frame+=1
            }
            segments.append((audio,start,duration))
            timeline.append(["scene":i+1,"title":scene.title,"start":start.seconds,"duration":Double(frames)/Double(fps)])
            print("scene \(i+1)/\(story.scenes.count)")
        }
        let total=CMTime(value:frame,timescale:fps)
        writer.endSession(atSourceTime:total);input.markAsFinished()
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in writer.finishWriting{c.resume()} }
        guard writer.status == .completed else {throw writer.error ?? BuildError.invalid("finish writer")}
        let composition=AVMutableComposition()
        let silentAsset=AVURLAsset(url:silent)
        let silentDuration=try await silentAsset.load(.duration)
        guard let video=composition.addMutableTrack(withMediaType:.video,preferredTrackID:kCMPersistentTrackID_Invalid),
              let voice=composition.addMutableTrack(withMediaType:.audio,preferredTrackID:kCMPersistentTrackID_Invalid),
              let source=try await silentAsset.loadTracks(withMediaType:.video).first else {throw BuildError.invalid("tracks")}
        try video.insertTimeRange(CMTimeRange(start:.zero,duration:silentDuration),of:source,at:.zero)
        for (audio,start,duration) in segments {
            guard let track=try await audio.loadTracks(withMediaType:.audio).first else {throw BuildError.invalid("audio track")}
            try voice.insertTimeRange(CMTimeRange(start:.zero,duration:duration),of:track,at:start)
        }
        guard let exporter=AVAssetExportSession(asset:composition,presetName:AVAssetExportPresetPassthrough) else {throw BuildError.invalid("export")}
        exporter.outputURL=output;exporter.outputFileType = .mp4;exporter.shouldOptimizeForNetworkUse=true
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in exporter.exportAsynchronously{c.resume()} }
        guard exporter.status == .completed else {throw exporter.error ?? BuildError.invalid("export failed")}
        let result:[String:Any]=["width":width,"height":height,"duration":total.seconds,"fps":fps,"video_codec":"H264","voice":"macOS Tingting","capture_kind":"static_ui_storyboard","timeline":timeline]
        try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:output.deletingPathExtension().appendingPathExtension("media.json"))
        print("exported \(total.seconds)s")
    }

    // Recovery keeps the original failed render and uses already encoded video/audio.
    static func mux(_ manifest:String,_ silent:String,_ output:String) async throws {
        guard !FileManager.default.fileExists(atPath:output) else {throw BuildError.invalid("output exists")}
        let story=try JSONDecoder().decode(Story.self,from:Data(contentsOf:URL(fileURLWithPath:manifest)))
        let source=AVURLAsset(url:URL(fileURLWithPath:silent)),total=try await source.load(.duration)
        let composition=AVMutableComposition()
        let video=composition.addMutableTrack(withMediaType:.video,preferredTrackID:kCMPersistentTrackID_Invalid)!
        let voice=composition.addMutableTrack(withMediaType:.audio,preferredTrackID:kCMPersistentTrackID_Invalid)!
        guard let track=try await source.loadTracks(withMediaType:.video).first else {throw BuildError.invalid("source video")}
        try video.insertTimeRange(CMTimeRange(start:.zero,duration:total),of:track,at:.zero)
        var frame:Int64=0,timeline:[[String:Any]]=[]
        for (i,scene) in story.scenes.enumerated(){
            let original=AVURLAsset(url:URL(fileURLWithPath:scene.audio))
            let duration=try await original.load(.duration),start=CMTime(value:frame,timescale:fps)
            let encoded=AVURLAsset(url:URL(fileURLWithPath:scene.audio).deletingPathExtension().appendingPathExtension("m4a"))
            guard let audio=try await encoded.loadTracks(withMediaType:.audio).first else {throw BuildError.invalid("source audio")}
            try voice.insertTimeRange(CMTimeRange(start:.zero,duration:duration),of:audio,at:start)
            let frames=Int64(ceil((duration.seconds+1)*Double(fps)))
            timeline.append(["scene":i+1,"title":scene.title,"start":start.seconds,"duration":Double(frames)/Double(fps)])
            frame+=frames
        }
        guard let exporter=AVAssetExportSession(asset:composition,presetName:AVAssetExportPresetPassthrough) else {throw BuildError.invalid("mux")}
        exporter.outputURL=URL(fileURLWithPath:output);exporter.outputFileType = .mp4;exporter.shouldOptimizeForNetworkUse=true
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in exporter.exportAsynchronously{c.resume()} }
        guard exporter.status == .completed else {throw exporter.error ?? BuildError.invalid("mux failed")}
        let result:[String:Any]=["width":width,"height":height,"duration":total.seconds,"fps":fps,"video_codec":"H264","voice":"macOS Tingting","capture_kind":"static_ui_storyboard","timeline":timeline]
        try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys]).write(to:URL(fileURLWithPath:output).deletingPathExtension().appendingPathExtension("media.json"))
        print("muxed \(total.seconds)s")
    }
}
