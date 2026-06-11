from roboflow import Roboflow
import os
import shutil


def setup_dataset():
    target_dir = "data/dataset_yolo"
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir)

    print("Rozpoczynam pobieranie z Roboflow...")

    # 2. Downloading data
    rf = Roboflow(api_key="jeMdI69Kvtfu8k1QYz6s")
    project = rf.workspace("roboflow-jvuqo").project("football-players-detection-3zvbc")
    version = project.version(1)

    dataset = version.download("yolov8")

    print("\nPorządkowanie plików...")

    downloaded_folder = dataset.location

    for item in os.listdir(downloaded_folder):
        s = os.path.join(downloaded_folder, item)
        d = os.path.join(target_dir, item)
        shutil.move(s, d)

    shutil.rmtree(downloaded_folder)

    yaml_path = os.path.join(target_dir, "data.yaml")
    with open(yaml_path, "r") as file:
        lines = file.readlines()

    with open(yaml_path, "w") as file:
        for line in lines:
            if line.startswith("test:"):
                file.write("test: ../data/dataset_yolo/test/images\n")
            elif line.startswith("train:"):
                file.write("train: ../data/dataset_yolo/train/images\n")
            elif line.startswith("val:"):
                file.write("val: ../data/dataset_yolo/valid/images\n")
            else:
                file.write(line)

    print(f"\nZbiór gotowy i zoptymalizowany w: {target_dir}")


if __name__ == "__main__":
    setup_dataset()
