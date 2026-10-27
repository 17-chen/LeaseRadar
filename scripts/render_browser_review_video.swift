// Re-encode decoded browser frames with a disclosure bar and timed local narration.
import Foundation
import AppKit
import AVFoundation
import ImageIO

struct Segment: Decodable { let start_frame:Int; let step:String; let narration:String; let audio:String }
struct Manifest: Decodable { let frames:String; let frame_count:Int; let segments:[Segment] }
enum RenderError:Error { case invalid(String) }
let fps:Int32=10, width=1280, height=840

func pixel(_ path:String, pool:CVPixelBufferPool) throws -> CVPixelBuffer {
    var candidate:CVPixelBuffer?
    guard CVPixelBufferPoolCreatePixelBuffer(nil,pool,&candidate)==kCVReturnSuccess,
          let buffer=candidate else { throw RenderError.invalid("pixel buffer") }
    guard let source=CGImageSourceCreateWithURL(URL(fileURLWithPath:path) as CFURL,nil),
          let image=CGImageSourceCreateImageAtIndex(source,0,nil),
          image.width==1280 && image.height==800 else { throw RenderError.invalid("frame image: \(path)") }
    CVPixelBufferLockBaseAddress(buffer,[])
    defer { CVPixelBufferUnlockBaseAddress(buffer,[]) }
    guard let context=CGContext(data:CVPixelBufferGetBaseAddress(buffer),width:width,height:height,
        bitsPerComponent:8,bytesPerRow:CVPixelBufferGetBytesPerRow(buffer),
        space:CGColorSpaceCreateDeviceRGB(),bitmapInfo:CGImageAlphaInfo.premultipliedFirst.rawValue | CGBitmapInfo.byteOrder32Little.rawValue)
        else { throw RenderError.invalid("drawing context") }
    context.setFillColor(NSColor(calibratedRed:0.12,green:0.20,blue:0.18,alpha:1).cgColor)
    context.fill(CGRect(x:0,y:0,width:width,height:height))
    context.draw(image,in:CGRect(x:0,y:0,width:1280,height:800))
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current=NSGraphicsContext(cgContext:context,flipped:false)
    ("铺讯 · 合成DEMO | 自动化浏览器操作 · 系统合成旁白 · 本地审阅稿" as NSString).draw(
        in:NSRect(x:14,y:808,width:1250,height:27),withAttributes:[
            .font:NSFont.boldSystemFont(ofSize:18),.foregroundColor:NSColor.white])
    NSGraphicsContext.restoreGraphicsState()
    return buffer
}

