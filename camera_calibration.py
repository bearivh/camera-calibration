import argparse
import json
from pathlib import Path

import cv2 as cv
import numpy as np


def select_img_from_video(video_file, board_pattern, wait_msec=30):
    video = cv.VideoCapture(video_file)
    if not video.isOpened():
        raise FileNotFoundError(f"Cannot open video: {video_file}")

    selected = []
    win_name = "Auto capture chessboard - ESC: finish"
    cv.namedWindow(win_name, cv.WINDOW_NORMAL)

    last_center = None
    min_center_dist = 40.0

    while True:
        valid, img = video.read()
        if not valid:
            break

        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        complete, pts = cv.findChessboardCorners(gray, board_pattern)

        view = img.copy()
        status = "NOT DETECTED"
        color = (0, 0, 255)

        if complete:
            pts = cv.cornerSubPix(
                gray,
                pts,
                (11, 11),
                (-1, -1),
                (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001),
            )

            cv.drawChessboardCorners(view, board_pattern, pts, complete)

            center = pts.reshape(-1, 2).mean(axis=0)

            should_save = False
            if last_center is None:
                should_save = True
            else:
                dist = np.linalg.norm(center - last_center)
                if dist > min_center_dist:
                    should_save = True

            if should_save:
                selected.append(img.copy())
                last_center = center
                print(f"Auto saved image: {len(selected)}")

            status = "DETECTED"
            color = (0, 255, 0)

        cv.putText(view, status, (20, 40), cv.FONT_HERSHEY_SIMPLEX, 1, color, 2)
        cv.putText(view, f"Saved: {len(selected)}", (20, 80), cv.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)

        max_w, max_h = 1200, 800
        h, w = view.shape[:2]
        scale = min(max_w / w, max_h / h, 1.0)
        display = cv.resize(view, None, fx=scale, fy=scale)

        cv.imshow(win_name, display)
        key = cv.waitKey(wait_msec) & 0xFF

        if key == 27:  # ESC
            break

    video.release()
    cv.destroyAllWindows()

    if len(selected) == 0:
        raise RuntimeError("No chessboard images were selected.")

    return selected


def calib_camera_from_chessboard(images, board_pattern, board_cellsize):
    img_points = []
    gray = None

    for img in images:
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)
        complete, pts = cv.findChessboardCorners(gray, board_pattern)

        if complete:
            pts = cv.cornerSubPix(
                gray,
                pts,
                (11, 11),
                (-1, -1),
                (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001),
            )
            img_points.append(pts)

    if len(img_points) == 0:
        raise RuntimeError("There is no set of complete chessboard points!")

    obj_pts = [[c, r, 0] for r in range(board_pattern[1]) for c in range(board_pattern[0])]
    obj_points = [np.array(obj_pts, dtype=np.float32) * board_cellsize for _ in range(len(img_points))]

    rms, K, dist_coeff, rvecs, tvecs = cv.calibrateCamera(
        obj_points,
        img_points,
        gray.shape[::-1],
        None,
        None,
    )

    return rms, K, dist_coeff, rvecs, tvecs, gray.shape[::-1]


def save_calibration_result(output_dir, rms, K, dist_coeff, image_size, num_images):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "image_width": int(image_size[0]),
        "image_height": int(image_size[1]),
        "num_images": int(num_images),
        "rms": float(rms),
        "fx": float(K[0, 0]),
        "fy": float(K[1, 1]),
        "cx": float(K[0, 2]),
        "cy": float(K[1, 2]),
        "camera_matrix": K.tolist(),
        "dist_coeff": dist_coeff.reshape(-1).tolist(),
    }

    with open(output_dir / "calibration_result.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)


def save_demo_images(images, K, dist_coeff, output_dir):
    output_dir = Path(output_dir)
    demo_dir = output_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)

    for i, img in enumerate(images[:2]):
        undist = cv.undistort(img, K, dist_coeff)
        side = np.hstack([img, undist])

        cv.putText(side, "Original", (20, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv.putText(side, "Rectified", (img.shape[1] + 20, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        cv.imwrite(str(demo_dir / f"demo_{i}.png"), side)


def save_demo_video(video_file, K, dist_coeff, output_path):
    video = cv.VideoCapture(video_file)
    if not video.isOpened():
        return

    fps = video.get(cv.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30

    valid, img = video.read()
    if not valid:
        video.release()
        return

    undist = cv.undistort(img, K, dist_coeff)
    side = np.hstack([img, undist])
    h, w = side.shape[:2]

    writer = cv.VideoWriter(
        str(output_path),
        cv.VideoWriter_fourcc(*"mp4v"),
        fps,
        (w, h),
    )

    while valid:
        undist = cv.undistort(img, K, dist_coeff)
        side = np.hstack([img, undist])

        cv.putText(side, "Original", (20, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv.putText(side, "Rectified", (img.shape[1] + 20, 30), cv.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        writer.write(side)
        valid, img = video.read()

    writer.release()
    video.release()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True, help="chessboard video path")
    parser.add_argument("--pattern-cols", type=int, default=7, help="number of inner corners in width")
    parser.add_argument("--pattern-rows", type=int, default=6, help="number of inner corners in height")
    parser.add_argument("--cell-size", type=float, default=0.025, help="size of one chessboard cell")
    parser.add_argument("--output-dir", default="output")
    args = parser.parse_args()

    board_pattern = (args.pattern_cols, args.pattern_rows)

    images = select_img_from_video(args.video, board_pattern)
    rms, K, dist_coeff, rvecs, tvecs, image_size = calib_camera_from_chessboard(
        images,
        board_pattern,
        args.cell_size,
    )

    save_calibration_result(args.output_dir, rms, K, dist_coeff, image_size, len(images))
    save_demo_images(images, K, dist_coeff, args.output_dir)
    save_demo_video(args.video, K, dist_coeff, Path(args.output_dir) / "rectified_demo.mp4")

    print("\n## Camera Calibration Results")
    print(f"* The number of applied images = {len(images)}")
    print(f"* RMS error = {rms:.6f}")
    print("* Camera matrix (K) =")
    for row in K:
        print(row.tolist())
    print("* Distortion coefficient (k1, k2, p1, p2, k3, ...) =")
    print(dist_coeff.reshape(-1).tolist())
    print(f"* fx = {K[0, 0]:.6f}")
    print(f"* fy = {K[1, 1]:.6f}")
    print(f"* cx = {K[0, 2]:.6f}")
    print(f"* cy = {K[1, 2]:.6f}")
    print(f"\nSaved to: {Path(args.output_dir).resolve()}")


if __name__ == "__main__":
    main()