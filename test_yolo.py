from ultralytics import YOLO

model = YOLO("models/yolov8_football_entities_v1.pt")
results = model("data/input/video_1.mp4", conf=0.25, save=True, save_txt=True, save_conf=True)
print(results[0])
print("------------------------------")
for box in results[0].boxes:
    print(box)
    