@main struct RenderBrowserReview {
    static func main() async throws {
        guard CommandLine.arguments.count==3 else { throw RenderError.invalid("manifest output.mp4") }
        let manifestURL=URL(fileURLWithPath:CommandLine.arguments[1]),output=URL(fileURLWithPath:CommandLine.arguments[2])
        guard !FileManager.default.fileExists(atPath:output.path) else { throw RenderError.invalid("output exists") }
        let plan=try JSONDecoder().decode(Manifest.self,from:Data(contentsOf:manifestURL))
        guard (500...600).contains(plan.frame_count),plan.segments.count==8 else { throw RenderError.invalid("frame or segment count") }
        let silent=manifestURL.deletingLastPathComponent().appendingPathComponent("silent.mp4")
        guard !FileManager.default.fileExists(atPath:silent.path) else { throw RenderError.invalid("silent output exists") }
        let writer=try AVAssetWriter(outputURL:silent,fileType:.mp4)
        let input=AVAssetWriterInput(mediaType:.video,outputSettings:[
            AVVideoCodecKey:AVVideoCodecType.h264,AVVideoWidthKey:width,AVVideoHeightKey:height,
            AVVideoCompressionPropertiesKey:[AVVideoAverageBitRateKey:3_000_000,AVVideoMaxKeyFrameIntervalKey:20]])
        input.expectsMediaDataInRealTime=false
        let adaptor=AVAssetWriterInputPixelBufferAdaptor(assetWriterInput:input,sourcePixelBufferAttributes:[
            kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA,
            kCVPixelBufferWidthKey as String:width,kCVPixelBufferHeightKey as String:height,
            kCVPixelBufferCGImageCompatibilityKey as String:true,kCVPixelBufferCGBitmapContextCompatibilityKey as String:true])
        writer.add(input)
        guard writer.startWriting(),let pool=adaptor.pixelBufferPool else { throw writer.error ?? RenderError.invalid("writer start") }
        writer.startSession(atSourceTime:.zero)
        for frame in 0..<plan.frame_count {
            while !input.isReadyForMoreMediaData {
                if writer.status == .failed { throw writer.error ?? RenderError.invalid("writer failed") }
                try await Task.sleep(nanoseconds:1_000_000)
            }
            let filename=String(format:"frame-%05d.png",frame+1)
            let path=URL(fileURLWithPath:plan.frames).appendingPathComponent(filename).path
            guard adaptor.append(try pixel(path,pool:pool),withPresentationTime:CMTime(value:Int64(frame),timescale:fps))
                else { throw writer.error ?? RenderError.invalid("append \(frame)") }
        }
        let total=CMTime(value:Int64(plan.frame_count),timescale:fps)
        writer.endSession(atSourceTime:total);input.markAsFinished()
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in writer.finishWriting{c.resume()} }
        guard writer.status == .completed else { throw writer.error ?? RenderError.invalid("finish writer") }

        let composition=AVMutableComposition(),silentAsset=AVURLAsset(url:silent)
        guard let video=composition.addMutableTrack(withMediaType:.video,preferredTrackID:kCMPersistentTrackID_Invalid),
              let voice=composition.addMutableTrack(withMediaType:.audio,preferredTrackID:kCMPersistentTrackID_Invalid),
              let source=try await silentAsset.loadTracks(withMediaType:.video).first else { throw RenderError.invalid("video track") }
        try video.insertTimeRange(CMTimeRange(start:.zero,duration:total),of:source,at:.zero)
        var timeline:[[String:Any]]=[]
        for (i,segment) in plan.segments.enumerated() {
            let asset=AVURLAsset(url:URL(fileURLWithPath:segment.audio))
            let duration=try await asset.load(.duration),start=CMTime(value:Int64(segment.start_frame),timescale:fps)
            let next=i+1<plan.segments.count ? plan.segments[i+1].start_frame : plan.frame_count
            guard duration.seconds>0 && duration.seconds+0.15<=Double(next-segment.start_frame)/Double(fps),
                  let track=try await asset.loadTracks(withMediaType:.audio).first else { throw RenderError.invalid("audio timing: \(segment.step)") }
            try voice.insertTimeRange(CMTimeRange(start:.zero,duration:duration),of:track,at:start)
            timeline.append(["step":segment.step,"start":start.seconds,"audio_duration":duration.seconds])
        }
        guard let exporter=AVAssetExportSession(asset:composition,presetName:AVAssetExportPresetPassthrough) else { throw RenderError.invalid("export session") }
        exporter.outputURL=output;exporter.outputFileType = .mp4;exporter.shouldOptimizeForNetworkUse=true
        await withCheckedContinuation { (c:CheckedContinuation<Void,Never>) in exporter.exportAsynchronously{c.resume()} }
        guard exporter.status == .completed else { throw exporter.error ?? RenderError.invalid("export failed") }
        let result:[String:Any]=["width":width,"height":height,"fps":fps,"duration":total.seconds,
            "video_codec":"H264","voice":"macOS Tingting","capture_kind":"edited_automated_browser_demo", "timeline":timeline]
        let data=try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
        try data.write(to:output.deletingPathExtension().appendingPathExtension("media.json"))
        print("exported \(total.seconds)s")
    }
}
