from utils import read_video, save_video
from tracking import Tracker

def main():
    # Read the input video
    video_frame = read_video('data/input_videos/video_1.mp4')

    # Initialize the tracker
    model_path = 'models/yolov8_football_entities_v1.pt'  # Path to the YOLO model
    tracker = Tracker(model_path)
    tracks = tracker.get_object_tracks(video_frame, 
                                       read_from_stub=True, 
                                       stub_path='data/stubs/tracks_stub.pkl')

    # Draw output
    # Draw object tracks on the video frames
    output_video_frames = tracker.draw_annotations(video_frame, tracks)
    
    
    # Save the output video
    save_video(output_video_frames, 'data/output/output_video_1.avi')


if __name__ == "__main__":
    main()