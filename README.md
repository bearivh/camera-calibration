# Camera Calibration and Distortion Correction

## 1. 개요
본 과제에서는 체스보드 패턴을 이용하여 카메라 캘리브레이션을 수행하고,  
추정된 파라미터를 이용하여 렌즈 왜곡을 보정한다.

목표는 다음과 같다:
- 카메라의 내부 파라미터(intrinsic parameters) 추정
- 렌즈 왜곡(distortion) 보정

---

## 2. Camera Calibration

### 사용 데이터
- 체스보드 영상: `fisheye.mp4`
- 사용 이미지 수: 7장
- 체스보드 패턴: 7 x 6 (inner corners 기준)

### 캘리브레이션 결과

- RMS error: 0.480710

#### Camera Matrix (K)

[1304.392481298388, 0.0, 533.6295374571994]
[0.0, 1299.298948418596, 957.7615551937473]
[0.0, 0.0, 1.0]


#### 파라미터
- fx = 1304.392481  
- fy = 1299.298948  
- cx = 533.629537  
- cy = 957.761555  

#### Distortion Coefficients

[-0.39981007497361726, -0.15985671371662705,
0.0004338340944151208, 0.005150458015154583,
-0.31001729575769105]


---

## 3. 왜곡 보정 (Distortion Correction)

캘리브레이션으로 얻은 파라미터를 이용하여 OpenCV의 `cv.undistort()`를 사용해  
렌즈 왜곡을 보정하였다.

### 결과 비교

| Original | Rectified |
|----------|-----------|
| ![](demo_0_original.png) | ![](demo_0_rectified.png) |


