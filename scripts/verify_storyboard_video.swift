// Decode the entire movie, check timing/audio, and export scene previews for visual review.
import Foundation
import AppKit
import AVFoundation

enum VerificationError:Error {case invalid(String)}
@main struct VerifyVideo {
    static func main() async throws {
        guard CommandLine.arguments.count==3 else {throw VerificationError.invalid("movie preview-directory")}
        let url=URL(fileURLWithPath:CommandLine.arguments[1]),directory=URL(fileURLWithPath:CommandLine.arguments[2])
        try FileManager.default.createDirectory(at:directory,withIntermediateDirectories:true)
        let asset=AVURLAsset(url:url),duration=try await asset.load(.duration)
        guard let video=try await asset.loadTracks(withMediaType:.video).first,
              let audio=try await asset.loadTracks(withMediaType:.audio).first else {throw VerificationError.invalid("missing track")}
        let dimensions=try await video.load(.naturalSize),rate=try await video.load(.nominalFrameRate)
        let media=url.deletingPathExtension().appendingPathExtension("media.json")
        let metadata=try JSONSerialization.jsonObject(with:Data(contentsOf:media)) as! [String:Any]
        let kind=metadata["capture_kind"] as? String
        let shortBrowser=kind == "edited_automated_browser_demo"
        let fullBrowser=kind == "edited_full_automated_browser_demo"
        let valid=shortBrowser
            ? (duration.seconds>=50 && duration.seconds<=60 && dimensions.width==1280 && dimensions.height==840)
            : fullBrowser
            ? (duration.seconds>=200 && duration.seconds<=220 && dimensions.width==1280 && dimensions.height==840)
            : (duration.seconds>60 && duration.seconds<600 && dimensions.width==1920 && dimensions.height==1080)
        guard valid else {throw VerificationError.invalid("duration or dimensions")}
        let reader=try AVAssetReader(asset:asset)
        let frames=AVAssetReaderTrackOutput(track:video,outputSettings:[kCVPixelBufferPixelFormatTypeKey as String:kCVPixelFormatType_32BGRA])
        reader.add(frames);guard reader.startReading() else {throw reader.error ?? VerificationError.invalid("read video")}
        var count=0,last=CMTime.negativeInfinity
        while let sample=frames.copyNextSampleBuffer(){
            let time=CMSampleBufferGetPresentationTimeStamp(sample)
            guard time>=last && CMSampleBufferGetImageBuffer(sample) != nil else {throw VerificationError.invalid("video frame order")}
            last=time;count+=1
        }
        guard reader.status == .completed && (shortBrowser ? (500...600).contains(count) : fullBrowser ? (2000...2200).contains(count) : count>1000)
            else {throw reader.error ?? VerificationError.invalid("video incomplete")}
        let sounds=try AVAssetReader(asset:asset)
        let pcm=AVAssetReaderTrackOutput(track:audio,outputSettings:[AVFormatIDKey:kAudioFormatLinearPCM,
            AVLinearPCMIsFloatKey:true,AVLinearPCMBitDepthKey:32,AVLinearPCMIsNonInterleaved:false])
        sounds.add(pcm);guard sounds.startReading() else {throw sounds.error ?? VerificationError.invalid("read audio")}
        var peak:Float=0,audioBuffers=0
        while let sample=pcm.copyNextSampleBuffer(){
            guard let block=CMSampleBufferGetDataBuffer(sample) else {continue}
            var data=Data(count:CMBlockBufferGetDataLength(block))
            let code=data.withUnsafeMutableBytes{CMBlockBufferCopyDataBytes(block,atOffset:0,dataLength:$0.count,destination:$0.baseAddress!)}
            guard code==kCMBlockBufferNoErr else {throw VerificationError.invalid("audio buffer")}
            data.withUnsafeBytes{bytes in for value in bytes.bindMemory(to:Float.self){peak=max(peak,abs(value))}}
            audioBuffers+=1
        }
        guard sounds.status == .completed && peak>0.01 else {throw sounds.error ?? VerificationError.invalid("silent audio")}
        let timeline=metadata["timeline"] as! [[String:Any]]
        let generator=AVAssetImageGenerator(asset:asset);generator.appliesPreferredTrackTransform=true
        generator.requestedTimeToleranceBefore = .zero;generator.requestedTimeToleranceAfter = .zero
        for (i,scene) in timeline.enumerated(){
            let time=(scene["start"] as! Double)+1
            let cg=try generator.copyCGImage(at:CMTime(seconds:time,preferredTimescale:600),actualTime:nil)
            let png=NSBitmapImageRep(cgImage:cg).representation(using:.png,properties:[:])!
            try png.write(to:directory.appendingPathComponent(String(format:"scene-%02d.png",i+1)))
        }
        let result:[String:Any]=["duration":duration.seconds,"width":dimensions.width,"height":dimensions.height,
            "nominal_fps":rate,"decoded_video_frames":count,"decoded_audio_buffers":audioBuffers,
            "audio_peak":peak,"scene_previews":timeline.count,"full_decode":"passed","human_listening_review":false]
        let json=try JSONSerialization.data(withJSONObject:result,options:[.prettyPrinted,.sortedKeys])
        try json.write(to:directory.appendingPathComponent("decode-proof.json"));print(String(data:json,encoding:.utf8)!)
    }
}
