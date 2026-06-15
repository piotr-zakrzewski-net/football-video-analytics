from utils import read_video, save_video
from tracking import Tracker
from team_assigner import TeamAssigner
from player_ball_assigner import PlayerBallAssigner
import cv2
import numpy as np


def main():
    # Read the input video
    video_frame = read_video('data/input_videos/video_1.mp4')

    # Initialize the tracker
    model_path = 'models/yolov8_football_entities_v1.pt'  # Path to the YOLO model
    tracker = Tracker(model_path)
    tracks = tracker.get_object_tracks(video_frame, 
                                       read_from_stub=True, 
                                       stub_path='data/stubs/tracks_stub.pkl')
    
    
    # Interpolate Ball positions 
    tracks['ball'] = tracker.interpolate_ball_positions(tracks['ball'])
    
    # Save cropped images of players
    for track_id, player in tracks['players'][0].items():
        bbox = player['bbox']
        frame = video_frame[0]  

        # Crop bbox from the frame
        cropped_image = frame[int(bbox[1]):int(bbox[3]), int(bbox[0]):int(bbox[2])]

        # Save the cropped image
        cv2.imwrite('data/output/cropped_image.jpg', cropped_image)
        break


    # Assign Player Team Colors
    team_assigner = TeamAssigner()
    team_assigner.assign_team_color(video_frame[0], tracks['players'][0])

    for frame_num, player_track in enumerate(tracks['players']):
        for player_id, track in player_track.items():
            team_id = team_assigner.get_player_team(video_frame[frame_num], track['bbox'], player_id)
            tracks['players'][frame_num][player_id]['team_id'] = team_id
            tracks['players'][frame_num][player_id]['team_color'] = team_assigner.team_colors[team_id]


    # Assign Ball Aquisition
    player_assigner = PlayerBallAssigner()
    team_ball_control = []
    for frame_num, player_track in enumerate(tracks['players']):
        ball_bbox = tracks['ball'][frame_num][1]['bbox']
        assigned_player = player_assigner.assign_ball_to_player(player_track, ball_bbox)

        if assigned_player != -1:
            tracks['players'][frame_num][assigned_player]['has_ball'] = True
            team_ball_control.append(tracks['players'][frame_num][assigned_player]['team_id'])
        else:
            team_ball_control.append(team_ball_control[-1])
    team_ball_control = np.array(team_ball_control)

    # Draw output
    # Draw object tracks on the video frames
    output_video_frames = tracker.draw_annotations(video_frame, tracks, team_ball_control)
    
    
    # Save the output video
    save_video(output_video_frames, 'data/output/output_video_1.avi')


if __name__ == "__main__":
    main()